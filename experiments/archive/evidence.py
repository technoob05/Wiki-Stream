import csv, glob
from pathlib import Path

DATA_DIR = Path("data")
targets = ["Brainiac242", "Goldenlane", "Wickkeypedia", "TheAmazingPeanuts", 
           "MKP2020", "Rtkat3", "M0NKEYMADNESS", "Necrothesp"]

# Find best file with LLM reasons
for lang_dir in DATA_DIR.iterdir():
    if not lang_dir.is_dir(): continue
    proc = lang_dir / "processed"
    if not proc.exists(): continue
    for pat in ["*_06_llm.csv"]:
        for f in sorted(proc.glob(pat)):
            with open(f, "r", encoding="utf-8") as csvf:
                reader = csv.DictReader(csvf)
                for row in reader:
                    user = row.get("user", "")
                    if not any(t in user for t in targets):
                        continue
                    
                    old = int(row.get("length_old", 0) or 0)
                    new = int(row.get("length_new", 0) or 0)
                    delta = new - old
                    
                    print("=" * 60)
                    print(f"USER:    {user}")
                    print(f"ARTICLE: {row.get('title', '')}")
                    print(f"COMMENT: {row.get('comment', '')}")
                    print(f"SIZE:    {old} -> {new} ({delta:+d} bytes)")
                    print(f"MINOR:   {row.get('minor', '')}")
                    print(f"TIME:    {row.get('timestamp', '')}")
                    print()
                    
                    rs = row.get("rule_score", "0")
                    ns = row.get("nlp_score", "0")
                    llm_c = row.get("llm_classification", "")
                    llm_conf = row.get("llm_confidence", "")
                    llm_reason = row.get("llm_reason", "")
                    
                    print(f"RULE SCORE: {rs}/5")
                    print(f"NLP SCORE:  {ns}")
                    
                    if llm_c:
                        print(f"LLM LABEL:  {llm_c}")
                        print(f"LLM CONF:   {llm_conf}")
                        print(f"LLM REASON: {llm_reason}")
                    else:
                        print(f"LLM: (not processed)")
                    print()
