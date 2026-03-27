"""
Stage 02: INFORMATION-THEORETIC FEATURE EXTRACTION v3.0
------------------------------------------------------------
Consolidated Stage: Rules + Diff Fetching + NLP + Info Theory
Input:  data/{lang}/raw/{timestamp}.csv
Output: data/{lang}/processed/{timestamp}_features.csv

Theoretical Foundation:
- Shannon Entropy H(X) for randomness quantification
- Rényi Entropy H_α(X) — parameterized generalization (Rényi, 1961)
  α=0.5: amplifies rare chars (gibberish), α=2: collision entropy (spam)
- Tsallis Entropy S_q(X) — non-extensive generalization (Tsallis, 1988)
  q<1: emphasizes rare events, q>1: emphasizes common events
- KL-Divergence D_KL(P||Q) for distribution anomaly
- Kolmogorov Complexity proxy via zlib compression
- Normalized Compression Distance NCD(x,y) — universal similarity metric
  (Li et al., 2004; parameter-free, captures structural patterns)
- Each sub-detector outputs a Dempster-Shafer mass function
  m = {v: P(vandalism), s: P(safe), theta: P(uncertain)}
------------------------------------------------------------
"""

import csv
import re
import json
import zlib
import math
import requests
from pathlib import Path
from collections import Counter
from html import unescape

# -- Config --
DATA_DIR = Path(__file__).parent / "data"
REPUTATION_FILE = Path(__file__).parent / "reputation.json"
REFERENCE_DIST_FILE = Path(__file__).parent / "reference_distributions.json"
HEADERS = {"User-Agent": "WikiStreamIntel/2.0 (university-research-project)"}
REQUEST_DELAY = 1.0

# -- Feature Constants --
# Profanity list: only words that won't cause false positives via regex \b matching
# Short Vietnamese words (du, di, cho, ngu, etc.) removed — they match English substrings
# and wiki markup too aggressively. Vietnamese profanity handled separately with stricter patterns.
PROFANITY_WORDS_EN = {
    "fuck", "shit", "penis", "vagina", "bitch", "nigger", "nigga",
    "faggot", "retard", "cunt", "whore", "slut", "bastard", "poop",
    "boob", "sexy", "porn", "nazi", "idiot", "loser",
}
# Vietnamese: require exact word match (these are standalone words, not substrings)
PROFANITY_WORDS_VI = {
    "dmm", "vcl", "vkl", "clgt",
}
# Compiled regex for profanity: word boundary matching, not substring
PROFANITY_RE = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in PROFANITY_WORDS_EN | PROFANITY_WORDS_VI) + r')\b',
    re.IGNORECASE
)

WIKI_MARKUP_PATTERNS = [
    r"\[\[.*?\]\]", r"\{\{.*?\}\}", r"<ref[^>]*>.*?</ref>", r"<ref[^>]*/>",
    r"\|", r"'''", r"''", r"==+", r"\*", r"#"
]

REVERT_KEYWORDS = {"revert", "undo", "undid", "rv", "rollback", "reverted"}

# -- Reference character distribution for KL-divergence --
# Precomputed from English Wikipedia legitimate edits (approximation)
# Source: character frequency analysis of 10k+ safe edits
DEFAULT_REFERENCE_DIST = {
    'e': 0.111, 't': 0.082, 'a': 0.075, 'o': 0.068, 'i': 0.064,
    'n': 0.062, 's': 0.058, 'h': 0.053, 'r': 0.050, 'd': 0.036,
    'l': 0.034, 'c': 0.027, 'u': 0.025, 'm': 0.022, 'w': 0.020,
    'f': 0.019, 'g': 0.017, 'y': 0.016, 'p': 0.016, 'b': 0.013,
    'v': 0.009, 'k': 0.006, 'j': 0.002, 'x': 0.002, 'q': 0.001,
    'z': 0.001, ' ': 0.170, '.': 0.012, ',': 0.010, '0': 0.004,
}


def load_reference_distribution():
    """Load or create reference character distribution for KL-divergence."""
    if REFERENCE_DIST_FILE.exists():
        with open(REFERENCE_DIST_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_REFERENCE_DIST


# ================================================================
# INFORMATION THEORY CORE
# ================================================================

def shannon_entropy(text: str) -> float:
    """
    Shannon Entropy H(X) = -sum(p(x) * log2(p(x)))
    Measures information content / randomness of text.
    - Low H: repetitive content (spam like "aaaaaaa")
    - High H: random/gibberish content
    - Normal text: H typically in [3.5, 5.0] for English
    """
    if not text or len(text) < 2:
        return 0.0
    freq = Counter(text.lower())
    total = len(text)
    entropy = -sum((c / total) * math.log2(c / total) for c in freq.values() if c > 0)
    return round(entropy, 4)


def strip_wiki_markup(text: str) -> str:
    """Remove wiki markup, URLs, and templates before text analysis.
    This prevents markup characters from skewing character distributions."""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove wiki templates {{...}}
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Remove wiki links [[...]] -> keep display text
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove remaining markup characters
    text = re.sub(r'[{}\[\]|=\'#*]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def kl_divergence(text: str, ref_dist: dict) -> float:
    """
    Kullback-Leibler Divergence D_KL(P || Q)
    D_KL = sum(P(x) * log(P(x) / Q(x)))

    Measures how the character distribution of the edit (P)
    diverges from the expected distribution of legitimate text (Q).
    High D_KL = anomalous content that doesn't match normal Wikipedia writing.

    Pre-strips wiki markup to avoid false positives from template syntax.
    Uses smoothing (epsilon) to handle zero probabilities.
    """
    if not text or len(text) < 10:
        return 0.0

    # Strip markup before computing distribution
    clean = strip_wiki_markup(text)
    if len(clean) < 10:
        return 0.0

    freq = Counter(clean.lower())
    total = len(clean)
    epsilon = 1e-8  # Laplace smoothing for unseen characters

    # Build P (observed distribution) — only compare on reference chars
    # This avoids inflating KL with rare/markup characters
    d_kl = 0.0
    for char in ref_dist:
        p = freq.get(char, 0) / total  # observed
        q = ref_dist[char]  # reference
        if p > 0:
            d_kl += p * math.log(p / max(q, epsilon))

    return round(max(d_kl, 0.0), 4)


def compression_ratio(text: str) -> float:
    """
    Kolmogorov Complexity approximation via zlib compression.
    ratio = len(compressed) / len(original)

    Theoretical basis: Kolmogorov complexity K(x) is uncomputable,
    but compression provides an upper bound. Low ratio = highly
    compressible = repetitive. High ratio = incompressible = random.
    Normal text: ratio typically in [0.3, 0.7]
    """
    if not text or len(text) < 10:
        return 0.5  # neutral
    raw = text.encode("utf-8")
    compressed = zlib.compress(raw)
    return round(len(compressed) / len(raw), 4)


def renyi_entropy(text: str, alpha: float = 2.0) -> float:
    """
    Rényi Entropy H_α(X) = 1/(1-α) * log₂(Σ p(x)^α)

    Generalization of Shannon entropy (Rényi, 1961).
    - α → 1: converges to Shannon entropy
    - α = 0.5: amplifies rare character contributions (detects gibberish injection)
    - α = 2: Collision entropy -log₂(Σ p²) — penalizes dominant chars (detects spam)
    - α → ∞: Min-entropy -log₂(max p) — worst-case measure (character flooding)

    Different α values detect different anomaly types, providing a multi-scale
    information-theoretic view of the text.
    """
    if not text or len(text) < 2 or alpha == 1.0:
        return shannon_entropy(text) if text and len(text) >= 2 else 0.0

    freq = Counter(text.lower())
    total = len(text)
    probs = [c / total for c in freq.values() if c > 0]

    if alpha == float('inf'):
        # Min-entropy: -log₂(max p)
        return round(-math.log2(max(probs)), 4)

    sum_p_alpha = sum(p ** alpha for p in probs)
    if sum_p_alpha <= 0:
        return 0.0

    h = (1.0 / (1.0 - alpha)) * math.log2(sum_p_alpha)
    return round(h, 4)


def tsallis_entropy(text: str, q: float = 2.0) -> float:
    """
    Tsallis Entropy S_q(X) = 1/(q-1) * (1 - Σ p(x)^q)

    Non-extensive generalization of Shannon entropy (Tsallis, 1988).
    - q → 1: converges to Shannon entropy
    - q < 1: emphasizes rare events (unusual char combinations in vandalism)
    - q > 1: emphasizes common events (repetitive spam patterns)

    Critical property: NON-ADDITIVE for independent systems:
    S_q(A+B) = S_q(A) + S_q(B) + (1-q)*S_q(A)*S_q(B)
    This makes Tsallis entropy sensitive to correlations between
    character distributions — capturing structural patterns that
    Shannon entropy misses.
    """
    if not text or len(text) < 2:
        return 0.0
    if abs(q - 1.0) < 1e-10:
        return shannon_entropy(text)

    freq = Counter(text.lower())
    total = len(text)
    probs = [c / total for c in freq.values() if c > 0]

    sum_p_q = sum(p ** q for p in probs)
    s = (1.0 / (q - 1.0)) * (1.0 - sum_p_q)
    return round(s, 4)


def normalized_compression_distance(text_a: str, text_b: str) -> float:
    """
    Normalized Compression Distance (Li et al., 2004):
    NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))

    A parameter-free, universal similarity metric based on Kolmogorov complexity.
    Uses zlib as practical compressor. NCD ∈ [0, 1]:
    - 0 = identical information content
    - 1 = completely unrelated

    Captures structural similarities that character n-grams miss:
    repeated phrases, formatting patterns, stylistic structures.
    """
    if not text_a or not text_b:
        return 1.0  # maximally different

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
    return round(max(0.0, min(1.0, ncd)), 4)


# ================================================================
# MASS FUNCTION HELPERS
# ================================================================

def make_mass(vandalism: float, safe: float) -> dict:
    """
    Create a Dempster-Shafer mass function.
    m = {v: belief in vandalism, s: belief in safe, t: uncertainty}
    Constraint: v + s + t = 1, all >= 0
    """
    v = max(0.0, min(1.0, vandalism))
    s = max(0.0, min(1.0, safe))
    remainder = 1.0 - v - s
    if remainder < 0:
        # Normalize
        total = v + s
        v, s = v / total, s / total
        remainder = 0.0
    return {"v": round(v, 4), "s": round(s, 4), "t": round(remainder, 4)}


def score_to_mass(score: float, max_score: float) -> dict:
    """
    Convert a heuristic score to a mass function.
    Higher score = more belief in vandalism, less uncertainty.
    Uses sigmoid-like mapping for smooth transition.
    """
    if max_score <= 0:
        return make_mass(0.0, 0.0)
    normalized = min(score / max_score, 1.0)
    # Sigmoid mapping: gentle curve, not binary
    # At normalized=0: v=0, s=0.3, t=0.7 (mostly uncertain, slight safe lean)
    # At normalized=0.5: v=0.35, s=0.05, t=0.6
    # At normalized=1: v=0.7, s=0.02, t=0.28
    v = 0.7 * (normalized ** 1.2)  # Slightly superlinear for high scores
    s = 0.3 * ((1 - normalized) ** 2)
    return make_mass(v, s)


# ================================================================
# [1] RULE ENGINE
# ================================================================

def get_rule_score(edit: dict, reputation: dict) -> tuple[float, list[str]]:
    """Structural heuristic scoring. Returns (score, matched_rules)."""
    total = 0.0
    matched = []

    # User Reputation
    if edit.get("user") in reputation.get("suspect_users", []):
        total += 2.0; matched.append("rep:suspect_user")
    if edit.get("title") in reputation.get("hotspot_articles", []):
        total += 1.5; matched.append("rep:hotspot")

    # Content Rules
    old = int(edit.get("length_old", 0) or 0)
    new = int(edit.get("length_new", 0) or 0)
    delta = new - old

    if old > 100 and new < old * 0.2:
        total += 5.0; matched.append("rule:blanking")
    elif delta < -5000:
        total += 3.0; matched.append("rule:large_del")

    if not edit.get("comment", "").strip():
        total += 1.0; matched.append("rule:no_comment")
        if abs(delta) > 500:
            total += 1.5; matched.append("rule:no_comment_big")

    # Text Patterns (using compiled regex with word boundaries)
    text = (edit.get("comment", "") + " " + edit.get("title", "")).lower()
    profanity_match = PROFANITY_RE.search(text)
    if profanity_match:
        total += 4.0; matched.append(f"rule:profanity:{profanity_match.group()}")

    if re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", edit.get("user", "")):
        total += 2.0; matched.append("rule:anon_ip")

    if edit.get("minor", "").lower() == "true" and abs(delta) > 1000:
        total += 2.0; matched.append("rule:minor_abuse")

    return round(total, 1), matched


# ================================================================
# [2] DIFF FETCHING
# ================================================================

def get_diff(domain: str, rev_old, rev_new) -> dict:
    """Fetch diff between two revisions. rev_old/rev_new can be str or int from CSV."""
    if not rev_old or not rev_new or str(rev_old) == "0" or str(rev_new) == "0":
        return {"added": "", "removed": "", "error": "Invalid revision ID"}

    api_url = f"https://{domain}/w/api.php"
    params = {"action": "compare", "fromrev": rev_old, "torev": rev_new,
              "format": "json"}

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        if "compare" not in data:
            return {"added": "", "removed": "", "error": str(data.get("error", "Unknown"))}

        # Wikipedia API returns diff in "*" key (default) or "body" key (when prop=diff)
        html = data["compare"].get("*", "") or data["compare"].get("body", "")
        added_parts = [unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
                       for m in re.finditer(r'<td class="diff-addedline[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL)]
        removed_parts = [unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())
                         for m in re.finditer(r'<td class="diff-deletedline[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL)]

        return {"added": "\n".join(added_parts), "removed": "\n".join(removed_parts), "error": None}
    except Exception as e:
        return {"added": "", "removed": "", "error": str(e)}


# ================================================================
# [3] NAMED ENTITY DIFF (NED)
# ================================================================

RE_YEAR = re.compile(r'\b(1[0-9]{3}|20[0-9]{2})\b')
RE_NUMBER = re.compile(r'\b\d{1,3}(?:[,\.]\d{3})+\b|\b\d{4,}\b')
RE_DATE = re.compile(
    r'\b(?:\d{1,2}\s+)?(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)[\s,]+\d{4}\b', re.IGNORECASE)
RE_PROPER_NOUN = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b')
RE_BIRTH_DEATH = re.compile(r'\b(?:born|died|b\.|d\.)\s*[:\s]*(\d{4})\b', re.IGNORECASE)
RE_LOCATION = re.compile(r'\b(?:in|from|at|of)\s+([A-Z][a-z]+(?:[,\s]+[A-Z][a-z]+)*)\b')

BIO_CONTEXT_WORDS = {
    "born", "died", "birth", "death", "married", "spouse", "children", "nationality",
    "birthplace", "hometown", "population", "founded", "established", "capital",
    "sinh", "mat", "que", "dan so", "thu do", "thanh lap"
}


def factual_diff_score(added: str, removed: str) -> tuple[float, list[str]]:
    """Detect subtle changes to proper nouns, dates, years, and numbers."""
    score = 0.0
    flags = []

    if not added or not removed:
        return 0.0, []

    # 1. Year Changes
    years_removed = set(RE_YEAR.findall(removed))
    years_added = set(RE_YEAR.findall(added))
    changed_years = years_removed.symmetric_difference(years_added)

    if changed_years and years_removed and years_added:
        swapped = years_removed - years_added
        if swapped:
            context = (added + " " + removed).lower()
            has_bio_context = any(w in context for w in BIO_CONTEXT_WORDS)
            if has_bio_context:
                score += 4.0
                flags.append(f"ned:bio_year_change({','.join(swapped)}->{','.join(years_added - years_removed)})")
            else:
                score += 1.0
                flags.append(f"ned:year_change({','.join(swapped)})")

    # 2. Date Changes
    dates_removed = set(RE_DATE.findall(removed))
    dates_added = set(RE_DATE.findall(added))
    if dates_removed and dates_added and dates_removed != dates_added:
        score += 3.5
        flags.append("ned:date_change")

    # 3. Proper Noun Changes
    names_removed = set(RE_PROPER_NOUN.findall(removed))
    names_added = set(RE_PROPER_NOUN.findall(added))

    if names_removed and names_added:
        missing_names = names_removed - names_added
        new_names = names_added - names_removed

        if missing_names and new_names:
            for old_name in missing_names:
                for new_name in new_names:
                    if _is_near_match(old_name, new_name):
                        score += 4.0
                        flags.append(f"ned:name_tamper({old_name}->{new_name})")
                        break
                else:
                    continue
                break
            else:
                score += 2.0
                flags.append(f"ned:name_swap({len(missing_names)})")

    # 4. Large Number Changes
    nums_removed = set(RE_NUMBER.findall(removed))
    nums_added = set(RE_NUMBER.findall(added))
    if nums_removed and nums_added and nums_removed != nums_added:
        score += 1.0
        flags.append("ned:number_change")

    # 5. Location Changes
    locs_removed = set(RE_LOCATION.findall(removed))
    locs_added = set(RE_LOCATION.findall(added))
    if locs_removed and locs_added:
        swapped_locs = locs_removed - locs_added
        if swapped_locs:
            context = (added + " " + removed).lower()
            has_bio_context = any(w in context for w in BIO_CONTEXT_WORDS)
            if has_bio_context:
                score += 3.5
                flags.append(f"ned:location_change({','.join(list(swapped_locs)[:2])})")
            else:
                score += 1.5
                flags.append("ned:location_swap")

    return round(score, 1), flags


def _is_near_match(a: str, b: str) -> bool:
    """Simple Levenshtein-like check: are two strings very similar but not identical?"""
    if a == b:
        return False
    if abs(len(a) - len(b)) > 3:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    matches = sum(1 for c1, c2 in zip(shorter, longer) if c1 == c2)
    ratio = matches / max(len(longer), 1)
    return ratio > 0.7


# ================================================================
# [4] NLP ANALYSIS (with Information Theory)
# ================================================================

def get_nlp_score(added: str, removed: str, ref_dist: dict) -> tuple[float, list[str], dict]:
    """
    NLP analysis with information-theoretic features.
    Returns (score, notes, info_theory_metrics).
    """
    total = 0.0
    notes = []
    info_metrics = {}

    if not added and not removed:
        return 0.0, [], {}

    # -- Information Theory Features --
    # Strip markup for info-theory analysis (avoids false positives from wiki syntax)
    clean_added = strip_wiki_markup(added)

    if len(clean_added) > 10:
        # 1. Shannon Entropy H(X) — classical information measure
        h = shannon_entropy(clean_added)
        info_metrics["entropy"] = h
        if h > 5.5:
            total += 2.5; notes.append(f"it:high_entropy({h:.2f})")
        elif h < 2.0 and len(added) > 30:
            total += 3.0; notes.append(f"it:low_entropy({h:.2f})")

        # 2. Rényi Entropy — multi-scale anomaly detection
        # α=0.5: amplifies rare chars → detects gibberish injection
        h_renyi_05 = renyi_entropy(clean_added, alpha=0.5)
        info_metrics["renyi_05"] = h_renyi_05
        # α=2 (collision entropy): penalizes dominant chars → detects spam
        h_renyi_2 = renyi_entropy(clean_added, alpha=2.0)
        info_metrics["renyi_2"] = h_renyi_2

        # Rényi divergence from Shannon: large gap = anomalous distribution shape
        # Normal text: H_0.5 ≈ H_2 ≈ H_Shannon (uniform-ish distribution)
        # Anomalous: H_0.5 >> H_2 (heavy-tailed, rare chars dominate)
        renyi_spread = h_renyi_05 - h_renyi_2
        info_metrics["renyi_spread"] = round(renyi_spread, 4)
        if renyi_spread > 2.5:
            total += 2.0; notes.append(f"it:renyi_anomaly({renyi_spread:.2f})")

        # 3. Tsallis Entropy — non-extensive, correlation-sensitive
        s_tsallis = tsallis_entropy(clean_added, q=0.5)
        info_metrics["tsallis_05"] = s_tsallis
        # High Tsallis(q=0.5) with low Shannon = structured repetition with rare outliers
        if s_tsallis > 8.0 and h < 3.5:
            total += 1.5; notes.append(f"it:tsallis_anomaly({s_tsallis:.2f})")

        # 4. KL-Divergence from reference distribution
        d_kl = kl_divergence(clean_added, ref_dist)
        info_metrics["kl_divergence"] = d_kl
        if d_kl > 2.0:
            total += 3.0; notes.append(f"it:high_kl_div({d_kl:.2f})")
        elif d_kl > 1.0:
            total += 1.5; notes.append(f"it:moderate_kl_div({d_kl:.2f})")

        # 5. Compression Ratio (Kolmogorov proxy)
        cr = compression_ratio(clean_added)
        info_metrics["compression_ratio"] = cr
        if cr < 0.2:
            total += 3.0; notes.append(f"it:repetitive({cr:.2f})")
        elif cr > 0.85:
            total += 2.0; notes.append(f"it:random({cr:.2f})")

    # -- Classical NLP Features --

    # Profanity Density (word boundary matching to avoid false positives)
    profanity_matches = PROFANITY_RE.findall(added)
    if profanity_matches:
        word_count = len(added.split())
        density = len(profanity_matches) / max(word_count, 1)
        total += min(density * 15, 5.0)
        notes.append(f"nlp:toxic({len(profanity_matches)})")

    # Markup Destruction
    rem_markup = sum(len(re.findall(p, removed)) for p in WIKI_MARKUP_PATTERNS)
    add_markup = sum(len(re.findall(p, added)) for p in WIKI_MARKUP_PATTERNS)
    if rem_markup > 5 and add_markup < rem_markup * 0.3:
        total += 2.5; notes.append("nlp:markup_del")

    # POV Shift (word boundary matching, only strong indicators)
    pov_words = ["best", "legendary", "greatest", "amazing", "worst", "terrible", "evil", "liar"]
    added_lower = added.lower()
    pov_found = [w for w in pov_words if re.search(r'\b' + re.escape(w) + r'\b', added_lower)]
    if pov_found:
        total += 1.5; notes.append(f"nlp:pov_shift({','.join(pov_found)})")

    # Hoax/Test Patterns (word boundary to avoid matching "Testament", "Testing", etc.)
    if re.search(r"^(test|hello|asdf|1234)\b", added.lower().strip()):
        total += 2.5; notes.append("nlp:test_edit")

    # Named Entity Diff
    ned_score, ned_flags = factual_diff_score(added, removed)
    total += ned_score
    notes.extend(ned_flags)

    # Citation Stripping
    refs_removed = len(re.findall(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', removed, re.DOTALL))
    refs_added = len(re.findall(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', added, re.DOTALL))
    if refs_removed >= 2 and refs_added < refs_removed * 0.3:
        total += 3.0; notes.append(f"nlp:citation_strip({refs_removed})")

    # External Link Injection (expanded whitelist to reduce false positives on news/reference sites)
    safe_domains = {
        "wikipedia.org", "wikimedia.org", "archive.org", "doi.org", "jstor.org",
        "ncbi.nlm.nih.gov", "web.archive.org", "books.google.com",
        # Major news / reference sources
        "nytimes.com", "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com",
        "theguardian.com", "washingtonpost.com", "cnn.com", "npr.org",
        "who.int", "un.org", "imdb.com", "britannica.com", "allmusic.com",
        "rottentomatoes.com", "metacritic.com", "worldcat.org",
    }
    new_links = re.findall(r'https?://(?:www\.)?([^\s/\]|]+)', added)
    suspicious_links = []
    for domain in new_links:
        if not any(safe in domain for safe in safe_domains):
            if not re.search(r'\.(gov|edu|org|ac\.\w+|mil)$', domain):
                suspicious_links.append(domain)
    if suspicious_links:
        total += 2.5; notes.append(f"nlp:ext_link({suspicious_links[0][:30]})")

    # Sneaky Redirect
    if re.search(r'#REDIRECT\s*\[\[', added, re.IGNORECASE) and len(removed) > 200:
        total += 4.0; notes.append("nlp:sneaky_redirect")

    return round(total, 1), notes, info_metrics


# ================================================================
# MAIN PROCESSING
# ================================================================

def process_lang(lang: str, reputation: dict, ref_dist: dict):
    lang_dir = DATA_DIR / lang
    raw_dir = lang_dir / "raw"
    proc_dir = lang_dir / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)

    for rf in sorted(raw_dir.glob("*.csv")):
        output_path = proc_dir / f"{rf.stem}_features.csv"
        if output_path.exists():
            continue

        print(f"\n  Processing {lang.upper()}: {rf.name}")

        with open(rf, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            edits = list(reader)
            fieldnames = list(reader.fieldnames)

        # Extend fieldnames
        new_cols = [
            "rule_score", "rules", "diff_added", "diff_removed",
            "nlp_score", "nlp_notes",
            "entropy", "renyi_05", "renyi_2", "renyi_spread",
            "tsallis_05", "kl_divergence", "compression_ratio",
            "mass_rule", "mass_nlp",
        ]
        for col in new_cols:
            if col not in fieldnames:
                fieldnames.append(col)

        from tqdm import tqdm
        for i, edit in enumerate(tqdm(edits, desc=f"   {lang.upper()} Processing", unit="edit")):
            # 1. Rule Engine
            r_score, r_matches = get_rule_score(edit, reputation)
            edit["rule_score"] = r_score
            edit["rules"] = ";".join(r_matches)

            # 2. Diff Fetcher
            if edit.get("bot") == "true" and r_score < 3.0:
                edit["diff_added"] = ""
                edit["diff_removed"] = ""
                edit["nlp_score"] = 0.0
                edit["nlp_notes"] = ""
                edit["entropy"] = 0.0
                edit["renyi_05"] = 0.0
                edit["renyi_2"] = 0.0
                edit["renyi_spread"] = 0.0
                edit["tsallis_05"] = 0.0
                edit["kl_divergence"] = 0.0
                edit["compression_ratio"] = 0.5
                # Bot with low rule score: safe-leaning mass
                edit["mass_rule"] = json.dumps(make_mass(0.0, 0.3))
                edit["mass_nlp"] = json.dumps(make_mass(0.0, 0.3))
            else:
                diff = get_diff(edit["domain"], edit["revision_old"], edit["revision_new"])
                edit["diff_added"] = diff["added"][:3000]
                edit["diff_removed"] = diff["removed"][:3000]

                # 3. NLP + Info Theory Analysis
                n_score, n_notes, info_m = get_nlp_score(diff["added"], diff["removed"], ref_dist)
                edit["nlp_score"] = n_score
                edit["nlp_notes"] = ";".join(n_notes)
                edit["entropy"] = info_m.get("entropy", 0.0)
                edit["renyi_05"] = info_m.get("renyi_05", 0.0)
                edit["renyi_2"] = info_m.get("renyi_2", 0.0)
                edit["renyi_spread"] = info_m.get("renyi_spread", 0.0)
                edit["tsallis_05"] = info_m.get("tsallis_05", 0.0)
                edit["kl_divergence"] = info_m.get("kl_divergence", 0.0)
                edit["compression_ratio"] = info_m.get("compression_ratio", 0.5)

                # 4. Mass Functions
                edit["mass_rule"] = json.dumps(score_to_mass(r_score, max_score=10.0))
                edit["mass_nlp"] = json.dumps(score_to_mass(n_score, max_score=15.0))

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edits)
        print(f"   Saved {output_path.name}")


def main():
    print("WIKI-STREAM FEATURE ENGINE v3.0 (Multi-Scale Information-Theoretic)")
    rep = {}
    if REPUTATION_FILE.exists():
        with open(REPUTATION_FILE, "r") as f:
            rep = json.load(f)

    ref_dist = load_reference_distribution()

    for lang in ["en", "vi"]:
        if (DATA_DIR / lang).exists():
            process_lang(lang, rep, ref_dist)


if __name__ == "__main__":
    main()
