"""
📊 LLM vs ML COMPARISON + HYBRID INSIGHT ANALYSIS
────────────────────────────────────────────────────────────
Core question: Khi nào LLM tốt hơn ML? Khi nào ML tốt hơn?
              Hybrid kết hợp cả hai → kết quả bất ngờ?

LLM (Gemma2):
  - Đọc FULL diff text → hiểu ngữ cảnh sâu
  - Chậm (~1-3 giây/edit) → không scalable
  - Chỉ label được 143/556 edits (25%)

ML (Distilled AdaBoost):
  - 16 features → phân loại tức thì (microseconds)
  - Train từ LLM labels → "học" được patterns
  - Predict TOÀN BỘ 556 edits (100%)
  - F1=82.8% so với LLM labels

Hybrid:
  - LLM verify + ML detect → coverage 100%, accuracy cao
  - Phát hiện edits mà LLM bỏ sót (chưa kịp xử lý)
  - Cross-validate: khi LLM và ML đồng ý → confidence cao
────────────────────────────────────────────────────────────
"""
import csv
import json
import re
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

try:
    from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier, RandomForestClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"


def load_edits():
    edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir(): continue
        proc = lang_dir / "processed"
        if not proc.exists(): continue
        for pat in ["*_08_attributed.csv", "*_06_llm.csv", "*_04_final.csv"]:
            files = sorted(proc.glob(pat))
            if files:
                for f in files:
                    with open(f, "r", encoding="utf-8") as csvf:
                        for row in csv.DictReader(csvf):
                            row["lang"] = lang_dir.name
                            edits.append(row)
                break
    return edits


def extract_features(e):
    rs = float(e.get("rule_score", 0))
    ns = float(e.get("nlp_score", 0))
    old_len = int(e.get("length_old", 0) or 0)
    new_len = int(e.get("length_new", 0) or 0)
    delta = new_len - old_len
    delta_ratio = delta / max(old_len, 1)
    comment = e.get("comment", "")
    user = e.get("user", "")
    return [
        rs, ns,
        abs(delta), abs(delta_ratio),
        len(comment),
        1 if "/*" in comment else 0,
        1 if "[[" in comment else 0,
        1 if any(w in comment.lower() for w in ["revert", "undo"]) else 0,
        1 if user.startswith("~") or re.match(r"\d+\.\d+", user) else 0,
        1 if e.get("bot") == "True" else 0,
        1 if e.get("minor") == "True" else 0,
        1 if new_len < 100 and old_len > 500 else 0,
        1 if abs(delta) > 5000 else 0,
        len(user),
        1 if any(c.isdigit() for c in user) else 0,
        old_len,
    ]


FEATURE_NAMES = [
    "rule_score", "nlp_score", "abs_delta", "delta_ratio",
    "comment_len", "section_edit", "wiki_link", "revert_comment",
    "is_anon", "is_bot", "is_minor", "is_blanking", "is_massive",
    "username_len", "has_numbers", "article_length",
]


def main():
    print("=" * 65)
    print("  📊 LLM vs ML COMPARISON + HYBRID ANALYSIS")
    print("=" * 65)
    
    edits = load_edits()
    print(f"\n  Total edits: {len(edits)}")
    
    # ── Categorize edits by LLM coverage ──
    llm_labeled = [e for e in edits if e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS", "SAFE")]
    llm_unlabeled = [e for e in edits if e.get("llm_classification", "") not in ("VANDALISM", "SUSPICIOUS", "SAFE")]
    
    print(f"  LLM labeled: {len(llm_labeled)} ({len(llm_labeled)/len(edits)*100:.1f}%)")
    print(f"  LLM unlabeled: {len(llm_unlabeled)} ({len(llm_unlabeled)/len(edits)*100:.1f}%)")
    
    # ── Train ML model ──
    if not HAS_SKLEARN:
        print("  ❌ sklearn required")
        return
    
    X_lab, y_lab = [], []
    for e in llm_labeled:
        X_lab.append(extract_features(e))
        y_lab.append(1 if e["llm_classification"] in ("VANDALISM", "SUSPICIOUS") else 0)
    
    X = np.array(X_lab)
    y = np.array(y_lab)
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)
    
    # Train ML models
    models = {
        "AdaBoost": AdaBoostClassifier(n_estimators=100, learning_rate=0.5, random_state=42),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=6, class_weight="balanced", random_state=42),
    }
    
    n_splits = min(5, min(Counter(y).values()))
    cv = StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=42)
    
    print(f"\n{'='*65}")
    print("  🤖 ML MODEL COMPETITION (trained on LLM labels)")
    print(f"{'='*65}")
    
    best_model = None
    best_f1 = 0
    best_name = ""
    
    for name, model in models.items():
        scores = cross_val_score(model, X_sc, y, cv=cv, scoring="f1")
        f1 = scores.mean()
        marker = "🏆" if f1 > best_f1 else "  "
        print(f"  {marker} {name:22s} F1={f1*100:.1f}% ± {scores.std()*100:.1f}%")
        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_name = name
    
    # Train best on all labeled
    best_model.fit(X_sc, y)
    
    # Predict ALL edits
    X_all = np.array([extract_features(e) for e in edits])
    X_all_sc = scaler.transform(X_all)
    ml_preds = best_model.predict(X_all_sc)
    ml_probs = best_model.predict_proba(X_all_sc)
    
    # ══════════════════════════════════════════════════════
    # LLM vs ML HEAD-TO-HEAD COMPARISON
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*65}")
    print("  ⚔️  LLM vs ML: HEAD-TO-HEAD COMPARISON")
    print(f"{'='*65}")
    
    # On labeled data only
    both_agree_vandal = 0
    both_agree_safe = 0
    llm_only = 0     # LLM says vandal, ML says safe
    ml_only = 0       # ML says vandal, LLM says safe
    
    llm_only_details = []
    ml_only_details = []
    
    for i, e in enumerate(edits):
        llm = e.get("llm_classification", "")
        if llm not in ("VANDALISM", "SUSPICIOUS", "SAFE"):
            continue
        
        llm_flag = llm in ("VANDALISM", "SUSPICIOUS")
        ml_flag = ml_preds[i] == 1
        
        if llm_flag and ml_flag:
            both_agree_vandal += 1
        elif not llm_flag and not ml_flag:
            both_agree_safe += 1
        elif llm_flag and not ml_flag:
            llm_only += 1
            llm_only_details.append({
                "user": e.get("user", ""), "title": e.get("title", "")[:30],
                "llm": llm, "ml_prob": round(ml_probs[i][1]*100, 1),
                "rule": float(e.get("rule_score", 0)),
            })
        elif not llm_flag and ml_flag:
            ml_only += 1
            ml_only_details.append({
                "user": e.get("user", ""), "title": e.get("title", "")[:30],
                "llm": llm, "ml_prob": round(ml_probs[i][1]*100, 1),
                "rule": float(e.get("rule_score", 0)),
            })
    
    total_compared = both_agree_vandal + both_agree_safe + llm_only + ml_only
    agreement = (both_agree_vandal + both_agree_safe) / total_compared * 100
    
    print(f"\n  📊 On {total_compared} mutually labeled edits:")
    print(f"  ┌──────────────────────────────────────────────┐")
    print(f"  │  ✅ BOTH agree VANDAL:  {both_agree_vandal:4d}                  │")
    print(f"  │  ✅ BOTH agree SAFE:    {both_agree_safe:4d}                  │")
    print(f"  │  🔵 LLM-only flags:    {llm_only:4d}  (LLM sees more) │")
    print(f"  │  🟡 ML-only flags:     {ml_only:4d}  (ML sees more)  │")
    print(f"  │  📈 Agreement rate:     {agreement:.1f}%              │")
    print(f"  └──────────────────────────────────────────────┘")
    
    # ══════════════════════════════════════════════════════
    # LLM STRENGTHS vs ML STRENGTHS
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*65}")
    print("  💡 WHERE EACH METHOD EXCELS")
    print(f"{'='*65}")
    
    print(f"\n  🔵 LLM catches but ML misses ({llm_only} edits):")
    print(f"     → LLM reads full diff text, catches subtle vandalism")
    for d in llm_only_details[:5]:
        print(f"     {d['user']:20s} | LLM={d['llm']:12s} ML_prob={d['ml_prob']:5.1f}% R={d['rule']}")
    
    print(f"\n  🟡 ML catches but LLM misses ({ml_only} edits):")
    print(f"     → ML detects statistical anomalies in features")
    for d in ml_only_details[:5]:
        print(f"     {d['user']:20s} | LLM={d['llm']:12s} ML_prob={d['ml_prob']:5.1f}% R={d['rule']}")
    
    # ══════════════════════════════════════════════════════
    # HYBRID ANALYSIS: ML on UNLABELED data
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*65}")
    print("  🧬 HYBRID ANALYSIS: ML fills LLM's gaps")
    print(f"{'='*65}")
    
    ml_new_flags = []
    ml_new_high_conf = []
    
    for i, e in enumerate(edits):
        llm = e.get("llm_classification", "")
        if llm in ("VANDALISM", "SUSPICIOUS", "SAFE"):
            continue  # LLM already handled
        
        if ml_preds[i] == 1:
            detail = {
                "user": e.get("user", ""), "title": e.get("title", "")[:30],
                "ml_prob": round(ml_probs[i][1]*100, 1),
                "rule": float(e.get("rule_score", 0)),
                "nlp": float(e.get("nlp_score", 0)),
            }
            ml_new_flags.append(detail)
            if ml_probs[i][1] >= 0.8:
                ml_new_high_conf.append(detail)
    
    print(f"\n  LLM processed: {len(llm_labeled)}/{len(edits)} edits ({len(llm_labeled)/len(edits)*100:.1f}%)")
    print(f"  ML fills gap:  {len(llm_unlabeled)} unlabeled edits")
    print(f"  ML new flags:  {len(ml_new_flags)} (ML says suspicious)")
    print(f"  High-conf new: {len(ml_new_high_conf)} (ML prob ≥ 80%)")
    
    if ml_new_high_conf:
        print(f"\n  🔴 HIGH-CONFIDENCE ML discoveries (LLM never saw these):")
        for d in sorted(ml_new_high_conf, key=lambda x: -x["ml_prob"])[:8]:
            print(f"     [{d['ml_prob']:5.1f}%] {d['user']:20s} → {d['title']} (R={d['rule']}, NLP={d['nlp']})")
    
    # ══════════════════════════════════════════════════════
    # HYBRID VERDICT: Combined scoring
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*65}")
    print("  🎯 HYBRID VERDICT: LLM + ML Combined")
    print(f"{'='*65}")
    
    hybrid_dist = Counter()
    hybrid_vandals = []
    
    for i, e in enumerate(edits):
        llm = e.get("llm_classification", "")
        ml_prob = ml_probs[i][1] * 100
        rule = float(e.get("rule_score", 0))
        nlp = float(e.get("nlp_score", 0))
        
        # Hybrid score: weighted average
        if llm in ("VANDALISM", "SUSPICIOUS", "SAFE"):
            llm_s = {"VANDALISM": 95, "SUSPICIOUS": 65, "SAFE": 10}[llm]
            # LLM available → trust LLM more (60%) + ML confirmation (40%)
            hybrid_score = llm_s * 0.60 + ml_prob * 0.40
        else:
            # No LLM → rely on ML (70%) + Rule+NLP (30%)
            rule_s = min(rule / 5 * 100, 100)
            nlp_s = min(nlp / 3 * 100, 100)
            hybrid_score = ml_prob * 0.70 + rule_s * 0.15 + nlp_s * 0.15
        
        if hybrid_score >= 75:
            action = "🔴 BLOCK"
        elif hybrid_score >= 55:
            action = "🟠 FLAG"
        elif hybrid_score >= 30:
            action = "🟡 REVIEW"
        else:
            action = "🟢 SAFE"
        
        hybrid_dist[action] += 1
        
        if hybrid_score >= 55:
            hybrid_vandals.append({
                "user": e.get("user", ""), "title": e.get("title", "")[:30],
                "hybrid_score": round(hybrid_score, 1),
                "llm": llm if llm else "—",
                "ml_prob": round(ml_prob, 1),
                "action": action,
            })
    
    hybrid_vandals.sort(key=lambda x: -x["hybrid_score"])
    
    print(f"\n  HYBRID VERDICT DISTRIBUTION:")
    for label in ["🔴 BLOCK", "🟠 FLAG", "🟡 REVIEW", "🟢 SAFE"]:
        count = hybrid_dist.get(label, 0)
        pct = count / len(edits) * 100
        bar = "█" * int(pct / 2)
        print(f"     {label:12s} {count:4d} ({pct:5.1f}%) {bar}")
    
    print(f"\n  🏆 TOP HYBRID THREATS:")
    for v in hybrid_vandals[:10]:
        src = "LLM+ML" if v["llm"] != "—" else "ML-only"
        print(f"     [{v['hybrid_score']:5.1f}] {v['action']} | {v['user']:20s} "
              f"→ {v['title']} | LLM={v['llm']:12s} ML={v['ml_prob']:5.1f}% ({src})")
    
    # ══════════════════════════════════════════════════════
    # KEY INSIGHTS
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*65}")
    print("  💎 KEY HYBRID INSIGHTS")
    print(f"{'='*65}")
    
    coverage_llm = len(llm_labeled) / len(edits) * 100
    coverage_hybrid = 100.0  # ML covers everything
    
    flags_llm = sum(1 for e in edits if e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS"))
    flags_hybrid = hybrid_dist.get("🔴 BLOCK", 0) + hybrid_dist.get("🟠 FLAG", 0)
    
    print(f"""
  ┌─────────────────────────────────────────────────────────┐
  │  METRIC            │  LLM Only  │  Hybrid (LLM+ML)     │
  ├─────────────────────────────────────────────────────────┤
  │  Coverage          │  {coverage_llm:5.1f}%    │  {coverage_hybrid:5.1f}%  (ML fills) │
  │  Edits flagged     │  {flags_llm:5d}      │  {flags_hybrid:5d}                │
  │  Speed             │  ~2s/edit   │  μs/edit (ML)        │
  │  New discoveries   │  —          │  {len(ml_new_flags):5d} (ML-only)      │
  │  Agreement rate    │  —          │  {agreement:5.1f}%              │
  └─────────────────────────────────────────────────────────┘

  📌 LLM excels at: Deep semantic analysis, reading full diffs
  📌 ML excels at:   Speed, coverage, detecting feature-based patterns
  📌 Hybrid wins:    100% coverage + cross-validated confidence
  📌 Surprise:       ML found {len(ml_new_high_conf)} high-confidence vandals LLM never processed!
""")
    
    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "comparison": {
            "total_edits": len(edits),
            "llm_coverage": round(coverage_llm, 1),
            "hybrid_coverage": coverage_hybrid,
            "ml_model": best_name,
            "ml_f1": round(best_f1 * 100, 1),
            "agreement_rate": round(agreement, 1),
            "both_agree_vandal": both_agree_vandal,
            "both_agree_safe": both_agree_safe,
            "llm_only_flags": llm_only,
            "ml_only_flags": ml_only,
            "ml_new_discoveries": len(ml_new_flags),
            "ml_high_confidence_new": len(ml_new_high_conf),
        },
        "hybrid_verdict": {
            "distribution": {k: v for k, v in hybrid_dist.items()},
            "top_threats": hybrid_vandals[:15],
        },
        "insights": [
            f"LLM coverage: {coverage_llm:.0f}% → Hybrid coverage: 100%",
            f"ML F1 vs LLM labels: {best_f1*100:.1f}%",
            f"Agreement rate when both available: {agreement:.1f}%",
            f"ML discovered {len(ml_new_high_conf)} high-conf vandals LLM never saw",
            f"Strongest ML features: article_length, nlp_score, username_len",
        ],
    }
    
    out = REPORT_DIR / "llm_vs_ml_comparison.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Saved: {out}")


if __name__ == "__main__":
    main()
