import csv
from pathlib import Path

DATA_DIR = Path("data")

# Get ALL edits with LLM labels
vandals = []
for lang_dir in DATA_DIR.iterdir():
    if not lang_dir.is_dir(): continue
    proc = lang_dir / "processed"
    if not proc.exists(): continue
    for f in sorted(proc.glob("*_06_llm.csv")):
        with open(f, "r", encoding="utf-8") as csvf:
            for r in csv.DictReader(csvf):
                llm = r.get("llm_classification", "")
                if llm == "VANDALISM":
                    vandals.append(r)

print(f"Total VANDALISM edits found: {len(vandals)}\n")

for i, e in enumerate(vandals[:8]):
    old = int(e.get("length_old", 0) or 0)
    new = int(e.get("length_new", 0) or 0)
    delta = new - old
    
    print(f"{'='*60}")
    print(f"CASE #{i+1}")
    print(f"{'='*60}")
    print(f"User:    {e.get('user','')}")
    print(f"Article: {e.get('title','')}")
    print(f"Comment: {e.get('comment','')}")
    print(f"Size:    {old} -> {new} ({delta:+d} bytes)")
    print()
    print(f"--- EVIDENCE CHAIN ---")
    print(f"1. Rule Engine:  Score {e.get('rule_score','0')}/5")
    print(f"2. NLP Analysis: Score {e.get('nlp_score','0')}")
    print(f"3. LLM (Gemma2): {e.get('llm_classification','')} "
          f"(conf={e.get('llm_confidence','')})")
    reason = e.get("llm_reason", "")
    if reason:
        print(f"   REASON: {reason}")
    print()
