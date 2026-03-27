"""Quick ground truth analysis."""
import csv, glob
from collections import Counter

files = sorted(glob.glob('data/*/processed/*_06_llm.csv'))
total = 0
reverted = 0
revert_details = []
tp = Counter(); fp = Counter(); fn = Counter(); tn = Counter()

for f in files:
    with open(f, 'r', encoding='utf-8') as csvf:
        for row in csv.DictReader(csvf):
            total += 1
            is_rev = row.get('is_reverted') == 'True'
            if is_rev:
                reverted += 1
                revert_details.append({
                    'user': row.get('user',''),
                    'title': row.get('title','')[:30],
                    'rule': float(row.get('rule_score',0)),
                    'nlp': float(row.get('nlp_score',0)),
                    'llm': row.get('llm_classification',''),
                })
            for sig, flag in [
                ('rule', float(row.get('rule_score',0)) >= 3),
                ('nlp', float(row.get('nlp_score',0)) >= 0.6),
                ('llm', row.get('llm_classification','') in ('VANDALISM','SUSPICIOUS')),
            ]:
                if flag and is_rev: tp[sig] += 1
                elif flag and not is_rev: fp[sig] += 1
                elif not flag and is_rev: fn[sig] += 1
                else: tn[sig] += 1

print(f"Total: {total}, Reverted: {reverted}")
print("\n=== PER-SIGNAL ACCURACY ===")
for sig in ['rule', 'nlp', 'llm']:
    t=tp[sig]; f_p=fp[sig]; f_n=fn[sig]
    prec = t/(t+f_p)*100 if (t+f_p)>0 else 0
    rec = t/(t+f_n)*100 if (t+f_n)>0 else 0
    f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0
    print(f"  {sig:6s}: TP={t} FP={f_p} FN={f_n} Prec={prec:.1f}% Rec={rec:.1f}% F1={f1:.1f}%")

print("\n=== REVERTED EDITS ===")
for d in revert_details:
    print(f"  {d['user']:20s} R={d['rule']:.0f} NLP={d['nlp']:.1f} LLM={d['llm']:12s} {d['title']}")
