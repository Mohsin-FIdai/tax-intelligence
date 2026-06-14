import pandas as pd
from rapidfuzz import process as rapidfuzz_process, fuzz as rapidfuzz_fuzz
from thefuzz import process as thefuzz_process, fuzz as thefuzz_fuzz

# Attempt to load urduhack for normalization, handling missing tensorflow gracefully
try:
    import sys
    # Patch sys.modules to bypass tensorflow import error in urduhack if TF is missing
    class DummyTF:
        class keras:
            class models:
                load_model = lambda *args, **kwargs: None
    sys.modules['tensorflow'] = DummyTF()
    from urduhack.normalization import normalize
except ImportError:
    def normalize(text):
        return text

try:
    from transliterate import translit
except ImportError:
    translit = lambda text, lang: text

from core.entity_resolution.roman_urdu import transliterate as custom_transliterate

def unify_query(query: str) -> tuple[str, str, str]:
    """
    Returns (clean_query, urdu_transliteration, transliterate_lib_output)
    """
    if not query:
        return "", "", ""
        
    query = str(query).strip()
    
    # 1. urduhack normalization (if it's already urdu)
    normalized = normalize(query)
    
    # 2. Custom Roman-to-Urdu (highly tuned for PK names)
    custom_urdu = custom_transliterate(normalized)
    
    # 3. Transliterate library fallback (e.g. Russian/etc. though not great for PK without packs)
    try:
        # Just use it as requested by the user, although it might fail for unsupported lang 'ur'
        lib_urdu = translit(normalized, 'ur')
    except Exception:
        lib_urdu = normalized
        
    return normalized, custom_urdu, lib_urdu


def advanced_fuzzy_search(
    df: pd.DataFrame, 
    query: str, 
    search_columns: list[str] = ["canonical_name", "cnic"],
    limit: int = 10,
    score_cutoff: float = 75.0
) -> pd.DataFrame:
    """
    A unified search engine utilizing rapidfuzz, thefuzz, urduhack, and transliterate.
    """
    if not query or df.empty:
        return pd.DataFrame(columns=df.columns)
        
    query_norm, query_urdu, query_translit = unify_query(query)
    clean_cnic = query.replace("-", "")

    # Stage 1: Fast Exact / Substring Matching (Pandas vectorized)
    masks = []
    for col in search_columns:
        if col not in df.columns: continue
        
        if col == "cnic":
            masks.append(df[col].str.replace("-", "").str.contains(clean_cnic, case=False, na=False, regex=False))
        else:
            masks.append(df[col].str.contains(query_norm, case=False, na=False, regex=False))
            masks.append(df[col].str.contains(query_urdu, case=False, na=False, regex=True))
            masks.append(df[col].str.contains(query_translit, case=False, na=False, regex=False))
            
    final_mask = masks[0]
    for m in masks[1:]:
        final_mask = final_mask | m
        
    exact_matches = df[final_mask]
    
    # If we found enough exact/substring matches, return them immediately
    if len(exact_matches) >= limit:
        return exact_matches.head(limit)

    # Stage 2: Deep Fuzzy Matching (using rapidfuzz and thefuzz)
    # Extract the names to search against
    if "canonical_name" not in df.columns:
        return exact_matches
        
    choices = df["canonical_name"].fillna("").tolist()
    
    # Rapidfuzz for English
    rf_matches = rapidfuzz_process.extract(
        query_norm, choices, 
        scorer=rapidfuzz_fuzz.WRatio, 
        limit=limit, 
        score_cutoff=score_cutoff
    )
    
    # thefuzz for Urdu
    from core.entity_resolution.roman_urdu import transliterate_plain
    plain_urdu = transliterate_plain(query_norm)
    tf_matches = thefuzz_process.extract(
        plain_urdu,
        choices, 
        scorer=thefuzz_fuzz.WRatio, 
        limit=limit
    )
    
    # Combine results
    best_names = set([m[0] for m in rf_matches])
    for m in tf_matches:
        if m[1] >= score_cutoff:
            best_names.add(m[0])
            
    if best_names:
        fuzzy_mask = df["canonical_name"].isin(best_names)
        fuzzy_matches = df[fuzzy_mask]
        
        # Merge exact and fuzzy
        combined = pd.concat([exact_matches, fuzzy_matches]).drop_duplicates()
        return combined.head(limit)
        
    return exact_matches
