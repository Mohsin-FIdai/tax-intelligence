"""
Entity Resolver — Merges records across datasets into unified citizen profiles.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import PROCESSED_DIR, ER_CONFIDENCE_THRESHOLD
from core.entity_resolution.name_normalizer import normalize_name
from core.entity_resolution.confidence_scorer import score_match, explain_match


class EntityResolver:
    """Multi-pass entity resolution engine.

    Strategy
    --------
    1. **Deterministic** — exact CNIC match across all datasets.
    2. **Strong probabilistic** — CNIC + phone or CNIC + name.
    3. **Fuzzy probabilistic** — name similarity + city.
    4. **Graph-based** — shared address / phone relationships.

    The output is a master citizen table with a unique ``citizen_id`` per
    resolved entity together with a match-log table.
    """

    def __init__(self, confidence_threshold: float = ER_CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.match_log: list[dict] = []

    # ────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _standardise(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
        """Add source label and normalise key columns."""
        df = df.copy()
        df["_source"] = source_label

        # Ensure a record_id
        if "record_id" not in df.columns and "citizen_id" not in df.columns:
            df["record_id"] = [f"{source_label}_{i}" for i in range(len(df))]
        elif "citizen_id" in df.columns and "record_id" not in df.columns:
            df["record_id"] = df["citizen_id"]

        # Find and normalise name column
        name_col = None
        for c in df.columns:
            if c.lower() in ("name", "owner_name", "account_holder", "traveler_name", "canonical_name"):
                name_col = c
                break
        if name_col:
            df["_norm_name"] = df[name_col].apply(lambda x: normalize_name(str(x)) if pd.notna(x) else "")

        # Normalise CNIC
        for c in df.columns:
            if "cnic" in c.lower():
                df["_cnic"] = df[c].astype(str).str.strip()
                df.loc[df["_cnic"].str.lower().isin(["", "nan", "none", "unknown", "n/a", "null"]), "_cnic"] = ""
                break

        return df

    def _merge_cluster(self, records: list[dict]) -> dict:
        """Merge a cluster of matched records into a single citizen profile."""
        citizen_id = f"CZ-{uuid.uuid4().hex[:8].upper()}"

        # Pick the best values (prefer non-empty, from tax records first)
        def _best(field: str):
            for r in records:
                val = r.get(field)
                if val and str(val).strip() not in ("", "nan", "None", "0"):
                    return val
            return ""

        # Collect all CNICs and names seen
        cnics = list({str(r.get("_cnic", "")) for r in records if r.get("_cnic")})
        names = list({r.get("_norm_name", "") for r in records if r.get("_norm_name")})
        sources = list({r.get("_source", "") for r in records})
        record_ids = [r.get("record_id", "") for r in records]

        # Determine canonical name
        canonical_name = names[0] if names else ""
        
        # Add Urdu script for multilingual display and search
        if canonical_name:
            try:
                from core.entity_resolution.roman_urdu import transliterate_plain
                urdu_name = transliterate_plain(canonical_name)
                if urdu_name and urdu_name != canonical_name:
                    canonical_name = f"{canonical_name} ({urdu_name})"
            except Exception:
                pass

        return {
            "citizen_id": citizen_id,
            "canonical_name": canonical_name,
            "cnic": cnics[0] if cnics else "",
            "ntn": _best("ntn"),
            "father_name": normalize_name(str(_best("father_name"))),
            "city": _best("city"),
            "province": _best("province"),
            "phone": _best("phone_number") or _best("phone"),
            "address": _best("address"),
            "filing_status": _best("filing_status"),
            "declared_income": _best("declared_income"),
            "tax_paid": _best("tax_paid"),
            "num_sources": len(sources),
            "sources": ",".join(sources),
            "merged_record_ids": ",".join(str(rid) for rid in record_ids),
        }

    # ────────────────────────────────────────────────────────────────
    # Main resolver
    # ────────────────────────────────────────────────────────────────

    def resolve(self, datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Resolve entities across multiple datasets.

        Parameters
        ----------
        datasets : dict mapping source label → DataFrame.

        Returns
        -------
        DataFrame of master citizen profiles.  Also saves ``entity_matches.csv``
        and ``master_citizens.csv`` to the processed data directory.
        """
        # Standardise all datasets
        all_records: list[dict] = []
        for label, df in datasets.items():
            std = self._standardise(df, label)
            all_records.extend(std.to_dict("records"))

        # ── Pre-Processing: Exact Duplicates ──────────────────────────
        unique_records = []
        seen_keys = set()
        
        for rec in all_records:
            # Create a signature of all key fields
            sig = (
                rec.get("_cnic", ""),
                rec.get("ntn", ""),
                str(rec.get("_norm_name", "")),
                str(rec.get("father_name", "")),
                str(rec.get("phone_number", rec.get("phone", "")))
            )
            if sig in seen_keys and sig != ("", "", "", "", ""):
                # It's an exact duplicate. We could log it, but user wants it auto-resolved (ignored in manual queue)
                continue
            seen_keys.add(sig)
            unique_records.append(rec)
            
        all_records = unique_records

        # Load previously reviewed merges to avoid showing them again
        reviewed_merges_path = PROCESSED_DIR / "reviewed_merges.csv"
        reviewed_pairs = set()
        if reviewed_merges_path.exists():
            try:
                df_rev = pd.read_csv(reviewed_merges_path)
                for _, row in df_rev.iterrows():
                    reviewed_pairs.add(tuple(sorted([str(row.get("record1_id")), str(row.get("record2_id"))])))
            except Exception:
                pass

        # ── Pass 1: Deterministic CNIC matching ─────────────────────
        cnic_groups: dict[str, list[dict]] = {}
        unmatched: list[dict] = []

        for rec in all_records:
            cnic = rec.get("_cnic", "")
            if cnic:
                cnic_groups.setdefault(cnic, []).append(rec)
            else:
                unmatched.append(rec)

        clusters: list[list[dict]] = []
        for cnic, group in cnic_groups.items():
            if len(group) >= 1:
                clusters.append(group)
                # Log matches within group
                if len(group) > 1:
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            rid1 = str(group[i].get("record_id", ""))
                            rid2 = str(group[j].get("record_id", ""))
                            if tuple(sorted([rid1, rid2])) in reviewed_pairs:
                                continue

                            conf = score_match(group[i], group[j])
                            explanation = explain_match(group[i], group[j])
                            self.match_log.append({
                                "record1_id": rid1,
                                "record2_id": rid2,
                                "confidence": conf,
                                "method": "deterministic_cnic",
                                "reasons": str([r["field"] for r in explanation["reasons"]]),
                                "risk_level": explanation["risk_level"],
                                "merge_reason": explanation["merge_reason"]
                            })

        # ── Pass 2: Fuzzy matching on unmatched records ─────────────
        # Try to attach unmatched records to existing clusters by name+city
        still_unmatched: list[dict] = []
        for rec in unmatched:
            best_cluster_idx = -1
            best_score = 0.0
            rec_name = rec.get("_norm_name", "")
            best_explanation = None

            if rec_name:
                for ci, cluster in enumerate(clusters):
                    # Compare against first record in cluster
                    rep = cluster[0]
                    conf = score_match(rec, rep)
                    if conf > best_score and conf >= self.confidence_threshold:
                        best_score = conf
                        best_cluster_idx = ci
                        best_explanation = explain_match(rec, rep)

            if best_cluster_idx >= 0:
                clusters[best_cluster_idx].append(rec)
                
                rid1 = str(rec.get("record_id", ""))
                rid2 = str(clusters[best_cluster_idx][0].get("record_id", ""))
                if tuple(sorted([rid1, rid2])) not in reviewed_pairs:
                    self.match_log.append({
                        "record1_id": rid1,
                        "record2_id": rid2,
                        "confidence": best_score,
                        "method": "probabilistic_match",
                        "reasons": str([r["field"] for r in best_explanation["reasons"]]),
                        "risk_level": best_explanation["risk_level"],
                        "merge_reason": best_explanation["merge_reason"]
                    })
            else:
                still_unmatched.append(rec)

        # Remaining unmatched become their own clusters
        for rec in still_unmatched:
            clusters.append([rec])

        # ── Merge clusters into citizen profiles ────────────────────
        citizens = [self._merge_cluster(cluster) for cluster in clusters]
        citizens_df = pd.DataFrame(citizens)

        # ── Save outputs ────────────────────────────────────────────
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        citizens_df.to_csv(PROCESSED_DIR / "master_citizens.csv", index=False)

        if self.match_log:
            matches_df = pd.DataFrame(self.match_log)
            matches_df.to_csv(PROCESSED_DIR / "entity_matches.csv", index=False)

        print(f"  ✓ Resolved {len(all_records):,} records → {len(citizens_df):,} unique citizens")
        print(f"  ✓ Logged {len(self.match_log):,} entity matches")

        return citizens_df

    def get_match_log(self) -> pd.DataFrame:
        """Return the match log as a DataFrame."""
        return pd.DataFrame(self.match_log) if self.match_log else pd.DataFrame()
