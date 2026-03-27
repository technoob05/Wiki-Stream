"""
PAN-WVC-10 Adapter — Convert PAN dataset to ITEFB pipeline format
------------------------------------------------------------
Reads PAN edits.csv + gold-annotations.csv
Outputs CSV files compatible with Stage 02+ of the pipeline.

Usage:
  python pan_adapter.py [--limit N]  (default: all 32,452 edits)
------------------------------------------------------------
"""

import csv
import json
import sys
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
PAN_DIR = BENCHMARK_DIR / "pan-wvc-10"
OUTPUT_DIR = BENCHMARK_DIR / "pan_data" / "en" / "raw"
GOLD_FILE = BENCHMARK_DIR / "pan_gold.json"


def find_pan_files():
    """Locate PAN dataset files (handles nested directory structures)."""
    # Try common locations
    candidates = [
        PAN_DIR,
        BENCHMARK_DIR / "pan-wikipedia-vandalism-corpus-2010",
        BENCHMARK_DIR,
    ]

    edits_csv = None
    gold_csv = None

    for base in candidates:
        if not base.exists():
            continue
        # Search recursively
        for f in base.rglob("edits.csv"):
            edits_csv = f
        for f in base.rglob("gold-annotations.csv"):
            gold_csv = f
        if edits_csv and gold_csv:
            break

    return edits_csv, gold_csv


def load_gold_annotations(gold_csv: Path) -> dict:
    """Load ground truth: editid -> 'vandalism' or 'regular'."""
    gold = {}
    with open(gold_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = row.get("editid", row.get("EDITID", "")).strip()
            cls = row.get("class", row.get("CLASS", "")).strip().lower()
            if eid:
                gold[eid] = cls
    return gold


def convert_pan_to_pipeline(limit: int = 0):
    """Convert PAN edits to pipeline-compatible CSV."""
    edits_csv, gold_csv = find_pan_files()

    if not edits_csv:
        print("ERROR: Cannot find edits.csv in benchmark directory.")
        print("  Expected locations:")
        print(f"    {PAN_DIR}/edits.csv")
        print(f"    {BENCHMARK_DIR}/pan-wikipedia-vandalism-corpus-2010/edits.csv")
        print("\n  Please unzip the PAN dataset first:")
        print(f"    cd {BENCHMARK_DIR}")
        print("    unzip pan-wvc-10.zip")
        return

    if not gold_csv:
        print("ERROR: Cannot find gold-annotations.csv")
        return

    print(f"  Found edits: {edits_csv}")
    print(f"  Found gold:  {gold_csv}")

    # Load gold annotations
    gold = load_gold_annotations(gold_csv)
    print(f"  Gold labels: {len(gold)} ({sum(1 for v in gold.values() if v == 'vandalism')} vandalism)")

    # Save gold as JSON for evaluation script
    with open(GOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(gold, f)
    print(f"  Saved gold to {GOLD_FILE}")

    # Read and convert edits
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(edits_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        pan_fieldnames = reader.fieldnames
        edits = list(reader)

    if limit > 0:
        edits = edits[:limit]

    print(f"  Converting {len(edits)} edits...")

    # Map PAN fields to pipeline fields
    # PAN: editid, oldrevisionid, newrevisionid, edittime, editor, articletitle, editcomment
    # Pipeline: timestamp, domain, user, title, comment, revision_old, revision_new, length_old, length_new, bot, minor, wiki_url
    pipeline_fieldnames = [
        "timestamp", "domain", "user", "title", "comment",
        "revision_old", "revision_new", "length_old", "length_new",
        "bot", "minor", "wiki_url", "pan_editid", "pan_gold",
    ]

    converted = []
    for edit in edits:
        eid = edit.get("editid", edit.get("EDITID", "")).strip()
        converted.append({
            "timestamp": edit.get("edittime", edit.get("EDITTIME", "")),
            "domain": "en.wikipedia.org",
            "user": edit.get("editor", edit.get("EDITOR", "")),
            "title": edit.get("articletitle", edit.get("ARTICLETITLE", "")),
            "comment": edit.get("editcomment", edit.get("EDITCOMMENT", "")),
            "revision_old": edit.get("oldrevisionid", edit.get("OLDREVISIONID", "")),
            "revision_new": edit.get("newrevisionid", edit.get("NEWREVISIONID", "")),
            "length_old": "0",
            "length_new": "0",
            "bot": "false",
            "minor": "false",
            "wiki_url": f"https://en.wikipedia.org/w/index.php?diff={edit.get('newrevisionid', edit.get('NEWREVISIONID', ''))}",
            "pan_editid": eid,
            "pan_gold": gold.get(eid, "unknown"),
        })

    # Split into chunks of ~5000 for pipeline compatibility
    chunk_size = 5000
    for i in range(0, len(converted), chunk_size):
        chunk = converted[i:i + chunk_size]
        chunk_name = f"pan_chunk_{i // chunk_size:02d}.csv"
        output_path = OUTPUT_DIR / chunk_name

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=pipeline_fieldnames)
            writer.writeheader()
            writer.writerows(chunk)

        print(f"  Wrote {output_path.name} ({len(chunk)} edits)")

    print(f"\n  Total: {len(converted)} edits in {OUTPUT_DIR}")
    print(f"  Vandalism: {sum(1 for e in converted if e['pan_gold'] == 'vandalism')}")
    print(f"  Regular:   {sum(1 for e in converted if e['pan_gold'] == 'regular')}")


if __name__ == "__main__":
    limit = 0
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    print("PAN-WVC-10 → ITEFB Pipeline Adapter")
    convert_pan_to_pipeline(limit)
