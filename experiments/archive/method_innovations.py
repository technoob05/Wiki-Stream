"""
🎓 METHOD INNOVATION SUITE
────────────────────────────────────────────────────────────
3 Novel Methods that produce SURPRISING results:

① KNOWLEDGE DISTILLATION (LLM → Fast Classifier)
   → Train a Random Forest on LLM labels
   → Result: LLM-quality decisions at microsecond speed
   → Novelty: Very few vandalism systems use Knowledge Distillation

② EDIT COMMENT FORENSICS (TF-IDF + Clustering)
   → Cluster users by edit summary patterns
   → Discover: vandal "signatures" in their comments
   → Novelty: Most systems ignore edit summaries entirely

③ BAYESIAN USER REPUTATION
   → Track user trustworthiness with Beta distribution
   → Prior: assume innocent (α=2, β=1)
   → Update: each edit updates the posterior
   → Novelty: Probabilistic trust with confidence intervals
────────────────────────────────────────────────────────────
"""
import csv
import json
import math
import re
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    import joblib
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def load_all_data():
    """Load all processed data."""
    all_edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir(): continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
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
# ① KNOWLEDGE DISTILLATION: LLM → Fast Classifier
# ═══════════════════════════════════════════════════════════
def extract_features(edit):
    """Extract feature vector from a single edit."""
    rule_score = float(edit.get("rule_score", 0))
    nlp_score = float(edit.get("nlp_score", 0))
    
    old_len = int(edit.get("length_old", 0) or 0)
    new_len = int(edit.get("length_new", 0) or 0)
    delta = new_len - old_len
    delta_ratio = delta / max(old_len, 1)
    
    comment = edit.get("comment", "")
    comment_len = len(comment)
    comment_has_section = 1 if "/*" in comment else 0
    comment_has_link = 1 if "[[" in comment else 0
    comment_has_revert = 1 if any(w in comment.lower() for w in ["revert", "undo", "rv"]) else 0
    
    # User features
    user = edit.get("user", "")
    is_anon = 1 if user.startswith("~") or re.match(r"\d+\.\d+\.\d+\.\d+", user) else 0
    is_bot = 1 if edit.get("bot") == "True" else 0
    is_minor = 1 if edit.get("minor") == "True" else 0
    
    # Content features
    is_blanking = 1 if new_len < 100 and old_len > 500 else 0
    is_massive = 1 if abs(delta) > 5000 else 0
    username_len = len(user)
    has_numbers_in_name = 1 if any(c.isdigit() for c in user) else 0
    
    return [
        rule_score,           # 0: heuristic score
        nlp_score,            # 1: NLP analysis score
        abs(delta),           # 2: absolute size change
        abs(delta_ratio),     # 3: relative size change
        comment_len,          # 4: comment length
        comment_has_section,  # 5: editing a section
        comment_has_link,     # 6: wiki-link in comment
        comment_has_revert,   # 7: is a revert action
        is_anon,              # 8: anonymous IP edit
        is_bot,               # 9: bot edit
        is_minor,             # 10: minor edit flag
        is_blanking,          # 11: content blanking
        is_massive,           # 12: massive change
        username_len,         # 13: username length
        has_numbers_in_name,  # 14: numbers in username
        old_len,              # 15: original article length
    ]


FEATURE_NAMES = [
    "rule_score", "nlp_score", "abs_delta", "abs_delta_ratio",
    "comment_len", "comment_has_section", "comment_has_link",
    "comment_has_revert", "is_anon", "is_bot", "is_minor",
    "is_blanking", "is_massive", "username_len", "has_numbers_in_name",
    "original_length",
]


def run_knowledge_distillation(edits):
    """
    Knowledge Distillation: LLM → Fast Classifier.
    
    Binary: FLAGGED (VANDALISM+SUSPICIOUS) vs SAFE
    Trains on LLM labels, predicts ALL edits including unlabeled ones.
    """
    if not HAS_SKLEARN:
        return {"error": "sklearn not installed"}
    
    from sklearn.svm import SVC
    from sklearn.ensemble import AdaBoostClassifier
    from sklearn.linear_model import LogisticRegression
    
    X_labeled, y_labeled = [], []
    X_all = []
    
    for e in edits:
        features = extract_features(e)
        X_all.append(features)
        
        llm_class = e.get("llm_classification", "")
        if llm_class in ("VANDALISM", "SUSPICIOUS"):
            X_labeled.append(features)
            y_labeled.append(1)  # FLAGGED
        elif llm_class == "SAFE":
            X_labeled.append(features)
            y_labeled.append(0)  # SAFE
    
    if len(X_labeled) < 20:
        return {"error": f"Not enough labeled data ({len(X_labeled)} edits)"}
    
    X = np.array(X_labeled)
    y = np.array(y_labeled)
    
    flagged = sum(y); safe = len(y) - flagged
    print(f"      Training: {len(X)} edits (FLAGGED={flagged}, SAFE={safe})")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Multiple model competition
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=6, random_state=42,
            class_weight="balanced", min_samples_leaf=3,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.1,
            random_state=42, subsample=0.8,
        ),
        "AdaBoost": AdaBoostClassifier(
            n_estimators=100, learning_rate=0.5,
            random_state=42,
        ),
        "LogisticRegression": LogisticRegression(
            class_weight="balanced", max_iter=1000, C=1.0,
            random_state=42,
        ),
    }
    
    best_model = None
    best_score = 0
    best_name = ""
    all_results = {}
    
    n_splits = min(5, min(Counter(y).values()))
    if n_splits < 2: n_splits = 2
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    for name, model in models.items():
        try:
            scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="f1")
            mean_f1 = scores.mean()
            all_results[name] = {
                "f1": round(mean_f1 * 100, 1),
                "std": round(scores.std() * 100, 1),
            }
            marker = "🏆" if mean_f1 > best_score else "  "
            print(f"      {marker} {name:22s} F1={mean_f1*100:.1f}% ± {scores.std()*100:.1f}%")
            
            if mean_f1 > best_score:
                best_score = mean_f1
                best_model = model
                best_name = name
        except Exception as ex:
            all_results[name] = {"error": str(ex)}
    
    # Train best on full labeled data
    best_model.fit(X_scaled, y)
    
    # Feature importance
    fi_list = []
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        fi = sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1])
        fi_list = [{"feature": n, "importance": round(float(v), 4)} for n, v in fi]
        print(f"\n      📊 Top Features ({best_name}):")
        for n, v in fi[:6]:
            bar = "█" * int(v * 40)
            print(f"         {n:24s} {v:.3f} {bar}")
    elif hasattr(best_model, "coef_"):
        coefs = np.abs(best_model.coef_[0])
        fi = sorted(zip(FEATURE_NAMES, coefs), key=lambda x: -x[1])
        fi_list = [{"feature": n, "importance": round(float(v), 4)} for n, v in fi]
    
    # Predict ALL
    X_all_scaled = scaler.transform(np.array(X_all))
    preds = best_model.predict(X_all_scaled)
    probs = best_model.predict_proba(X_all_scaled)
    
    new_flags = 0
    high_conf_flags = 0
    for i, e in enumerate(edits):
        llm = e.get("llm_classification", "")
        if not llm and preds[i] == 1:
            new_flags += 1
            if probs[i][1] >= 0.8:
                high_conf_flags += 1
    
    # On-training accuracy
    y_pred = best_model.predict(X_scaled)
    cm = confusion_matrix(y, y_pred)
    train_f1 = round(best_score * 100, 1)
    
    model_path = REPORT_DIR / "distilled_model.joblib"
    joblib.dump({"model": best_model, "scaler": scaler, "features": FEATURE_NAMES}, model_path)
    
    return {
        "best_model": best_name,
        "best_f1": train_f1,
        "all_models": all_results,
        "feature_importance": fi_list[:10],
        "predictions": {"FLAGGED": int(sum(preds)), "SAFE": int(len(preds) - sum(preds))},
        "new_discoveries": new_flags,
        "high_confidence_new": high_conf_flags,
        "confusion_matrix": cm.tolist(),
        "training_size": len(X_labeled),
        "total_predicted": len(X_all),
        "model_saved": str(model_path),
    }


# ═══════════════════════════════════════════════════════════
# ② EDIT COMMENT FORENSICS (TF-IDF + Clustering)
# ═══════════════════════════════════════════════════════════
def run_comment_forensics(edits):
    """
    Cluster users by their edit comment patterns.
    
    Insight: Vandals often use distinctive comment patterns:
      - Empty comments (hiding their actions)
      - Vague one-word comments ("test", "fix", "edit")
      - Copy-pasted automated comments
      - Suspiciously detailed comments to avoid detection
    """
    if not HAS_SKLEARN:
        return {"error": "sklearn not installed"}
    
    # Collect comments per user
    user_comments = defaultdict(list)
    user_flags = defaultdict(int)
    all_comments = []
    comment_edits = []
    
    for e in edits:
        user = e.get("user", "")
        comment = e.get("comment", "").strip()
        if not comment:
            comment = "[EMPTY]"
        
        user_comments[user].append(comment)
        all_comments.append(comment)
        comment_edits.append(e)
        
        if (float(e.get("rule_score", 0)) >= 3 or
            e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS")):
            user_flags[user] += 1
    
    if len(all_comments) < 10:
        return {"error": "Not enough comments"}
    
    # TF-IDF on all comments
    tfidf = TfidfVectorizer(
        max_features=200, stop_words="english",
        ngram_range=(1, 2), min_df=2, max_df=0.8,
    )
    
    try:
        X_tfidf = tfidf.fit_transform(all_comments)
    except ValueError:
        return {"error": "TF-IDF failed (not enough unique terms)"}
    
    # Cluster comments
    n_clusters = min(6, len(all_comments) // 5)
    if n_clusters < 2:
        n_clusters = 2
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_tfidf)
    
    # Analyze each cluster
    cluster_profiles = []
    for c_id in range(n_clusters):
        members = [i for i, c in enumerate(clusters) if c == c_id]
        if not members:
            continue
        
        cluster_comments = [all_comments[i] for i in members]
        cluster_users = set(comment_edits[i].get("user", "") for i in members)
        
        # Vandal ratio in this cluster
        vandal_count = sum(1 for i in members 
                          if float(comment_edits[i].get("rule_score", 0)) >= 3
                          or comment_edits[i].get("llm_classification") in ("VANDALISM", "SUSPICIOUS"))
        vandal_ratio = vandal_count / len(members) * 100
        
        # Top terms in cluster (from centroid)
        centroid = kmeans.cluster_centers_[c_id]
        feature_names = tfidf.get_feature_names_out()
        top_indices = centroid.argsort()[-5:][::-1]
        top_terms = [feature_names[i] for i in top_indices if centroid[i] > 0]
        
        # Average comment length
        avg_len = sum(len(c) for c in cluster_comments) / len(cluster_comments)
        
        # Empty comment ratio
        empty_ratio = sum(1 for c in cluster_comments if c == "[EMPTY]") / len(cluster_comments) * 100
        
        threat = ("🔴 VANDAL PATTERN" if vandal_ratio >= 50 else
                  "🟠 SUSPICIOUS" if vandal_ratio >= 25 else "🟢 NORMAL")
        
        cluster_profiles.append({
            "cluster_id": c_id,
            "size": len(members),
            "unique_users": len(cluster_users),
            "vandal_ratio": round(vandal_ratio, 1),
            "avg_comment_length": round(avg_len, 1),
            "empty_ratio": round(empty_ratio, 1),
            "top_terms": top_terms[:5],
            "sample_comments": cluster_comments[:3],
            "threat": threat,
        })
    
    cluster_profiles.sort(key=lambda x: -x["vandal_ratio"])
    
    # Suspicious comment patterns
    patterns = {
        "empty": sum(1 for c in all_comments if c == "[EMPTY]"),
        "very_short": sum(1 for c in all_comments if 0 < len(c) <= 5),
        "has_test": sum(1 for c in all_comments if "test" in c.lower()),
        "has_revert": sum(1 for c in all_comments if any(w in c.lower() for w in ["revert", "undo", "rv"])),
        "section_edit": sum(1 for c in all_comments if "/*" in c),
        "automated": sum(1 for c in all_comments if "[[WP:" in c or "AWB" in c),
    }
    
    return {
        "total_comments": len(all_comments),
        "clusters": cluster_profiles,
        "comment_patterns": patterns,
        "tfidf_features": len(tfidf.get_feature_names_out()),
    }


# ═══════════════════════════════════════════════════════════
# ③ BAYESIAN USER REPUTATION
# ═══════════════════════════════════════════════════════════
def run_bayesian_reputation(edits):
    """
    Beta-Binomial Bayesian reputation system.
    
    Each user starts with prior Alpha=2, Beta=1 (slight trust).
    Each edit updates the posterior:
      - Good edit (safe): α += 1
      - Bad edit (vandal): β += 2 (punish harder)
      - Suspicious: β += 0.5
    
    Reputation = α / (α + β) = mean of Beta distribution
    Confidence = 1 - 1/(α + β) = how sure we are
    
    Key insight: Users with many safe edits build trust.
    New users with vandalism get LOW reputation fast.
    """
    user_stats = defaultdict(lambda: {
        "alpha": 2.0,   # prior: slight trust
        "beta": 1.0,
        "edits": 0,
        "good": 0,
        "bad": 0,
        "suspicious": 0,
    })
    
    for e in edits:
        user = e.get("user", "")
        if not user:
            continue
        
        user_stats[user]["edits"] += 1
        
        rule_score = float(e.get("rule_score", 0))
        nlp_score = float(e.get("nlp_score", 0))
        llm_class = e.get("llm_classification", "")
        
        # Determine edit quality
        is_bad = (rule_score >= 3 or llm_class == "VANDALISM")
        is_suspicious = (rule_score >= 1 or nlp_score >= 0.5 or llm_class == "SUSPICIOUS")
        
        if is_bad:
            user_stats[user]["beta"] += 2.0   # Strong evidence of bad faith
            user_stats[user]["bad"] += 1
        elif is_suspicious:
            user_stats[user]["beta"] += 0.5   # Mild negative signal
            user_stats[user]["suspicious"] += 1
        else:
            user_stats[user]["alpha"] += 1.0  # Good faith edit
            user_stats[user]["good"] += 1
    
    # Compute reputation scores
    reputations = []
    for user, stats in user_stats.items():
        a, b = stats["alpha"], stats["beta"]
        
        reputation = a / (a + b)              # Mean of Beta distribution
        confidence = 1 - 1.0 / (a + b)        # How sure are we
        
        # 95% credible interval (Beta distribution quantiles)
        # Using normal approximation for speed
        std = math.sqrt(a * b / ((a + b)**2 * (a + b + 1)))
        lower = max(0, reputation - 1.96 * std)
        upper = min(1, reputation + 1.96 * std)
        
        threat = ("🔴 UNTRUSTED" if reputation < 0.3 else
                  "🟠 LOW TRUST" if reputation < 0.5 else
                  "🟡 NEUTRAL" if reputation < 0.7 else
                  "🟢 TRUSTED")
        
        reputations.append({
            "user": user,
            "reputation": round(reputation * 100, 1),  # 0-100 scale
            "confidence": round(confidence * 100, 1),
            "credible_interval": [round(lower * 100, 1), round(upper * 100, 1)],
            "edits": stats["edits"],
            "good": stats["good"],
            "bad": stats["bad"],
            "suspicious": stats["suspicious"],
            "threat": threat,
        })
    
    reputations.sort(key=lambda x: x["reputation"])
    
    # Distribution
    dist = Counter(r["threat"] for r in reputations)
    
    return {
        "total_users": len(reputations),
        "distribution": dict(dist),
        "lowest_reputation": reputations[:15],
        "highest_reputation": reputations[-5:],
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("🎓 Method Innovation Suite Running...")
    edits = load_all_data()
    if not edits:
        print("   ⚠️ No data.")
        return
    
    print(f"   📂 Loaded {len(edits)} edits\n")
    results = {"generated_at": datetime.now().isoformat(), "total_edits": len(edits)}
    
    # ① Knowledge Distillation
    print("   🧠 [1/3] Knowledge Distillation (LLM → Fast Classifier)...")
    kd = run_knowledge_distillation(edits)
    results["knowledge_distillation"] = kd
    if "error" not in kd:
        print(f"\n      🏆 BEST MODEL: {kd['best_model']} (F1={kd['best_f1']}%)")
        print(f"      📊 Predictions: {kd['predictions']}")
        print(f"      🆕 New discoveries (unlabeled → flagged): {kd['new_discoveries']}")
    else:
        print(f"      ❌ {kd['error']}")
    
    # ② Comment Forensics
    print(f"\n   💬 [2/3] Edit Comment Forensics (TF-IDF Clustering)...")
    cf = run_comment_forensics(edits)
    results["comment_forensics"] = cf
    if "error" not in cf:
        print(f"      Clusters: {len(cf['clusters'])}")
        for c in cf["clusters"][:3]:
            print(f"         Cluster {c['cluster_id']}: {c['size']} edits, "
                  f"vandal={c['vandal_ratio']}%, {c['threat']}")
            print(f"            Terms: {', '.join(c['top_terms'][:3])}")
    else:
        print(f"      ❌ {cf['error']}")
    
    # ③ Bayesian Reputation
    print(f"\n   📊 [3/3] Bayesian User Reputation...")
    br = run_bayesian_reputation(edits)
    results["bayesian_reputation"] = br
    print(f"      Users: {br['total_users']}")
    print(f"      Distribution: {br['distribution']}")
    print(f"\n      🔴 Lowest Reputation Users:")
    for u in br["lowest_reputation"][:5]:
        print(f"         {u['user']:20s} Rep={u['reputation']:5.1f}% "
              f"[{u['credible_interval'][0]:.0f}-{u['credible_interval'][1]:.0f}%] "
              f"({u['good']}✅ {u['bad']}❌ {u['suspicious']}⚠️)")
    
    # Save
    report_path = REPORT_DIR / "method_innovations.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n   ✅ Saved: {report_path}")


if __name__ == "__main__":
    main()
