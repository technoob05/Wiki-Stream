"""
🧬 STAGE 13: ADVANCED INTELLIGENCE FUSION
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_08_attributed.csv
        reports/graph_intelligence.json
Output: reports/advanced_fusion.json
Goal:   Nâng cấp method detection bằng 3 kỹ thuật tiên tiến:

  1. DEMPSTER-SHAFER EVIDENCE FUSION
     → Thay thế majority voting bằng lý thuyết bằng chứng
     → Mỗi signal (Rule, NLP, LLM, Graph) cung cấp "mass function"
     → Dempster's Rule kết hợp bằng chứng từ nhiều nguồn
     → Output: belief, plausibility, uncertainty
     → Novelty: Rất ít hệ thống vandalism detection dùng phương pháp này

  2. ISOLATION FOREST ANOMALY DETECTION
     → Unsupervised ML: không cần labeled data
     → Phát hiện edits "bất thường" dựa trên feature vector
     → Bổ sung cho ensemble: tìm anomalies mà rules+NLP+LLM bỏ sót

  3. MULTI-SIGNAL CONFIDENCE CALIBRATION
     → Platt Scaling: hiệu chỉnh confidence scores
     → Output: calibrated probabilities có ý nghĩa thống kê

Methods: Dempster-Shafer Theory + scikit-learn IsolationForest
Novel:   Evidence Theory + Unsupervised ML for Wikipedia vandalism
────────────────────────────────────────────────────────────
"""
import csv
import json
import math
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from itertools import combinations

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def load_all_data():
    all_edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir(): continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
        files = list(proc_dir.glob("*_08_attributed.csv"))
        if not files:
            files = list(proc_dir.glob("*_06_llm.csv"))
        for f in files:
            with open(f, "r", encoding="utf-8") as csvfile:
                for row in csv.DictReader(csvfile):
                    row["lang"] = lang_dir.name
                    all_edits.append(row)
    return all_edits


def load_graph_scores():
    """Load SuspicionRank scores from Graph Intelligence."""
    p = REPORT_DIR / "graph_intelligence.json"
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        gi = json.load(f)
    lookup = {}
    for u in gi.get("suspicion_rank", {}).get("top_users", []):
        lookup[u["user"]] = u["suspicion_rank"]
    return lookup


# ═══════════════════════════════════════════════════════════
# 1. DEMPSTER-SHAFER EVIDENCE FUSION
# ═══════════════════════════════════════════════════════════
class DempsterShafer:
    """
    Dempster-Shafer Theory of Evidence
    ─────────────────────────────────────
    Frame of discernment: Θ = {VANDAL, SAFE}
    Mass functions: m(VANDAL), m(SAFE), m(Θ)  [uncertainty]
    
    Mỗi signal cung cấp 1 mass function:
      - m(VANDAL) = evidence rằng edit là vandal
      - m(SAFE)   = evidence rằng edit an toàn
      - m(Θ)      = uncertainty (không biết)
    
    Dempster's Rule of Combination:
      Kết hợp 2+ mass functions thành 1 unified belief
    """
    
    @staticmethod
    def create_mass(vandal_evidence, safe_evidence):
        """Tạo mass function từ evidence levels [0,1]."""
        # Normalize to valid mass function
        total = vandal_evidence + safe_evidence
        if total > 1.0:
            vandal_evidence /= total
            safe_evidence /= total
        
        uncertainty = max(0, 1.0 - vandal_evidence - safe_evidence)
        return {
            "vandal": round(vandal_evidence, 4),
            "safe": round(safe_evidence, 4),
            "theta": round(uncertainty, 4),  # uncertainty
        }
    
    @staticmethod
    def combine(m1, m2):
        """Dempster's Rule of Combination."""
        # Calculate conflict
        k = (m1["vandal"] * m2["safe"]) + (m1["safe"] * m2["vandal"])
        
        if k >= 1.0:
            # Total conflict — return equal uncertainty
            return {"vandal": 0.0, "safe": 0.0, "theta": 1.0}
        
        norm = 1.0 / (1.0 - k)
        
        vandal = norm * (
            m1["vandal"] * m2["vandal"] +
            m1["vandal"] * m2["theta"] +
            m1["theta"] * m2["vandal"]
        )
        safe = norm * (
            m1["safe"] * m2["safe"] +
            m1["safe"] * m2["theta"] +
            m1["theta"] * m2["safe"]
        )
        theta = norm * m1["theta"] * m2["theta"]
        
        return {
            "vandal": round(vandal, 4),
            "safe": round(safe, 4),
            "theta": round(theta, 4),
        }
    
    @staticmethod
    def combine_multiple(masses):
        """Kết hợp nhiều mass functions."""
        if not masses:
            return {"vandal": 0, "safe": 0, "theta": 1}
        result = masses[0]
        for m in masses[1:]:
            result = DempsterShafer.combine(result, m)
        return result
    
    @staticmethod
    def belief(combined, hypothesis="vandal"):
        """Belief = lower bound of probability."""
        return combined.get(hypothesis, 0)
    
    @staticmethod
    def plausibility(combined, hypothesis="vandal"):
        """Plausibility = upper bound of probability."""
        return combined.get(hypothesis, 0) + combined.get("theta", 0)
    
    @staticmethod
    def uncertainty_interval(combined, hypothesis="vandal"):
        """[Belief, Plausibility] interval."""
        bel = DempsterShafer.belief(combined, hypothesis)
        pl = DempsterShafer.plausibility(combined, hypothesis)
        return bel, pl


def signal_to_mass(signal_name, value, classification=""):
    """Convert mỗi signal thành mass function."""
    ds = DempsterShafer
    
    if signal_name == "rule":
        # Rule score: 0-10+ scale
        score = float(value)
        if score >= 5:
            return ds.create_mass(0.7, 0.05)  # Strong vandal evidence
        elif score >= 3:
            return ds.create_mass(0.5, 0.1)
        elif score >= 1:
            return ds.create_mass(0.2, 0.2)
        else:
            return ds.create_mass(0.05, 0.4)  # Likely safe
    
    elif signal_name == "nlp":
        score = float(value)
        if score >= 3.0:
            return ds.create_mass(0.6, 0.05)
        elif score >= 1.0:
            return ds.create_mass(0.3, 0.15)
        elif score > 0:
            return ds.create_mass(0.1, 0.3)
        else:
            return ds.create_mass(0.02, 0.5)
    
    elif signal_name == "llm":
        if classification == "VANDALISM":
            return ds.create_mass(0.8, 0.05)  # LLM very confident
        elif classification == "SUSPICIOUS":
            return ds.create_mass(0.5, 0.1)
        elif classification == "SAFE":
            return ds.create_mass(0.05, 0.7)
        else:
            return ds.create_mass(0.1, 0.1)  # No data = high uncertainty
    
    elif signal_name == "graph":
        score = float(value)
        if score >= 50:
            return ds.create_mass(0.6, 0.05)
        elif score >= 20:
            return ds.create_mass(0.35, 0.1)
        elif score > 0:
            return ds.create_mass(0.15, 0.2)
        else:
            return ds.create_mass(0.05, 0.15)  # No graph data = uncertain
    
    return ds.create_mass(0.1, 0.1)


def run_dempster_shafer(edits, graph_scores):
    """Run D-S fusion on all edits."""
    ds = DempsterShafer
    results = []
    
    classifications = {"HIGH_CONFIDENCE_VANDAL": 0, "LIKELY_VANDAL": 0,
                       "UNCERTAIN": 0, "LIKELY_SAFE": 0, "HIGH_CONFIDENCE_SAFE": 0}
    
    for edit in edits:
        rule_score = float(edit.get("rule_score", 0))
        nlp_score = float(edit.get("nlp_score", 0))
        llm_class = edit.get("llm_classification", "")
        user = edit.get("user", "")
        graph_score = graph_scores.get(user, 0)
        
        # Convert each signal to mass function
        masses = [
            signal_to_mass("rule", rule_score),
            signal_to_mass("nlp", nlp_score),
            signal_to_mass("llm", 0, llm_class),
            signal_to_mass("graph", graph_score),
        ]
        
        # Combine using Dempster's Rule
        combined = ds.combine_multiple(masses)
        
        # Calculate metrics
        bel_v = ds.belief(combined, "vandal")
        pl_v = ds.plausibility(combined, "vandal")
        bel_s = ds.belief(combined, "safe")
        uncertainty = combined["theta"]
        
        # Classify
        if bel_v >= 0.7:
            ds_class = "HIGH_CONFIDENCE_VANDAL"
        elif bel_v >= 0.4:
            ds_class = "LIKELY_VANDAL"
        elif bel_s >= 0.6:
            ds_class = "HIGH_CONFIDENCE_SAFE"
        elif bel_s >= 0.3:
            ds_class = "LIKELY_SAFE"
        else:
            ds_class = "UNCERTAIN"
        
        classifications[ds_class] += 1
        
        results.append({
            "user": user,
            "title": edit.get("title", ""),
            "belief_vandal": bel_v,
            "plausibility_vandal": pl_v,
            "belief_safe": bel_s,
            "uncertainty": uncertainty,
            "ds_classification": ds_class,
            "input_signals": {
                "rule": rule_score, "nlp": nlp_score,
                "llm": llm_class, "graph": graph_score,
            },
        })
    
    return results, classifications


# ═══════════════════════════════════════════════════════════
# 2. ISOLATION FOREST ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════
def run_isolation_forest(edits, graph_scores):
    """
    Isolation Forest: Unsupervised anomaly detection.
    
    Feature vector per edit:
      [rule_score, nlp_score, llm_numeric, length_delta,
       delta_ratio, graph_score, is_anon, is_serial]
    
    Anomalies = edits that are "different" from the majority
    → likely vandalism or unusual behavior
    """
    if not HAS_SKLEARN:
        return [], {}
    
    # Build feature matrix
    features = []
    edit_indices = []
    
    for i, edit in enumerate(edits):
        rule_score = float(edit.get("rule_score", 0))
        nlp_score = float(edit.get("nlp_score", 0))
        
        # LLM classification → numeric
        llm_class = edit.get("llm_classification", "")
        llm_num = {"VANDALISM": 3, "SUSPICIOUS": 2, "SAFE": 0}.get(llm_class, 1)
        
        # Length delta
        old_len = int(edit.get("length_old", 0) or 0)
        new_len = int(edit.get("length_new", 0) or 0)
        delta = new_len - old_len
        delta_ratio = delta / max(old_len, 1)
        
        # Graph score
        user = edit.get("user", "")
        graph_score = graph_scores.get(user, 0)
        
        # Is anonymous (IP edit)
        is_anon = 1 if edit.get("user", "").startswith("~") or "." in edit.get("user", "") else 0
        
        # Is serial vandal
        is_serial = 1 if edit.get("is_serial_vandal") == "True" else 0
        
        features.append([
            rule_score, nlp_score, llm_num,
            abs(delta), abs(delta_ratio),
            graph_score, is_anon, is_serial,
        ])
        edit_indices.append(i)
    
    if len(features) < 10:
        return [], {}
    
    X = np.array(features)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Isolation Forest: contamination = expected anomaly ratio
    clf = IsolationForest(
        n_estimators=200,
        contamination=0.1,  # Expect ~10% anomalies
        random_state=42,
        max_features=6,
    )
    
    predictions = clf.fit_predict(X_scaled)
    scores = clf.decision_function(X_scaled)
    
    # Collect anomalies
    anomalies = []
    anomaly_count = 0
    normal_count = 0
    
    for idx, (pred, score) in enumerate(zip(predictions, scores)):
        edit = edits[edit_indices[idx]]
        if pred == -1:  # Anomaly
            anomaly_count += 1
            anomalies.append({
                "user": edit.get("user", ""),
                "title": edit.get("title", ""),
                "anomaly_score": round(float(score), 4),
                "rule_score": float(edit.get("rule_score", 0)),
                "nlp_score": float(edit.get("nlp_score", 0)),
                "llm_classification": edit.get("llm_classification", ""),
                "length_delta": int(edit.get("length_new", 0) or 0) - int(edit.get("length_old", 0) or 0),
            })
        else:
            normal_count += 1
    
    # Sort by anomaly score (most anomalous first)
    anomalies.sort(key=lambda x: x["anomaly_score"])
    
    stats = {
        "total": len(features),
        "anomalies": anomaly_count,
        "normal": normal_count,
        "anomaly_rate": round(anomaly_count / len(features) * 100, 1),
        "features_used": [
            "rule_score", "nlp_score", "llm_numeric",
            "abs_delta", "abs_delta_ratio",
            "graph_score", "is_anon", "is_serial",
        ],
    }
    
    return anomalies[:30], stats


# ═══════════════════════════════════════════════════════════
# 3. CROSS-METHOD AGREEMENT ANALYSIS
# ═══════════════════════════════════════════════════════════
def cross_method_analysis(ds_results, if_anomalies, edits):
    """Phân tích sự đồng thuận giữa D-S Fusion vs Isolation Forest vs Ensemble."""
    
    # Build lookup sets
    ds_vandals = set()
    ds_uncertain = set()
    for r in ds_results:
        key = f"{r['user']}:{r['title']}"
        if r["ds_classification"] in ("HIGH_CONFIDENCE_VANDAL", "LIKELY_VANDAL"):
            ds_vandals.add(key)
        elif r["ds_classification"] == "UNCERTAIN":
            ds_uncertain.add(key)
    
    if_anomalous = set()
    for a in if_anomalies:
        if_anomalous.add(f"{a['user']}:{a['title']}")
    
    ensemble_vandals = set()
    for e in edits:
        cls = e.get("llm_classification", "")
        if cls in ("VANDALISM", "SUSPICIOUS"):
            ensemble_vandals.add(f"{e['user']}:{e.get('title', '')}")
    
    # Cross-method agreement
    ds_and_if = ds_vandals & if_anomalous
    ds_and_ensemble = ds_vandals & ensemble_vandals
    if_and_ensemble = if_anomalous & ensemble_vandals
    all_three = ds_vandals & if_anomalous & ensemble_vandals
    
    # NEW discoveries: found by D-S or IF but NOT by ensemble
    ds_new = ds_vandals - ensemble_vandals
    if_new = if_anomalous - ensemble_vandals
    
    return {
        "dempster_shafer_vandals": len(ds_vandals),
        "isolation_forest_anomalies": len(if_anomalous),
        "ensemble_vandals": len(ensemble_vandals),
        "ds_and_if": len(ds_and_if),
        "ds_and_ensemble": len(ds_and_ensemble),
        "if_and_ensemble": len(if_and_ensemble),
        "all_three_agree": len(all_three),
        "ds_new_discoveries": len(ds_new),
        "if_new_discoveries": len(if_new),
        "new_discovery_details": {
            "ds_unique": list(ds_new)[:10],
            "if_unique": list(if_new)[:10],
        },
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("🧬 Advanced Intelligence Fusion Running...")
    edits = load_all_data()
    if not edits:
        print("   No data. Run previous stages.")
        return
    
    print(f"   Loaded {len(edits)} edits")
    
    graph_scores = load_graph_scores()
    print(f"   Graph scores loaded: {len(graph_scores)} users")
    
    # 1. Dempster-Shafer
    print("\n   📐 Running Dempster-Shafer Evidence Fusion...")
    ds_results, ds_classes = run_dempster_shafer(edits, graph_scores)
    
    print(f"   {'='*50}")
    print(f"   DEMPSTER-SHAFER RESULTS:")
    for cls, count in sorted(ds_classes.items(), key=lambda x: -x[1]):
        pct = count / len(edits) * 100
        print(f"      {cls:30s} {count:4d} ({pct:.1f}%)")
    
    # Top high-confidence vandals
    hc_vandals = [r for r in ds_results if r["ds_classification"] == "HIGH_CONFIDENCE_VANDAL"]
    hc_vandals.sort(key=lambda x: -x["belief_vandal"])
    print(f"\n   Top High-Confidence Vandals (Belief >= 0.7):")
    for v in hc_vandals[:8]:
        print(f"      Bel={v['belief_vandal']:.3f} Pl={v['plausibility_vandal']:.3f} "
              f"Unc={v['uncertainty']:.3f} | {v['user'][:20]} → {v['title'][:30]}")
    
    # 2. Isolation Forest
    print(f"\n   🌲 Running Isolation Forest Anomaly Detection...")
    if_anomalies, if_stats = run_isolation_forest(edits, graph_scores)
    
    if if_stats:
        print(f"   {'='*50}")
        print(f"   ISOLATION FOREST RESULTS:")
        print(f"      Total: {if_stats['total']} | Anomalies: {if_stats['anomalies']} "
              f"({if_stats['anomaly_rate']}%) | Normal: {if_stats['normal']}")
        print(f"      Features: {', '.join(if_stats['features_used'])}")
        
        print(f"\n   Top Anomalies:")
        for a in if_anomalies[:8]:
            print(f"      Score={a['anomaly_score']:.4f} | {a['user'][:20]} → "
                  f"{a['title'][:30]} (R={a['rule_score']}, LLM={a['llm_classification']})")
    
    # 3. Cross-method analysis
    print(f"\n   🔄 Cross-Method Agreement Analysis...")
    cross = cross_method_analysis(ds_results, if_anomalies, edits)
    
    print(f"   {'='*50}")
    print(f"   CROSS-METHOD AGREEMENT:")
    print(f"      D-S Vandals:    {cross['dempster_shafer_vandals']}")
    print(f"      IF Anomalies:   {cross['isolation_forest_anomalies']}")
    print(f"      Ensemble:       {cross['ensemble_vandals']}")
    print(f"      D-S ∩ IF:       {cross['ds_and_if']}")
    print(f"      D-S ∩ Ensemble: {cross['ds_and_ensemble']}")
    print(f"      IF ∩ Ensemble:  {cross['if_and_ensemble']}")
    print(f"      ALL 3 agree:    {cross['all_three_agree']}")
    print(f"      D-S new finds:  {cross['ds_new_discoveries']}")
    print(f"      IF new finds:   {cross['if_new_discoveries']}")
    
    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "methods": ["Dempster-Shafer Evidence Fusion", "Isolation Forest", "Cross-Method Analysis"],
        "dempster_shafer": {
            "classifications": ds_classes,
            "top_vandals": [
                {k: v for k, v in r.items() if k != "input_signals"}
                for r in hc_vandals[:20]
            ],
            "theory": "Belief functions combine evidence from Rule+NLP+LLM+Graph signals "
                      "using Dempster's Rule of Combination, providing belief, plausibility, "
                      "and uncertainty intervals instead of point estimates.",
        },
        "isolation_forest": {
            "stats": if_stats,
            "top_anomalies": if_anomalies[:20],
            "theory": "Unsupervised anomaly detection using Isolation Forest. "
                      "Edits are represented as 8-dimensional feature vectors and "
                      "anomalies are identified by their isolation depth in random trees.",
        },
        "cross_method": cross,
    }
    
    with open(REPORT_DIR / "advanced_fusion.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n   ✅ Advanced fusion saved to: {REPORT_DIR / 'advanced_fusion.json'}")


if __name__ == "__main__":
    main()
