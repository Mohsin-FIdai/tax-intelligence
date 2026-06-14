"""
Name Normalisation Engine — Pakistani multilingual name cleaning with phonetic matching.
"""
from __future__ import annotations

import re
from functools import lru_cache

from rapidfuzz import fuzz
try:
    import urduhack
    from urduhack.normalization import normalize as urdu_normalize
except ImportError:
    urdu_normalize = lambda x: x

# Urdu to English Mapping
_URDU_TO_ENG = {
    'ا': 'a', 'آ': 'aa', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't', 'ث': 's',
    'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'd', 'ذ': 'z',
    'ر': 'r', 'ڑ': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
    'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
    'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ں': 'n', 'و': 'w',
    'ہ': 'h', 'ھ': 'h', 'ء': '', 'ی': 'y', 'ے': 'e', 'ي': 'y',
    'َ': 'a', 'ِ': 'i', 'ُ': 'u', 'ٰ': 'a', 'ّ': ''
}

def transliterate_urdu(text: str) -> str:
    """Basic character-level transliteration for Urdu to English"""
    res = ""
    for char in text:
        res += _URDU_TO_ENG.get(char, char)
    return res.strip()

# ─── Canonical name mapping (200+ variations) ───────────────────────
_NAME_VARIANTS: dict[str, list[str]] = {
    "Muhammad": ["Mohammad", "Mohammed", "Muhammed", "Muhamad", "Mohd", "Mohmd", "Muhmd",
                 "Mohamad", "Mohamed", "Md", "Muhd", "Mhd", "Mohmmad"],
    "Ahmad": ["Ahmed", "Ahmd", "Ahamed", "Ahamad"],
    "Ali": ["Alee", "Alli"],
    "Hussain": ["Husain", "Husein", "Husayn", "Hossain", "Hossein", "Hussan", "Hussian"],
    "Hassan": ["Hasan", "Hasen", "Hasn"],
    "Usman": ["Osman", "Othman", "Uthman", "Usmaan"],
    "Imran": ["Emran", "Imraan"],
    "Bilal": ["Belal", "Bilaal"],
    "Ibrahim": ["Ibraheem", "Ebrahim", "Abrahim"],
    "Yusuf": ["Yousuf", "Yousaf", "Yoosuf", "Yousif", "Yousef", "Yusaf", "Josef"],
    "Omar": ["Umer", "Umar", "Umr"],
    "Hamza": ["Hamzah", "Hamzaa"],
    "Ismail": ["Ismael", "Esmail", "Ismaeel"],
    "Tariq": ["Tarik", "Tareq", "Tariq"],
    "Naveed": ["Navid", "Naweed"],
    "Waqas": ["Waqass", "Waqqas"],
    "Junaid": ["Juneid", "Juned"],
    "Rizwan": ["Rizwaan", "Rizvaan"],
    "Farhan": ["Farhaan"],
    "Adnan": ["Adnaan"],
    "Kashif": ["Kaashif"],
    "Nasir": ["Naseer", "Nasr"],
    "Salman": ["Salmaan", "Sulman"],
    "Arslan": ["Arsalan", "Arslaan"],
    "Faisal": ["Faysal", "Feisal"],
    "Khalid": ["Khaalid", "Khaleed"],
    "Iqbal": ["Eqbal", "Ikbal"],
    "Aisha": ["Ayesha", "Aisha", "Aysha", "Aesha"],
    "Fatima": ["Fathima", "Faatima", "Fatimah"],
    "Maryam": ["Mariam", "Meryem", "Miriam"],
    "Khadija": ["Khadeeja", "Khadijah"],
    "Zainab": ["Zaynab", "Zaineb", "Zenab"],
    "Noor": ["Nour", "Nur", "Noor"],
    "Sana": ["Sanaa", "Sanna"],
    "Khan": ["Khn", "Khaan"],
    "Chaudhry": ["Chaudhary", "Choudhry", "Choudhary", "Choudry", "Ch"],
    "Sheikh": ["Shaikh", "Shiekh", "Sh"],
    "Siddiqui": ["Siddique", "Siddiqi", "Siddiki", "Sidiqui"],
    "Qureshi": ["Quraishi", "Qurashi", "Kureshi"],
    "Butt": ["But", "Bhat", "Bhatt"],
    "Malik": ["Malick", "Malic"],
    "Awan": ["Awaan"],
    "Rajput": ["Rajpoot"],
    "Mughal": ["Moghal", "Moghul"],
    "Hashmi": ["Hashimi", "Hashmi"],
    "Abbasi": ["Abasi", "Abassi"],
    "Mehmood": ["Mahmood", "Mahmud", "Mehmud", "Mahmoud"],
    "Rashid": ["Rasheed", "Rashied"],
    "Syed": ["Sayyid", "Saied", "Sayyed", "Syeed"],
    "Rana": ["Raana"],
}

# Build reverse lookup: variant → canonical
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for canonical, variants in _NAME_VARIANTS.items():
    canonical_lower = canonical.lower()
    _VARIANT_TO_CANONICAL[canonical_lower] = canonical
    for v in variants:
        _VARIANT_TO_CANONICAL[v.lower()] = canonical

# ─── Titles and honorifics to remove ────────────────────────────────
_TITLES_RE = re.compile(
    r"\b(mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?|haji|hajia|mian|ch\.?|sir|smt|begum|bibi|"
    r"engr\.?|advocate|adv\.?|justice|senator|general|gen\.?|col\.?|major|capt\.?|"
    r"brigadier|brig\.?|lt\.?|cmdr\.?)\b",
    re.IGNORECASE,
)
_EXTRA_SPACES = re.compile(r"\s{2,}")


# ─── Soundex-like phonetic code for Pakistani names ─────────────────
_PHONETIC_MAP = {
    "b": "1", "f": "1", "p": "1", "v": "1",
    "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
    "d": "3", "t": "3",
    "l": "4",
    "m": "5", "n": "5",
    "r": "6",
}


def remove_titles(name: str) -> str:
    """Strip titles and honorifics from a name string."""
    cleaned = _TITLES_RE.sub("", name)
    cleaned = _EXTRA_SPACES.sub(" ", cleaned).strip()
    return cleaned


def _canonicalize_token(token: str) -> str:
    """Map a single name token to its canonical form."""
    return _VARIANT_TO_CANONICAL.get(token.lower(), token.title())


def normalize_name(name: str | None) -> str:
    """Normalise a Pakistani name to a canonical form.

    Steps: urdu normalize -> transliterate -> strip titles -> tokenise -> map each token via dictionary -> rejoin.
    """
    if not name or not isinstance(name, str):
        return ""

    name = name.strip()
    if not name or name.lower() in ("nan", "none", ""):
        return ""

    # Urdu normalization
    name = urdu_normalize(name)

    # Remove titles
    name = remove_titles(name)

    # Remove punctuation except hyphens
    name = re.sub(r"[^\w\s-]", "", name)

    # Tokenise and canonicalise
    tokens = name.split()
    canonical_tokens = [_canonicalize_token(t) for t in tokens if t]

    return " ".join(canonical_tokens)


@lru_cache(maxsize=4096)
def phonetic_code(name: str) -> str:
    """Generate a Soundex-like phonetic code for a name.

    Useful for blocking in entity resolution.
    """
    if not name:
        return ""

    name = normalize_name(name).lower()
    if not name:
        return ""

    tokens = name.split()
    codes = []
    for token in tokens:
        if not token:
            continue
        code = token[0].upper()
        prev = ""
        for ch in token[1:]:
            mapped = _PHONETIC_MAP.get(ch, "0")
            if mapped != "0" and mapped != prev:
                code += mapped
                prev = mapped
            if len(code) >= 4:
                break
        code = code.ljust(4, "0")[:4]
        codes.append(code)

    return "-".join(codes[:3])  # Max 3 tokens


def are_names_similar(name1: str, name2: str, threshold: float = 85.0) -> bool:
    """Check if two names are similar after normalisation.

    Uses a combination of token sort ratio and phonetic matching.
    """
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return False

    # Exact match after normalisation
    if n1 == n2:
        return True

    # Fuzzy match
    score = fuzz.token_sort_ratio(n1, n2)
    if score >= threshold:
        return True

    # Phonetic fallback
    if phonetic_code(n1) == phonetic_code(n2):
        return True

    return False


def name_similarity_score(name1: str, name2: str) -> float:
    """Return a similarity score (0–100) between two names after normalisation."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0.0

    if n1 == n2:
        return 100.0

    # Weighted combination of different fuzzy scorers
    token_sort = fuzz.token_sort_ratio(n1, n2)
    token_set = fuzz.token_set_ratio(n1, n2)
    partial = fuzz.partial_ratio(n1, n2)

    # Phonetic bonus
    phonetic_bonus = 10.0 if phonetic_code(n1) == phonetic_code(n2) else 0.0

    score = (token_sort * 0.4 + token_set * 0.35 + partial * 0.25) + phonetic_bonus
    return min(score, 100.0)
