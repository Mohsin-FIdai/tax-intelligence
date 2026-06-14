"""
Confidence Scorer — Compute match confidence between two records.
"""
from __future__ import annotations

import sys
from pathlib import Path

from rapidfuzz import fuzz

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    ER_CNIC_WEIGHT, ER_NTN_WEIGHT, ER_PHONE_WEIGHT,
    ER_NAME_WEIGHT, ER_ADDRESS_WEIGHT, ER_FATHER_NAME_WEIGHT, ER_CITY_WEIGHT,
)
from core.entity_resolution.name_normalizer import normalize_name, name_similarity_score


_TOTAL_WEIGHT = (
    ER_CNIC_WEIGHT + ER_NTN_WEIGHT + ER_PHONE_WEIGHT +
    ER_NAME_WEIGHT + ER_ADDRESS_WEIGHT + ER_FATHER_NAME_WEIGHT + ER_CITY_WEIGHT
)


def _safe_str(val) -> str:
    """Convert a value to a stripped string, returning '' for missing values."""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _exact_match(a: str, b: str) -> bool:
    return a != "" and b != "" and a == b


def _fuzzy_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return fuzz.token_sort_ratio(a.lower(), b.lower())


def score_match(record1: dict, record2: dict) -> float:
    """Compute an overall match confidence (0–100) between two records.

    Uses weighted scoring across strong, medium, and weak identifiers.
    Rules:
    - Never assign 100% confidence unless CNIC matches and Name/Father Name also match.
    """
    weighted_sum = 0.0
    
    has_cnic = False
    has_name = False
    has_father = False

    # ── Strong identifiers ──────────────────────────────────────────
    cnic1 = _safe_str(record1.get("cnic"))
    cnic2 = _safe_str(record2.get("cnic"))
    if _exact_match(cnic1, cnic2):
        weighted_sum += ER_CNIC_WEIGHT
        has_cnic = True

    # ── Medium identifiers ──────────────────────────────────────────
    phone1 = _safe_str(record1.get("phone", record1.get("phone_number", "")))
    phone2 = _safe_str(record2.get("phone", record2.get("phone_number", "")))
    phone1_digits = phone1.replace("-", "")
    phone2_digits = phone2.replace("-", "")
    if _exact_match(phone1_digits, phone2_digits):
        weighted_sum += ER_PHONE_WEIGHT

    # ── Weak identifiers ────────────────────────────────────────────
    name1 = _safe_str(record1.get("name", record1.get("owner_name", record1.get("account_holder", ""))))
    name2 = _safe_str(record2.get("name", record2.get("owner_name", record2.get("account_holder", ""))))
    if name1 and name2:
        nscore = name_similarity_score(name1, name2)
        if nscore >= 90:
            weighted_sum += ER_NAME_WEIGHT
            has_name = True
        elif nscore >= 70:
            weighted_sum += ER_NAME_WEIGHT * (nscore / 100)

    addr1 = _safe_str(record1.get("address"))
    addr2 = _safe_str(record2.get("address"))
    if addr1 and addr2:
        ascore = _fuzzy_score(addr1, addr2)
        if ascore >= 70:
            weighted_sum += ER_ADDRESS_WEIGHT * (ascore / 100)

    fname1 = _safe_str(record1.get("father_name"))
    fname2 = _safe_str(record2.get("father_name"))
    if fname1 and fname2:
        fscore = name_similarity_score(fname1, fname2)
        if fscore >= 90:
            weighted_sum += ER_FATHER_NAME_WEIGHT
            has_father = True
        elif fscore >= 70:
            weighted_sum += ER_FATHER_NAME_WEIGHT * (fscore / 100)

    # Base scale
    confidence = (weighted_sum / 120.0) * 100

    # Rules
    if confidence >= 100.0:
        if not (has_cnic and has_name and has_father):
            confidence = 99.9

    return round(min(confidence, 100.0), 1)


def explain_match(record1: dict, record2: dict) -> dict:
    """Return matching reasons, risk level, and merge reason."""
    reasons: list[dict] = []

    def _add(field, v1, v2, match_type, score):
        if score > 0:
            reasons.append({
                "field": field,
                "value_left": v1,
                "value_right": v2,
                "match_type": match_type,
                "score": round(score, 1),
            })

    cnic_exact = False
    name_similar = False
    father_similar = False

    cnic1 = _safe_str(record1.get("cnic"))
    cnic2 = _safe_str(record2.get("cnic"))
    if _exact_match(cnic1, cnic2):
        _add("CNIC", cnic1, cnic2, "exact", ER_CNIC_WEIGHT)
        cnic_exact = True

    ntn1 = _safe_str(record1.get("ntn"))
    ntn2 = _safe_str(record2.get("ntn"))
    if _exact_match(ntn1, ntn2):
        _add("NTN", ntn1, ntn2, "exact", ER_NTN_WEIGHT)

    phone1 = _safe_str(record1.get("phone", record1.get("phone_number", "")))
    phone2 = _safe_str(record2.get("phone", record2.get("phone_number", "")))
    if phone1.replace("-", "") and phone1.replace("-", "") == phone2.replace("-", ""):
        _add("Phone", phone1, phone2, "exact", ER_PHONE_WEIGHT)

    name1 = _safe_str(record1.get("name", record1.get("owner_name", "")))
    name2 = _safe_str(record2.get("name", record2.get("owner_name", "")))
    if name1 and name2:
        ns = name_similarity_score(name1, name2)
        if ns >= 90:
            _add("Name", name1, name2, "exact_ish", ER_NAME_WEIGHT)
            name_similar = True
        elif ns >= 70:
            _add("Name", name1, name2, "fuzzy", ER_NAME_WEIGHT * ns / 100)

    addr1 = _safe_str(record1.get("address"))
    addr2 = _safe_str(record2.get("address"))
    if addr1 and addr2:
        ascore = _fuzzy_score(addr1, addr2)
        if ascore >= 70:
            _add("Address", addr1, addr2, "fuzzy", ER_ADDRESS_WEIGHT * ascore / 100)

    fname1 = _safe_str(record1.get("father_name"))
    fname2 = _safe_str(record2.get("father_name"))
    if fname1 and fname2:
        fscore = name_similarity_score(fname1, fname2)
        if fscore >= 90:
            _add("Father Name", fname1, fname2, "exact_ish", ER_FATHER_NAME_WEIGHT)
            father_similar = True
        elif fscore >= 70:
            _add("Father Name", fname1, fname2, "fuzzy", ER_FATHER_NAME_WEIGHT * fscore / 100)

    # Risk Classification
    if cnic_exact and not name_similar:
        risk_level = "High Risk"
        merge_reason = "Identity Conflict"
    elif name_similar and not cnic_exact:
        risk_level = "Medium Risk"
        merge_reason = "Possible Duplicate"
    elif cnic_exact and name_similar and father_similar:
        risk_level = "Low Risk"
        merge_reason = "Safe Merge"
    else:
        risk_level = "Medium Risk"
        merge_reason = "Review Required"

    return {
        "reasons": reasons,
        "risk_level": risk_level,
        "merge_reason": merge_reason
    }
