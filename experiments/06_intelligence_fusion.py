"""
Stage 06: INTELLIGENCE FUSION HUB v3.0 (Advanced DS + Multi-Algorithm)
------------------------------------------------------------
Input:  data/{lang}/processed/{timestamp}_attributed.csv
Output: reports/intelligence_master.json

Theoretical Foundation:
1. Dempster-Shafer Evidence Theory — Advanced Methods:
   - Murphy's Modified Combination Rule (Murphy, 2000):
     Average BPAs first, then combine — order-independent
   - PCR5 — Proportional Conflict Redistribution Rule 5
     (Smarandache & Dezert, 2006): redistributes conflict proportionally
     to source masses, superior to Dempster's normalization for high-k cases
   - Deng Entropy (Deng, 2016): generalization of Shannon entropy to DS
     framework — measures uncertainty of mass functions, not just probability
   - Pignistic Transformation (Smets, 1990): principled BPA → probability
     conversion for decision-making (Transferable Belief Model)
   - Evidence Discounting (Shafer, 1976): dynamic reliability weighting
     per source based on evidence strength

2. Anomaly Detection: Isolation Forest (Liu et al., 2008)
   - Extended feature set with Rényi/Tsallis entropy metrics

3. Beta-Bayesian Reputation (Josang & Ismail, 2002)

4. Dual Graph Ranking:
   - SuspicionRank (PageRank variant on DiGraph)
   - HITS Algorithm (Kleinberg, 1999): Hub-Authority decomposition
     on user-article bipartite graph — naturally separates user
     suspicion (hub) from article vulnerability (authority)
------------------------------------------------------------
"""

import csv
import json
import math
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# -- Optional Dependencies --
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# -- Config --
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


# ================================================================
# DEMPSTER-SHAFER COMBINATION — CLASSICAL
# ================================================================

def ds_combine(m1: dict, m2: dict) -> tuple[dict, float]:
    """
    Dempster's Rule of Combination for two mass functions.
    m_combined(A) = (1/(1-k)) * sum_{B∩C=A} m1(B)*m2(C)
    Returns (combined_mass, conflict_coefficient_k).
    """
    k = m1['v'] * m2['s'] + m1['s'] * m2['v']

    if k >= 0.99:
        return {'v': 0.0, 's': 0.0, 't': 1.0}, k

    normalizer = 1.0 / (1.0 - k)

    combined = {
        'v': normalizer * (m1['v']*m2['v'] + m1['v']*m2['t'] + m1['t']*m2['v']),
        's': normalizer * (m1['s']*m2['s'] + m1['s']*m2['t'] + m1['t']*m2['s']),
        't': normalizer * (m1['t'] * m2['t']),
    }

    total = combined['v'] + combined['s'] + combined['t']
    if total > 0:
        combined = {k_: round(v / total, 4) for k_, v in combined.items()}

    return combined, round(k, 4)


# ================================================================
# MURPHY'S MODIFIED COMBINATION RULE (Murphy, 2000)
# ================================================================

def murphy_combine(masses: list[dict]) -> tuple[dict, float]:
    """
    Murphy's Modified Combination Rule.

    Problem with sequential Dempster: result depends on combination ORDER.
    Murphy's solution: average all BPAs first, then combine the averaged
    BPA with itself (n-1) times.

    m_avg(A) = (1/n) * Σ m_i(A)
    m_combined = m_avg ⊕ m_avg ⊕ ... ⊕ m_avg  (n-1 combinations)

    Properties:
    - Order-independent (commutative by construction)
    - Naturally handles high-conflict cases better than sequential DS
    - Convergent: more sources → sharper result
    """
    if not masses:
        return {'v': 0.0, 's': 0.0, 't': 1.0}, 0.0
    if len(masses) == 1:
        return masses[0], 0.0

    n = len(masses)
    # Step 1: Average all mass functions
    avg = {'v': 0.0, 's': 0.0, 't': 0.0}
    for m in masses:
        avg['v'] += m['v']
        avg['s'] += m['s']
        avg['t'] += m['t']
    avg = {k_: v / n for k_, v in avg.items()}

    # Step 2: Combine averaged mass with itself (n-1) times
    result = avg.copy()
    max_k = 0.0
    for _ in range(n - 1):
        result, k = ds_combine(result, avg)
        max_k = max(max_k, k)

    return result, max_k


# ================================================================
# PCR5 — PROPORTIONAL CONFLICT REDISTRIBUTION RULE 5
# (Smarandache & Dezert, 2006)
# ================================================================

def pcr5_combine(m1: dict, m2: dict) -> tuple[dict, float]:
    """
    PCR5: Proportional Conflict Redistribution Rule 5.

    Unlike Dempster's rule which normalizes conflict away, PCR5
    redistributes conflicting mass back to the elements involved
    in the conflict, proportionally to their individual masses.

    For two sources with conflict between {v} and {s}:
    - Conflict mass from m1(v)*m2(s) is split:
      → m1(v)²*m2(s)/(m1(v)+m2(s)) goes back to {v}
      → m1(v)*m2(s)²/(m1(v)+m2(s)) goes back to {s}
    - Similarly for m1(s)*m2(v)

    Advantages over Dempster's rule:
    - No normalization artifact (k doesn't inflate beliefs)
    - Conflict is redistributed, not discarded
    - More nuanced for high-conflict cases (k > 0.3)
    """
    # Conjunctive (unnormalized) combination
    conj = {
        'v': m1['v']*m2['v'] + m1['v']*m2['t'] + m1['t']*m2['v'],
        's': m1['s']*m2['s'] + m1['s']*m2['t'] + m1['t']*m2['s'],
        't': m1['t']*m2['t'],
    }

    # Conflict coefficient
    k = m1['v'] * m2['s'] + m1['s'] * m2['v']

    # PCR5 redistribution of conflict
    # Conflict 1: m1(v) * m2(s) — vandalism vs safe
    c1 = m1['v'] * m2['s']
    if m1['v'] + m2['s'] > 0 and c1 > 0:
        conj['v'] += (m1['v'] ** 2 * m2['s']) / (m1['v'] + m2['s'])
        conj['s'] += (m2['s'] ** 2 * m1['v']) / (m1['v'] + m2['s'])

    # Conflict 2: m1(s) * m2(v) — safe vs vandalism
    c2 = m1['s'] * m2['v']
    if m1['s'] + m2['v'] > 0 and c2 > 0:
        conj['s'] += (m1['s'] ** 2 * m2['v']) / (m1['s'] + m2['v'])
        conj['v'] += (m2['v'] ** 2 * m1['s']) / (m1['s'] + m2['v'])

    # Normalize to ensure valid mass function
    total = conj['v'] + conj['s'] + conj['t']
    if total > 0:
        conj = {k_: round(v / total, 4) for k_, v in conj.items()}
    else:
        conj = {'v': 0.0, 's': 0.0, 't': 1.0}

    return conj, round(k, 4)


def pcr5_combine_multiple(masses: list[dict]) -> tuple[dict, float]:
    """Sequential PCR5 combination for multiple sources."""
    if not masses:
        return {'v': 0.0, 's': 0.0, 't': 1.0}, 0.0
    result = masses[0]
    max_k = 0.0
    for m in masses[1:]:
        result, k = pcr5_combine(result, m)
        max_k = max(max_k, k)
    return result, max_k


# ================================================================
# ADAPTIVE FUSION STRATEGY
# ================================================================

def adaptive_combine(masses: list[dict]) -> tuple[dict, float, str]:
    """
    Adaptive fusion: selects combination rule based on conflict level.

    Strategy:
    - Low conflict (k < 0.3): Murphy's rule (stable, order-independent)
    - High conflict (k ≥ 0.3): PCR5 (conflict-redistributing, more nuanced)

    This is principled: when sources agree, Murphy's averaging + combination
    produces sharper results. When sources disagree, PCR5's proportional
    redistribution avoids Dempster's normalization artifact that inflates
    the majority opinion.

    Returns (combined_mass, max_conflict, method_used).
    """
    if not masses:
        return {'v': 0.0, 's': 0.0, 't': 1.0}, 0.0, "none"
    if len(masses) == 1:
        return masses[0], 0.0, "single"

    # First pass: Murphy's rule (always computed as baseline)
    murphy_result, murphy_k = murphy_combine(masses)

    # If high conflict detected, switch to PCR5
    if murphy_k >= 0.3:
        pcr5_result, pcr5_k = pcr5_combine_multiple(masses)
        return pcr5_result, pcr5_k, "PCR5"

    return murphy_result, murphy_k, "Murphy"


# ================================================================
# DENG ENTROPY (Deng, 2016)
# ================================================================

def deng_entropy(mass: dict) -> float:
    """
    Deng Entropy — generalization of Shannon entropy to DS framework.

    E_d(m) = -Σ m(A) * log₂( m(A) / (2^|A| - 1) )

    Where |A| is the cardinality of focal element A.
    When BPA degenerates to probability (all singletons), Deng entropy
    reduces exactly to Shannon entropy (since 2^1 - 1 = 1).

    For our frame Θ = {vandalism, safe}:
    - m(v): singleton, |A|=1, factor = 2^1 - 1 = 1
    - m(s): singleton, |A|=1, factor = 1
    - m(θ): full frame, |A|=2, factor = 2^2 - 1 = 3

    So: E_d = -m(v)*log₂(m(v)) - m(s)*log₂(m(s)) - m(θ)*log₂(m(θ)/3)

    Deng entropy ≥ Shannon entropy (always), because uncertainty mass θ
    gets "credit" for representing multiple hypotheses.

    High Deng entropy = high residual uncertainty after fusion.
    Low Deng entropy = confident assessment.
    """
    e = 0.0
    for key, cardinality in [('v', 1), ('s', 1), ('t', 2)]:
        m = mass.get(key, 0)
        if m > 0:
            factor = 2 ** cardinality - 1  # 1 for singletons, 3 for theta
            e -= m * math.log2(m / factor)
    return round(e, 4)


# ================================================================
# PIGNISTIC TRANSFORMATION (Smets, 1990 — TBM)
# ================================================================

def pignistic_transform(mass: dict) -> dict:
    """
    Pignistic Probability Transformation (Transferable Belief Model).

    BetP(A) = Σ_{B⊇A} m(B) / |B|  *  1/(1 - m(∅))

    Converts mass function to probability distribution for decision-making.
    This is the theoretically principled way to go from DS belief to action
    (instead of using Belief directly, which is a lower bound).

    For our frame:
    BetP(vandalism) = m(v) + m(θ)/2
    BetP(safe) = m(s) + m(θ)/2

    The uncertainty mass θ is split equally between hypotheses —
    this is the maximum entropy (least committed) probability assignment
    consistent with the belief function.
    """
    m_empty = 0.0  # We don't use open-world assumption
    normalizer = 1.0 / (1.0 - m_empty) if m_empty < 1.0 else 1.0

    # θ = {v, s}, cardinality 2 → each singleton gets m(θ)/2
    betP_v = (mass.get('v', 0) + mass.get('t', 0) / 2.0) * normalizer
    betP_s = (mass.get('s', 0) + mass.get('t', 0) / 2.0) * normalizer

    return {"vandalism": round(betP_v, 4), "safe": round(betP_s, 4)}


# ================================================================
# EVIDENCE DISCOUNTING (Shafer, 1976)
# ================================================================

def evidence_discount(mass: dict, reliability: float) -> dict:
    """
    Shafer's Evidence Discounting Operation.

    m_discounted(A) = α * m(A)         for A ≠ Θ
    m_discounted(Θ) = 1 - α * (1 - m(Θ))

    Where α ∈ [0,1] is the source reliability.
    α = 1: fully reliable (no discounting)
    α = 0: completely unreliable (vacuous mass)

    This is a principled alternative to ad-hoc filtering of "vacuous masses".
    Instead of binary include/exclude, we continuously weight each source
    by its estimated reliability.
    """
    alpha = max(0.0, min(1.0, reliability))
    discounted = {
        'v': round(alpha * mass.get('v', 0), 4),
        's': round(alpha * mass.get('s', 0), 4),
    }
    discounted['t'] = round(1.0 - discounted['v'] - discounted['s'], 4)
    return discounted


def compute_source_reliability(edit: dict, source: str) -> float:
    """
    Dynamic reliability estimation per source per edit.

    - Rule engine: reliability scales with number of rules triggered
      (more rules = more evidence = higher reliability)
    - NLP: reliability scales with text length
      (short text = insufficient signal for NLP)
    - LLM: reliability from confidence score
      (already partially encoded in mass, but discounting adds granularity)
    - Attribution: reliability from fingerprint DB size
      (few profiles = less reliable matching)
    """
    if source == "rule":
        score = float(edit.get('rule_score', 0) or 0)
        # Logistic: 0 rules → 0.3, 5 rules → 0.7, 10+ → 0.9
        return 0.3 + 0.6 * (1 - math.exp(-score / 4.0))

    elif source == "nlp":
        added = edit.get('diff_added', '')
        text_len = len(added) if added else 0
        # Short text is unreliable for NLP: <20 chars → 0.2, >200 → 0.9
        return 0.2 + 0.7 * min(text_len / 200.0, 1.0)

    elif source == "llm":
        conf = float(edit.get('llm_conf', 0) or 0)
        return max(0.3, min(0.95, conf))

    elif source == "attribution":
        sim = float(edit.get('attribution_sim', 0) or 0)
        # No match → low reliability; high similarity → high reliability
        return 0.2 + 0.7 * sim

    return 0.5  # default


def belief_plausibility(mass: dict) -> tuple[float, float]:
    """
    Bel(V) = m(V), Pl(V) = 1 - m(S).
    Interval [Bel, Pl] captures the range of possible conclusions.
    """
    bel = mass.get('v', 0)
    pl = 1.0 - mass.get('s', 0)
    return round(bel, 4), round(pl, 4)


# ================================================================
# ISOLATION FOREST (ANOMALY DETECTION)
# ================================================================

def run_isolation_forest(edits: list[dict]) -> dict:
    """
    IsolationForest on multi-dimensional feature vectors.

    Features used: rule_score, nlp_score, entropy, kl_divergence,
    compression_ratio, attribution_sim.

    Returns dict mapping edit index -> anomaly_score in [-1, 1].
    Negative = more anomalous.
    """
    if not HAS_SKLEARN or len(edits) < 10:
        return {}

    # Extended feature set: includes Rényi/Tsallis entropy from v3.0 pipeline
    feature_keys = ["rule_score", "nlp_score", "entropy", "renyi_05", "renyi_2",
                    "tsallis_05", "kl_divergence", "compression_ratio", "attribution_sim"]

    X = []
    valid_indices = []
    for i, e in enumerate(edits):
        try:
            row = [float(e.get(k, 0) or 0) for k in feature_keys]
            X.append(row)
            valid_indices.append(i)
        except (ValueError, TypeError):
            continue

    if len(X) < 10:
        return {}

    X = np.array(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # contamination='auto' lets sklearn estimate anomaly proportion
    iso = IsolationForest(
        n_estimators=100,
        contamination=0.1,  # Expect ~10% anomalies in Wikipedia edits
        random_state=42
    )
    iso.fit(X_scaled)

    # decision_function: negative = more anomalous
    scores = iso.decision_function(X_scaled)

    # Normalize to [0, 100] where 100 = most anomalous
    min_s, max_s = scores.min(), scores.max()
    if max_s - min_s > 0:
        normalized = (1 - (scores - min_s) / (max_s - min_s)) * 100
    else:
        normalized = np.full_like(scores, 50.0)

    return {valid_indices[i]: round(float(normalized[i]), 1) for i in range(len(valid_indices))}


# ================================================================
# BETA-BAYESIAN REPUTATION
# ================================================================

def compute_reputation(edits: list[dict]) -> dict:
    """
    Beta-Bayesian user reputation model.

    Each user starts with prior Beta(alpha=2, beta=1) — slight trust bias.
    - Observe VANDALISM: beta += 2 (strong negative evidence)
    - Observe SUSPICIOUS: beta += 0.5 (weak negative evidence)
    - Observe SAFE (with signal): alpha += 1 (positive evidence)

    Reputation = E[Beta] = alpha / (alpha + beta)
    Range: [0, 1] where 0 = completely untrusted, 1 = fully trusted.

    Suspicion score = (1 - reputation) * 100.
    """
    rep_db = defaultdict(lambda: {'alpha': 2.0, 'beta': 1.0})

    for e in edits:
        u = e.get('user', '')
        if not u:
            continue

        llm_class = e.get('llm_class', '')
        if llm_class == 'VANDALISM':
            rep_db[u]['beta'] += 2.0
        elif llm_class == 'SUSPICIOUS':
            rep_db[u]['beta'] += 0.5
        elif llm_class == 'SAFE' and float(e.get('rule_score', 0) or 0) > 0:
            rep_db[u]['alpha'] += 1.0

    # Compute suspicion scores
    suspicion = {}
    for u, params in rep_db.items():
        reputation = params['alpha'] / (params['alpha'] + params['beta'])
        suspicion[u] = round((1.0 - reputation) * 100, 1)

    return suspicion


# ================================================================
# SUSPICIONRANK (PAGERANK VARIANT)
# ================================================================

def compute_suspicion_rank(edits: list[dict]) -> dict:
    """
    SuspicionRank: PageRank on user-article bipartite graph.

    Edges weighted by suspicion level:
    - Vandalism edit: weight = 3.0
    - Suspicious edit: weight = 2.0
    - Normal edit with signals: weight = 1.0

    High PageRank = user is central to the suspicious edit network
    (touches many articles that are also touched by other suspects).
    """
    if not HAS_NX:
        return {}

    # DiGraph: user -> article (directed, semantically correct)
    G = nx.DiGraph()
    users_set = set()
    for e in edits:
        user = e.get('user', '')
        title = e.get('title', '')
        if not user or not title:
            continue

        llm_class = e.get('llm_class', '')
        score = float(e.get('rule_score', 0) or 0)

        if llm_class == 'VANDALISM':
            weight = 3.0
        elif llm_class == 'SUSPICIOUS' or score > 3:
            weight = 2.0
        elif score > 0:
            weight = 1.0
        else:
            continue

        users_set.add(user)
        if G.has_edge(user, title):
            G[user][title]['weight'] += weight
        else:
            G.add_edge(user, title, weight=weight)

    if len(G.nodes) < 2:
        return {}

    pr = nx.pagerank(G, alpha=0.85, weight='weight')

    # Normalize among users only (not articles) to avoid scale mixing
    user_scores = {u: pr.get(u, 0) for u in users_set}
    max_user_pr = max(user_scores.values()) if user_scores else 1
    if max_user_pr <= 0:
        return {}
    return {u: round((s / max_user_pr) * 100, 1) for u, s in user_scores.items()}


# ================================================================
# HITS ALGORITHM (Kleinberg, 1999)
# ================================================================

def compute_hits(edits: list[dict]) -> tuple[dict, dict]:
    """
    HITS (Hyperlink-Induced Topic Search) on user-article bipartite graph.

    Unlike PageRank (global centrality), HITS decomposes the graph into:
    - Hub scores (users): A user is a "good hub" if they edit many articles
      that are "good authorities" (heavily vandalized articles)
    - Authority scores (articles): An article is a "good authority" if
      it's edited by many "good hubs" (frequent vandals)

    This decomposition is NATURAL for bipartite user-article graphs:
    - High hub score → user consistently targets vulnerable articles
    - High authority score → article is a magnet for vandalism

    Iterative update:
    auth(a) = Σ_{u→a} hub(u) * weight(u,a)
    hub(u) = Σ_{u→a} auth(a) * weight(u,a)

    Returns (hub_scores_for_users, authority_scores_for_articles).
    """
    if not HAS_NX:
        return {}, {}

    G = nx.DiGraph()
    users_set = set()
    articles_set = set()

    for e in edits:
        user = e.get('user', '')
        title = e.get('title', '')
        if not user or not title:
            continue

        llm_class = e.get('llm_class', '')
        score = float(e.get('rule_score', 0) or 0)

        if llm_class == 'VANDALISM':
            weight = 3.0
        elif llm_class == 'SUSPICIOUS' or score > 3:
            weight = 2.0
        elif score > 0:
            weight = 1.0
        else:
            continue

        users_set.add(user)
        articles_set.add(title)
        if G.has_edge(user, title):
            G[user][title]['weight'] += weight
        else:
            G.add_edge(user, title, weight=weight)

    if len(G.nodes) < 2:
        return {}, {}

    try:
        hubs, authorities = nx.hits(G, max_iter=100, normalized=True)
    except nx.PowerIterationFailedConvergence:
        return {}, {}

    # Normalize hub scores (users) to [0, 100]
    user_hubs = {u: hubs.get(u, 0) for u in users_set}
    max_hub = max(user_hubs.values()) if user_hubs else 1
    if max_hub <= 0:
        user_hubs_norm = {}
    else:
        user_hubs_norm = {u: round((s / max_hub) * 100, 1) for u, s in user_hubs.items()}

    # Normalize authority scores (articles) to [0, 100]
    article_auths = {a: authorities.get(a, 0) for a in articles_set}
    max_auth = max(article_auths.values()) if article_auths else 1
    if max_auth <= 0:
        article_auths_norm = {}
    else:
        article_auths_norm = {a: round((s / max_auth) * 100, 1) for a, s in article_auths.items()}

    return user_hubs_norm, article_auths_norm


# ================================================================
# MAIN FUSION
# ================================================================

def load_master_data() -> list[dict]:
    all_edits = []
    for f in DATA_DIR.glob("**/processed/*_attributed.csv"):
        with open(f, "r", encoding="utf-8") as csvf:
            for row in csv.DictReader(csvf):
                all_edits.append(row)
    return all_edits


def parse_mass(mass_str: str) -> dict:
    """Parse mass function from CSV string. Returns vacuous mass on failure."""
    try:
        m = json.loads(mass_str)
        if isinstance(m, dict) and 'v' in m and 's' in m and 't' in m:
            return m
    except (json.JSONDecodeError, TypeError):
        pass
    return {'v': 0.0, 's': 0.0, 't': 1.0}


def run_fusion(edits: list[dict]):
    print(f"  Fusing intelligence for {len(edits)} edits...")

    # -- Pre-compute global signals --
    suspicion_rank = compute_suspicion_rank(edits)
    reputation = compute_reputation(edits)
    anomaly_scores = run_isolation_forest(edits)
    hits_hubs, hits_authorities = compute_hits(edits)

    print(f"  SuspicionRank: {len(suspicion_rank)} nodes")
    print(f"  HITS: {len(hits_hubs)} hubs, {len(hits_authorities)} authorities")
    print(f"  Reputation: {len(reputation)} users")
    print(f"  IsolationForest: {len(anomaly_scores)} scored")

    # -- Per-edit fusion --
    verdicts = []
    fusion_methods = Counter()

    for i, e in enumerate(edits):
        user = e.get('user', '')
        title = e.get('title', '')

        # 1. Collect mass functions from all sources
        mass_rule = parse_mass(e.get('mass_rule', ''))
        mass_nlp = parse_mass(e.get('mass_nlp', ''))
        mass_llm = parse_mass(e.get('mass_llm', ''))
        mass_attr = parse_mass(e.get('mass_attribution', ''))

        # 2. Evidence Discounting — weight each source by reliability
        sources = {
            "rule": mass_rule, "nlp": mass_nlp,
            "llm": mass_llm, "attribution": mass_attr,
        }
        discounted_masses = []
        reliability_scores = {}
        for src_name, src_mass in sources.items():
            rel = compute_source_reliability(e, src_name)
            reliability_scores[src_name] = round(rel, 3)
            disc = evidence_discount(src_mass, rel)
            # Only include if discounted mass carries some evidence
            if disc['v'] > 0.005 or disc['s'] > 0.10:
                discounted_masses.append(disc)

        # 3. Adaptive DS Fusion (Murphy or PCR5 based on conflict level)
        if discounted_masses:
            ds_result, max_conflict, fusion_method = adaptive_combine(discounted_masses)
        else:
            ds_result = {'v': 0.0, 's': 0.3, 't': 0.7}
            max_conflict = 0.0
            fusion_method = "none"
        fusion_methods[fusion_method] += 1

        # 4. Deng Entropy — residual uncertainty after fusion
        d_entropy = deng_entropy(ds_result)

        # 5. Pignistic Transformation — principled BPA → probability for decision
        pignistic = pignistic_transform(ds_result)

        # 6. Belief/Plausibility interval
        bel_v, pl_v = belief_plausibility(ds_result)

        # 7. Auxiliary signals
        s_pagerank = suspicion_rank.get(user, 0.0)
        s_hits_hub = hits_hubs.get(user, 0.0)
        s_hits_auth = hits_authorities.get(title, 0.0)
        s_rep = reputation.get(user, 33.0)
        s_anomaly = anomaly_scores.get(i, 50.0)

        # Blended graph score: PageRank + HITS hub (complementary perspectives)
        s_graph = 0.5 * s_pagerank + 0.5 * s_hits_hub

        # 8. Final Verdict Score (0-100)
        # Evidence-Weighted Scoring: blend belief ↔ pignistic by evidence strength
        #
        # Principle: BetP distributes θ equally among hypotheses. This is correct
        # when we HAVE evidence to anchor the distribution. But when θ is large
        # (little evidence), BetP inflates the vandalism probability.
        #
        # Solution: evidence_strength = 1 - m(θ) measures how much non-uncertain
        # evidence we have. We blend:
        #   - Low evidence (high θ) → lean on belief (conservative lower bound)
        #   - High evidence (low θ) → lean on pignistic (distribute remaining θ)
        #
        # When θ=0: score = pignistic (full evidence, trust the distribution)
        # When θ=1: score = belief = 0 (no evidence, no claim)
        pignistic_v = pignistic["vandalism"]
        evidence_strength = max(0.0, 1.0 - ds_result.get('t', 1.0))

        # Vandalism-specific evidence ratio: what fraction of non-θ evidence
        # points to vandalism (vs safe)?
        # When evidence is mostly vandalism: vand_ratio → 1 → trust pignistic
        # When evidence is mostly safe: vand_ratio → 0 → stick to belief (conservative)
        # This prevents safe-leaning evidence from inflating vandalism scores
        # via the pignistic transform's equal θ-distribution.
        non_theta = ds_result.get('v', 0) + ds_result.get('s', 0)
        vand_ratio = ds_result.get('v', 0) / max(non_theta, 1e-8) if non_theta > 0.01 else 0.0
        ds_score = (bel_v + (pignistic_v - bel_v) * vand_ratio) * 100

        # Auxiliary weight: scale by total evidence strength
        aux_weight = min(1.0, evidence_strength * 1.5)

        verdict_score = round(
            ds_score * 0.70 +
            s_anomaly * 0.10 * aux_weight +
            s_rep * 0.10 * aux_weight +
            s_graph * 0.10 * aux_weight,
            1
        )

        # 9. Uncertainty-adjusted action classification
        # Deng entropy for our 2-hypothesis frame: theoretical max ≈ 2.32 (log₂3)
        # when m(θ)=1. Typical range: 0.5 (confident) to 2.0 (uncertain).
        # Only penalize genuinely extreme uncertainty.
        # Deng entropy max for Θ={v,s} is log₂3 ≈ 2.32
        # Most edits cluster at 1.8-2.1, so penalize only extreme cases
        block_thresh = 72 if d_entropy < 2.1 else 78
        flag_thresh = 48 if d_entropy < 2.2 else 55
        review_thresh = 24

        # Anomaly override: IsolationForest detects multivariate patterns
        # that individual DS sources miss. When IF score is extreme AND
        # there's at least some DS signal, override to REVIEW minimum.
        # This implements a "defense-in-depth" principle: behavioral layer
        # can escalate when evidence layer has insufficient coverage.
        has_some_signal = (float(e.get('rule_score', 0) or 0) > 0 or
                          float(e.get('nlp_score', 0) or 0) > 0)
        if s_anomaly >= 65 and has_some_signal and verdict_score < review_thresh:
            verdict_score = review_thresh + 0.1

        action = "SAFE"
        if verdict_score > block_thresh:
            action = "BLOCK"
        elif verdict_score > flag_thresh:
            action = "FLAG"
        elif verdict_score > review_thresh:
            action = "REVIEW"

        # 10. Uncertainty interval
        uncertainty_width = round(pl_v - bel_v, 4)

        verdicts.append({
            "user": user,
            "title": title,
            "score": verdict_score,
            "action": action,
            # DS provenance (advanced)
            "ds_belief": bel_v,
            "ds_plausibility": pl_v,
            "ds_uncertainty": uncertainty_width,
            "ds_conflict": max_conflict,
            "ds_method": fusion_method,
            "deng_entropy": d_entropy,
            "pignistic": pignistic,
            # Component signals
            "signals": {
                "rule": round(float(e.get('rule_score', 0) or 0), 1),
                "nlp": round(float(e.get('nlp_score', 0) or 0), 1),
                "llm": e.get('llm_class', ''),
                "llm_conf": e.get('llm_conf', ''),
                "attribution": e.get('attribution_match', ''),
                "anomaly": s_anomaly,
                "reputation": s_rep,
                "pagerank": s_pagerank,
                "hits_hub": s_hits_hub,
                "hits_authority": s_hits_auth,
            },
            # Reliability & mass provenance
            "reliability": reliability_scores,
            "mass_combined": ds_result,
            "mass_sources": {
                "rule": mass_rule,
                "nlp": mass_nlp,
                "llm": mass_llm,
                "attribution": mass_attr,
            },
            # Info theory metrics (extended)
            "entropy": float(e.get('entropy', 0) or 0),
            "renyi_05": float(e.get('renyi_05', 0) or 0),
            "renyi_2": float(e.get('renyi_2', 0) or 0),
            "tsallis_05": float(e.get('tsallis_05', 0) or 0),
            "kl_divergence": float(e.get('kl_divergence', 0) or 0),
            # Metadata
            "domain": e.get('domain', ''),
            "timestamp": e.get('timestamp', ''),
            "comment": e.get('comment', ''),
            "diff_added": e.get('diff_added', '')[:200],
            "diff_removed": e.get('diff_removed', '')[:200],
            "is_reverted": e.get('is_reverted', ''),
            "wiki_url": e.get('wiki_url', ''),
        })

    verdicts.sort(key=lambda x: -x["score"])
    print(f"  Fusion methods used: {dict(fusion_methods)}")
    return verdicts


def main():
    print("WIKI-STREAM INTELLIGENCE FUSION v3.0 (Advanced DS + HITS + Pignistic)")
    edits = load_master_data()
    if not edits:
        print("  No data found.")
        return

    verdicts = run_fusion(edits)

    # Statistics
    dist = Counter(v['action'] for v in verdicts)
    conflicts = [v['ds_conflict'] for v in verdicts if v['ds_conflict'] > 0.3]
    uncertainties = [v['ds_uncertainty'] for v in verdicts]
    deng_entropies = [v['deng_entropy'] for v in verdicts]
    fusion_methods = Counter(v['ds_method'] for v in verdicts)

    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(edits),
        "methodology": {
            "fusion": "Adaptive DS (Murphy + PCR5) with Evidence Discounting",
            "uncertainty": "Deng Entropy (generalized Shannon for DS framework)",
            "decision": "Pignistic Probability Transformation (Smets TBM)",
            "anomaly_detection": "Isolation Forest (extended feature set)",
            "reputation": "Beta-Bayesian",
            "network": "Dual: SuspicionRank (PageRank) + HITS (Hub-Authority)",
            "features": "Multi-scale Information Theory (Shannon, Rényi, Tsallis, KL-Divergence, Kolmogorov)",
            "attribution": "Writeprints-MCD-NCD with Benford's Law",
        },
        "distribution": dict(dist),
        "statistics": {
            "high_conflict_edits": len(conflicts),
            "avg_uncertainty": round(sum(uncertainties) / max(len(uncertainties), 1), 3),
            "avg_deng_entropy": round(sum(deng_entropies) / max(len(deng_entropies), 1), 3),
            "mean_verdict": round(sum(v['score'] for v in verdicts) / max(len(verdicts), 1), 1),
            "fusion_methods": dict(fusion_methods),
        },
        "top_threats": verdicts[:50],
        "all_verdicts": verdicts,
    }

    with open(REPORT_DIR / "intelligence_master.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"  Intelligence Fusion Complete.")
    print(f"  Distribution: {dict(dist)}")
    print(f"  Fusion methods: {dict(fusion_methods)}")
    print(f"  High-conflict edits: {len(conflicts)}")
    print(f"  Avg Deng entropy: {report['statistics']['avg_deng_entropy']:.3f}")
    print(f"  Avg uncertainty width: {report['statistics']['avg_uncertainty']:.3f}")
    print(f"  Saved to reports/intelligence_master.json")


if __name__ == "__main__":
    main()
