"""
Blocking Strategies — Reduce the comparison space for entity resolution.
"""
from __future__ import annotations

from typing import Sequence

import pandas as pd
import numpy as np

from core.entity_resolution.name_normalizer import normalize_name, phonetic_code


def _ensure_index(df: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    """Ensure a consistent record-id column exists."""
    df = df.copy()
    if id_col not in df.columns:
        df[id_col] = [f"r_{i}" for i in range(len(df))]
    return df


def _find_cnic_col(df: pd.DataFrame) -> str | None:
    """Locate the CNIC column regardless of casing."""
    for c in df.columns:
        if "cnic" in c.lower():
            return c
    return None


def _find_phone_col(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if "phone" in c.lower() or "mobile" in c.lower():
            return c
    return None


def _find_name_col(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        cl = c.lower()
        if cl in ("name", "owner_name", "account_holder", "traveler_name",
                   "owner", "holder", "citizen_name"):
            return c
    return None


def _find_city_col(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if "city" in c.lower():
            return c
    return None


# ────────────────────────────────────────────────────────────────────
# Public blocking functions
# ────────────────────────────────────────────────────────────────────

def cnic_blocker(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    id_col: str = "record_id",
) -> pd.DataFrame:
    """Block on exact CNIC match (strongest signal).

    Returns a DataFrame of candidate pairs with columns:
    ``id_left``, ``id_right``, ``block_key``, ``block_method``.
    """
    df1 = _ensure_index(df1, id_col)
    df2 = _ensure_index(df2, id_col)
    cnic1 = _find_cnic_col(df1)
    cnic2 = _find_cnic_col(df2)
    if cnic1 is None or cnic2 is None:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    left = df1[[id_col, cnic1]].rename(columns={cnic1: "_cnic"}).dropna(subset=["_cnic"])
    right = df2[[id_col, cnic2]].rename(columns={cnic2: "_cnic"}).dropna(subset=["_cnic"])
    left = left[left["_cnic"].astype(str).str.strip() != ""]
    right = right[right["_cnic"].astype(str).str.strip() != ""]

    merged = left.merge(right, on="_cnic", suffixes=("_left", "_right"))
    if merged.empty:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_cnic"],
        "block_method": "cnic",
    })


def phone_blocker(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    id_col: str = "record_id",
) -> pd.DataFrame:
    """Block on exact phone number match."""
    df1 = _ensure_index(df1, id_col)
    df2 = _ensure_index(df2, id_col)
    phone1 = _find_phone_col(df1)
    phone2 = _find_phone_col(df2)
    if phone1 is None or phone2 is None:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    left = df1[[id_col, phone1]].rename(columns={phone1: "_phone"}).dropna(subset=["_phone"])
    right = df2[[id_col, phone2]].rename(columns={phone2: "_phone"}).dropna(subset=["_phone"])
    left["_phone"] = left["_phone"].astype(str).str.replace("-", "").str.strip()
    right["_phone"] = right["_phone"].astype(str).str.replace("-", "").str.strip()
    left = left[left["_phone"] != ""]
    right = right[right["_phone"] != ""]

    merged = left.merge(right, on="_phone", suffixes=("_left", "_right"))
    if merged.empty:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_phone"],
        "block_method": "phone",
    })


def name_city_blocker(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    id_col: str = "record_id",
) -> pd.DataFrame:
    """Block on phonetic name code + city (sorted-neighbourhood-like)."""
    df1 = _ensure_index(df1, id_col)
    df2 = _ensure_index(df2, id_col)
    name1 = _find_name_col(df1)
    name2 = _find_name_col(df2)
    city1 = _find_city_col(df1)
    city2 = _find_city_col(df2)

    if name1 is None or name2 is None:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    def _block_key(row, name_col, city_col):
        n = normalize_name(str(row.get(name_col, "")))
        pc = phonetic_code(n)
        c = str(row.get(city_col, "")).strip().lower() if city_col else ""
        return f"{pc}|{c}"

    left = df1[[id_col, name1] + ([city1] if city1 else [])].copy()
    right = df2[[id_col, name2] + ([city2] if city2 else [])].copy()
    left["_bk"] = left.apply(lambda r: _block_key(r, name1, city1), axis=1)
    right["_bk"] = right.apply(lambda r: _block_key(r, name2, city2), axis=1)
    left = left[left["_bk"] != "|"]
    right = right[right["_bk"] != "|"]

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    if merged.empty:
        return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "name_city",
    })


def multi_pass_blocker(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    id_col: str = "record_id",
) -> pd.DataFrame:
    """Run all blocking strategies and return the union of candidate pairs."""
    blocks = [
        cnic_blocker(df1, df2, id_col),
        phone_blocker(df1, df2, id_col),
        name_city_blocker(df1, df2, id_col),
    ]
    combined = pd.concat(blocks, ignore_index=True)
    if combined.empty:
        return combined
    # Deduplicate pairs
    combined["_pair"] = combined.apply(
        lambda r: tuple(sorted([str(r["id_left"]), str(r["id_right"])])), axis=1
    )
    combined = combined.drop_duplicates(subset=["_pair"]).drop(columns=["_pair"])
    return combined.reset_index(drop=True)
