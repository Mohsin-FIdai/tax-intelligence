"""
Run Pipeline — Master script that executes the full data processing pipeline.
Generates synthetic data → ETL → Entity Resolution → Feature Engineering →
ML Anomaly Detection → Risk Scoring → Knowledge Graph
"""
import sys
import time
import io
from pathlib import Path

# Force UTF-8 for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config.settings import SYNTHETIC_DIR, PROCESSED_DIR, MODELS_DIR


def _safe_read(path: Path) -> pd.DataFrame | None:
    """Read a CSV if it exists, else return None."""
    if path.exists():
        return pd.read_csv(path, low_memory=False)
    return None


def run_full_pipeline(source_dir: Path | str = SYNTHETIC_DIR, use_synthetic: bool = False, progress_callback=None):
    start = time.time()
    print("=" * 70)
    print("  GRAPH AI TAX INTELLIGENCE — FULL PIPELINE")
    print("=" * 70)

    # ── Step 1: Generate Synthetic Data ─────────────────────────────
    if use_synthetic:
        if progress_callback: progress_callback(5, "Generating synthetic data...")
        print("\n[1/6] Generating synthetic data...")
        from generators.generate_synthetic_data import generate_all_datasets
        generate_all_datasets()
        source_dir = SYNTHETIC_DIR

    source_dir = Path(source_dir)

    # ── Step 2: ETL Pipeline ────────────────────────────────────────
    if progress_callback: progress_callback(15, "Running ETL data ingestion...")
    print("\n[2/6] Running ETL pipeline...")
    from core.data_ingestion.etl_pipeline import ETLPipeline
    pipeline = ETLPipeline(output_dir=PROCESSED_DIR)
    pipeline.add_sources_from_dir(source_dir, extensions=(".csv", ".xlsx"))
    results = pipeline.run()
    for label, info in results.items():
        print(f"  ✓ {label}: {info['rows_in']} → {info['rows_out']} rows ({info['elapsed_sec']}s)")

    # ── Step 3: Entity Resolution ───────────────────────────────────
    if progress_callback: progress_callback(30, "Running entity resolution...")
    print("\n[3/6] Running entity resolution...")
    from core.entity_resolution.entity_resolver import EntityResolver

    datasets = {}
    for csv_file in sorted(PROCESSED_DIR.glob("*_clean.csv")):
        label = csv_file.stem.replace("_clean", "")
        if label.startswith("_"):  # skip ground truth
            continue
        datasets[label] = pd.read_csv(csv_file, low_memory=False)

    resolver = EntityResolver()
    citizens_df = resolver.resolve(datasets)
    print(f"  ✓ Resolved → {len(citizens_df):,} unique citizens")

    # ── Step 4: Feature Engineering + ML ────────────────────────────
    if progress_callback: progress_callback(50, "Extracting features and running ML models...")
    print("\n[4/6] Running ML pipeline...")
    from core.ml.feature_engineering import FeatureEngineer
    from core.ml.anomaly_detector import AnomalyDetector
    from core.ml.risk_classifier import RiskClassifier

    # Load cleaned datasets for feature extraction
    # The feature engineering module joins on citizen_id, but our cleaned CSVs
    # use cnic. We need to map cnic → citizen_id for each dataset.
    if "cnic" in citizens_df.columns:
        cnic_to_cid = dict(zip(citizens_df["cnic"].astype(str), citizens_df["citizen_id"]))
    else:
        cnic_to_cid = {}

    def _add_citizen_id(df: pd.DataFrame | None) -> pd.DataFrame | None:
        """Map cnic column to citizen_id for feature engineering joins."""
        if df is None or df.empty:
            return df
        df = df.copy()
        
        # If the input file already has citizen_id, use it
        if "citizen_id" in df.columns:
            return df
            
        if "cnic" in df.columns:
            df["citizen_id"] = df["cnic"].astype(str).map(cnic_to_cid)
        else:
            for col in df.columns:
                if "cnic" in col.lower():
                    df["citizen_id"] = df[col].astype(str).map(cnic_to_cid)
                    break
                
        if "citizen_id" not in df.columns:
            # Create a dummy citizen_id column if we couldn't map it, to prevent crashes downstream
            df["citizen_id"] = "UNKNOWN"
            return df
            
        df = df.dropna(subset=["citizen_id"])
        return df

    vehicles = _add_citizen_id(_safe_read(PROCESSED_DIR / "vehicle_records_clean.csv"))
    properties = _add_citizen_id(_safe_read(PROCESSED_DIR / "property_records_clean.csv"))
    utilities = _add_citizen_id(_safe_read(PROCESSED_DIR / "utility_bills_clean.csv"))
    travel = _add_citizen_id(_safe_read(PROCESSED_DIR / "travel_records_clean.csv"))
    business = _add_citizen_id(_safe_read(PROCESSED_DIR / "business_records_clean.csv"))
    banking = _add_citizen_id(_safe_read(PROCESSED_DIR / "banking_indicators_clean.csv"))
    mobile = _add_citizen_id(_safe_read(PROCESSED_DIR / "mobile_records_clean.csv"))

    # Add market_value column alias for vehicles if needed
    if vehicles is not None and "market_value" in vehicles.columns and "vehicle_value" not in vehicles.columns:
        vehicles["vehicle_value"] = vehicles["market_value"]

    # Add property_value alias if needed
    if properties is not None and "property_value" not in properties.columns:
        for col in properties.columns:
            if "value" in col.lower():
                properties["property_value"] = properties[col]
                break

    # Feature engineering
    fe = FeatureEngineer()
    features_df = fe.extract_features(
        citizens_df, vehicles, properties, utilities, travel, business, banking
    )
    features_df.to_csv(PROCESSED_DIR / "feature_vectors.csv", index=False)
    print(f"  ✓ Feature vectors: {features_df.shape}")

    # Get numeric feature columns (exclude citizen_id)
    numeric_cols = [c for c in features_df.columns
                    if c != "citizen_id" and features_df[c].dtype in ["float64", "int64", "float32", "int32"]]
    X = features_df[numeric_cols].fillna(0)

    # Anomaly detection
    ad = AnomalyDetector()
    ad.fit(X)
    suspicion = ad.get_suspicion_percentage(X)
    citizens_df["suspicion_pct"] = suspicion[:len(citizens_df)]
    print(f"  ✓ Anomaly detection complete. Mean suspicion: {suspicion.mean():.1f}%")

    # Risk classifier — generate labels and train
    rc = RiskClassifier()
    labels = rc.generate_labels(features_df)
    if labels is not None and len(labels) > 0 and labels.nunique() >= 2:
        try:
            metrics = rc.train(X, labels)
            print(f"  ✓ Risk classifier trained. CV Accuracy: {metrics.get('cv_accuracy_mean', 0):.3f}")
            importance_df = rc.get_feature_importance()
            importance_df = importance_df.rename(columns={"avg_importance": "importance"})
            importance_df.to_csv(PROCESSED_DIR / "feature_importance.csv", index=False)
        except Exception as e:
            print(f"  ⚠ Risk classifier training failed (non-critical): {e}")
    else:
        print("  ⚠ Insufficient label diversity for classifier training, skipping.")

    # ── Step 5: Risk Scoring ────────────────────────────────────────
    if progress_callback: progress_callback(70, "Computing multi-dimensional risk scores...")
    print("\n[5/6] Computing risk scores...")
    from core.risk_scoring.net_worth_estimator import NetWorthEstimator
    from core.risk_scoring.deviation_scorer import DeviationScorer
    from core.risk_scoring.risk_categorizer import RiskCategorizer

    nwe = NetWorthEstimator()
    ds = DeviationScorer()
    rc2 = RiskCategorizer()

    net_worths = []
    dev_scores = []
    risk_cats = []

    for idx in range(len(citizens_df)):
        # Build citizen data dict from citizens + features
        citizen_row = citizens_df.iloc[idx].to_dict()
        feat_row = features_df.iloc[idx].to_dict() if idx < len(features_df) else {}
        citizen_data = {**citizen_row, **feat_row}

        # Net worth estimation
        nw_result = nwe.estimate(citizen_data)
        est_nw = nw_result.get("estimated_net_worth", 0)
        net_worths.append(est_nw)

        # Deviation scoring (needs estimated_net_worth and anomaly_suspicion)
        citizen_data["estimated_net_worth"] = est_nw
        citizen_data["anomaly_suspicion"] = float(suspicion[idx]) if idx < len(suspicion) else 0

        dev_result = ds.score(citizen_data)
        dev_score = dev_result.get("deviation_score", 0)
        dev_scores.append(dev_score)

        # Risk categorization
        cat_result = rc2.categorize(dev_score)
        risk_cats.append(cat_result.get("category", "C"))

    citizens_df["estimated_net_worth"] = net_worths
    citizens_df["deviation_score"] = dev_scores
    citizens_df["risk_category"] = risk_cats

    # Tax Gap Estimation
    if progress_callback: progress_callback(75, "Estimating tax gap and recoverable revenue...")
    from core.risk_scoring.tax_gap_estimator import TaxGapEstimator
    tge = TaxGapEstimator()
    citizens_df = tge.process_dataframe(citizens_df)

    # Merge key features into citizens for dashboard
    feature_cols_to_merge = [
        "total_vehicle_value", "total_property_value", "foreign_travel_count",
        "business_count", "business_class_trips", "avg_monthly_electricity",
        "avg_monthly_gas", "vehicle_count", "property_count",
        "total_utility_spend", "directorship_count", "avg_bank_balance",
    ]
    for col in feature_cols_to_merge:
        if col in features_df.columns:
            vals = features_df[col].values
            citizens_df[col] = vals[:len(citizens_df)] if len(vals) >= len(citizens_df) else \
                np.pad(vals, (0, len(citizens_df) - len(vals)), constant_values=0)

    # Save enriched citizens
    citizens_df.to_csv(PROCESSED_DIR / "master_citizens.csv", index=False)

    cat_counts = citizens_df["risk_category"].value_counts().sort_index()
    print(f"  ✓ Risk scoring complete. Distribution:")
    for cat, count in cat_counts.items():
        from config.settings import RISK_CATEGORIES
        info = RISK_CATEGORIES.get(cat, {})
        print(f"    Cat {cat} ({info.get('label', '?'):25s}): {count:,}")

    # ── Step 6: Knowledge Graph ─────────────────────────────────────
    if progress_callback: progress_callback(85, "Building complex knowledge graph...")
    print("\n[6/6] Building knowledge graph...")
    from core.knowledge_graph.graph_builder import KnowledgeGraphBuilder

    gb = KnowledgeGraphBuilder()
    G = gb.build_graph(
        citizens_df=citizens_df,
        vehicles_df=_safe_read(PROCESSED_DIR / "vehicle_records_clean.csv"),
        properties_df=_safe_read(PROCESSED_DIR / "property_records_clean.csv"),
        utilities_df=_safe_read(PROCESSED_DIR / "utility_bills_clean.csv"),
        travel_df=_safe_read(PROCESSED_DIR / "travel_records_clean.csv"),
        business_df=_safe_read(PROCESSED_DIR / "business_records_clean.csv"),
        mobile_df=_safe_read(PROCESSED_DIR / "mobile_records_clean.csv"),
        banking_df=_safe_read(PROCESSED_DIR / "banking_indicators_clean.csv"),
    )
    gb.save_graph()

    # ── Summary ─────────────────────────────────────────────────────
    elapsed = time.time() - start
    high_risk = len(citizens_df[citizens_df["risk_category"].isin(["D", "E"])])

    print("\n" + "=" * 70)
    print(f"  ✅ PIPELINE COMPLETE in {elapsed:.1f} seconds")
    print(f"  📊 Citizens: {len(citizens_df):,}")
    print(f"  🕸️  Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    print(f"  ⚠️  High-risk (Cat D+E): {high_risk:,}")
    print("=" * 70)
    print(f"\n  Launch dashboard: streamlit run app/streamlit_app.py")
    if progress_callback: progress_callback(100, "Intelligence Pipeline Complete!")


if __name__ == "__main__":
    run_full_pipeline(use_synthetic=True)
