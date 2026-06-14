"""
Schema Detection Module — Automatically detects column types, data quality, and field semantics.
"""
import re
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


# ─── Field-type detection patterns ──────────────────────────────────
_CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")
_PHONE_PATTERN = re.compile(r"^0[3]\d{2}-?\d{7}$")
_NTN_PATTERN = re.compile(r"^\d{7}(-\d)?$")
_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")

_NAME_KEYWORDS = {"name", "owner", "holder", "traveler", "person", "citizen", "applicant"}
_CNIC_KEYWORDS = {"cnic", "nic", "identity", "national_id"}
_PHONE_KEYWORDS = {"phone", "mobile", "cell", "contact", "telephone"}
_AMOUNT_KEYWORDS = {"amount", "value", "price", "income", "salary", "tax", "bill",
                     "worth", "balance", "revenue", "paid", "cost", "fee"}
_ADDRESS_KEYWORDS = {"address", "location", "street", "area", "sector"}
_DATE_KEYWORDS = {"date", "dob", "departure", "return", "registration", "filing"}


def detect_field_type(column_name: str, sample_values: pd.Series) -> str:
    """Infer the semantic type of a column from its name and sample values.

    Returns one of: 'cnic', 'phone', 'ntn', 'email', 'name', 'amount',
    'address', 'date', 'categorical', 'numeric', 'other'.
    """
    col_lower = column_name.lower().replace(" ", "_")
    non_null = sample_values.dropna().astype(str)

    # Pattern-based detection on values
    if non_null.size > 0:
        match_rate = non_null.apply(lambda v: bool(_CNIC_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "cnic"

        match_rate = non_null.apply(lambda v: bool(_PHONE_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "phone"

        match_rate = non_null.apply(lambda v: bool(_NTN_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.4:
            return "ntn"

        match_rate = non_null.apply(lambda v: bool(_EMAIL_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "email"

    # Keyword-based detection on column name
    tokens = set(col_lower.replace("-", "_").split("_"))
    if tokens & _CNIC_KEYWORDS:
        return "cnic"
    if tokens & _PHONE_KEYWORDS:
        return "phone"
    if tokens & _NAME_KEYWORDS:
        return "name"
    if tokens & _AMOUNT_KEYWORDS:
        return "amount"
    if tokens & _ADDRESS_KEYWORDS:
        return "address"
    if tokens & _DATE_KEYWORDS:
        return "date"

    # Dtype-based fallback
    if pd.api.types.is_numeric_dtype(sample_values):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(sample_values):
        return "date"
    if sample_values.nunique() < max(20, len(sample_values) * 0.05):
        return "categorical"

    return "other"


def detect_schema(filepath: str | Path) -> dict[str, Any]:
    """Analyse a tabular file and return a detailed schema report.

    Parameters
    ----------
    filepath : path to a CSV, XLSX, or JSON file.

    Returns
    -------
    dict with keys: ``columns`` (list of column dicts), ``row_count``,
    ``file_type``, ``overall_quality_score``.
    """
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(filepath, low_memory=False)
    elif ext in {".xlsx", ".xls"}:
        df = pd.read_excel(filepath)
    elif ext == ".json":
        df = pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    columns_info: list[dict] = []
    quality_scores: list[float] = []

    for col in df.columns:
        series = df[col]
        null_pct = float(series.isna().mean())
        unique_count = int(series.nunique())
        dtype_str = str(series.dtype)
        sample = series.dropna().head(5).tolist()
        field_type = detect_field_type(col, series)

        # Column-level quality: penalise nulls and low uniqueness for IDs
        col_quality = 1.0 - null_pct
        if field_type in {"cnic", "phone", "ntn"} and unique_count < len(series) * 0.5:
            col_quality *= 0.8  # many duplicates in an ID column is suspicious
        quality_scores.append(col_quality)

        columns_info.append({
            "name": col,
            "dtype": dtype_str,
            "field_type": field_type,
            "null_count": int(series.isna().sum()),
            "null_pct": round(null_pct * 100, 2),
            "unique_count": unique_count,
            "sample_values": sample,
        })

    overall_quality = round(float(np.mean(quality_scores)) * 100, 1) if quality_scores else 0.0

    return {
        "file": str(filepath.name),
        "file_type": ext.lstrip("."),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_info,
        "overall_quality_score": overall_quality,
    }


def generate_quality_report(filepath: str | Path) -> dict[str, Any]:
    """High-level quality report with actionable insights."""
    schema = detect_schema(filepath)
    issues: list[str] = []

    for col_info in schema["columns"]:
        if col_info["null_pct"] > 20:
            issues.append(f"Column '{col_info['name']}' has {col_info['null_pct']}% missing values")
        if col_info["field_type"] == "cnic" and col_info["unique_count"] < schema["row_count"] * 0.8:
            issues.append(f"Column '{col_info['name']}' (CNIC) has many duplicates")

    return {
        **schema,
        "issues": issues,
        "issue_count": len(issues),
        "recommendation": "Data is suitable for processing" if not issues else "Review flagged issues before processing",
    }
