"""
WVC-07 Benchmark Runner
------------------------------------------------------------
Quick benchmark on 940 edits. Steps:
  1. Parse XML → CSV
  2. Stage 02: Feature extraction (diff fetch + NLP + InfoTheory)
  3. Stage 03: Skip (use WVC-07 gold)
  4. Stage 04: LLM classification (or fallback)
  5. Stage 05: Attribution
  6. Stage 06: Fusion
  7. Evaluate vs gold

Usage:
  python run_wvc07.py                 # Full 940 edits
  python run_wvc07.py --limit 100     # Quick test 100 edits
  python run_wvc07.py --skip-collect  # Skip API calls (if features already fetched)
  python run_wvc07.py --eval-only     # Only evaluate
------------------------------------------------------------
"""

import os
import sys
import csv
import json
import shutil
from pathlib import Path
from importlib import import_module

BENCHMARK_DIR = Path(__file__).parent
EXPERIMENTS_DIR = BENCHMARK_DIR.parent
WVC07_DATA = BENCHMARK_DIR / "wvc07_data"
WVC07_REPORTS = BENCHMARK_DIR / "wvc07_reports"
GOLD_FILE = BENCHMARK_DIR / "wvc07_gold.json"

sys.path.insert(0, str(EXPERIMENTS_DIR))
sys.path.insert(0, str(BENCHMARK_DIR))


def step_adapt(limit: int = 0):
    print("\n[1/6] Parsing WVC-07 XML...")
    from wvc07_adapter import convert
    convert(limit)


def step_features(skip: bool = False):
    print("\n[2/6] Stage 02: Feature Extraction...")
    if skip:
        print("  Skipped (--skip-collect)")
        return

    proc_dir = WVC07_DATA / "en" / "processed"
    if proc_dir.exists() and list(proc_dir.glob("*_features.csv")):
        print("  Already done, skipping. Use --force to redo.")
        return

    stage02 = import_module("02_feature_extraction")
    orig = stage02.DATA_DIR
    stage02.DATA_DIR = WVC07_DATA

    rep = {}
    rep_file = EXPERIMENTS_DIR / "reputation.json"
    if rep_file.exists():
        with open(rep_file, "r") as f:
            rep = json.load(f)

    ref_dist = stage02.load_reference_distribution()
    stage02.process_lang("en", rep, ref_dist)
    stage02.DATA_DIR = orig


def step_truth():
    print("\n[3/6] Stage 03: Skip (WVC-07 gold used instead)")
    proc_dir = WVC07_DATA / "en" / "processed"
    if not proc_dir.exists():
        return
    for f in proc_dir.glob("*_features.csv"):
        truth = proc_dir / f.name.replace("_features.csv", "_truth.csv")
        if not truth.exists():
            shutil.copy(f, truth)
            print(f"  Created {truth.name}")


def step_llm():
    print("\n[4/6] Stage 04: LLM Classification...")
    proc_dir = WVC07_DATA / "en" / "processed"

    # Check if already done
    if list(proc_dir.glob("*_classified.csv")):
        print("  Already done.")
        return

    try:
        stage04 = import_module("04_llm_classification")
        orig = stage04.DATA_DIR
        stage04.DATA_DIR = WVC07_DATA
        stage04.process_lang("en")
        stage04.DATA_DIR = orig
    except Exception as e:
        print(f"  LLM failed ({e}), creating fallback...")
        for f in proc_dir.glob("*_truth.csv"):
            cls_path = proc_dir / f.name.replace("_truth.csv", "_classified.csv")
            if cls_path.exists():
                continue
            with open(f, "r", encoding="utf-8") as rf:
                reader = csv.DictReader(rf)
                rows = list(reader)
                fnames = list(reader.fieldnames)
            for col in ["llm_class", "llm_conf", "llm_reason", "mass_llm"]:
                if col not in fnames:
                    fnames.append(col)
            for row in rows:
                row["llm_class"] = ""
                row["llm_conf"] = "0"
                row["llm_reason"] = ""
                row["mass_llm"] = json.dumps({"v": 0.0, "s": 0.0, "t": 1.0})
            with open(cls_path, "w", newline="", encoding="utf-8") as wf:
                writer = csv.DictWriter(wf, fieldnames=fnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  Fallback: {cls_path.name}")


def step_attribution():
    print("\n[5/6] Stage 05: Attribution...")
    proc_dir = WVC07_DATA / "en" / "processed"

    if list(proc_dir.glob("*_attributed.csv")):
        print("  Already done.")
        return

    try:
        stage05 = import_module("05_user_attribution")
        orig = stage05.DATA_DIR
        stage05.DATA_DIR = WVC07_DATA
        db = stage05.update_db()
        cov_inv = stage05.estimate_covariance(db)
        threshold = stage05.compute_adaptive_threshold(db, cov_inv)
        stage05.process_lang("en", db, cov_inv, threshold)
        stage05.DATA_DIR = orig
    except Exception as e:
        print(f"  Attribution failed ({e}), creating fallback...")
        for f in proc_dir.glob("*_classified.csv"):
            attr_path = proc_dir / f.name.replace("_classified.csv", "_attributed.csv")
            if attr_path.exists():
                continue
            with open(f, "r", encoding="utf-8") as rf:
                reader = csv.DictReader(rf)
                rows = list(reader)
                fnames = list(reader.fieldnames)
            for col in ["attribution_match", "attribution_sim", "is_serial", "mass_attribution"]:
                if col not in fnames:
                    fnames.append(col)
            for row in rows:
                row["attribution_match"] = ""
                row["attribution_sim"] = "0"
                row["is_serial"] = "False"
                row["mass_attribution"] = json.dumps({"v": 0.0, "s": 0.05, "t": 0.95})
            with open(attr_path, "w", newline="", encoding="utf-8") as wf:
                writer = csv.DictWriter(wf, fieldnames=fnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  Fallback: {attr_path.name}")


def step_fusion():
    print("\n[6/6] Stage 06: Intelligence Fusion...")
    WVC07_REPORTS.mkdir(parents=True, exist_ok=True)

    stage06 = import_module("06_intelligence_fusion")
    orig_data = stage06.DATA_DIR
    orig_report = stage06.REPORT_DIR
    stage06.DATA_DIR = WVC07_DATA
    stage06.REPORT_DIR = WVC07_REPORTS
    stage06.main()
    stage06.DATA_DIR = orig_data
    stage06.REPORT_DIR = orig_report


def step_evaluate():
    print("\n" + "=" * 70)
    print("  EVALUATION — WVC-07 Benchmark")
    print("=" * 70)

    # Load gold
    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold = json.load(f)

    # Load verdicts
    master_file = WVC07_REPORTS / "intelligence_master.json"
    if not master_file.exists():
        print("  ERROR: No results found. Run pipeline first.")
        return

    with open(master_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    verdicts = data.get("all_verdicts", [])

    # Match
    y_true = []
    y_scores = []
    y_pred = []

    for v in verdicts:
        eid = v.get("pan_editid", "")
        if not eid:
            # Try to construct from wiki_url
            url = v.get("wiki_url", "")
            if "diff=" in url:
                rev = url.split("diff=")[-1]
                eid = f"wvc07_{rev}"

        label = gold.get(eid)
        if label is None:
            continue

        y_true.append(1 if label == "vandalism" else 0)
        y_scores.append(float(v.get("score", 0)) / 100.0)
        action = v.get("action", "SAFE")
        y_pred.append(1 if action in ("BLOCK", "FLAG") else 0)

    print(f"\n  Matched: {len(y_true)} / {len(verdicts)} verdicts")
    print(f"  Vandalism in gold: {sum(y_true)} / {len(y_true)} ({sum(y_true)/max(len(y_true),1)*100:.1f}%)")

    if len(y_true) < 10:
        print("  ERROR: Too few matches for evaluation.")
        return

    import numpy as np
    from sklearn.metrics import (
        roc_auc_score, average_precision_score,
        precision_recall_curve, f1_score,
        precision_score, recall_score
    )

    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    y_pred = np.array(y_pred)

    roc_auc = roc_auc_score(y_true, y_scores)
    pr_auc = average_precision_score(y_true, y_scores)
    f1 = f1_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)

    # Optimal F1
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
    f1s = 2 * precisions * recalls / (precisions + recalls + 1e-8)
    best_idx = np.argmax(f1s)
    best_f1 = f1s[best_idx]
    best_thresh = thresholds[best_idx] if best_idx < len(thresholds) else 0.5

    y_pred_opt = (y_scores >= best_thresh).astype(int)
    p_opt = precision_score(y_true, y_pred_opt, zero_division=0)
    r_opt = recall_score(y_true, y_pred_opt, zero_division=0)

    from collections import Counter
    dist = Counter(v.get("action", "SAFE") for v in verdicts)

    print(f"\n  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*40}")
    print(f"  {'ROC-AUC':<25} {roc_auc:>10.4f}")
    print(f"  {'PR-AUC':<25} {pr_auc:>10.4f}")
    print(f"  {'F1 (BLOCK+FLAG)':<25} {f1:>10.4f}")
    print(f"  {'Precision (BLOCK+FLAG)':<25} {prec:>10.4f}")
    print(f"  {'Recall (BLOCK+FLAG)':<25} {rec:>10.4f}")
    print(f"  {'Optimal F1':<25} {best_f1:>10.4f}  (threshold={best_thresh:.3f})")
    print(f"  {'P @ optimal':<25} {p_opt:>10.4f}")
    print(f"  {'R @ optimal':<25} {r_opt:>10.4f}")
    print(f"  {'Distribution':<25} {dict(dist)}")

    print(f"\n  {'COMPARISON':^60}")
    print(f"  {'-'*60}")
    print(f"  {'System':<40} {'ROC-AUC':>8} {'PR-AUC':>8}")
    print(f"  {'-'*40} {'-'*8} {'-'*8}")
    print(f"  {'PAN 2010 #1 (RF, supervised)':<40} {'0.9224':>8} {'—':>8}")
    print(f"  {'WikiTrust (reputation, supervised)':<40} {'0.9035':>8} {'—':>8}")
    print(f"  {'PAN 2011 #1 (STiki, supervised)':<40} {'—':>8} {'0.8223':>8}")
    print(f"  {'ORES (GBT, supervised, millions)':<40} {'~0.96':>8} {'—':>8}")
    print(f"  {'ITEFB v3.0 (Ours, training-free)':<40} {roc_auc:>8.4f} {pr_auc:>8.4f}")

    # Save
    results = {
        "dataset": "Webis-WVC-07",
        "total_edits": len(y_true),
        "vandalism": int(sum(y_true)),
        "metrics": {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "f1": round(f1, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "optimal_f1": round(best_f1, 4),
            "optimal_threshold": round(best_thresh, 3),
        },
        "distribution": dict(dist),
    }
    results_file = WVC07_REPORTS / "wvc07_benchmark_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"\n  Saved: {results_file}")


def main():
    args = sys.argv[1:]
    limit = 0
    skip = "--skip-collect" in args
    eval_only = "--eval-only" in args

    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            limit = int(args[idx + 1])

    print("=" * 60)
    print("  ITEFB v3.0 — Webis-WVC-07 Benchmark (940 edits)")
    print("=" * 60)

    if eval_only:
        step_evaluate()
        return

    step_adapt(limit)
    step_features(skip)
    step_truth()
    step_llm()
    step_attribution()
    step_fusion()
    step_evaluate()


if __name__ == "__main__":
    main()
