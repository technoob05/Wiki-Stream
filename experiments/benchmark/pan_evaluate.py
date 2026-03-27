"""
PAN-WVC-10 Evaluation — Compare ITEFB results against gold standard
------------------------------------------------------------
Computes ROC-AUC, PR-AUC, F1, Precision, Recall
and compares with PAN 2010/2011 leaderboard baselines.

Usage:
  python pan_evaluate.py
------------------------------------------------------------
"""

import json
import csv
import numpy as np
from pathlib import Path
from collections import Counter

BENCHMARK_DIR = Path(__file__).parent
GOLD_FILE = BENCHMARK_DIR / "pan_gold.json"
RESULTS_DIR = BENCHMARK_DIR / "pan_data" / "en" / "processed"
REPORT_DIR = BENCHMARK_DIR / "pan_results"


def load_gold():
    """Load gold annotations."""
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_verdicts():
    """Load ITEFB verdicts from attributed CSVs and intelligence_master."""
    # Try intelligence_master first (has final verdict scores)
    master_file = BENCHMARK_DIR / "pan_reports" / "intelligence_master.json"
    if master_file.exists():
        with open(master_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("all_verdicts", [])

    # Fallback: read from attributed CSVs
    verdicts = []
    for f in sorted(RESULTS_DIR.glob("*_attributed.csv")):
        with open(f, "r", encoding="utf-8") as csvf:
            for row in csv.DictReader(csvf):
                verdicts.append(row)
    return verdicts


def evaluate():
    """Run full evaluation against PAN gold standard."""
    from sklearn.metrics import (
        roc_auc_score, average_precision_score,
        precision_recall_curve, roc_curve,
        f1_score, precision_score, recall_score,
        classification_report
    )

    gold = load_gold()
    verdicts = load_verdicts()

    if not verdicts:
        print("ERROR: No verdicts found. Run the pipeline on PAN data first.")
        return

    print(f"  Gold labels: {len(gold)}")
    print(f"  Verdicts:    {len(verdicts)}")

    # Match verdicts to gold labels
    y_true = []
    y_scores = []
    y_pred = []
    matched = 0

    for v in verdicts:
        # Try to find pan_editid
        eid = v.get("pan_editid", "")
        if not eid:
            # Try matching by revision
            rev = v.get("revision_new", "") or v.get("wiki_url", "").split("diff=")[-1]
            # Skip if no match possible
            continue

        label = gold.get(eid)
        if label is None:
            continue

        matched += 1
        y_true.append(1 if label == "vandalism" else 0)

        # Score: use verdict score normalized to [0, 1]
        score = float(v.get("score", 0)) / 100.0
        y_scores.append(score)

        # Binary prediction based on action
        action = v.get("action", "SAFE")
        y_pred.append(1 if action in ("BLOCK", "FLAG") else 0)

    print(f"  Matched:     {matched}")

    if matched < 10:
        print("ERROR: Too few matches. Check pan_editid mapping.")
        return

    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    y_pred = np.array(y_pred)

    # --- Metrics ---
    roc_auc = roc_auc_score(y_true, y_scores)
    pr_auc = average_precision_score(y_true, y_scores)
    f1 = f1_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)

    # Optimal F1 threshold
    precisions, recalls, thresholds_pr = precision_recall_curve(y_true, y_scores)
    f1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_f1_idx = np.argmax(f1_scores)
    best_f1 = f1_scores[best_f1_idx]
    best_threshold = thresholds_pr[best_f1_idx] if best_f1_idx < len(thresholds_pr) else 0.5

    # At optimal threshold
    y_pred_optimal = (y_scores >= best_threshold).astype(int)
    p_opt = precision_score(y_true, y_pred_optimal, zero_division=0)
    r_opt = recall_score(y_true, y_pred_optimal, zero_division=0)

    # Distribution
    dist = Counter()
    for v in verdicts:
        eid = v.get("pan_editid", "")
        if eid in gold:
            dist[v.get("action", "SAFE")] += 1

    # --- Print Results ---
    print("\n" + "=" * 70)
    print("  ITEFB v3.0 — PAN-WVC-10 Benchmark Results")
    print("=" * 70)

    print(f"\n  ROC-AUC:           {roc_auc:.4f}")
    print(f"  PR-AUC:            {pr_auc:.4f}")
    print(f"  F1 (BL+FL):        {f1:.4f}")
    print(f"  Precision (BL+FL): {precision:.4f}")
    print(f"  Recall (BL+FL):    {recall:.4f}")

    print(f"\n  Optimal F1:        {best_f1:.4f} (threshold={best_threshold:.3f})")
    print(f"  P@optimal:         {p_opt:.4f}")
    print(f"  R@optimal:         {r_opt:.4f}")

    print(f"\n  Distribution: {dict(dist)}")
    print(f"  Vandalism in gold: {sum(y_true)} / {len(y_true)} ({sum(y_true)/len(y_true)*100:.1f}%)")

    # --- Comparison Table ---
    print("\n" + "-" * 70)
    print("  COMPARISON WITH BASELINES")
    print("-" * 70)
    print(f"  {'System':<35} {'ROC-AUC':>8} {'PR-AUC':>8}")
    print(f"  {'-'*35} {'-'*8} {'-'*8}")
    print(f"  {'PAN 2010 #1 (Mola-Velasco, RF)':<35} {'0.9224':>8} {'—':>8}")
    print(f"  {'PAN 2010 #2 (WikiTrust)':<35} {'0.9035':>8} {'—':>8}")
    print(f"  {'PAN 2011 #1 (West & Lee, STiki)':<35} {'—':>8} {'0.8223':>8}")
    print(f"  {'ORES (Wikimedia, GBT, supervised)':<35} {'~0.96':>8} {'—':>8}")
    print(f"  {'ITEFB v3.0 (Ours, training-free)':<35} {roc_auc:>8.4f} {pr_auc:>8.4f}")

    # --- Save results ---
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "dataset": "PAN-WVC-10",
        "matched_edits": matched,
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "f1_block_flag": round(f1, 4),
            "precision_block_flag": round(precision, 4),
            "recall_block_flag": round(recall, 4),
            "optimal_f1": round(best_f1, 4),
            "optimal_threshold": round(best_threshold, 3),
            "precision_at_optimal": round(p_opt, 4),
            "recall_at_optimal": round(r_opt, 4),
        },
        "distribution": dict(dist),
        "baselines": {
            "PAN_2010_winner": {"roc_auc": 0.9224, "method": "Random Forest (supervised)"},
            "PAN_2010_wikitrust": {"roc_auc": 0.9035, "method": "Reputation-based"},
            "PAN_2011_winner": {"pr_auc": 0.8223, "method": "STiki + WikiTrust + NLP"},
            "ORES": {"roc_auc": 0.96, "method": "Gradient Boosted Trees (supervised)"},
        },
    }

    results_file = REPORT_DIR / "pan_benchmark_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"\n  Results saved to {results_file}")


if __name__ == "__main__":
    print("PAN-WVC-10 Benchmark Evaluation")
    evaluate()
