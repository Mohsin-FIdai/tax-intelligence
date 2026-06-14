"""
Synthetic Data Generator — Tax Intelligence Platform

Creates realistic, complex datasets mimicking disparate national records.
Deliberately introduces noise, aliases, spelling errors, and extreme anomalies
to test the Entity Resolution and Machine Learning pipelines.
"""
from __future__ import annotations

import sys
import io
import json
import random
import uuid
import datetime
from pathlib import Path

# Force UTF-8 for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import csv
import random
import string
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    CITIES_BY_PROVINCE,
    NUM_CITIZENS,
    PROVINCES,
    SYNTHETIC_DIR,
    TAX_FILING_RATE,
    ANOMALY_RATE,
    EXTREME_ANOMALY_RATE,
    NON_FILER_WITH_ACTIVITY,
)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ---------------------------------------------------------------------------
# Pakistani-specific constants
# ---------------------------------------------------------------------------
FIRST_NAMES_MALE: list[str] = [
    "Muhammad", "Ahmad", "Ali", "Usman", "Bilal", "Hassan", "Hussain",
    "Hamza", "Umar", "Asad", "Faisal", "Kamran", "Naveed", "Shahid",
    "Tariq", "Waqas", "Zubair", "Imran", "Kashif", "Rizwan",
    "Adnan", "Arif", "Azhar", "Babar", "Danish", "Ehsan", "Farhan",
    "Ghulam", "Habib", "Iqbal", "Javed", "Khalid", "Liaquat",
    "Mansoor", "Nadeem", "Owais", "Pervaiz", "Qasim", "Rashid",
    "Saeed", "Tahir", "Umair", "Waheed", "Yasir", "Zahid",
    "Amir", "Atif", "Basit", "Daniyal", "Fahad", "Salman", "Sohail",
    "Tanveer", "Zafar", "Shoaib", "Irfan", "Junaid", "Mushtaq",
    "Noman", "Rafiq", "Sajid", "Talha", "Waseem", "Zeeshan",
]

FIRST_NAMES_FEMALE: list[str] = [
    "Fatima", "Ayesha", "Khadija", "Maryam", "Sana", "Hina", "Nadia",
    "Rabia", "Zainab", "Amna", "Bushra", "Farah", "Saima", "Noor",
    "Samina", "Uzma", "Asma", "Farzana", "Nasreen", "Rubina",
    "Aisha", "Iram", "Lubna", "Maheen", "Nighat", "Parveen",
    "Qudsia", "Riffat", "Shazia", "Tahira", "Yasmin", "Zubaida",
    "Aneela", "Bano", "Durr-e-Shahwar", "Ghazala", "Humaira", "Jaweria",
    "Komal", "Madiha", "Naila", "Sadia", "Tanzeela", "Wardah",
]

LAST_NAMES: list[str] = [
    "Khan", "Ahmed", "Ali", "Malik", "Shah", "Hussain", "Iqbal",
    "Sheikh", "Butt", "Chaudhry", "Awan", "Siddiqui", "Qureshi",
    "Bhatti", "Raza", "Mirza", "Baig", "Shaikh", "Hashmi",
    "Aslam", "Tahir", "Niazi", "Rajput", "Mughal", "Abbasi",
    "Durrani", "Khattak", "Afridi", "Yousafzai", "Baloch",
    "Mengal", "Bugti", "Laghari", "Khoso", "Brohi",
    "Soomro", "Junejo", "Chandio", "Memon", "Jatoi",
    "Gill", "Cheema", "Virk", "Warraich", "Gondal",
    "Randhawa", "Sethi", "Minhas", "Kayani", "Jamali",
]

# Name variations for entity-resolution testing (Urdu transliterations & extreme phonetic variations)
NAME_VARIATIONS: dict[str, list[str]] = {
    "Muhammad": ["Mohammad", "Mohd", "Muhamad", "Muhammed", "Mohamed", "Mohamad", "M.", "Mhd"],
    "Ahmad": ["Ahmed", "Ahmd", "Ahemad"],
    "Hussain": ["Husain", "Husein", "Hussien", "Hussan", "Hossein"],
    "Ali": ["Alee", "Allee"],
    "Usman": ["Osman", "Uthman", "Usmaan"],
    "Hassan": ["Hasan", "Haasan", "Hassaan"],
    "Fatima": ["Fathima", "Fatimah", "Fateema"],
    "Ayesha": ["Aisha", "Aesha", "Ayesha", "Aysha"],
    "Khadija": ["Khadeeja", "Khadijah", "Khadeejah"],
    "Khalid": ["Khaled", "Khaleed"],
    "Rashid": ["Rasheed", "Rasheid"],
    "Saeed": ["Saeid", "Said", "Sayeed"],
    "Shahid": ["Shaheed"],
    "Tariq": ["Tarik", "Tareq", "Taariq"],
    "Imran": ["Emran", "Imraan", "Imron"],
    "Qasim": ["Kasim", "Qasem", "Kassim"],
    "Zainab": ["Zaineb", "Zenab", "Zeynab"],
    "Maryam": ["Mariam", "Meriam", "Marium"],
    "Nadia": ["Nadeea", "Nadiya", "Naadia"],
    "Zubair": ["Zubayr", "Zubayer"],
    "Farhan": ["Farhaan", "Furhan", "Ferhan"],
    "Mansoor": ["Mansur", "Manzoor", "Munsoor"],
    "Sana": ["Sanaa", "Sunna"],
}

TITLES: list[str] = [
    "Mr", "Dr", "Haji", "Mian", "Ch", "Syed", "Rana", "Raja",
    "Malik", "Pir", "Sardar", "Nawab",
]

# Vehicle constants
VEHICLE_TYPES: list[dict[str, Any]] = [
    {"make": "Suzuki",   "model": "Alto",       "type": "Car",  "min_val": 1_800_000,  "max_val": 2_800_000,  "weight": 0.18},
    {"make": "Suzuki",   "model": "Cultus",     "type": "Car",  "min_val": 2_500_000,  "max_val": 3_500_000,  "weight": 0.10},
    {"make": "Suzuki",   "model": "WagonR",     "type": "Car",  "min_val": 2_200_000,  "max_val": 3_200_000,  "weight": 0.08},
    {"make": "Suzuki",   "model": "Swift",      "type": "Car",  "min_val": 3_000_000,  "max_val": 4_200_000,  "weight": 0.06},
    {"make": "Toyota",   "model": "Corolla",    "type": "Car",  "min_val": 4_000_000,  "max_val": 7_500_000,  "weight": 0.15},
    {"make": "Toyota",   "model": "Yaris",      "type": "Car",  "min_val": 3_500_000,  "max_val": 5_500_000,  "weight": 0.07},
    {"make": "Honda",    "model": "Civic",      "type": "Car",  "min_val": 5_500_000,  "max_val": 9_000_000,  "weight": 0.08},
    {"make": "Honda",    "model": "City",       "type": "Car",  "min_val": 4_000_000,  "max_val": 6_000_000,  "weight": 0.07},
    {"make": "Hyundai",  "model": "Tucson",     "type": "SUV",  "min_val": 7_000_000,  "max_val": 11_000_000, "weight": 0.04},
    {"make": "Hyundai",  "model": "Elantra",    "type": "Car",  "min_val": 5_000_000,  "max_val": 7_000_000,  "weight": 0.03},
    {"make": "KIA",      "model": "Sportage",   "type": "SUV",  "min_val": 7_500_000,  "max_val": 12_000_000, "weight": 0.04},
    {"make": "KIA",      "model": "Picanto",    "type": "Car",  "min_val": 3_000_000,  "max_val": 4_500_000,  "weight": 0.02},
    {"make": "Toyota",   "model": "Fortuner",   "type": "SUV",  "min_val": 12_000_000, "max_val": 18_000_000, "weight": 0.02},
    {"make": "Toyota",   "model": "Land Cruiser", "type": "SUV","min_val": 40_000_000, "max_val": 65_000_000, "weight": 0.01},
    {"make": "Mercedes", "model": "C-Class",    "type": "Car",  "min_val": 18_000_000, "max_val": 30_000_000, "weight": 0.01},
    {"make": "BMW",      "model": "3 Series",   "type": "Car",  "min_val": 15_000_000, "max_val": 28_000_000, "weight": 0.005},
    {"make": "Audi",     "model": "A4",         "type": "Car",  "min_val": 15_000_000, "max_val": 25_000_000, "weight": 0.005},
    {"make": "Honda",    "model": "CD-70",      "type": "Motorcycle", "min_val": 110_000, "max_val": 160_000, "weight": 0.03},
    {"make": "Yamaha",   "model": "YBR-125",    "type": "Motorcycle", "min_val": 200_000, "max_val": 350_000, "weight": 0.02},
]

VEHICLE_REG_PREFIXES: dict[str, list[str]] = {
    "Punjab": ["LEA", "LEB", "LEC", "LED", "RIR", "RIA", "FSD", "GRW", "MLT", "SRG", "SLK", "BWP"],
    "Sindh": ["KHI", "AKD", "AGR", "HYD", "SKP", "MRP"],
    "KPK": ["PSH", "A", "B", "MRD"],
    "Balochistan": ["QTA", "QB", "TBT"],
    "Islamabad": ["ISB", "ICT"],
    "AJK": ["AJK", "MZF"],
    "GB": ["GBT", "GLT"],
}

# Property constants
PROPERTY_TYPES: list[str] = ["House", "Flat", "Plot", "Commercial", "Agricultural Land"]

AREA_NAMES_BY_CITY: dict[str, list[str]] = {
    "Lahore": ["DHA Phase 5", "Gulberg III", "Model Town", "Johar Town", "Bahria Town",
               "Garden Town", "Cantt", "Iqbal Town", "Wapda Town", "Township"],
    "Karachi": ["DHA Phase 6", "Clifton", "Gulshan-e-Iqbal", "North Nazimabad",
                "PECHS", "Gulistan-e-Johar", "Bahria Town Karachi", "Malir Cantt"],
    "Islamabad": ["F-6", "F-7", "F-8", "F-10", "F-11", "G-9", "G-10", "G-11",
                  "E-11", "DHA Phase 2", "Bahria Town Phase 7", "I-8"],
    "Rawalpindi": ["Bahria Town Phase 8", "DHA Phase 2", "Satellite Town",
                   "Chaklala Cantt", "Saddar", "Committee Chowk"],
    "Faisalabad": ["Peoples Colony", "Madina Town", "Ghulam Muhammad Abad",
                   "Jinnah Colony", "D Ground"],
}

# Property value ranges per marla by city tier
PROPERTY_VALUE_PER_MARLA: dict[str, tuple[int, int]] = {
    "Lahore": (2_000_000, 15_000_000),
    "Karachi": (1_500_000, 12_000_000),
    "Islamabad": (3_000_000, 20_000_000),
    "Rawalpindi": (1_500_000, 8_000_000),
    "Faisalabad": (500_000, 3_000_000),
    "_default": (300_000, 2_000_000),
}

# Utility providers
ELECTRICITY_PROVIDERS: dict[str, list[str]] = {
    "Punjab": ["LESCO", "FESCO", "GEPCO", "MEPCO"],
    "Sindh": ["K-Electric", "HESCO", "SEPCO"],
    "KPK": ["PESCO"],
    "Balochistan": ["QESCO"],
    "Islamabad": ["IESCO"],
    "AJK": ["IESCO"],
    "GB": ["IESCO"],
}

GAS_PROVIDERS: dict[str, str] = {
    "Punjab": "SNGPL",
    "Sindh": "SSGC",
    "KPK": "SNGPL",
    "Balochistan": "SSGC",
    "Islamabad": "SNGPL",
    "AJK": "SNGPL",
    "GB": "SNGPL",
}

# Mobile operators with prefixes
MOBILE_OPERATORS: dict[str, list[str]] = {
    "Jazz":    ["0300", "0301", "0302", "0303", "0304", "0305", "0306", "0307", "0308", "0309"],
    "Telenor": ["0340", "0341", "0342", "0343", "0344", "0345", "0346", "0347", "0348", "0349"],
    "Zong":    ["0310", "0311", "0312", "0313", "0314", "0315", "0316", "0317", "0318", "0319"],
    "Ufone":   ["0330", "0331", "0332", "0333", "0334", "0335", "0336", "0337", "0338", "0339"],
}

BANKS: list[str] = [
    "Habib Bank", "United Bank", "MCB Bank", "Allied Bank", "Bank Alfalah",
    "Meezan Bank", "Faysal Bank", "Standard Chartered", "Askari Bank",
    "Bank of Punjab", "JS Bank", "Soneri Bank", "Summit Bank",
    "National Bank", "Bank Al Habib",
]

TRAVEL_DESTINATIONS: list[dict[str, Any]] = [
    {"country": "UAE", "weight": 0.25, "class_dist": {"Economy": 0.65, "Business": 0.30, "First": 0.05}},
    {"country": "Saudi Arabia", "weight": 0.25, "class_dist": {"Economy": 0.80, "Business": 0.18, "First": 0.02}},
    {"country": "UK", "weight": 0.10, "class_dist": {"Economy": 0.55, "Business": 0.35, "First": 0.10}},
    {"country": "Turkey", "weight": 0.10, "class_dist": {"Economy": 0.70, "Business": 0.25, "First": 0.05}},
    {"country": "Malaysia", "weight": 0.08, "class_dist": {"Economy": 0.75, "Business": 0.22, "First": 0.03}},
    {"country": "Thailand", "weight": 0.06, "class_dist": {"Economy": 0.80, "Business": 0.18, "First": 0.02}},
    {"country": "USA", "weight": 0.05, "class_dist": {"Economy": 0.50, "Business": 0.35, "First": 0.15}},
    {"country": "China", "weight": 0.04, "class_dist": {"Economy": 0.60, "Business": 0.35, "First": 0.05}},
    {"country": "Canada", "weight": 0.03, "class_dist": {"Economy": 0.55, "Business": 0.35, "First": 0.10}},
    {"country": "Qatar", "weight": 0.02, "class_dist": {"Economy": 0.60, "Business": 0.30, "First": 0.10}},
    {"country": "Oman", "weight": 0.02, "class_dist": {"Economy": 0.75, "Business": 0.22, "First": 0.03}},
]

AIRLINES: list[str] = [
    "PIA", "Emirates", "Qatar Airways", "Turkish Airlines", "Saudi Airlines",
    "Etihad", "Air Blue", "Serene Air", "Fly Jinnah", "Gulf Air",
    "Oman Air", "Malaysia Airlines", "Thai Airways", "British Airways",
]

BUSINESS_TYPES: list[str] = [
    "Retail", "Wholesale", "Manufacturing", "Construction", "Real Estate",
    "IT Services", "Textile", "Pharmaceutical", "Import/Export",
    "Restaurant", "Transport", "Education", "Healthcare", "Agriculture",
    "Financial Services", "E-Commerce", "Automotive",
]


# =====================================================================
# Helper functions
# =====================================================================

def _choose_province() -> str:
    """Pick a province using population-weighted distribution."""
    provinces = list(PROVINCES.keys())
    weights = [PROVINCES[p]["weight"] for p in provinces]
    return random.choices(provinces, weights=weights, k=1)[0]


def _choose_city(province: str) -> str:
    """Pick a city within the given province."""
    cities = CITIES_BY_PROVINCE.get(province, ["Unknown"])
    # First city in the list is the biggest — give it more weight
    weights = [3.0] + [1.0] * (len(cities) - 1)
    return random.choices(cities, weights=weights, k=1)[0]


def _generate_cnic(province: str, gender: str) -> str:
    """Generate a CNIC in XXXXX-XXXXXXX-X format.

    Args:
        province: Province name for first digit lookup.
        gender:   'M' or 'F' — last digit is odd for male, even for female.

    Returns:
        Formatted CNIC string.
    """
    province_code = PROVINCES.get(province, {}).get("code", "3")
    first_five = province_code + "".join(random.choices(string.digits, k=4))
    middle_seven = "".join(random.choices(string.digits, k=7))
    if gender == "M":
        last_digit = str(random.choice([1, 3, 5, 7, 9]))
    else:
        last_digit = str(random.choice([0, 2, 4, 6, 8]))
    return f"{first_five}-{middle_seven}-{last_digit}"


def _generate_ntn() -> str:
    """Generate a realistic Pakistani NTN (7-digit + optional suffix)."""
    return "".join(random.choices(string.digits, k=7))


def _vary_name(name: str, probability: float = 0.60) -> str:
    """Possibly return a spelling variation of the first name.

    Args:
        name:        Original name.
        probability: Chance of variation occurring.

    Returns:
        Original or varied name.
    """
    if random.random() < probability and name in NAME_VARIATIONS:
        return random.choice(NAME_VARIATIONS[name])
    return name


def _add_title(name: str, probability: float = 0.10) -> str:
    """Optionally prepend an honorific/title to a name."""
    if random.random() < probability:
        title = random.choice(TITLES)
        return f"{title} {name}"
    return name


def _maybe_null(value: Any, null_prob: float = 0.07) -> Any:
    """Return None with the given probability to simulate missing data."""
    if random.random() < null_prob:
        return None
    return value


def _generate_phone() -> tuple[str, str]:
    """Generate a Pakistani phone number and return (number, operator)."""
    operator = random.choice(list(MOBILE_OPERATORS.keys()))
    prefix = random.choice(MOBILE_OPERATORS[operator])
    number = "".join(random.choices(string.digits, k=7))
    return f"{prefix}-{number}", operator


def _generate_vehicle_reg(province: str) -> str:
    """Generate a vehicle registration number for a given province."""
    prefix = random.choice(VEHICLE_REG_PREFIXES.get(province, ["XXX"]))
    digits = random.randint(1, 9999)
    return f"{prefix}-{digits}"


def _generate_passport() -> str:
    """Generate a Pakistani passport number."""
    letters = random.choices(string.ascii_uppercase, k=2)
    digits = "".join(random.choices(string.digits, k=7))
    return "".join(letters) + digits


def _pick_vehicle() -> dict[str, Any]:
    """Choose a vehicle type using weighted distribution."""
    weights = [v["weight"] for v in VEHICLE_TYPES]
    chosen = random.choices(VEHICLE_TYPES, weights=weights, k=1)[0]
    return chosen


def _pick_travel_dest() -> dict[str, Any]:
    """Choose a travel destination using weighted distribution."""
    weights = [d["weight"] for d in TRAVEL_DESTINATIONS]
    return random.choices(TRAVEL_DESTINATIONS, weights=weights, k=1)[0]


def _income_for_class(wealth_class: str) -> float:
    """Generate a declared income based on wealth class."""
    ranges = {
        "low":    (200_000, 800_000),
        "middle": (600_000, 3_000_000),
        "upper":  (2_000_000, 10_000_000),
        "high":   (5_000_000, 50_000_000),
    }
    lo, hi = ranges.get(wealth_class, (200_000, 800_000))
    return round(np.random.lognormal(mean=np.log((lo + hi) / 2), sigma=0.3))


def _tax_for_income(income: float, is_filer: bool) -> float:
    """Compute approximate tax paid based on Pakistani tax slabs."""
    if income <= 600_000:
        tax = 0
    elif income <= 1_200_000:
        tax = (income - 600_000) * 0.025
    elif income <= 2_400_000:
        tax = 15_000 + (income - 1_200_000) * 0.125
    elif income <= 3_600_000:
        tax = 165_000 + (income - 2_400_000) * 0.225
    elif income <= 6_000_000:
        tax = 435_000 + (income - 3_600_000) * 0.275
    else:
        tax = 1_095_000 + (income - 6_000_000) * 0.35
    # Non-filers typically don't pay or pay less
    if not is_filer:
        tax = tax * random.uniform(0, 0.1)
    # Add some noise
    tax = tax * random.uniform(0.85, 1.15)
    return round(max(0, tax))


# =====================================================================
# Citizen master profile generator
# =====================================================================

def _generate_citizen_profiles(n: int) -> list[dict[str, Any]]:
    """Generate n base citizen profiles with demographics.

    Args:
        n: Number of citizens to generate.

    Returns:
        List of citizen profile dicts.
    """
    citizens: list[dict[str, Any]] = []

    # Pre-determine flags
    anomaly_indices = set(random.sample(range(n), k=int(n * ANOMALY_RATE)))
    extreme_indices = set(random.sample(list(anomaly_indices), k=int(n * EXTREME_ANOMALY_RATE)))
    filer_indices = set(random.sample(range(n), k=int(n * TAX_FILING_RATE)))
    non_filer_ids = set(range(n)) - filer_indices
    active_non_filers = set(random.sample(list(non_filer_ids), k=int(len(non_filer_ids) * NON_FILER_WITH_ACTIVITY)))

    for i in range(n):
        province = _choose_province()
        city = _choose_city(province)
        gender = random.choice(["M", "F"])

        if gender == "M":
            first_name = random.choice(FIRST_NAMES_MALE)
            father_first = random.choice(FIRST_NAMES_MALE)
        else:
            first_name = random.choice(FIRST_NAMES_FEMALE)
            father_first = random.choice(FIRST_NAMES_MALE)

        last_name = random.choice(LAST_NAMES)
        father_last = random.choice(LAST_NAMES)

        canonical_first = first_name
        canonical_name = f"{first_name} {last_name}"
        father_name = f"{father_first} {father_last}"

        cnic = _generate_cnic(province, gender)
        is_filer = i in filer_indices
        is_anomaly = i in anomaly_indices
        is_extreme = i in extreme_indices
        has_activity = i in active_non_filers or is_filer

        # Assign wealth class
        if is_extreme:
            wealth_class = "high"
        elif is_anomaly:
            wealth_class = random.choice(["upper", "high"])
        else:
            wealth_class = random.choices(
                ["low", "middle", "upper", "high"],
                weights=[0.35, 0.40, 0.18, 0.07],
            )[0]

        # Explicitly categorize for the UI (Positive, Medium, Negative)
        if is_extreme:
            category = "Negative"
        elif is_anomaly or (not is_filer and has_activity):
            category = "Medium"
        else:
            category = "Positive"

        # Declared income — anomalies report much lower
        if is_extreme:
            declared_income = round(random.uniform(0, 200_000))
        elif is_anomaly:
            real_income = _income_for_class(wealth_class)
            declared_income = round(real_income * random.uniform(0.05, 0.25))
        else:
            declared_income = _income_for_class(wealth_class)

        tax_paid = _tax_for_income(declared_income, is_filer)
        if is_extreme:
            tax_paid = 0

        ntn = _generate_ntn() if is_filer else None

        citizens.append({
            "citizen_id": f"CIT-{i + 1:06d}",
            "cnic": cnic,
            "canonical_first": canonical_first,
            "canonical_name": canonical_name,
            "first_name": first_name,
            "last_name": last_name,
            "father_name": father_name,
            "ntn": ntn,
            "gender": gender,
            "province": province,
            "city": city,
            "wealth_class": wealth_class,
            "declared_income": declared_income,
            "tax_paid": tax_paid,
            "is_filer": is_filer,
            "is_anomaly": is_anomaly,
            "is_extreme": is_extreme,
            "has_activity": has_activity,
            "category": category,
        })

    return citizens


# =====================================================================
# Record generators for each CSV
# =====================================================================

def _generate_tax_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate tax_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with tax record rows.
    """
    rows: list[dict] = []
    tax_years = [2020, 2021, 2022, 2023, 2024]
    for c in citizens:
        # Each citizen gets 1-3 years of records
        n_years = random.choices([1, 2, 3], weights=[0.3, 0.4, 0.3])[0]
        selected_years = sorted(random.sample(tax_years, k=min(n_years, len(tax_years))))
        for year in selected_years:
            display_name = _add_title(_vary_name(c["first_name"]) + " " + c["last_name"])
            income_variation = c["declared_income"] * random.uniform(0.85, 1.15)
            tax_variation = c["tax_paid"] * random.uniform(0.90, 1.10)
            rows.append({
                "citizen_id": c["citizen_id"],
                "cnic": c["cnic"],
                "name": _maybe_null(display_name, 0.02),
                "father_name": _maybe_null(c["father_name"], 0.08),
                "ntn": _maybe_null(c["ntn"], 0.05) if c["ntn"] else None,
                "declared_income": _maybe_null(round(income_variation), 0.03),
                "tax_paid": _maybe_null(round(max(0, tax_variation)), 0.03),
                "filing_status": "Filer" if c["is_filer"] else "Non-Filer",
                "tax_year": year,
                "province": c["province"],
                "city": _maybe_null(c["city"], 0.04),
            })
    return pd.DataFrame(rows)


def _generate_vehicle_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate vehicle_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with vehicle record rows.
    """
    rows: list[dict] = []
    record_id = 1
    for c in citizens:
        # Decide how many vehicles based on wealth class
        vehicle_counts = {
            "low": (0, [0.75, 0.20, 0.05]),
            "middle": (0, [0.40, 0.45, 0.15]),
            "upper": (0, [0.10, 0.40, 0.35, 0.15]),
            "high": (0, [0.05, 0.20, 0.35, 0.30, 0.10]),
        }
        max_v, weights = vehicle_counts.get(c["wealth_class"], (0, [0.75, 0.25]))
        n_vehicles = random.choices(range(len(weights)), weights=weights)[0]

        for _ in range(n_vehicles):
            vehicle = _pick_vehicle()
            # Force luxury vehicles for anomalies
            if c["is_extreme"] and random.random() < 0.6:
                luxury = [v for v in VEHICLE_TYPES if v["min_val"] >= 10_000_000]
                vehicle = random.choice(luxury) if luxury else vehicle
            elif c["is_anomaly"] and random.random() < 0.4:
                upper = [v for v in VEHICLE_TYPES if v["min_val"] >= 5_000_000]
                vehicle = random.choice(upper) if upper else vehicle

            market_value = random.randint(vehicle["min_val"], vehicle["max_val"])
            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]
            year = random.randint(2015, 2025)

            rows.append({
                "record_id": f"VEH-{record_id:06d}",
                "owner_name": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "registration_number": _generate_vehicle_reg(c["province"]),
                "vehicle_type": vehicle["type"],
                "vehicle_make": vehicle["make"],
                "vehicle_model": vehicle["model"],
                "vehicle_year": _maybe_null(year, 0.06),
                "market_value": _maybe_null(market_value, 0.04),
                "province": c["province"],
            })
            record_id += 1
    return pd.DataFrame(rows)


def _generate_property_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate property_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with property record rows.
    """
    rows: list[dict] = []
    record_id = 1
    for c in citizens:
        prop_counts = {
            "low": (0, [0.65, 0.30, 0.05]),
            "middle": (0, [0.30, 0.50, 0.15, 0.05]),
            "upper": (0, [0.10, 0.30, 0.35, 0.20, 0.05]),
            "high": (0, [0.05, 0.10, 0.25, 0.35, 0.20, 0.05]),
        }
        _, weights = prop_counts.get(c["wealth_class"], (0, [0.70, 0.30]))
        n_props = random.choices(range(len(weights)), weights=weights)[0]

        for _ in range(n_props):
            city = c["city"]
            prop_type = random.choice(PROPERTY_TYPES)
            areas = AREA_NAMES_BY_CITY.get(city, [f"{city} Area {i}" for i in range(1, 6)])
            area = random.choice(areas)
            address = f"{random.randint(1, 500)}-{area}, {city}"

            if prop_type == "Agricultural Land":
                size_marla = random.randint(100, 2000)
                val_range = PROPERTY_VALUE_PER_MARLA.get(city, PROPERTY_VALUE_PER_MARLA["_default"])
                per_marla = random.randint(val_range[0] // 5, val_range[1] // 5)
            elif prop_type == "Flat":
                size_marla = random.randint(3, 12)
                val_range = PROPERTY_VALUE_PER_MARLA.get(city, PROPERTY_VALUE_PER_MARLA["_default"])
                per_marla = random.randint(val_range[0], val_range[1])
            elif prop_type == "Plot":
                size_marla = random.choice([5, 7, 10, 14, 20])
                val_range = PROPERTY_VALUE_PER_MARLA.get(city, PROPERTY_VALUE_PER_MARLA["_default"])
                per_marla = random.randint(val_range[0], val_range[1])
            else:
                size_marla = random.choice([3, 5, 7, 10, 14, 20])
                val_range = PROPERTY_VALUE_PER_MARLA.get(city, PROPERTY_VALUE_PER_MARLA["_default"])
                per_marla = random.randint(val_range[0], val_range[1])

            property_value = size_marla * per_marla

            # Anomalies: force expensive property
            if c["is_extreme"] and random.random() < 0.7:
                property_value = random.randint(30_000_000, 200_000_000)
            elif c["is_anomaly"] and random.random() < 0.4:
                property_value = random.randint(15_000_000, 80_000_000)

            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]
            rows.append({
                "record_id": f"PROP-{record_id:06d}",
                "owner_name": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "address": _maybe_null(address, 0.06),
                "area_name": _maybe_null(area, 0.04),
                "city": _maybe_null(city, 0.02),
                "province": c["province"],
                "property_type": prop_type,
                "size_marla": _maybe_null(size_marla, 0.05),
                "property_value": _maybe_null(property_value, 0.04),
            })
            record_id += 1
    return pd.DataFrame(rows)


def _generate_utility_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate utility_bills.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with utility bill rows.
    """
    rows: list[dict] = []
    record_id = 1

    bill_ranges = {
        "low":    (500, 5_000),
        "middle": (3_000, 15_000),
        "upper":  (8_000, 40_000),
        "high":   (15_000, 100_000),
    }

    for c in citizens:
        if not c["has_activity"] and random.random() < 0.4:
            continue

        province = c["province"]
        city = c["city"]
        lo, hi = bill_ranges.get(c["wealth_class"], (500, 5_000))

        # Electricity bill
        elec_provider = random.choice(ELECTRICITY_PROVIDERS.get(province, ["WAPDA"]))
        elec_amount = random.randint(lo, hi)

        areas = AREA_NAMES_BY_CITY.get(city, [f"{city} Area"])
        address = f"{random.randint(1, 500)}-{random.choice(areas)}, {city}"
        display_name = _vary_name(c["first_name"]) + " " + c["last_name"]

        rows.append({
            "record_id": f"UTIL-{record_id:06d}",
            "account_holder": _maybe_null(display_name, 0.05),
            "cnic": _maybe_null(c["cnic"], 0.04),
            "utility_type": "electricity",
            "provider": elec_provider,
            "monthly_amount": _maybe_null(elec_amount, 0.05),
            "address": _maybe_null(address, 0.06),
            "city": _maybe_null(city, 0.03),
        })
        record_id += 1

        # Gas bill (not everyone has gas)
        if random.random() < 0.70:
            gas_provider = GAS_PROVIDERS.get(province, "SNGPL")
            gas_amount = random.randint(lo // 2, hi // 2)
            rows.append({
                "record_id": f"UTIL-{record_id:06d}",
                "account_holder": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.04),
                "utility_type": "gas",
                "provider": gas_provider,
                "monthly_amount": _maybe_null(gas_amount, 0.05),
                "address": _maybe_null(address, 0.06),
                "city": _maybe_null(city, 0.03),
            })
            record_id += 1

    return pd.DataFrame(rows)


def _generate_banking_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate banking_indicators.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with banking indicator rows.
    """
    rows: list[dict] = []
    record_id = 1

    balance_ranges = {
        "low":    (5_000, 200_000),
        "middle": (50_000, 2_000_000),
        "upper":  (500_000, 15_000_000),
        "high":   (2_000_000, 100_000_000),
    }

    txn_ranges = {
        "low":    (2, 30),
        "middle": (10, 80),
        "upper":  (30, 200),
        "high":   (50, 500),
    }

    for c in citizens:
        if not c["has_activity"] and random.random() < 0.5:
            continue

        n_accounts = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10])[0]
        if c["wealth_class"] in ("upper", "high"):
            n_accounts = random.choices([1, 2, 3, 4], weights=[0.20, 0.35, 0.30, 0.15])[0]

        for _ in range(n_accounts):
            lo_b, hi_b = balance_ranges.get(c["wealth_class"], (5_000, 200_000))
            lo_t, hi_t = txn_ranges.get(c["wealth_class"], (2, 30))
            avg_balance = random.randint(lo_b, hi_b)
            monthly_txn = random.randint(lo_t, hi_t)
            bank = random.choice(BANKS)
            acct_type = random.choices(
                ["Current", "Savings", "Business"],
                weights=[0.35, 0.45, 0.20],
            )[0]
            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]

            rows.append({
                "record_id": f"BANK-{record_id:06d}",
                "account_holder": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "monthly_transactions": _maybe_null(monthly_txn, 0.06),
                "avg_balance": _maybe_null(avg_balance, 0.04),
                "bank_name": bank,
                "account_type": acct_type,
            })
            record_id += 1

    return pd.DataFrame(rows)


def _generate_travel_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate travel_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with travel record rows.
    """
    rows: list[dict] = []
    record_id = 1

    for c in citizens:
        # Travel probability based on wealth
        travel_probs = {"low": 0.05, "middle": 0.20, "upper": 0.50, "high": 0.80}
        prob = travel_probs.get(c["wealth_class"], 0.10)
        # Anomalies travel more regardless
        if c["is_anomaly"]:
            prob = max(prob, 0.60)
        if c["is_extreme"]:
            prob = 0.90

        if random.random() > prob:
            continue

        n_trips = random.choices([1, 2, 3, 4], weights=[0.40, 0.35, 0.15, 0.10])[0]
        if c["is_extreme"]:
            n_trips = random.randint(2, 6)

        passport = _generate_passport()

        for _ in range(n_trips):
            dest = _pick_travel_dest()
            class_dist = dest["class_dist"]
            travel_class = random.choices(
                list(class_dist.keys()),
                weights=list(class_dist.values()),
            )[0]
            # Extreme anomalies fly business/first more
            if c["is_extreme"] and random.random() < 0.5:
                travel_class = random.choice(["Business", "First"])

            dep_date = fake.date_between(start_date="-3y", end_date="today")
            duration = random.randint(3, 30)
            ret_date = dep_date + timedelta(days=duration)
            airline = random.choice(AIRLINES)
            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]

            rows.append({
                "record_id": f"TRVL-{record_id:06d}",
                "traveler_name": _maybe_null(display_name, 0.04),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "passport_number": _maybe_null(passport, 0.05),
                "destination": dest["country"],
                "airline": _maybe_null(airline, 0.04),
                "travel_class": travel_class,
                "departure_date": str(dep_date),
                "return_date": _maybe_null(str(ret_date), 0.06),
            })
            record_id += 1

    return pd.DataFrame(rows)


def _generate_business_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate business_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with business record rows.
    """
    rows: list[dict] = []
    record_id = 1

    revenue_ranges = {
        "low":    (500_000, 5_000_000),
        "middle": (2_000_000, 20_000_000),
        "upper":  (10_000_000, 100_000_000),
        "high":   (50_000_000, 500_000_000),
    }

    for c in citizens:
        biz_probs = {"low": 0.05, "middle": 0.15, "upper": 0.35, "high": 0.55}
        prob = biz_probs.get(c["wealth_class"], 0.10)
        if c["is_anomaly"]:
            prob = max(prob, 0.40)

        if random.random() > prob:
            continue

        n_biz = random.choices([1, 2, 3], weights=[0.60, 0.30, 0.10])[0]
        for _ in range(n_biz):
            biz_type = random.choice(BUSINESS_TYPES)
            role = random.choices(
                ["Director", "Owner", "Partner"],
                weights=[0.30, 0.50, 0.20],
            )[0]
            share_pct = random.choice([25, 33, 50, 51, 60, 75, 100]) if role != "Director" else random.choice([0, 5, 10, 20, 25, 50])
            lo, hi = revenue_ranges.get(c["wealth_class"], (500_000, 5_000_000))
            annual_revenue = random.randint(lo, hi)
            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]
            biz_name = f"{random.choice(LAST_NAMES)} {biz_type} {'Pvt Ltd' if random.random() < 0.3 else 'Enterprises'}"

            rows.append({
                "record_id": f"BIZ-{record_id:06d}",
                "business_name": biz_name,
                "owner_name": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "business_type": biz_type,
                "role": role,
                "share_percentage": _maybe_null(share_pct, 0.06),
                "annual_revenue": _maybe_null(annual_revenue, 0.05),
                "registration_city": _maybe_null(c["city"], 0.04),
            })
            record_id += 1

    return pd.DataFrame(rows)


def _generate_mobile_records(citizens: list[dict]) -> pd.DataFrame:
    """Generate mobile_records.csv data.

    Args:
        citizens: List of citizen profile dicts.

    Returns:
        DataFrame with mobile record rows.
    """
    rows: list[dict] = []
    record_id = 1

    for c in citizens:
        n_phones = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10])[0]
        for _ in range(n_phones):
            phone, operator = _generate_phone()
            reg_date = fake.date_between(start_date="-8y", end_date="today")
            display_name = _vary_name(c["first_name"]) + " " + c["last_name"]

            rows.append({
                "record_id": f"MOB-{record_id:06d}",
                "owner_name": _maybe_null(display_name, 0.05),
                "cnic": _maybe_null(c["cnic"], 0.03),
                "phone_number": phone,
                "operator": operator,
                "registration_date": _maybe_null(str(reg_date), 0.04),
            })
            record_id += 1

    return pd.DataFrame(rows)


# =====================================================================
# Main orchestrator
# =====================================================================

def generate_all_datasets() -> dict[str, Path]:
    """Generate all 8 synthetic CSV files and save to SYNTHETIC_DIR.

    Returns:
        Dictionary mapping dataset name to file path.
    """
    print(f"Generating {NUM_CITIZENS:,} synthetic citizen profiles ...")
    citizens = _generate_citizen_profiles(NUM_CITIZENS)
    print(f"  [OK] {len(citizens):,} citizen profiles created")

    generators: dict[str, Any] = {
        "tax_records":        (_generate_tax_records, citizens),
        "vehicle_records":    (_generate_vehicle_records, citizens),
        "property_records":   (_generate_property_records, citizens),
        "utility_bills":      (_generate_utility_records, citizens),
        "banking_indicators": (_generate_banking_records, citizens),
        "travel_records":     (_generate_travel_records, citizens),
        "business_records":   (_generate_business_records, citizens),
        "mobile_records":     (_generate_mobile_records, citizens),
    }

    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, Path] = {}

    for name, (gen_func, args) in generators.items():
        print(f"  Generating {name} ...")
        df = gen_func(args)
        path = SYNTHETIC_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        output_paths[name] = path
        null_pct = df.isnull().mean().mean() * 100
        print(f"    [OK] {len(df):,} rows | {len(df.columns)} cols | {null_pct:.1f}% nulls → {path.name}")

    # Also save a ground-truth file for evaluation
    gt_df = pd.DataFrame(citizens)
    gt_path = SYNTHETIC_DIR / "_ground_truth.csv"
    gt_df.to_csv(gt_path, index=False)
    print(f"\n  Ground truth saved → {gt_path.name}")

    _print_summary(citizens, output_paths)
    return output_paths


def _print_summary(citizens: list[dict], paths: dict[str, Path]) -> None:
    """Print a summary of the generated data.

    Args:
        citizens: List of citizen profile dicts.
        paths:    Dictionary of dataset names to file paths.
    """
    n = len(citizens)
    n_filers = sum(1 for c in citizens if c["is_filer"])
    n_anomaly = sum(1 for c in citizens if c["is_anomaly"])
    n_extreme = sum(1 for c in citizens if c["is_extreme"])
    n_active_nf = sum(1 for c in citizens if c["has_activity"] and not c["is_filer"])

    print("\n" + "=" * 60)
    print("  SYNTHETIC DATA GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Total citizens:            {n:,}")
    print(f"  Tax filers:                {n_filers:,} ({n_filers / n * 100:.1f}%)")
    print(f"  Non-filers:                {n - n_filers:,} ({(n - n_filers) / n * 100:.1f}%)")
    print(f"  Anomalies (mismatch):      {n_anomaly:,} ({n_anomaly / n * 100:.1f}%)")
    print(f"  Extreme outliers:          {n_extreme:,} ({n_extreme / n * 100:.1f}%)")
    print(f"  Active non-filers:         {n_active_nf:,}")
    print(f"  Output directory:          {SYNTHETIC_DIR}")
    print("=" * 60)

    for name, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"    {name + '.csv':<28s} {size_kb:>8.1f} KB")
    print()


# =====================================================================
# CLI entry point
# =====================================================================
if __name__ == "__main__":
    generate_all_datasets()
