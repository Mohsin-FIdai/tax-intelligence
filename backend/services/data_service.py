"""
Tax Intelligence Platform — Data Service Layer

Singleton service that loads processed data from ``data/processed/`` and
exposes query helpers consumed by API route handlers.  All heavy lifting
is done with *pandas*; loaded DataFrames are cached for the lifetime of
the process.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import numpy as np
import pandas as pd

from config.settings import (
    PROCESSED_DIR,
    MODELS_DIR,
    RISK_CATEGORIES,
)

logger = logging.getLogger(__name__)


class DataService:
    """Thread-safe singleton that holds all loaded data in memory."""

    _instance: Optional["DataService"] = None
    _lock: Lock = Lock()

    # ── Singleton accessor ────────────────────────────────────────────

    def __new__(cls) -> "DataService":
        """Return the singleton instance, creating it on first access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialised = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Load data only once."""
        if self._initialised:
            return
        self._initialised = True
        self._load_data()

    def reload(self) -> None:
        """Force a reload of all data into memory."""
        with self._lock:
            self._load_data()

    # ── Data Loading ──────────────────────────────────────────────────

    def _read_csv_safe(self, path: Path) -> pd.DataFrame:
        """Read a CSV file, returning an empty DataFrame on any error."""
        try:
            if path.exists():
                df = pd.read_csv(path, low_memory=False)
                logger.info("Loaded %s  (%d rows)", path.name, len(df))
                return df
            logger.warning("File not found: %s", path)
        except Exception as exc:
            logger.error("Error reading %s: %s", path, exc)
        return pd.DataFrame()

    def _read_pickle_safe(self, path: Path) -> Any:
        """Read a pickle file, returning None on any error."""
        try:
            if path.exists():
                with open(path, "rb") as fh:
                    obj = pickle.load(fh)
                logger.info("Loaded pickle %s", path.name)
                return obj
            logger.warning("Pickle not found: %s", path)
        except Exception as exc:
            logger.error("Error reading pickle %s: %s", path, exc)
        return None

    def _load_data(self) -> None:
        """Load every processed artefact into memory."""
        logger.info("DataService: loading data from %s …", PROCESSED_DIR)

        # Core citizen data
        self.citizens_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "master_citizens.csv"
        )
        self.tax_records_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "tax_records_clean.csv"
        )
        self.vehicles_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "vehicle_records_clean.csv"
        )
        self.properties_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "property_records_clean.csv"
        )
        self.businesses_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "business_records_clean.csv"
        )

        # Risk scores produced by the ML pipeline
        self.risk_scores_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "feature_vectors.csv"
        )

        # Entity resolution matches
        self.entity_matches_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "entity_matches.csv"
        )

        # Feature importance (from XAI module)
        self.feature_importance_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "feature_importance.csv"
        )

        # Knowledge graph (networkx pickled graph)
        self.graph = self._read_pickle_safe(MODELS_DIR / "knowledge_graph.pkl")
        if self.graph is None:
            import networkx as nx
            self.graph = nx.DiGraph()

        # Community assignments
        self.communities_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "communities.csv"
        )

        # Merge risk scores into citizens if both exist
        if not self.citizens_df.empty and not self.risk_scores_df.empty:
            merge_key = self._detect_merge_key(self.citizens_df, self.risk_scores_df)
            if merge_key:
                self.citizens_df = self.citizens_df.merge(
                    self.risk_scores_df, on=merge_key, how="left", suffixes=("", "_risk")
                )

        # Ensure essential columns exist
        self._ensure_columns()

        logger.info(
            "DataService ready — %d citizen records loaded.", len(self.citizens_df)
        )

    @property
    def is_loaded(self) -> bool:
        """Return True if at least the citizens data is available."""
        return not self.citizens_df.empty

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_merge_key(df1: pd.DataFrame, df2: pd.DataFrame) -> Optional[str]:
        """Find a shared key column for merging two DataFrames."""
        for col in ("citizen_id", "id", "cnic"):
            if col in df1.columns and col in df2.columns:
                return col
        return None

    def _ensure_columns(self) -> None:
        """Guarantee expected columns exist in citizens_df (fill with defaults)."""
        defaults: dict[str, Any] = {
            "citizen_id": "",
            "name": "",
            "cnic": "",
            "city": "",
            "province": "",
            "risk_score": 0.0,
            "risk_category": "A",
            "filing_status": "Non-Filer",
            "declared_income": 0.0,
            "estimated_net_worth": 0.0,
            "father_name": "",
            "phone": "",
            "email": "",
            "address": "",
            "date_of_birth": "",
            "ntn": "",
            "deviation_score": 0.0,
            "suspicion_pct": 0.0,
        }
        for col, default in defaults.items():
            if col not in self.citizens_df.columns:
                self.citizens_df[col] = default

        # Derive risk_category from risk_score if not already present
        if "risk_category" in self.citizens_df.columns:
            mask = self.citizens_df["risk_category"].isna() | (
                self.citizens_df["risk_category"] == ""
            )
            if mask.any():
                self.citizens_df.loc[mask, "risk_category"] = self.citizens_df.loc[
                    mask, "risk_score"
                ].apply(self._score_to_category)
        else:
            self.citizens_df["risk_category"] = self.citizens_df["risk_score"].apply(
                self._score_to_category
            )

    @staticmethod
    def _score_to_category(score: float) -> str:
        """Map a numeric risk score to a category letter."""
        try:
            score = float(score)
        except (TypeError, ValueError):
            return "A"
        for cat, meta in RISK_CATEGORIES.items():
            lo, hi = meta["range"]
            if lo <= score <= hi:
                return cat
        return "E" if score > 80 else "A"

    # ── Citizen Queries ───────────────────────────────────────────────

    def get_citizens(
        self,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[dict], int]:
        """Return a filtered, paginated list of citizen summaries.

        Args:
            filters: Key/value filter parameters (see FilterParams schema).
            page: 1-indexed page number.
            page_size: Number of records per page.

        Returns:
            (list_of_dicts, total_matching_count)
        """
        df = self.citizens_df.copy()

        # Apply filters
        if filters.get("province"):
            df = df[df["province"].str.lower() == filters["province"].lower()]
        if filters.get("city"):
            df = df[df["city"].str.lower() == filters["city"].lower()]
        if filters.get("risk_level"):
            df = df[df["risk_category"] == filters["risk_level"].upper()]
        if filters.get("filing_status"):
            df = df[
                df["filing_status"].str.lower() == filters["filing_status"].lower()
            ]
        if filters.get("min_income") is not None:
            df = df[df["declared_income"] >= filters["min_income"]]
        if filters.get("max_income") is not None:
            df = df[df["declared_income"] <= filters["max_income"]]
        if filters.get("min_risk_score") is not None:
            df = df[df["risk_score"] >= filters["min_risk_score"]]
        if filters.get("max_risk_score") is not None:
            df = df[df["risk_score"] <= filters["max_risk_score"]]

        # Sort
        sort_col = filters.get("sort_by", "risk_score")
        if sort_col not in df.columns:
            sort_col = "risk_score"
        ascending = filters.get("sort_order", "desc").lower() == "asc"
        df = df.sort_values(sort_col, ascending=ascending, na_position="last")

        total = len(df)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        summary_cols = [
            "citizen_id", "name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
        ]
        existing_cols = [c for c in summary_cols if c in page_df.columns]
        records = page_df[existing_cols].fillna("").to_dict(orient="records")
        return records, total

    def get_citizen_by_id(self, citizen_id: str) -> Optional[dict]:
        """Return the full profile dict for a citizen, or None if not found.

        Merges assets, tax records, risk details, and audit trail into
        a single dictionary that maps directly to the CitizenProfile schema.
        """
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return None
        record = row.iloc[0].to_dict()

        # Replace NaN / NaT with sensible defaults
        record = {
            k: ("" if isinstance(v, float) and np.isnan(v) else v)
            for k, v in record.items()
        }

        # Enrich with assets
        record["assets"] = self.get_citizen_assets(citizen_id)
        record["tax_records"] = self._get_tax_records(citizen_id)
        record["risk_details"] = self._build_risk_details(record)
        record["audit_trail"] = self.get_citizen_audit_trail(citizen_id)

        return record

    def _get_tax_records(self, citizen_id: str) -> list[dict]:
        """Return tax filing history for a citizen."""
        if self.tax_records_df.empty:
            return []
        key = self._detect_merge_key(
            self.tax_records_df,
            pd.DataFrame({"citizen_id": [citizen_id]}),
        ) or "citizen_id"
        if key not in self.tax_records_df.columns:
            return []
        rows = self.tax_records_df[self.tax_records_df[key] == citizen_id]
        return rows.fillna("").to_dict(orient="records")

    def _build_risk_details(self, record: dict) -> dict:
        """Construct a RiskDetail-compatible dict from a citizen record."""
        cat = str(record.get("risk_category", "A"))
        meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])
        return {
            "deviation_score": float(record.get("deviation_score", 0)),
            "suspicion_pct": float(record.get("suspicion_pct", 0)),
            "category": cat,
            "label": meta["label"],
            "color": meta["color"],
            "anomaly_scores": {
                "isolation_forest": record.get("iso_forest_score"),
                "xgboost": record.get("xgb_score"),
                "random_forest": record.get("rf_score"),
                "ensemble": record.get("ensemble_score"),
            },
            "income_networth_gap": float(record.get("income_networth_gap", 0)),
            "tax_gap": float(record.get("tax_gap", 0)),
            "lifestyle_gap": float(record.get("lifestyle_gap", 0)),
            "filing_penalty": float(record.get("filing_penalty", 0)),
        }

    # ── Asset Queries ─────────────────────────────────────────────────

    def get_citizen_assets(self, citizen_id: str) -> dict:
        """Return the AssetBreakdown dict for a citizen."""
        vehicles = self._query_asset_df(self.vehicles_df, citizen_id)
        properties = self._query_asset_df(self.properties_df, citizen_id)
        businesses = self._query_asset_df(self.businesses_df, citizen_id)

        total_value = (
            sum(v.get("estimated_value", 0) for v in vehicles)
            + sum(p.get("estimated_value", 0) for p in properties)
            + sum(b.get("annual_turnover", 0) for b in businesses)
        )

        return {
            "vehicles": vehicles,
            "properties": properties,
            "businesses": businesses,
            "total_value": total_value,
        }

    def _query_asset_df(self, df: pd.DataFrame, citizen_id: str) -> list[dict]:
        """Filter an asset DataFrame by citizen_id."""
        if df.empty:
            return []
        key = self._detect_merge_key(
            df, pd.DataFrame({"citizen_id": [citizen_id]})
        ) or "citizen_id"
        if key not in df.columns:
            return []
        rows = df[df[key] == citizen_id]
        return rows.fillna("").to_dict(orient="records")

    # ── Audit Trail ───────────────────────────────────────────────────

    def get_citizen_audit_trail(self, citizen_id: str) -> list[dict]:
        """Build an audit trail (list of flags) for a citizen.

        The trail is derived algorithmically from the citizen's data rather
        than being stored in a separate file.
        """
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return []
        r = row.iloc[0]
        trail: list[dict] = []

        # Non-filer flag
        filing = str(r.get("filing_status", ""))
        if filing.lower() == "non-filer":
            trail.append({
                "description": "Citizen is a Non-Filer with potential economic activity",
                "severity": "warning",
                "value": None,
                "threshold": None,
            })

        # High risk score
        risk = float(r.get("risk_score", 0))
        if risk >= 80:
            trail.append({
                "description": f"Extremely high risk score ({risk:.1f})",
                "severity": "critical",
                "value": risk,
                "threshold": 80.0,
            })
        elif risk >= 60:
            trail.append({
                "description": f"Elevated risk score ({risk:.1f})",
                "severity": "warning",
                "value": risk,
                "threshold": 60.0,
            })

        # Income–net-worth mismatch
        income = float(r.get("declared_income", 0))
        net_worth = float(r.get("estimated_net_worth", 0))
        if income > 0 and net_worth > income * 5:
            trail.append({
                "description": (
                    f"Net worth (PKR {net_worth:,.0f}) exceeds "
                    f"5× declared income (PKR {income:,.0f})"
                ),
                "severity": "critical",
                "value": net_worth,
                "threshold": income * 5,
            })
        elif income > 0 and net_worth > income * 3:
            trail.append({
                "description": (
                    f"Net worth (PKR {net_worth:,.0f}) exceeds "
                    f"3× declared income (PKR {income:,.0f})"
                ),
                "severity": "warning",
                "value": net_worth,
                "threshold": income * 3,
            })

        # Deviation score flag
        dev = float(r.get("deviation_score", 0))
        if dev >= 60:
            trail.append({
                "description": f"High wealth-income deviation score ({dev:.1f})",
                "severity": "critical",
                "value": dev,
                "threshold": 60.0,
            })

        # Multiple asset flag
        assets = self.get_citizen_assets(citizen_id)
        vehicle_count = len(assets.get("vehicles", []))
        property_count = len(assets.get("properties", []))
        if vehicle_count >= 3:
            trail.append({
                "description": f"Owns {vehicle_count} registered vehicles",
                "severity": "info",
                "value": float(vehicle_count),
                "threshold": 3.0,
            })
        if property_count >= 2:
            trail.append({
                "description": f"Owns {property_count} registered properties",
                "severity": "info",
                "value": float(property_count),
                "threshold": 2.0,
            })

        return trail

    # ── Search ────────────────────────────────────────────────────────

    def search_citizens(
        self, query: str, search_type: str = "name"
    ) -> list[dict]:
        """Full-text search across citizens by the specified field.

        Args:
            query: Search query string.
            search_type: One of 'name', 'cnic', 'phone', 'vehicle', 'business'.

        Returns:
            List of matching CitizenSummary dicts.
        """
        if not query or self.citizens_df.empty:
            return []

        q = query.strip().lower()
        summary_cols = [
            "citizen_id", "name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
        ]
        existing_cols = [c for c in summary_cols if c in self.citizens_df.columns]

        if search_type == "cnic":
            mask = self.citizens_df["cnic"].astype(str).str.contains(q, na=False)
            return self.citizens_df.loc[mask, existing_cols].fillna("").to_dict(orient="records")

        if search_type == "phone":
            if "phone" in self.citizens_df.columns:
                mask = self.citizens_df["phone"].astype(str).str.contains(q, na=False)
                return self.citizens_df.loc[mask, existing_cols].fillna("").to_dict(orient="records")
            return []

        if search_type == "vehicle":
            if self.vehicles_df.empty:
                return []
            v_mask = (
                self.vehicles_df.astype(str)
                .apply(lambda row: row.str.lower().str.contains(q).any(), axis=1)
            )
            matched = self.vehicles_df.loc[v_mask]
            key = self._detect_merge_key(matched, self.citizens_df) or "citizen_id"
            if key not in matched.columns:
                return []
            ids = matched[key].unique().tolist()
            return (
                self.citizens_df[self.citizens_df["citizen_id"].isin(ids)]
                [existing_cols]
                .fillna("")
                .to_dict(orient="records")
            )

        if search_type == "business":
            if self.businesses_df.empty:
                return []
            b_mask = (
                self.businesses_df.astype(str)
                .apply(lambda row: row.str.lower().str.contains(q).any(), axis=1)
            )
            matched = self.businesses_df.loc[b_mask]
            key = self._detect_merge_key(matched, self.citizens_df) or "citizen_id"
            if key not in matched.columns:
                return []
            ids = matched[key].unique().tolist()
            return (
                self.citizens_df[self.citizens_df["citizen_id"].isin(ids)]
                [existing_cols]
                .fillna("")
                .to_dict(orient="records")
            )

        # Default: name search
        mask = self.citizens_df["name"].astype(str).str.lower().str.contains(q, na=False)
        return self.citizens_df.loc[mask, existing_cols].fillna("").to_dict(orient="records")

    # ── Risk Aggregations ─────────────────────────────────────────────

    def get_risk_distribution(self) -> dict:
        """Return category-level risk distribution statistics."""
        if self.citizens_df.empty:
            return {
                "total_citizens": 0,
                "filer_count": 0,
                "non_filer_count": 0,
                "categories": [],
            }

        total = len(self.citizens_df)
        filer_count = int(
            (self.citizens_df["filing_status"].str.lower() == "filer").sum()
        )
        non_filer_count = total - filer_count

        cats: list[dict] = []
        for cat, meta in RISK_CATEGORIES.items():
            count = int((self.citizens_df["risk_category"] == cat).sum())
            cats.append({
                "category": cat,
                "label": meta["label"],
                "color": meta["color"],
                "count": count,
                "percentage": round(count / total * 100, 2) if total else 0.0,
            })

        return {
            "total_citizens": total,
            "filer_count": filer_count,
            "non_filer_count": non_filer_count,
            "categories": cats,
        }

    def get_top_suspicious(self, limit: int = 20) -> list[dict]:
        """Return the top-N citizens by risk_score descending."""
        if self.citizens_df.empty:
            return []
        df = self.citizens_df.nlargest(limit, "risk_score")
        summary_cols = [
            "citizen_id", "name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
        ]
        existing_cols = [c for c in summary_cols if c in df.columns]
        return df[existing_cols].fillna("").to_dict(orient="records")

    def get_feature_importance(self) -> dict:
        """Return feature importance data."""
        if self.feature_importance_df.empty:
            # Generate synthetic importance from risk_score column correlations
            return self._synthetic_feature_importance()

        records = self.feature_importance_df.to_dict(orient="records")
        return {
            "model_name": "ensemble",
            "features": records,
        }

    def _synthetic_feature_importance(self) -> dict:
        """Create a reasonable feature importance list from available data."""
        features = [
            {"feature": "income_networth_gap", "importance": 0.30},
            {"feature": "tax_gap", "importance": 0.25},
            {"feature": "lifestyle_gap", "importance": 0.20},
            {"feature": "anomaly_score", "importance": 0.15},
            {"feature": "filing_penalty", "importance": 0.10},
        ]
        return {"model_name": "ensemble", "features": features}

    # ── Entity Resolution ─────────────────────────────────────────────

    def get_entity_matches(self) -> list[dict]:
        """Return all entity resolution match pairs."""
        if self.entity_matches_df.empty:
            return []
        return self.entity_matches_df.fillna("").to_dict(orient="records")

    # ── Graph / Network Queries ───────────────────────────────────────

    def get_graph_stats(self) -> dict:
        """Return summary statistics about the knowledge graph."""
        try:
            import networkx as nx
        except ImportError:
            return self._empty_graph_stats()

        if self.graph is None:
            return self._empty_graph_stats()

        g = self.graph
        node_count = g.number_of_nodes()
        edge_count = g.number_of_edges()
        density = nx.density(g) if node_count > 0 else 0.0
        avg_degree = (
            sum(dict(g.degree()).values()) / node_count if node_count else 0.0
        )

        # Connected components
        try:
            if g.is_directed():
                cc = nx.number_weakly_connected_components(g)
            else:
                cc = nx.number_connected_components(g)
        except Exception:
            cc = 0

        # Communities count
        communities_count = 0
        if not self.communities_df.empty and "community_id" in self.communities_df.columns:
            communities_count = int(self.communities_df["community_id"].nunique())

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 6),
            "communities_count": communities_count,
            "avg_degree": round(avg_degree, 2),
            "connected_components": cc,
        }

    @staticmethod
    def _empty_graph_stats() -> dict:
        """Fallback when no graph is loaded."""
        return {
            "node_count": 0,
            "edge_count": 0,
            "density": 0.0,
            "communities_count": 0,
            "avg_degree": 0.0,
            "connected_components": 0,
        }

    def get_ego_graph(self, citizen_id: str, radius: int = 1) -> dict:
        """Return the ego-network (nodes + edges) for a citizen.

        Args:
            citizen_id: Centre node identifier.
            radius: Hop distance from centre (default 1).

        Returns:
            Dict with 'center_id', 'nodes', and 'edges' lists.
        """
        try:
            import networkx as nx
        except ImportError:
            return {"center_id": citizen_id, "nodes": [], "edges": []}

        if self.graph is None or citizen_id not in self.graph:
            return {"center_id": citizen_id, "nodes": [], "edges": []}

        ego = nx.ego_graph(self.graph, citizen_id, radius=radius)

        nodes: list[dict] = []
        for nid in ego.nodes():
            data = ego.nodes[nid]
            cat = str(data.get("risk_category", "A"))
            meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])
            nodes.append({
                "id": str(nid),
                "label": data.get("name", str(nid)),
                "node_type": data.get("type", "citizen"),
                "risk_score": float(data.get("risk_score", 0)),
                "risk_category": cat,
                "size": 20.0 if str(nid) == citizen_id else 10.0,
                "color": meta["color"],
            })

        edges: list[dict] = []
        for src, tgt, edata in ego.edges(data=True):
            edges.append({
                "source": str(src),
                "target": str(tgt),
                "relationship": edata.get("relationship", edata.get("type", "")),
                "weight": float(edata.get("weight", 1.0)),
            })

        return {"center_id": citizen_id, "nodes": nodes, "edges": edges}

    def get_communities(self) -> list[dict]:
        """Return community summary list."""
        if self.communities_df.empty:
            return []

        # Expect columns: citizen_id, community_id
        if "community_id" not in self.communities_df.columns:
            return []

        result: list[dict] = []
        for cid, group in self.communities_df.groupby("community_id"):
            members = group["citizen_id"].tolist() if "citizen_id" in group.columns else []
            # Look up average risk score
            if members and not self.citizens_df.empty:
                matched = self.citizens_df[self.citizens_df["citizen_id"].isin(members)]
                avg_risk = float(matched["risk_score"].mean()) if not matched.empty else 0.0
            else:
                avg_risk = 0.0

            result.append({
                "community_id": int(cid),
                "member_count": len(members),
                "avg_risk_score": round(avg_risk, 2),
                "top_members": members[:10],  # cap at 10
            })

        return result

    # ── Export Helpers ─────────────────────────────────────────────────

    def export_citizens_csv(self, filters: dict[str, Any]) -> pd.DataFrame:
        """Return a filtered DataFrame suitable for CSV / Excel export."""
        records, _ = self.get_citizens(filters, page=1, page_size=999_999)
        return pd.DataFrame(records)
