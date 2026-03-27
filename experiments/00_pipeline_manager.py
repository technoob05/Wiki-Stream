"""
🚀 WIKI-STREAM INTELLIGENCE PIPELINE (7-STAGE PRODUCTION)
────────────────────────────────────────────────────────────
Consolidated Manager for High-Performance Forensic Analysis.
────────────────────────────────────────────────────────────
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# ── Pipeline Architecture ──
STAGES = [
    ("01_collect_data.py",      "📥 Stage 01: Data Collection"),
    ("02_feature_extraction.py", "🔍 Stage 02: Feature Extraction"),
    ("03_ground_truth.py",       "⚖️  Stage 03: Ground Truth"),
    ("04_llm_classification.py", "🤖 Stage 04: LLM Classification"),
    ("05_user_attribution.py",   "🕵️  Stage 05: User Attribution"),
    ("06_intelligence_fusion.py", "🧬 Stage 06: Intelligence Fusion"),
    ("07_report_generator.py",   "📊 Stage 07: Report Synthesis"),
]

def run_stage(script, name):
    print(f"\n{'-'*60}\n{name}\n{'-'*60}")
    start = time.time()
    try:
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run([sys.executable, script], check=True)
        elapsed = time.time() - start
        print(f"✅ Completed in {elapsed:.1f}s")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed: {script}")
        return False

def main():
    print("🚀 WIKI-STREAM PRODUCTION PIPELINE v2.0")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for script, name in STAGES:
        if not os.path.exists(script):
            print(f"⚠️ Missing script: {script}")
            continue
            
        success = run_stage(script, name)
        if not success:
            print(f"\n🛑 Pipeline halted due to error in {script}")
            break
            
    print(f"\n{'='*60}")
    print("🏁 PIPELINE EXECUTION FINISHED")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
