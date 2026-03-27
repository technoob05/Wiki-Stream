"""
🌙 OVERNIGHT PIPELINE — Thu data lớn + Full 12-Stage Analysis
────────────────────────────────────────────────────────────
Chạy trước khi đi ngủ. Script sẽ:
  1. Thu ~3000 edits từ Wikipedia SSE (khoảng 1-2 tiếng)
  2. Chạy full 12-stage pipeline tự động
  3. Log kết quả vào overnight_log.txt
────────────────────────────────────────────────────────────
"""
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "reports" / "overnight_log.txt"
LOG_FILE.parent.mkdir(exist_ok=True)

# Override Stage 01 TARGET_COUNT to 3000
COLLECT_TARGET = 3000

STAGES = [
    "01_collect_data.py",
    "02_rule_engine.py",
    "03_diff_fetcher.py",
    "04_nlp_analysis.py",
    "05_revert_check.py",
    "06_llm_verification.py",
    "07_vandal_fingerprinting.py",
    "08_attribution_engine.py",
    "09_intelligence_aggregator.py",
    "10_advanced_analytics.py",
]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_stage(script, extra_env=None):
    log(f"▶ Starting {script}...")
    start = time.time()
    
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        env.update(extra_env)
    
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script)],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env, cwd=str(SCRIPT_DIR)
    )
    
    elapsed = time.time() - start
    
    if result.returncode == 0:
        log(f"✅ {script} completed in {elapsed:.1f}s")
        # Log last 5 lines of output
        lines = result.stdout.strip().split("\n")
        for line in lines[-5:]:
            log(f"   {line.strip()}")
    else:
        log(f"❌ {script} FAILED (exit code {result.returncode}) after {elapsed:.1f}s")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-5:]:
                log(f"   ERR: {line.strip()}")
    
    return result.returncode == 0


def main():
    log("=" * 60)
    log("🌙 OVERNIGHT PIPELINE STARTED")
    log(f"   Target: {COLLECT_TARGET} edits")
    log(f"   Stages: {len(STAGES)}")
    log("=" * 60)
    
    total_start = time.time()
    
    # Stage 01: Override TARGET_COUNT via env var
    # We need to temporarily patch the collect script
    log(f"\n📡 Phase 1: Collecting {COLLECT_TARGET} edits (this takes 1-2 hours)...")
    
    # Dynamically patch TARGET_COUNT
    collect_script = SCRIPT_DIR / "01_collect_data.py"
    original_content = collect_script.read_text(encoding="utf-8")
    patched_content = original_content.replace(
        "TARGET_COUNT = 300",
        f"TARGET_COUNT = {COLLECT_TARGET}"
    )
    collect_script.write_text(patched_content, encoding="utf-8")
    
    success = run_stage("01_collect_data.py")
    
    # Restore original
    collect_script.write_text(original_content, encoding="utf-8")
    log("   (Restored original TARGET_COUNT = 300)")
    
    if not success:
        log("❌ Data collection failed. Aborting pipeline.")
        return
    
    # Stages 02-12
    log(f"\n🔬 Phase 2: Running analysis pipeline (02-12)...")
    
    for i, stage in enumerate(STAGES[1:], 2):
        stage_path = SCRIPT_DIR / stage
        if not stage_path.exists():
            log(f"⏭️ Skipping {stage} (not found)")
            continue
        
        success = run_stage(stage)
        if not success and i <= 6:  # Critical stages
            log(f"⚠️ Critical stage {stage} failed, but continuing...")
    
    total_elapsed = time.time() - total_start
    hours = total_elapsed / 3600
    
    log(f"\n{'=' * 60}")
    log(f"🌅 OVERNIGHT PIPELINE COMPLETE!")
    log(f"   Total time: {hours:.1f} hours ({total_elapsed:.0f}s)")
    log(f"   Check: reports/insights.md")
    log(f"   Check: reports/graph_intelligence.json")
    log(f"   Check: reports/graph_vandal_network.png")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
