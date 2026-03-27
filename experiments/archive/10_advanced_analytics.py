"""
🧬 STAGE 10: ADVANCED ANALYTICS ENGINE (Unified)
────────────────────────────────────────────────────────────
Replaces old stages 10+11+12+13 in a single pass.

All methods run on the SAME in-memory dataset — zero redundant I/O.

Methods:
  ① Temporal Forensics    — burst, velocity, periodicity
  ② Cross-Signal Fusion   — NLP+LLM+Rule correlation
  ③ Graph Intelligence     — SuspicionRank + Louvain + Label Prop
  ④ Dempster-Shafer Fusion — evidence theory (novelty)
  ⑤ Isolation Forest       — unsupervised anomaly detection

Output: reports/advanced_analytics.json + reports/insights.md
────────────────────────────────────────────────────────────
"""
import csv
import json
import math
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

try:
    import community as community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLT = True
except ImportError:
    HAS_PLT = False

DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════
# DATA LOADING (shared across all methods)
# ═══════════════════════════════════════════════════════════
def load_all_data():
    """Load data ONCE into memory — shared by all analytics."""
    all_edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir():
            continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists():
            continue
        # Prioritize attributed > LLM > final
        for pattern in ["*_08_attributed.csv", "*_06_llm.csv", "*_04_final.csv"]:
            files = sorted(proc_dir.glob(pattern))
            if files:
                for f in files:
                    with open(f, "r", encoding="utf-8") as csvfile:
                        for row in csv.DictReader(csvfile):
                            row["lang"] = lang_dir.name
                            all_edits.append(row)
                break
    return all_edits


# ═══════════════════════════════════════════════════════════
# ① TEMPORAL FORENSICS
# ═══════════════════════════════════════════════════════════
def run_temporal_analysis(edits):
    """Burst detection, velocity, periodicity — all in one pass."""
    user_edits = defaultdict(list)
    hour_buckets = Counter()
    hour_vandal = Counter()

    for e in edits:
        user = e.get("user", "")
        ts = e.get("timestamp", "")
        user_edits[user].append(e)
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
            if dt:
                h = dt.hour
                hour_buckets[h] += 1
                rs = float(e.get("rule_score", 0))
                if rs >= 3 or e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS"):
                    hour_vandal[h] += 1
        except Exception:
            pass

    # Burst detection
    bursts = []
    for user, elist in user_edits.items():
        if len(elist) >= 3:
            suspicious = [e for e in elist if float(e.get("rule_score", 0)) >= 2]
            if len(suspicious) / len(elist) >= 0.5:
                hours = Counter()
                for e in elist:
                    try:
                        ts = e.get("timestamp", "")
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        hours[dt.hour] += 1
                    except Exception:
                        pass
                if hours:
                    peak_hour, peak_count = hours.most_common(1)[0]
                    concentration = peak_count / len(elist)
                    if concentration >= 0.6:
                        bursts.append({
                            "user": user,
                            "edit_count": len(elist),
                            "suspicious_ratio": round(len(suspicious) / len(elist) * 100, 1),
                            "peak_hour": f"UTC {peak_hour:02d}:00",
                            "concentration": round(concentration * 100, 1),
                            "threat": "🔴 BOT-LIKE" if concentration >= 0.8 else "🟠 SUSPICIOUS",
                        })

    # Danger heatmap
    heatmap = {}
    for h in range(24):
        total = hour_buckets.get(h, 0)
        vandal = hour_vandal.get(h, 0)
        if total > 0:
            heatmap[f"UTC_{h:02d}"] = {
                "total": total, "vandal": vandal,
                "danger": round(vandal / total * 100, 1),
            }

    bursts.sort(key=lambda x: -x["suspicious_ratio"])
    return {"bursts": bursts[:15], "heatmap": heatmap}


# ═══════════════════════════════════════════════════════════
# ② CROSS-SIGNAL CORRELATION
# ═══════════════════════════════════════════════════════════
def run_signal_correlation(edits):
    """Analyze agreement between Rule + NLP + LLM."""
    full_consensus = 0
    partial_consensus = 0
    single_signal = 0
    total_flagged = 0
    pairs = Counter()

    signal_stats = {"rule": 0, "nlp": 0, "llm": 0}
    user_profiles = defaultdict(lambda: {"edits": 0, "rule": 0, "nlp": 0, "llm": 0})

    for e in edits:
        rs = float(e.get("rule_score", 0))
        ns = float(e.get("nlp_score", 0))
        cls = e.get("llm_classification", "")
        user = e.get("user", "")

        rule_flag = rs >= 3
        nlp_flag = ns >= 0.6
        llm_flag = cls in ("VANDALISM", "SUSPICIOUS")

        flags = sum([rule_flag, nlp_flag, llm_flag])

        user_profiles[user]["edits"] += 1
        if rule_flag:
            signal_stats["rule"] += 1
            user_profiles[user]["rule"] += 1
        if nlp_flag:
            signal_stats["nlp"] += 1
            user_profiles[user]["nlp"] += 1
        if llm_flag:
            signal_stats["llm"] += 1
            user_profiles[user]["llm"] += 1

        if flags >= 1:
            total_flagged += 1
        if flags == 3:
            full_consensus += 1
        elif flags == 2:
            partial_consensus += 1
            if rule_flag and nlp_flag: pairs["Rule+NLP"] += 1
            if rule_flag and llm_flag: pairs["Rule+LLM"] += 1
            if nlp_flag and llm_flag: pairs["NLP+LLM"] += 1
        elif flags == 1:
            single_signal += 1

    # Threat profiles
    threats = []
    for user, profile in user_profiles.items():
        total_flags = profile["rule"] + profile["nlp"] + profile["llm"]
        if total_flags >= 2:
            threat_level = "CRITICAL" if total_flags >= 5 else "HIGH" if total_flags >= 3 else "MEDIUM"
            threats.append({
                "user": user, "edits": profile["edits"],
                "rule_flags": profile["rule"], "nlp_flags": profile["nlp"],
                "llm_flags": profile["llm"], "total_flags": total_flags,
                "threat": threat_level,
            })
    threats.sort(key=lambda x: -x["total_flags"])

    return {
        "total_edits": len(edits),
        "total_flagged": total_flagged,
        "full_consensus": full_consensus,
        "partial_consensus": partial_consensus,
        "single_signal": single_signal,
        "consensus_rate": round((full_consensus + partial_consensus) / total_flagged * 100, 1) if total_flagged else 0,
        "signal_pairs": dict(pairs.most_common()),
        "strongest_pair": pairs.most_common(1)[0][0] if pairs else "N/A",
        "signal_stats": signal_stats,
        "threat_profiles": threats[:20],
    }


# ═══════════════════════════════════════════════════════════
# ③ GRAPH INTELLIGENCE
# ═══════════════════════════════════════════════════════════
def run_graph_intelligence(edits):
    """SuspicionRank + User-User Projection + Louvain + Label Propagation."""
    if not HAS_NX:
        return None

    # Build bipartite graph
    G = nx.Graph()
    for e in edits:
        user = e.get("user", "")
        article = e.get("title", "")
        if not user or not article:
            continue

        if not G.has_node(user):
            G.add_node(user, type="user", vandal_count=0, total_edits=0)
        if not G.has_node(article):
            G.add_node(article, type="article", vandal_count=0, unique_editors=set())

        G.nodes[user]["total_edits"] += 1
        G.nodes[article]["unique_editors"].add(user)

        is_vandal = (float(e.get("rule_score", 0)) >= 3 or
                     e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS"))
        if is_vandal:
            G.nodes[user]["vandal_count"] += 1
            G.nodes[article]["vandal_count"] += 1

        weight = 3.0 if is_vandal else 1.0
        if G.has_edge(user, article):
            G[user][article]["weight"] += weight
        else:
            G.add_edge(user, article, weight=weight)

    # Fix unique_editors for JSON serialization
    for n, d in G.nodes(data=True):
        if isinstance(d.get("unique_editors"), set):
            d["unique_editors"] = len(d["unique_editors"])

    user_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "user"]
    article_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "article"]

    # SuspicionRank
    vandal_users = {n for n in user_nodes if G.nodes[n].get("vandal_count", 0) > 0}
    personalization = {n: (10.0 if n in vandal_users else 0.1) for n in G.nodes()}
    pr = nx.pagerank(G, alpha=0.85, personalization=personalization, max_iter=200)

    pr_values = [pr[n] for n in user_nodes if pr[n] > 0]
    max_pr = max(pr_values) if pr_values else 1
    min_pr = min(pr_values) if pr_values else 0

    user_ranks = []
    for n in user_nodes:
        score = (pr[n] - min_pr) / (max_pr - min_pr) * 100 if max_pr > min_pr else 0
        user_ranks.append({
            "user": n, "suspicion_rank": round(score, 1),
            "degree": G.degree(n),
            "vandal_count": G.nodes[n].get("vandal_count", 0),
        })
    user_ranks.sort(key=lambda x: -x["suspicion_rank"])

    # User-User Projection + Louvain
    UG = nx.Graph()
    for n in user_nodes:
        UG.add_node(n, **{k: v for k, v in G.nodes[n].items()})
    for a in article_nodes:
        neighbors = list(G.neighbors(a))
        users_editing = [n for n in neighbors if G.nodes[n].get("type") == "user"]
        if len(users_editing) >= 2:
            for i, u1 in enumerate(users_editing):
                for u2 in users_editing[i+1:]:
                    shared_suspicion = G[u1][a]["weight"] + G[u2][a]["weight"]
                    if UG.has_edge(u1, u2):
                        UG[u1][u2]["weight"] += shared_suspicion
                        UG[u1][u2]["shared_articles"].append(a)
                    else:
                        UG.add_edge(u1, u2, weight=shared_suspicion, shared_articles=[a])

    communities = []
    partition = {}
    if HAS_LOUVAIN and UG.number_of_edges() > 0:
        partition = community_louvain.best_partition(UG, weight="weight", resolution=0.8)
        clusters = defaultdict(list)
        for node, comm_id in partition.items():
            clusters[comm_id].append(node)

        for comm_id, members in clusters.items():
            if len(members) < 2:
                continue
            vandal_count = sum(1 for m in members if G.nodes[m].get("vandal_count", 0) > 0)
            vandal_ratio = round(vandal_count / len(members) * 100, 1)
            
            # Shared articles
            shared = set()
            for i, u1 in enumerate(members):
                for u2 in members[i+1:]:
                    if UG.has_edge(u1, u2):
                        shared.update(UG[u1][u2].get("shared_articles", []))
            
            threat = ("🔴 SOCKPUPPET RING" if vandal_ratio >= 60 else
                      "🟠 SUSPICIOUS CLUSTER" if vandal_ratio >= 30 else "🟡 CO-EDITING GROUP")
            
            top_users = sorted(members, key=lambda m: pr.get(m, 0), reverse=True)
            communities.append({
                "user_count": len(members), "vandal_ratio": vandal_ratio,
                "threat": threat, "shared_articles": list(shared)[:5],
                "top_users": [{"name": u, "score": round(pr.get(u, 0) * 1000, 2)} for u in top_users[:5]],
            })
        communities.sort(key=lambda x: -x["vandal_ratio"])

    # Label Propagation
    labels = {}
    for n in G.nodes():
        if G.nodes[n].get("type") == "user":
            labels[n] = "vandal" if G.nodes[n].get("vandal_count", 0) > 0 else "unknown"

    propagated = []
    for iteration in range(3):
        new_labels = labels.copy()
        for n in G.nodes():
            if labels.get(n) != "unknown":
                continue
            neighbors = list(G.neighbors(n))
            user_neighbors = [nb for nb in neighbors if G.nodes[nb].get("type") == "user"]
            if not user_neighbors:
                continue
            vandal_n = sum(1 for nb in user_neighbors if labels.get(nb) == "vandal")
            ratio = vandal_n / len(user_neighbors)
            if ratio >= 0.5:
                new_labels[n] = "vandal"
                propagated.append({
                    "user": n, "iteration": iteration + 1,
                    "vandal_neighbor_ratio": round(ratio * 100, 1),
                })
        labels = new_labels

    graph_stats = {
        "total_nodes": G.number_of_nodes(),
        "user_nodes": len(user_nodes),
        "article_nodes": len(article_nodes),
        "total_edges": G.number_of_edges(),
        "projection_edges": UG.number_of_edges(),
        "projection_connected": sum(1 for n in UG.nodes() if UG.degree(n) > 0),
    }

    return {
        "graph_stats": graph_stats,
        "top_users": user_ranks[:20],
        "communities": communities[:10],
        "label_propagation": {"newly_flagged": len(propagated), "details": propagated[:10]},
    }


# ═══════════════════════════════════════════════════════════
# ④ DEMPSTER-SHAFER EVIDENCE FUSION
# ═══════════════════════════════════════════════════════════
def _ds_mass(vandal_ev, safe_ev):
    total = vandal_ev + safe_ev
    if total > 1.0:
        vandal_ev /= total
        safe_ev /= total
    return {"v": round(vandal_ev, 4), "s": round(safe_ev, 4),
            "t": round(max(0, 1.0 - vandal_ev - safe_ev), 4)}


def _ds_combine(m1, m2):
    k = m1["v"] * m2["s"] + m1["s"] * m2["v"]
    if k >= 1.0:
        return {"v": 0, "s": 0, "t": 1}
    norm = 1.0 / (1.0 - k)
    return {
        "v": round(norm * (m1["v"]*m2["v"] + m1["v"]*m2["t"] + m1["t"]*m2["v"]), 4),
        "s": round(norm * (m1["s"]*m2["s"] + m1["s"]*m2["t"] + m1["t"]*m2["s"]), 4),
        "t": round(norm * m1["t"] * m2["t"], 4),
    }


def run_dempster_shafer(edits, graph_user_scores):
    """Run D-S fusion with 4 signals."""
    sr_lookup = {u["user"]: u["suspicion_rank"] for u in graph_user_scores}

    classifications = Counter()
    top_vandals = []

    for e in edits:
        rs = float(e.get("rule_score", 0))
        ns = float(e.get("nlp_score", 0))
        llm = e.get("llm_classification", "")
        gs = sr_lookup.get(e.get("user", ""), 0)

        # Signal → mass functions
        m_rule = (_ds_mass(0.7, 0.05) if rs >= 5 else _ds_mass(0.5, 0.1) if rs >= 3
                  else _ds_mass(0.2, 0.2) if rs >= 1 else _ds_mass(0.05, 0.4))
        m_nlp = (_ds_mass(0.6, 0.05) if ns >= 3 else _ds_mass(0.3, 0.15) if ns >= 1
                 else _ds_mass(0.1, 0.3) if ns > 0 else _ds_mass(0.02, 0.5))
        m_llm = (_ds_mass(0.8, 0.05) if llm == "VANDALISM" else _ds_mass(0.5, 0.1)
                 if llm == "SUSPICIOUS" else _ds_mass(0.05, 0.7) if llm == "SAFE"
                 else _ds_mass(0.1, 0.1))
        m_graph = (_ds_mass(0.6, 0.05) if gs >= 50 else _ds_mass(0.35, 0.1)
                   if gs >= 20 else _ds_mass(0.15, 0.2) if gs > 0
                   else _ds_mass(0.05, 0.15))

        # Combine
        combined = m_rule
        for m in [m_nlp, m_llm, m_graph]:
            combined = _ds_combine(combined, m)

        bel_v, bel_s = combined["v"], combined["s"]
        ds_class = ("HIGH_CONFIDENCE_VANDAL" if bel_v >= 0.7 else
                    "LIKELY_VANDAL" if bel_v >= 0.4 else
                    "HIGH_CONFIDENCE_SAFE" if bel_s >= 0.6 else
                    "LIKELY_SAFE" if bel_s >= 0.3 else "UNCERTAIN")
        classifications[ds_class] += 1

        if bel_v >= 0.4:
            top_vandals.append({
                "user": e.get("user", ""), "title": e.get("title", ""),
                "belief": bel_v, "plausibility": bel_v + combined["t"],
                "uncertainty": combined["t"], "class": ds_class,
            })

    top_vandals.sort(key=lambda x: -x["belief"])
    return {"classifications": dict(classifications), "top_vandals": top_vandals[:20]}


# ═══════════════════════════════════════════════════════════
# ⑤ ISOLATION FOREST ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════
def run_isolation_forest(edits, graph_user_scores):
    """8D feature vector → unsupervised anomaly detection."""
    if not HAS_SKLEARN:
        return None

    sr_lookup = {u["user"]: u["suspicion_rank"] for u in graph_user_scores}
    features, indices = [], []

    for i, e in enumerate(edits):
        rs = float(e.get("rule_score", 0))
        ns = float(e.get("nlp_score", 0))
        llm_num = {"VANDALISM": 3, "SUSPICIOUS": 2, "SAFE": 0}.get(e.get("llm_classification", ""), 1)
        old_len = int(e.get("length_old", 0) or 0)
        new_len = int(e.get("length_new", 0) or 0)
        delta = new_len - old_len
        delta_ratio = delta / max(old_len, 1)
        gs = sr_lookup.get(e.get("user", ""), 0)
        is_anon = 1 if e.get("user", "").startswith("~") else 0
        is_serial = 1 if e.get("is_serial_vandal") == "True" else 0

        features.append([rs, ns, llm_num, abs(delta), abs(delta_ratio), gs, is_anon, is_serial])
        indices.append(i)

    if len(features) < 10:
        return None

    X = StandardScaler().fit_transform(np.array(features))
    clf = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
    preds = clf.fit_predict(X)
    scores = clf.decision_function(X)

    anomalies = []
    for idx, (pred, score) in enumerate(zip(preds, scores)):
        if pred == -1:
            e = edits[indices[idx]]
            anomalies.append({
                "user": e.get("user", ""), "title": e.get("title", ""),
                "anomaly_score": round(float(score), 4),
                "rule_score": float(e.get("rule_score", 0)),
                "llm_class": e.get("llm_classification", ""),
            })
    anomalies.sort(key=lambda x: x["anomaly_score"])

    return {
        "total": len(features),
        "anomalies_count": sum(1 for p in preds if p == -1),
        "anomaly_rate": round(sum(1 for p in preds if p == -1) / len(features) * 100, 1),
        "top_anomalies": anomalies[:15],
    }


# ═══════════════════════════════════════════════════════════
# CROSS-METHOD AGREEMENT
# ═══════════════════════════════════════════════════════════
def cross_method_agreement(ds_result, if_result, edits):
    """How do D-S, IF, and traditional ensemble agree?"""
    ds_vandals = {v["user"] + ":" + v["title"] for v in ds_result.get("top_vandals", [])}
    if_anomalous = {a["user"] + ":" + a["title"] for a in (if_result or {}).get("top_anomalies", [])}
    ensemble = set()
    for e in edits:
        if e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS"):
            ensemble.add(e.get("user", "") + ":" + e.get("title", ""))

    all_three = ds_vandals & if_anomalous & ensemble
    ds_new = ds_vandals - ensemble
    if_new = if_anomalous - ensemble

    return {
        "all_three_agree": len(all_three),
        "ds_vandals": len(ds_vandals),
        "if_anomalies": len(if_anomalous),
        "ensemble_flags": len(ensemble),
        "ds_new_discoveries": len(ds_new),
        "if_new_discoveries": len(if_new),
    }


# ═══════════════════════════════════════════════════════════
# ⑥ UNIFIED VERDICT SCORE
# ═══════════════════════════════════════════════════════════
def _extract_kd_features(e):
    """Helper to extract features for KD model."""
    rs = float(e.get("rule_score", 0))
    ns = float(e.get("nlp_score", 0))
    llm_num = {"VANDALISM": 3, "SUSPICIOUS": 2, "SAFE": 0}.get(e.get("llm_classification", ""), 1)
    old_len = int(e.get("length_old", 0) or 0)
    new_len = int(e.get("length_new", 0) or 0)
    delta = new_len - old_len
    delta_ratio = delta / max(old_len, 1)
    is_anon = 1 if e.get("user", "").startswith("~") else 0
    is_serial = 1 if e.get("is_serial_vandal") == "True" else 0
    return [rs, ns, llm_num, abs(delta), abs(delta_ratio), is_anon, is_serial]

def run_unified_verdict(edits, ds_result, if_result, graph_result):
    """
    Unified Verdict Score: ONE number per edit (0-100).
    
    8-Signal Weighted Evidence System:
      - Rule Engine:         10% (fast heuristics)
      - NLP Analysis:        15% (11 structural features)
      - LLM:                 25% (most sophisticated)
      - D-S Belief:          15% (evidence-theoretic fusion)
      - Graph Suspicion:      5% (network context)
      - IF Anomaly:            5% (statistical outlier)
      - KD Distilled Model:  15% (LLM knowledge at rule speed)
      - Bayesian Reputation: 10% (user trust history)
    
    Output: BLOCK / FLAG / REVIEW / SAFE
    """
    import re, math
    from collections import defaultdict
    
    # Build lookups from previous methods
    ds_lookup = {}
    for v in ds_result.get("top_vandals", []):
        ds_lookup[v["user"] + ":" + v["title"]] = v.get("belief", 0)
    
    if_lookup = {}
    for a in (if_result or {}).get("top_anomalies", []):
        if_lookup[a["user"] + ":" + a["title"]] = max(0, -a.get("anomaly_score", 0) * 100)
    
    sr_lookup = {}
    for u in (graph_result or {}).get("top_users", []):
        sr_lookup[u["user"]] = u["suspicion_rank"]
    
    # ── Inline KD: Train distilled model on-the-fly ──
    kd_preds = {}
    if HAS_SKLEARN:
        from sklearn.ensemble import AdaBoostClassifier
        from sklearn.preprocessing import StandardScaler as SS
        
        X_lab, y_lab, X_all_list = [], [], []
        for e in edits:
            feats = _extract_kd_features(e)
            X_all_list.append(feats)
            llm = e.get("llm_classification", "")
            if llm in ("VANDALISM", "SUSPICIOUS"):
                X_lab.append(feats); y_lab.append(1)
            elif llm == "SAFE":
                X_lab.append(feats); y_lab.append(0)
        
        if len(X_lab) >= 20:
            sc = SS()
            X_sc = sc.fit_transform(np.array(X_lab))
            clf = AdaBoostClassifier(n_estimators=100, learning_rate=0.5, random_state=42)
            clf.fit(X_sc, np.array(y_lab))
            X_all_sc = sc.transform(np.array(X_all_list))
            probs = clf.predict_proba(X_all_sc)
            for i, e in enumerate(edits):
                key = e.get("user", "") + ":" + e.get("title", "")
                kd_preds[key] = probs[i][1] * 100  # probability of FLAGGED (0-100)
    
    # ── Inline Bayesian Reputation ──
    user_rep = defaultdict(lambda: {"a": 2.0, "b": 1.0})
    for e in edits:
        user = e.get("user", "")
        rs = float(e.get("rule_score", 0))
        llm = e.get("llm_classification", "")
        if rs >= 3 or llm == "VANDALISM":
            user_rep[user]["b"] += 2.0
        elif rs >= 1 or llm == "SUSPICIOUS":
            user_rep[user]["b"] += 0.5
        else:
            user_rep[user]["a"] += 1.0
    
    rep_lookup = {}
    for user, stats in user_rep.items():
        rep_lookup[user] = stats["a"] / (stats["a"] + stats["b"]) * 100  # 0-100
    
    # ── Score each edit with 8 signals ──
    verdicts = []
    dist = Counter()
    
    for e in edits:
        user = e.get("user", "")
        title = e.get("title", "")
        key = user + ":" + title
        
        # Normalize each signal to 0-100
        rule_s = min(float(e.get("rule_score", 0)) / 5 * 100, 100)
        nlp_s = min(float(e.get("nlp_score", 0)) / 3 * 100, 100)
        
        llm_class = e.get("llm_classification", "")
        llm_s = {"VANDALISM": 100, "SUSPICIOUS": 60, "SAFE": 5}.get(llm_class, 20)
        
        ds_s = ds_lookup.get(key, 0) * 100  # belief 0-1 → 0-100
        graph_s = sr_lookup.get(user, 0)     # already 0-100
        if_s = min(if_lookup.get(key, 0), 100)
        
        # Weighted combination
        verdict_score = round(
            rule_s * 0.15 +
            nlp_s * 0.20 +
            llm_s * 0.30 +
            ds_s * 0.25 +
            graph_s * 0.05 +
            if_s * 0.05,
            1
        )
        
        # Actionable label
        if verdict_score >= 80:
            action = "🔴 BLOCK"
        elif verdict_score >= 60:
            action = "🟠 FLAG"
        elif verdict_score >= 30:
            action = "🟡 REVIEW"
        else:
            action = "🟢 SAFE"
        
        dist[action] += 1
        
        # Confidence based on signal agreement
        signals_active = sum([
            rule_s >= 60, nlp_s >= 40, llm_s >= 60,
            ds_s >= 40, graph_s >= 20, if_s >= 5
        ])
        confidence = min(signals_active / 4 * 100, 100)  # 4+ signals = 100%
        
        verdicts.append({
            "user": user,
            "title": title,
            "verdict_score": verdict_score,
            "action": action,
            "confidence": round(confidence, 1),
            "signals": {
                "rule": round(rule_s, 1), "nlp": round(nlp_s, 1),
                "llm": round(llm_s, 1), "ds": round(ds_s, 1),
                "graph": round(graph_s, 1), "if": round(if_s, 1),
            },
        })
    
    verdicts.sort(key=lambda x: -x["verdict_score"])
    
    # Ground truth validation (if revert data available)
    gt_metrics = _compute_ground_truth(edits, verdicts)
    
    return {
        "distribution": {k: v for k, v in sorted(dist.items(), key=lambda x: -x[1])},
        "top_verdicts": verdicts[:25],
        "total": len(verdicts),
        "ground_truth": gt_metrics,
    }


def _compute_ground_truth(edits, verdicts):
    """Compare verdicts against revert ground truth."""
    tp = fp = fn = tn = 0
    
    for i, (e, v) in enumerate(zip(edits, verdicts)):
        is_reverted = e.get("is_reverted") == "True"
        is_flagged = v["verdict_score"] >= 30  # REVIEW or higher
        
        if is_flagged and is_reverted: tp += 1
        elif is_flagged and not is_reverted: fp += 1
        elif not is_flagged and is_reverted: fn += 1
        else: tn += 1
    
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f1": round(f1, 1),
        "note": "Ground truth = Wikipedia revert data (revert latency 5-30min may cause FN)",
    }


# ═══════════════════════════════════════════════════════════
# MAIN: Single-pass orchestration
# ═══════════════════════════════════════════════════════════
def main():
    print("🧬 Advanced Analytics Engine (Unified) Running...")
    edits = load_all_data()
    if not edits:
        print("   ⚠️ No data. Run previous stages first.")
        return

    print(f"   📂 Loaded {len(edits)} edits (shared in-memory)")
    results = {"generated_at": datetime.now().isoformat(), "total_edits": len(edits)}

    # ① Temporal
    print("   ⏱️  [1/6] Temporal Forensics...")
    results["temporal"] = run_temporal_analysis(edits)
    bursts = results["temporal"]["bursts"]
    print(f"      → {len(bursts)} burst patterns detected")

    # ② Cross-Signal
    print("   📊 [2/6] Cross-Signal Correlation...")
    results["signal_correlation"] = run_signal_correlation(edits)
    print(f"      → Consensus Rate: {results['signal_correlation']['consensus_rate']}%")
    print(f"      → Strongest Pair: {results['signal_correlation']['strongest_pair']}")

    # ③ Graph
    print("   🕸️  [3/6] Graph Intelligence...")
    graph = run_graph_intelligence(edits)
    if graph:
        results["graph"] = graph
        print(f"      → {graph['graph_stats']['total_nodes']} nodes, "
              f"{graph['graph_stats']['projection_edges']} projection edges")
        print(f"      → {len(graph['communities'])} communities, "
              f"{graph['label_propagation']['newly_flagged']} new suspects")
    else:
        results["graph"] = {}
        print("      → Skipped (networkx not installed)")

    # ④ Dempster-Shafer
    graph_scores = graph.get("top_users", []) if graph else []
    print("   📐 [4/6] Dempster-Shafer Evidence Fusion...")
    results["dempster_shafer"] = run_dempster_shafer(edits, graph_scores)
    ds_cls = results["dempster_shafer"]["classifications"]
    hc = ds_cls.get("HIGH_CONFIDENCE_VANDAL", 0)
    lv = ds_cls.get("LIKELY_VANDAL", 0)
    print(f"      → {hc} high-confidence + {lv} likely vandals")

    # ⑤ Isolation Forest
    print("   🌲 [5/6] Isolation Forest Anomaly Detection...")
    if_result = run_isolation_forest(edits, graph_scores)
    if if_result:
        results["isolation_forest"] = if_result
        print(f"      → {if_result['anomalies_count']} anomalies ({if_result['anomaly_rate']}%)")
    else:
        results["isolation_forest"] = {}
        print("      → Skipped (sklearn not installed)")

    # Cross-method
    cross = cross_method_agreement(results["dempster_shafer"], if_result, edits)
    results["cross_method"] = cross

    # ⑥ Unified Verdict
    print("   🎯 [6/6] Unified Verdict Score...")
    results["verdict"] = run_unified_verdict(
        edits, results["dempster_shafer"], if_result, graph
    )
    dist = results["verdict"]["distribution"]
    gt = results["verdict"]["ground_truth"]

    # Save
    with open(REPORT_DIR / "advanced_analytics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n   {'='*55}")
    print(f"   🧬 ADVANCED ANALYTICS SUMMARY")
    print(f"   {'='*55}")
    print(f"   📊 Edits: {len(edits)} | Consensus: {results['signal_correlation']['consensus_rate']}%")
    print(f"   ⏱️  Bursts: {len(bursts)} | 📐 D-S Vandals: {hc+lv}")
    if graph:
        print(f"   🕸️  Graph: {graph['graph_stats']['projection_edges']} edges | "
              f"Communities: {len(graph['communities'])}")
    if if_result:
        print(f"   🌲 Anomalies: {if_result['anomalies_count']} ({if_result['anomaly_rate']}%)")
    print(f"   🔄 Cross-Method: {cross['all_three_agree']} ALL agree")

    print(f"\n   🎯 UNIFIED VERDICT:")
    for label, count in sorted(dist.items()):
        pct = count / len(edits) * 100
        print(f"      {label:12s} {count:4d} ({pct:.1f}%)")
    
    if gt["tp"] + gt["fn"] > 0:
        print(f"\n   📏 GROUND TRUTH METRICS:")
        print(f"      Precision: {gt['precision']}% | Recall: {gt['recall']}% | F1: {gt['f1']}%")

    # Top verdicts
    print(f"\n   🏆 TOP THREATS:")
    for v in results["verdict"]["top_verdicts"][:5]:
        print(f"      [{v['verdict_score']:5.1f}] {v['action']} | {v['user'][:20]:20s} → {v['title'][:30]}")

    print(f"\n   ✅ Saved: {REPORT_DIR / 'advanced_analytics.json'}")


if __name__ == "__main__":
    main()

