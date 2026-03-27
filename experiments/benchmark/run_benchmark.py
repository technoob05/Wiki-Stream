"""
PAN-WVC-10 Benchmark Runner
------------------------------------------------------------
Master script: unzip → adapt → run pipeline → evaluate

Usage:
  python run_benchmark.py                   # Full 32K edits
  python run_benchmark.py --limit 500       # Quick test with 500 edits
  python run_benchmark.py --skip-collect    # Skip diff fetching (if already done)
  python run_benchmark.py --eval-only       # Only run evaluation (if pipeline done)
------------------------------------------------------------
"""

import os
import sys
import zipfile
import time
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
EXPERIMENTS_DIR = BENCHMARK_DIR.parent
PAN_DATA_DIR = BENCHMARK_DIR / "pan_data"

# Add experiments dir to path for imports
sys.path.insert(0, str(EXPERIMENTS_DIR))


def step_unzip():
    """Step 0: Unzip PAN dataset."""
    zip_file = BENCHMARK_DIR / "pan-wvc-10-full.zip"
    if not zip_file.exists():
        zip_file = BENCHMARK_DIR / "pan-wvc-10.zip"

    if not zip_file.exists():
        print("ERROR: Download PAN-WVC-10 first!")
        print(f"  Expected: {zip_file}")
        return False

    # Check if already unzipped
    pan_dir = None
    for candidate in [
        BENCHMARK_DIR / "pan-wvc-10",
        BENCHMARK_DIR / "pan-wikipedia-vandalism-corpus-2010",
    ]:
        if candidate.exists() and any(candidate.rglob("edits.csv")):
            pan_dir = candidate
            break

    if pan_dir:
        print(f"  Already unzipped: {pan_dir}")
        return True

    print(f"  Unzipping {zip_file.name}...")
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(BENCHMARK_DIR)
        print("  Unzipped successfully.")
        return True
    except zipfile.BadZipFile:
        size = zip_file.stat().st_size
        print(f"  ERROR: Bad zip file ({size} bytes). Re-download needed.")
        return False


def step_adapt(limit: int = 0):
    """Step 1: Convert PAN format to pipeline format."""
    print("\n[STEP 1] Adapting PAN data to pipeline format...")
    from pan_adapter import convert_pan_to_pipeline
    convert_pan_to_pipeline(limit)


def step_run_pipeline(skip_collect: bool = False):
    """Step 2: Run ITEFB pipeline stages 02-07 on PAN data."""
    import json

    # Override DATA_DIR for all pipeline stages
    pan_data = PAN_DATA_DIR
    pan_reports = BENCHMARK_DIR / "pan_reports"
    pan_reports.mkdir(exist_ok=True)

    # --- Stage 02: Feature Extraction ---
    if not skip_collect:
        print("\n[STEP 2] Stage 02: Feature Extraction (diff fetching + NLP + InfoTheory)...")
        print("  WARNING: This fetches diffs from Wikipedia API (~1 req/s)")

        from importlib import import_module
        stage02 = import_module("02_feature_extraction")

        # Monkey-patch DATA_DIR
        original_data_dir = stage02.DATA_DIR
        stage02.DATA_DIR = pan_data

        rep = {}
        rep_file = EXPERIMENTS_DIR / "reputation.json"
        if rep_file.exists():
            with open(rep_file, "r") as f:
                rep = json.load(f)

        ref_dist = stage02.load_reference_distribution()
        for lang in ["en"]:
            if (pan_data / lang).exists():
                stage02.process_lang(lang, rep, ref_dist)

        stage02.DATA_DIR = original_data_dir
    else:
        print("\n[STEP 2] Skipping feature extraction (--skip-collect)")

    # --- Stage 03: Ground Truth (skip — PAN has its own gold) ---
    print("\n[STEP 3] Stage 03: Skipping (using PAN gold annotations instead)")

    # Create dummy _truth.csv by copying _features.csv
    proc_dir = pan_data / "en" / "processed"
    if proc_dir.exists():
        for f in proc_dir.glob("*_features.csv"):
            truth_path = proc_dir / f.name.replace("_features.csv", "_truth.csv")
            if not truth_path.exists():
                import shutil
                shutil.copy(f, truth_path)
                print(f"  Created {truth_path.name}")

    # --- Stage 04: LLM Classification ---
    print("\n[STEP 4] Stage 04: LLM Classification...")
    print("  NOTE: This requires Ollama running with Gemma 2")

    try:
        stage04 = import_module("04_llm_classification")
        original_data_dir_04 = stage04.DATA_DIR
        stage04.DATA_DIR = pan_data

        for lang in ["en"]:
            stage04.process_lang(lang)

        stage04.DATA_DIR = original_data_dir_04
    except Exception as e:
        print(f"  LLM stage failed: {e}")
        print("  Creating fallback classified files (no LLM)...")
        # Copy truth as classified with default LLM mass
        if proc_dir.exists():
            import csv
            for f in proc_dir.glob("*_truth.csv"):
                cls_path = proc_dir / f.name.replace("_truth.csv", "_classified.csv")
                if not cls_path.exists():
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

    # --- Stage 05: Attribution ---
    print("\n[STEP 5] Stage 05: User Attribution...")
    try:
        stage05 = import_module("05_user_attribution")
        original_data_dir_05 = stage05.DATA_DIR
        stage05.DATA_DIR = pan_data

        db = stage05.update_db()
        cov_inv = stage05.estimate_covariance(db)
        threshold = stage05.compute_adaptive_threshold(db, cov_inv)
        for lang in ["en"]:
            stage05.process_lang(lang, db, cov_inv, threshold)

        stage05.DATA_DIR = original_data_dir_05
    except Exception as e:
        print(f"  Attribution failed: {e}")
        # Create fallback
        if proc_dir.exists():
            import csv
            for f in proc_dir.glob("*_classified.csv"):
                attr_path = proc_dir / f.name.replace("_classified.csv", "_attributed.csv")
                if not attr_path.exists():
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

    # --- Stage 06: Intelligence Fusion ---
    print("\n[STEP 6] Stage 06: Intelligence Fusion...")
    stage06 = import_module("06_intelligence_fusion")
    original_data_dir_06 = stage06.DATA_DIR
    original_report_dir_06 = stage06.REPORT_DIR
    stage06.DATA_DIR = pan_data
    stage06.REPORT_DIR = pan_reports

    stage06.main()

    stage06.DATA_DIR = original_data_dir_06
    stage06.REPORT_DIR = original_report_dir_06


def step_evaluate():
    """Step 3: Evaluate against PAN gold standard."""
    print("\n[STEP 7] Evaluation against PAN gold standard...")
    from pan_evaluate import evaluate
    evaluate()


def main():
    args = sys.argv[1:]
    limit = 0
    skip_collect = "--skip-collect" in args
    eval_only = "--eval-only" in args

    if "--limit" in args:
        idx = args.index("--limit")
        if idx + 1 < len(args):
            limit = int(args[idx + 1])

    print("=" * 60)
    print("  ITEFB v3.0 — PAN-WVC-10 Benchmark")
    print("=" * 60)

    if eval_only:
        step_evaluate()
        return

    # Step 0: Unzip
    print("\n[STEP 0] Checking PAN dataset...")
    if not step_unzip():
        return

    # Step 1: Adapt
    step_adapt(limit)

    # Step 2: Pipeline
    step_run_pipeline(skip_collect)

    # Step 3: Evaluate
    step_evaluate()

    print("\n" + "=" * 60)
    print("  Benchmark complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
