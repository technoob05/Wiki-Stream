"""
Stage 05: STATISTICAL USER ATTRIBUTION & FINGERPRINTING v3.0
------------------------------------------------------------
Input:  data/{lang}/processed/{timestamp}_classified.csv
Output: data/{lang}/processed/{timestamp}_attributed.csv
        vandal_fingerprints.json

Theoretical Foundation:
- Stylometric analysis: authorship attribution via writing style
  (Stamatatos, 2009 — "A Survey of Modern Authorship Attribution Methods")
- Writeprints-lite: expanded feature space with vocabulary richness metrics
  (Abbasi & Chen, 2008 — type-token ratio, hapax legomena)
- Cosine similarity on n-gram vectors (standard in IR/NLP literature)
- Mahalanobis distance with Minimum Covariance Determinant (MCD)
  (Rousseeuw, 1984 — robust to outlier contamination up to 50%)
- Normalized Compression Distance (Li et al., 2004)
  — parameter-free universal similarity, captures structural patterns
- Benford's Law deviation for edit size distribution anomaly
  (Newcomb-Benford Law — detects non-natural edit patterns)
- Adaptive threshold: mu + 2*sigma of self-similarity distribution
- Output: DS mass function for attribution evidence
------------------------------------------------------------
"""

import csv
import json
import re
import math
import zlib
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

# -- Config --
DATA_DIR = Path(__file__).parent / "data"
FINGERPRINT_DB = Path(__file__).parent / "vandal_fingerprints.json"

# English function words (style markers, content-independent)
FUNCTION_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "of", "in", "to",
    "for", "with", "on", "at", "from", "by", "as", "or", "and", "but",
    "if", "not", "no", "it", "this", "that", "they", "he", "she", "we",
}

# Top character bigrams in English (for n-gram frequency vectors)
TOP_BIGRAMS = [
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd",
    "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar",
    "st", "to", "nt", "ng", "se", "ha", "as", "ou", "io", "le",
    "ve", "co", "me", "de", "hi", "ri", "ro", "ic", "ne", "ea",
    "ra", "ce", "li", "ch", "ll", "be", "ma", "si", "om", "ur",
]


# ================================================================
# FEATURE EXTRACTION
# ================================================================

def extract_style(text: str) -> dict | None:
    """
    Extract multi-dimensional stylometric fingerprint.

    Features (3 categories):
    1. Lexical Ratios: punctuation%, capitalization%, digit%, exclamation%, markup%
    2. Word-Level: mean word length, std word length, function word ratio
    3. Character N-grams: frequency vector of top 50 bigrams (for cosine similarity)
    """
    if not text or len(text) < 10:
        return None

    total_chars = len(text)
    text_lower = text.lower()

    # -- Lexical Ratios --
    punc = len(re.findall(r'[^\w\s]', text))
    caps = len(re.findall(r'[A-Z]', text))
    digits = len(re.findall(r'\d', text))
    exclaims = text.count("!")
    markup = text.count("[") + text.count("{") + text.count("<")

    # -- Word-Level Features --
    words = text.split()
    word_count = len(words)
    if word_count < 2:
        return None

    word_lengths = [len(w) for w in words]
    mean_wl = sum(word_lengths) / word_count
    std_wl = math.sqrt(sum((l - mean_wl) ** 2 for l in word_lengths) / max(word_count - 1, 1))

    # Function word ratio (content-independent style marker)
    func_count = sum(1 for w in words if w.lower() in FUNCTION_WORDS)
    func_ratio = func_count / word_count

    # -- Vocabulary Richness (Writeprints-lite) --
    # Type-Token Ratio: unique words / total words
    # High TTR = diverse vocabulary (legitimate editor), Low = repetitive (spam)
    words_lower = [w.lower() for w in words]
    unique_words = set(words_lower)
    ttr = len(unique_words) / word_count

    # Hapax Legomena Ratio: words appearing exactly once / total words
    # High hapax = rich vocabulary, Low = formulaic/repetitive
    word_freq = Counter(words_lower)
    hapax = sum(1 for c in word_freq.values() if c == 1)
    hapax_ratio = hapax / word_count

    # Sentence length variation (via punctuation splitting)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 2:
        sent_lengths = [len(s.split()) for s in sentences]
        mean_sl = sum(sent_lengths) / len(sent_lengths)
        std_sl = math.sqrt(sum((l - mean_sl) ** 2 for l in sent_lengths) / max(len(sent_lengths) - 1, 1))
    else:
        std_sl = 0.0

    # -- Character Bigram Frequencies --
    bigram_counts = Counter()
    for i in range(len(text_lower) - 1):
        bg = text_lower[i:i+2]
        if bg.isalpha():
            bigram_counts[bg] += 1

    total_bigrams = sum(bigram_counts.values()) or 1
    bigram_vec = [bigram_counts.get(bg, 0) / total_bigrams for bg in TOP_BIGRAMS]

    return {
        # Lexical ratios
        "punc": round(punc / total_chars, 4),
        "caps": round(caps / total_chars, 4),
        "digits": round(digits / total_chars, 4),
        "excl": round(exclaims / total_chars, 4),
        "mark": round(markup / total_chars, 4),
        # Word-level
        "mean_wl": round(mean_wl, 4),
        "std_wl": round(std_wl, 4),
        "func_ratio": round(func_ratio, 4),
        # Vocabulary richness (Writeprints-lite)
        "ttr": round(ttr, 4),
        "hapax_ratio": round(hapax_ratio, 4),
        "sent_std": round(std_sl, 4),
        "word_count": word_count,
        # N-gram vector
        "bigram_vec": bigram_vec,
    }


# ================================================================
# SIMILARITY METRICS
# ================================================================

def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Cosine similarity for n-gram frequency vectors.
    cos(A, B) = (A . B) / (||A|| * ||B||)

    Standard metric in information retrieval and authorship attribution.
    Range: [0, 1] for non-negative vectors. 1 = identical distribution.
    """
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Extended feature keys for Mahalanobis (includes Writeprints-lite features)
RATIO_KEYS = ["punc", "caps", "digits", "excl", "mark", "mean_wl", "std_wl",
              "func_ratio", "ttr", "hapax_ratio", "sent_std"]


def mahalanobis_similarity(s1: dict, s2: dict, cov_inv: np.ndarray | None) -> float:
    """
    Mahalanobis-based similarity for ratio features.
    D_M(x, y) = sqrt((x-y)^T * S^-1 * (x-y))

    Unlike Euclidean distance, Mahalanobis accounts for feature
    correlations (covariance). If punctuation and capitalization
    are correlated in vandal edits, this metric captures that.

    Uses Minimum Covariance Determinant (MCD) for robust estimation
    when available (Rousseeuw, 1984).

    Returns similarity in [0, 1] via exponential decay: exp(-D_M / scale)
    """
    x = np.array([s1.get(k, 0) for k in RATIO_KEYS])
    y = np.array([s2.get(k, 0) for k in RATIO_KEYS])

    diff = x - y

    if cov_inv is not None:
        d_sq = diff @ cov_inv @ diff
        d_m = math.sqrt(max(d_sq, 0))
    else:
        d_m = np.linalg.norm(diff)

    # Scale factor chosen so that D_M=1 -> similarity ~0.6
    return math.exp(-d_m / 2.0)


def ncd_similarity(s1: dict, s2: dict) -> float:
    """
    Normalized Compression Distance similarity (Li et al., 2004).
    NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))

    Converts NCD distance to similarity: sim = 1 - NCD.
    Parameter-free and universal — captures structural patterns
    (repeated phrases, formatting habits) that character n-grams miss.

    Uses the raw text stored in fingerprint signatures.
    """
    text_a = s1.get("raw_sample", "")
    text_b = s2.get("raw_sample", "")
    if not text_a or not text_b:
        return 0.0

    raw_a = text_a.encode("utf-8")
    raw_b = text_b.encode("utf-8")
    raw_ab = raw_a + raw_b

    c_a = len(zlib.compress(raw_a))
    c_b = len(zlib.compress(raw_b))
    c_ab = len(zlib.compress(raw_ab))

    min_c = min(c_a, c_b)
    max_c = max(c_a, c_b)
    if max_c == 0:
        return 0.0

    ncd = (c_ab - min_c) / max_c
    return max(0.0, min(1.0, 1.0 - ncd))


def combined_similarity(s1: dict, s2: dict, cov_inv: np.ndarray | None) -> float:
    """
    Triple-metric similarity: cosine + Mahalanobis + NCD.

    - Cosine (bigrams): captures writing rhythm
    - Mahalanobis (ratios): captures style with covariance awareness
    - NCD (raw text): captures structural/pattern similarity

    Weights: 0.45 cosine + 0.35 Mahalanobis + 0.20 NCD
    NCD provides independent validation channel — if cosine and Mahalanobis
    agree but NCD disagrees, the match is less reliable.
    """
    cos_sim = cosine_similarity(s1.get("bigram_vec", []), s2.get("bigram_vec", []))
    mah_sim = mahalanobis_similarity(s1, s2, cov_inv)
    ncd_sim = ncd_similarity(s1, s2)

    return 0.45 * cos_sim + 0.35 * mah_sim + 0.20 * ncd_sim


# ================================================================
# ADAPTIVE THRESHOLD
# ================================================================

def compute_adaptive_threshold(db: dict, cov_inv: np.ndarray | None) -> float:
    """
    Compute match threshold from data instead of hardcoding.

    Method: Calculate self-similarity distribution (each known vandal
    vs. all others). Threshold = mean + 2*sigma.
    This means: a match must be >2 standard deviations above the
    average inter-vandal similarity to be considered a true match.

    If insufficient data, fall back to 0.80 (conservative).
    """
    if len(db) < 3:
        return 0.80

    users = list(db.keys())
    sims = []
    for i, u1 in enumerate(users):
        for u2 in users[i+1:]:
            sim = combined_similarity(db[u1]["sig"], db[u2]["sig"], cov_inv)
            sims.append(sim)

    if len(sims) < 3:
        return 0.80

    mean_sim = sum(sims) / len(sims)
    std_sim = math.sqrt(sum((s - mean_sim) ** 2 for s in sims) / len(sims))

    # Threshold = mean + 2*sigma (captures top ~2.5% of similarities)
    threshold = mean_sim + 2 * std_sim
    # Clamp to reasonable range
    return max(0.70, min(0.95, round(threshold, 3)))


# ================================================================
# COVARIANCE ESTIMATION
# ================================================================

def estimate_covariance(db: dict) -> np.ndarray | None:
    """
    Robust inverse covariance estimation via Minimum Covariance Determinant.

    MCD (Rousseeuw, 1984): finds the subset of (n+d+1)/2 observations whose
    empirical covariance has the smallest determinant. This yields a "pure"
    subset resistant to up to ~50% outlier contamination.

    Falls back to regularized sample covariance if MCD unavailable or
    insufficient data.
    """
    if len(db) < 5:
        return None

    data = []
    for user_data in db.values():
        sig = user_data["sig"]
        data.append([sig.get(k, 0) for k in RATIO_KEYS])

    X = np.array(data)
    if X.shape[0] < X.shape[1] + 1:
        return None

    # Try MCD first (robust to outliers in vandal fingerprints)
    try:
        from sklearn.covariance import MinCovDet
        mcd = MinCovDet(random_state=42).fit(X)
        return np.linalg.inv(mcd.covariance_)
    except Exception:
        pass

    # Fallback: regularized sample covariance
    cov = np.cov(X, rowvar=False)
    reg = 0.01 * np.eye(cov.shape[0])
    try:
        return np.linalg.inv(cov + reg)
    except np.linalg.LinAlgError:
        return None


def benford_deviation(edit_sizes: list[int]) -> float:
    """
    Benford's Law deviation for edit size distribution.

    Benford's Law: P(d) = log10(1 + 1/d) for leading digit d ∈ {1,...,9}

    Legitimate editors make diverse edits → edit sizes follow Benford's Law.
    Vandals who repeatedly make similar-sized edits (e.g., always blanking ~500 chars,
    or always inserting ~20 chars of profanity) deviate from Benford's distribution.

    Returns Mean Absolute Deviation (MAD) from expected Benford frequencies.
    Higher MAD = more anomalous edit size pattern.
    """
    if len(edit_sizes) < 5:
        return 0.0

    # Extract leading digits from non-zero edit sizes
    leading_digits = []
    for s in edit_sizes:
        s_abs = abs(s)
        if s_abs > 0:
            leading = int(str(s_abs)[0])
            if 1 <= leading <= 9:
                leading_digits.append(leading)

    if len(leading_digits) < 5:
        return 0.0

    # Expected Benford distribution
    expected = {d: math.log10(1 + 1 / d) for d in range(1, 10)}

    # Observed distribution
    digit_counts = Counter(leading_digits)
    total = len(leading_digits)
    observed = {d: digit_counts.get(d, 0) / total for d in range(1, 10)}

    # Mean Absolute Deviation
    mad = sum(abs(observed[d] - expected[d]) for d in range(1, 10)) / 9
    return round(mad, 4)


# ================================================================
# MASS FUNCTION FOR ATTRIBUTION
# ================================================================

def attribution_to_mass(similarity: float, has_match: bool) -> dict:
    """
    Convert attribution result to DS mass function.

    High similarity match = strong evidence of serial vandalism.
    No match = vacuous (uncertain), not evidence of safety.
    """
    if has_match:
        # Strong match: high belief in vandalism
        v = min(0.6, similarity * 0.7)
        return {"v": round(v, 4), "s": round(0.02, 4), "t": round(1.0 - v - 0.02, 4)}
    else:
        # No match: mostly uncertain (absence of match != safe)
        return {"v": 0.0, "s": 0.05, "t": 0.95}


# ================================================================
# DATABASE OPERATIONS
# ================================================================

def update_db() -> dict:
    """Scan all classified files to build fingerprint database."""
    print("  Updating Vandal Fingerprint Database...")
    vandal_data = defaultdict(list)
    vandal_texts = defaultdict(list)
    vandal_edit_sizes = defaultdict(list)

    for csv_file in DATA_DIR.glob("**/processed/*_classified.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("llm_class") == "VANDALISM":
                    added = row.get("diff_added", "")
                    style = extract_style(added)
                    if style:
                        vandal_data[row["user"]].append(style)
                        vandal_texts[row["user"]].append(added[:500])
                    # Track edit sizes for Benford's Law
                    try:
                        old_len = int(row.get("length_old", 0) or 0)
                        new_len = int(row.get("length_new", 0) or 0)
                        delta = abs(new_len - old_len)
                        if delta > 0:
                            vandal_edit_sizes[row["user"]].append(delta)
                    except (ValueError, TypeError):
                        pass

    db = {}
    all_ratio_keys = [k for k in RATIO_KEYS]
    for user, styles in vandal_data.items():
        avg = {}
        for k in all_ratio_keys:
            vals = [s.get(k, 0) for s in styles]
            avg[k] = round(sum(vals) / len(vals), 4)
        # Average bigram vectors
        vec_len = len(TOP_BIGRAMS)
        avg_vec = [0.0] * vec_len
        for s in styles:
            for i, val in enumerate(s.get("bigram_vec", [0.0] * vec_len)):
                avg_vec[i] += val
        avg["bigram_vec"] = [round(v / len(styles), 6) for v in avg_vec]

        # Concatenate raw samples for NCD (up to 2000 chars)
        raw_sample = " ".join(vandal_texts.get(user, []))[:2000]
        avg["raw_sample"] = raw_sample

        # Benford's Law deviation for this user's edit sizes
        benford_mad = benford_deviation(vandal_edit_sizes.get(user, []))

        db[user] = {"sig": avg, "count": len(styles), "benford_mad": benford_mad}

    with open(FINGERPRINT_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

    print(f"  Database: {len(db)} vandal profiles")
    return db


def process_lang(lang: str, db: dict, cov_inv: np.ndarray | None, threshold: float):
    folder = DATA_DIR / lang / "processed"
    if not folder.exists():
        return

    for rf in sorted(folder.glob("*_classified.csv")):
        output_path = folder / f"{rf.stem.replace('_classified', '')}_attributed.csv"
        if output_path.exists():
            continue

        print(f"  Attributing: {rf.name}")
        with open(rf, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            edits = list(reader)
            fieldnames = list(reader.fieldnames)

        for col in ["attribution_match", "attribution_sim", "is_serial", "mass_attribution"]:
            if col not in fieldnames:
                fieldnames.append(col)

        matches = 0
        from tqdm import tqdm
        for edit in tqdm(edits, desc=f"   {lang.upper()} Attributing", unit="edit"):
            style = extract_style(edit.get("diff_added", ""))
            if not style or edit.get("llm_class") == "SAFE":
                edit["attribution_match"] = ""
                edit["attribution_sim"] = 0.0
                edit["is_serial"] = "False"
                edit["mass_attribution"] = json.dumps({"v": 0.0, "s": 0.05, "t": 0.95})
                continue

            best_match, best_sim = "", 0.0
            for name, data in db.items():
                if name == edit["user"]:
                    continue
                sim = combined_similarity(style, data["sig"], cov_inv)
                if sim > best_sim:
                    best_sim, best_match = sim, name

            edit["attribution_sim"] = round(best_sim, 4)
            has_match = best_sim > threshold
            if has_match:
                edit["attribution_match"] = best_match
                edit["is_serial"] = "True"
                matches += 1
            else:
                edit["attribution_match"] = ""
                edit["is_serial"] = "False"

            edit["mass_attribution"] = json.dumps(attribution_to_mass(best_sim, has_match))

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edits)
        print(f"   Done ({matches} serial matches, threshold={threshold:.3f})")


def main():
    print("WIKI-STREAM ATTRIBUTION ENGINE v3.0 (Writeprints-MCD-NCD-Benford)")
    db = update_db()
    cov_inv = estimate_covariance(db)
    threshold = compute_adaptive_threshold(db, cov_inv)
    print(f"  Adaptive threshold: {threshold:.3f}")
    for lang in ["en", "vi"]:
        process_lang(lang, db, cov_inv, threshold)


if __name__ == "__main__":
    main()
