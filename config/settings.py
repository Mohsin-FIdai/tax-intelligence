"""
Graph AI Tax Intelligence Platform — Central Configuration
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_UPLOADS_DIR = DATA_DIR / "raw_uploads"
MODELS_DIR = BASE_DIR / "models_store"
REPORTS_DIR = BASE_DIR / "reports"

for d in [SYNTHETIC_DIR, PROCESSED_DIR, RAW_UPLOADS_DIR, MODELS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Dataset Sizes ───────────────────────────────────────────────────
NUM_CITIZENS = 10_000
TAX_FILING_RATE = 0.40           # 40% are filers
ANOMALY_RATE = 0.15              # 15% wealth-income mismatch
EXTREME_ANOMALY_RATE = 0.05      # 5% extreme outliers
NON_FILER_WITH_ACTIVITY = 0.25   # 25% non-filers with economic activity

# ─── Entity Resolution Thresholds ────────────────────────────────────
ER_CNIC_WEIGHT = 70
ER_NAME_WEIGHT = 20
ER_FATHER_NAME_WEIGHT = 15
ER_PHONE_WEIGHT = 10
ER_ADDRESS_WEIGHT = 5
ER_NTN_WEIGHT = 35
ER_CITY_WEIGHT = 0
ER_CONFIDENCE_THRESHOLD = 70     # Minimum confidence to merge
ER_NAME_SIMILARITY_THRESHOLD = 0.85

# ─── ML Model Parameters ────────────────────────────────────────────
ISO_FOREST_PARAMS = {
    "n_estimators": 200,
    "contamination": 0.15,
    "max_features": 0.8,
    "random_state": 42,
}

XGBOOST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "use_label_encoder": False,
    "eval_metric": "logloss",
}

RF_PARAMS = {
    "n_estimators": 200,
    "max_depth": 10,
    "random_state": 42,
}

# ─── Risk Scoring Weights ───────────────────────────────────────────
NET_WORTH_WEIGHTS = {
    "vehicle": 1.0,
    "property": 1.0,
    "business": 0.8,
    "utility_lifestyle": 0.3,
    "travel": 0.2,
    "banking": 0.5,
}

DEVIATION_WEIGHTS = {
    "income_networth_gap": 0.30,
    "tax_gap": 0.25,
    "lifestyle_gap": 0.20,
    "anomaly_score": 0.15,
    "filing_penalty": 0.10,
}

# ─── Risk Categories ────────────────────────────────────────────────
RISK_CATEGORIES = {
    "A": {"range": (0, 20), "label": "Tax Compliant", "color": "#00d4aa", "emoji": "🟢"},
    "B": {"range": (21, 40), "label": "Needs Review", "color": "#4a9eff", "emoji": "🔵"},
    "C": {"range": (41, 60), "label": "Suspicious", "color": "#ffd000", "emoji": "🟡"},
    "D": {"range": (61, 80), "label": "Likely Tax Evader", "color": "#ff8c00", "emoji": "🟠"},
    "E": {"range": (81, 100), "label": "Confirmed Tax Deviation", "color": "#ff3355", "emoji": "🔴"},
}

# ─── Pakistani Data Constants ────────────────────────────────────────
PROVINCES = {
    "Punjab": {"code": "3", "weight": 0.53},
    "Sindh": {"code": "4", "weight": 0.23},
    "KPK": {"code": "1", "weight": 0.12},
    "Balochistan": {"code": "5", "weight": 0.06},
    "Islamabad": {"code": "6", "weight": 0.04},
    "AJK": {"code": "7", "weight": 0.01},
    "GB": {"code": "7", "weight": 0.01},
}

CITIES_BY_PROVINCE = {
    "Punjab": ["Lahore", "Faisalabad", "Rawalpindi", "Gujranwala", "Multan",
               "Sargodha", "Sialkot", "Bahawalpur", "Sheikhupura", "Gujrat",
               "Sahiwal", "Jhelum", "Rahim Yar Khan", "Dera Ghazi Khan"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah",
              "Mirpur Khas", "Jacobabad", "Shikarpur", "Khairpur"],
    "KPK": ["Peshawar", "Mardan", "Mingora", "Kohat", "Abbottabad",
            "Dera Ismail Khan", "Swabi", "Mansehra", "Nowshera"],
    "Balochistan": ["Quetta", "Turbat", "Khuzdar", "Hub", "Chaman",
                    "Gwadar", "Sibi", "Loralai", "Zhob"],
    "Islamabad": ["Islamabad"],
    "AJK": ["Muzaffarabad", "Mirpur", "Rawalakot", "Kotli"],
    "GB": ["Gilgit", "Skardu", "Chilas", "Hunza"],
}

# ─── UI Theme Constants ──────────────────────────────────────────────
THEME = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#12121a",
    "bg_card": "#1a1a2e",
    "bg_card_hover": "#22223a",
    "accent": "#00d4aa",
    "accent_secondary": "#4a9eff",
    "danger": "#ff3355",
    "warning": "#ffd000",
    "success": "#00d4aa",
    "text_primary": "#e8e8ed",
    "text_secondary": "#8888a0",
    "border": "#2a2a3e",
    "gradient_start": "#00d4aa",
    "gradient_end": "#4a9eff",
}
