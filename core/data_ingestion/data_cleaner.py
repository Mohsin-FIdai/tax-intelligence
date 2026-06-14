"""
Data Cleaning Module — Null handling, deduplication, string normalisation, amount standardisation.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Sequence

import numpy as np
import pandas as pd


def clean_nulls(df: pd.DataFrame, strategy: str = "smart") -> pd.DataFrame:
    """Fill null values using a configurable strategy.

    Strategies
    ----------
    'smart' : Numeric columns → 0, string columns → '', dates → NaT kept.
    'drop'  : Drop rows with any null.
    'mode'  : Fill with column mode (most frequent value).
    """
    df = df.copy()

    if strategy == "drop":
        return df.dropna()

    for col in df.columns:
        if df[col].isna().sum() == 0:
            continue

        if strategy == "mode":
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val.iloc[0])
            continue

        # 'smart' strategy
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            pass  # leave NaT
        else:
            df[col] = df[col].fillna("")

    return df


def remove_duplicates(
    df: pd.DataFrame,
    subset_cols: Sequence[str] | None = None,
    keep: str = "first",
) -> pd.DataFrame:
    """Remove duplicate rows.

    Parameters
    ----------
    subset_cols : Columns to consider for identifying duplicates.
                  If None, all columns are used.
    keep : 'first', 'last', or False (drop all duplicates).
    """
    before = len(df)
    df = df.drop_duplicates(subset=subset_cols, keep=keep).reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"  ↳ Removed {removed:,} duplicate rows")
    return df


def normalize_strings(df: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Trim whitespace, normalise unicode, and title-case string columns."""
    if df.empty:
        return df
    
    # Safe column selection that avoids duplicated column names issues
    if columns is None:
        cols = [c for c, dt in df.dtypes.items() if dt == "object"]
    else:
        cols = columns

    df = df.copy()
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .apply(lambda x: unicodedata.normalize("NFKC", x) if x != "nan" else "")
        )
    return df


def standardize_amounts(df: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Convert amount columns to float: strip commas, currency symbols, whitespace."""
    df = df.copy()
    if columns is None:
        # Auto-detect columns that look like amounts
        columns = [c for c in df.columns
                   if any(kw in c.lower() for kw in ("amount", "value", "price", "income",
                                                       "tax", "bill", "worth", "balance",
                                                       "revenue", "paid", "salary"))]

    for col in columns:
        if col not in df.columns:
            continue
        cleaned_str = (
            df[col]
            .astype(str)
            .str.replace(r"[₨Rs.,\s]", "", regex=True)
            .str.strip()
            .replace({"": "0", "nan": "0", "None": "0"})
        )
        df[col] = pd.to_numeric(cleaned_str, errors="coerce").fillna(0.0)
    return df


def normalize_cnic(df: pd.DataFrame, cnic_col: str = "cnic") -> pd.DataFrame:
    """Ensure all CNIC values follow the XXXXX-XXXXXXX-X format."""
    df = df.copy()
    if cnic_col not in df.columns:
        return df

    def _fmt(val):
        if pd.isna(val) or str(val).strip() in ("", "nan"):
            return ""
        digits = re.sub(r"\D", "", str(val).strip())
        if len(digits) == 13:
            return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
        return str(val).strip()

    df[cnic_col] = df[cnic_col].apply(_fmt)
    return df


def normalize_phone(df: pd.DataFrame, phone_col: str = "phone_number") -> pd.DataFrame:
    """Ensure phone numbers follow the 03XX-XXXXXXX format."""
    df = df.copy()
    if phone_col not in df.columns:
        return df

    def _fmt(val):
        if pd.isna(val) or str(val).strip() in ("", "nan"):
            return ""
        digits = re.sub(r"\D", "", str(val).strip())
        if len(digits) == 11 and digits.startswith("03"):
            return f"{digits[:4]}-{digits[4:]}"
        if len(digits) == 12 and digits.startswith("923"):
            return f"0{digits[2:5]}-{digits[5:]}"
        return str(val).strip()

    df[phone_col] = df[phone_col].apply(_fmt)
    return df


def map_schema_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Intelligently map uploaded CSV columns to expected internal column names."""
    df = df.copy()
    col_map = {}
    
    # Define fuzzy match aliases for standard internal columns
    # Define exact or highly specific aliases to prevent cross-contamination
    ALIASES = {
        "cnic": ["national id", "id number", "cnic", "citizen id", "nic", "ssn", "identifier"],
        "canonical_name": ["full name", "person name", "citizen name", "canonical name", "first name", "name", "owner name", "traveler name"],
        "declared_income": ["income", "annual salary", "declared income", "earnings"],
        "tax_paid": ["tax paid", "tax amount", "paid tax", "tax deducted"],
        "filing_status": ["filer status", "is filer", "filing status"],
        "phone": ["mobile", "contact", "cell", "telephone", "phone number", "mobile number", "contact no", "phone"],
        "property_value": ["property value", "house value", "estate value", "land value", "asset value"],
        "market_value": ["vehicle value", "car value", "auto value", "market value", "price", "estimated market value"],
        "electricity_bill": ["power bill", "wapda", "electricity bill", "lesco", "ke", "k electric"],
        "gas_bill": ["gas bill", "sui gas", "ssgc", "sngpl"],
        "destination": ["travel destination", "destination", "visited", "travelling to"],
        "travel_class": ["flight class", "travel class", "cabin"],
        "business_type": ["business type", "sector", "industry", "company type"],
        "share_value": ["share value", "equity", "investment"],
        "monthly_transactions": ["monthly tx", "tx count", "monthly transactions"],
        "avg_balance": ["avg balance", "account balance", "average balance", "bank balance"],
        "city": ["location", "municipality", "town", "city", "home city"],
        "province": ["state", "region", "territory", "province"],
        
        # New aliases for ego graph
        "meter_no": ["meter no", "meter number"],
        "passport_no": ["passport no", "passport number"],
        "visa_type": ["visa type", "visa"],
        "plot_house_no": ["house no", "plot no", "house number", "plot house no"],
        "car_registration_number": ["car registration", "license plate", "vehicle no", "car registration number"],
        "annual_recharge_amount": ["annual recharge", "recharge amount"],
        "car_model": ["car model", "vehicle model"],
        "model_year": ["model year"],
        "property_type": ["type of property", "property type"],
        "avg_expenditure": ["avg expenditure per month"],
    }

    # Helper to check if any alias is in the column name
    for col in df.columns:
        col_lower = str(col).lower().replace("_", " ")
        matched = False
        for std_col, aliases in ALIASES.items():
            if any(alias == col_lower for alias in aliases):
                # Don't overwrite if we already mapped something to this standard column unless it's a better match
                if std_col not in col_map.values():
                    col_map[col] = std_col
                    matched = True
                    break
        if not matched:
            col_map[col] = col # Keep original if no match

    df = df.rename(columns=col_map)
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full cleaning pipeline on a DataFrame.

    Steps: normalize strings → standardize amounts → normalize CNICs →
           normalize phones → handle nulls → remove exact duplicates.
    """
    df = df.copy()
    
    # Normalize column names first
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    
    # Map to internal schema intelligently
    df = map_schema_columns(df)
    
    # Remove any duplicated columns that resulted from mapping
    df = df.loc[:, ~df.columns.duplicated()]

    df = normalize_strings(df)
    df = standardize_amounts(df)

    # Normalize identifiers if present
    for col in df.columns:
        cl = col.lower()
        if "cnic" in cl:
            df = normalize_cnic(df, col)
        if "phone" in cl or "mobile" in cl:
            df = normalize_phone(df, col)

    df = clean_nulls(df, strategy="smart")
    df = remove_duplicates(df)
    return df
