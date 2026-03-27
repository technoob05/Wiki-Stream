from pathlib import Path

stages_new = [
    "01_collect_data.py", "02_feature_extraction.py", "03_ground_truth.py",
    "04_llm_classification.py", "05_user_attribution.py", 
    "06_intelligence_fusion.py", "07_report_synthesis.py",
]
stages_old = [
    "01_collect_data.py", "02_rule_engine.py", "03_diff_fetcher.py",
    "04_nlp_analysis.py", "05_revert_check.py", "06_llm_verification.py",
    "07_vandal_fingerprinting.py", "08_attribution_engine.py",
    "09_intelligence_aggregator.py", "10_advanced_analytics.py",
]

print("=== NEW 7-STAGE ===")
for s in stages_new:
    e = "OK" if Path(s).exists() else "--"
    print(f"  {e} {s}")

print("\n=== OLD FILES (fallback) ===")
for s in stages_old:
    e = "OK" if Path(s).exists() else "--"
    print(f"  {e} {s}")
