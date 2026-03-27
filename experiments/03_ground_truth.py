"""
⚖️ STAGE 03: GROUND TRUTH VERIFICATION
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_features.csv
Output: data/{lang}/processed/{timestamp}_truth.csv
Goal:   Check if the edit was actually REVERTED on Wikipedia.
        This provides the ultimate Ground Truth for accuracy.
────────────────────────────────────────────────────────────
"""

import csv
import time
import requests
from pathlib import Path

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
HEADERS = {"User-Agent": "WikiStreamIntel/1.1 (verification-engine)"}
REQUEST_DELAY = 1.0
REVERT_KEYWORDS = {"revert", "undo", "undid", "rv", "rollback", "reverted"}

def check_revert(domain: str, title: str, rev_new: int) -> dict:
    api_url = f"https://{domain}/w/api.php"
    params = {
        "action": "query", "titles": title, "prop": "revisions",
        "rvlimit": "5", "rvprop": "ids|user|comment|timestamp", "format": "json"
    }

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=12)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages: return {"reverted": False, "by": "", "msg": ""}
        
        page = list(pages.values())[0]
        revisions = page.get("revisions", [])
        if not revisions: return {"reverted": False, "by": "", "msg": ""}

        # If latest rev is our rev, it's definitely not reverted (yet)
        if revisions[0]["revid"] == rev_new:
            return {"reverted": False, "by": "", "msg": ""}

        # Check subsequent revisions for revert keywords or manual overwrites
        for rev in revisions:
            if rev["revid"] <= rev_new: break
            
            comment = rev.get("comment", "").lower()
            if any(w in comment for w in REVERT_KEYWORDS):
                return {"reverted": True, "by": rev.get("user", ""), "msg": rev.get("comment", "")}
            
            # Parent ID check (jump back over our edit)
            if rev.get("parentid", 0) > 0 and rev["parentid"] < rev_new:
                return {"reverted": True, "by": rev.get("user", ""), "msg": "Overwritten/Rollback"}

        return {"reverted": False, "by": "", "msg": ""}
    except Exception as e:
        return {"reverted": False, "by": "", "msg": f"Error: {e}"}

def process_lang(lang: str):
    folder = DATA_DIR / lang / "processed"
    if not folder.exists(): return

    for rf in sorted(folder.glob("*_features.csv")):
        output_path = folder / f"{rf.stem.replace('_features', '')}_truth.csv"
        if output_path.exists(): continue
        
        print(f"\n⚖️ Verifying Ground Truth: {rf.name}")
        
        with open(rf, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            edits = list(reader)
            fieldnames = list(reader.fieldnames)

        for col in ["is_reverted", "revert_by", "revert_comment"]:
            if col not in fieldnames: fieldnames.append(col)

        reverted_count = 0
        for i, edit in enumerate(edits):
            # Check if edit has any signal (rule or NLP) — unified_score doesn't exist at this stage
            score = float(edit.get("rule_score", 0) or 0) + float(edit.get("nlp_score", 0) or 0)
            if score > 0:
                res = check_revert(edit["domain"], edit["title"], int(edit["revision_new"]))
                edit["is_reverted"] = str(res["reverted"])
                edit["revert_by"] = res["by"]
                edit["revert_comment"] = res["msg"][:200]
                
                if res["reverted"]:
                    reverted_count += 1
                    print(f"   🔄 [{i+1}] REVERTED: {edit['title'][:30]}")
                time.sleep(REQUEST_DELAY)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edits)
        print(f"   ✅ Saved {output_path.name} ({reverted_count} reverts found)")

def main():
    print("⚖️ WIKI-STREAM GROUND TRUTH ENGINE")
    for lang in ["en", "vi"]:
        process_lang(lang)

if __name__ == "__main__":
    main()
