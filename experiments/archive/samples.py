import json

with open("reports/deep_insights.json", "r", encoding="utf-8") as f:
    deep = json.load(f)
with open("reports/llm_vs_ml_comparison.json", "r", encoding="utf-8") as f:
    comp = json.load(f)
with open("reports/advanced_analytics.json", "r", encoding="utf-8") as f:
    adv = json.load(f)

print("=" * 70)
print("  SAMPLE 1: TOP THREATS (Unified 8-Signal Verdict)")
print("=" * 70)
for v in adv.get("verdict", {}).get("top_verdicts", [])[:5]:
    u = v["user"]
    t = v["title"]
    s = v["signals"]
    print(f"  User:    {u}")
    print(f"  Article: {t}")
    print(f"  Score:   {v['verdict_score']} -> {v['action']}")
    print(f"  Signals: Rule={s['rule']} NLP={s['nlp']} LLM={s['llm']} DS={s['ds']} Graph={s['graph']} IF={s['if']}")
    print()

print("=" * 70)
print("  SAMPLE 2: HYBRID LLM+ML TOP THREATS")
print("=" * 70)
for v in comp.get("hybrid_verdict", {}).get("top_threats", [])[:5]:
    print(f"  User:    {v['user']}")
    print(f"  Article: {v['title']}")
    print(f"  Hybrid:  {v['hybrid_score']} -> {v['action']}")
    print(f"  LLM:     {v['llm']}  |  ML prob: {v['ml_prob']}%")
    print()

print("=" * 70)
print("  SAMPLE 3: ML-ONLY DISCOVERIES (LLM never saw)")
print("=" * 70)
ml_risk = deep.get("ml_risk", {}).get("high_risk_edits", [])
ml_only = [x for x in ml_risk if not x["has_llm"]][:5]
for v in ml_only:
    print(f"  User:    {v['user']}")
    print(f"  Article: {v['title']}")
    print(f"  ML Risk: {v['ml_risk']}%  (LLM: never processed!)")
    print()

print("=" * 70)
print("  SAMPLE 4: BEHAVIORAL ARCHETYPES")
print("=" * 70)
for sv in deep.get("behavioral_profiles", {}).get("serial_vandals", [])[:3]:
    print(f"  SERIAL:  {sv['user']} | {sv['vandal_edits']} vandal edits | {sv['unique_articles']} articles | anon={sv['is_anon']}")
for hr in deep.get("behavioral_profiles", {}).get("hit_and_run", [])[:3]:
    print(f"  HITRUN:  {hr['user']} | ratio={hr['vandal_ratio']}% | avg_delta={hr['avg_delta']}")

print()
print("=" * 70)
print("  SAMPLE 5: DEMPSTER-SHAFER EVIDENCE FUSION")
print("=" * 70)
for v in adv.get("dempster_shafer", {}).get("top_vandals", [])[:3]:
    b = v["belief"]
    p = v["plausibility"]
    u = v["uncertainty"]
    print(f"  User:    {v['user']}")
    print(f"  Belief={b:.3f}  Plausibility={p:.3f}  Uncertainty={u:.3f}")
    print(f"  Class:   {v['classification']}")
    print()
