"""
Webis-WVC-07 Adapter — Convert WVC-07 XML to ITEFB pipeline format
------------------------------------------------------------
Reads wwvc-11-07.xml (940 edits, 301 vandalism)
Outputs CSV compatible with Stage 02+ and gold labels JSON.
------------------------------------------------------------
"""

import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
WVC07_DIR = BENCHMARK_DIR / "webis-wikipedia-vandalism-corpus-2007"
OUTPUT_DIR = BENCHMARK_DIR / "wvc07_data" / "en" / "raw"
GOLD_FILE = BENCHMARK_DIR / "wvc07_gold.json"

NS = {'w': 'http://www.uni-weimar.de/medien/webis/research/misuse/vandalism'}


def convert(limit: int = 0):
    xml_file = WVC07_DIR / "wwvc-11-07.xml"
    if not xml_file.exists():
        print(f"ERROR: {xml_file} not found")
        return

    tree = ET.parse(xml_file)
    root = tree.getroot()

    edits = []
    gold = {}

    for edit_el in root.findall('w:edit', NS):
        new_rev = edit_el.findtext('w:newRevisionID', '', NS).strip()
        old_rev = edit_el.findtext('w:oldRevisionID', '', NS).strip()
        is_vandalism = edit_el.find('w:vandalism', NS) is not None

        if not new_rev or not old_rev:
            continue

        edit_id = f"wvc07_{new_rev}"
        gold[edit_id] = "vandalism" if is_vandalism else "regular"

        edits.append({
            "timestamp": "",
            "domain": "en.wikipedia.org",
            "user": "",
            "title": "",
            "comment": "",
            "revision_old": old_rev,
            "revision_new": new_rev,
            "length_old": "0",
            "length_new": "0",
            "bot": "false",
            "minor": "false",
            "wiki_url": f"https://en.wikipedia.org/w/index.php?diff={new_rev}",
            "pan_editid": edit_id,
            "pan_gold": gold[edit_id],
        })

    if limit > 0:
        edits = edits[:limit]
        gold = {e["pan_editid"]: gold[e["pan_editid"]] for e in edits}

    # Save gold
    with open(GOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(gold, f)

    # Save CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(edits[0].keys())

    output_path = OUTPUT_DIR / "wvc07_edits.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edits)

    vandalism_count = sum(1 for v in gold.values() if v == "vandalism")
    print(f"  Converted {len(edits)} edits ({vandalism_count} vandalism, {len(edits)-vandalism_count} regular)")
    print(f"  Output: {output_path}")
    print(f"  Gold: {GOLD_FILE}")


if __name__ == "__main__":
    limit = 0
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    print("Webis-WVC-07 → ITEFB Adapter")
    convert(limit)
