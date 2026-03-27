"""
🔗 STAGE 03: DIFF FETCHING ENGINE
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_02_scored.csv
Output: data/{lang}/processed/{timestamp}_03_diff.csv
Goal:   Sử dụng Wikipedia API (action=compare) để lấy nội dung 
        added/removed cụ thể cho các edits đã được flagged.
────────────────────────────────────────────────────────────
"""

import csv
import re
import time
import json
from pathlib import Path
from html import unescape

import requests

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"

HEADERS = {
    "User-Agent": "WikiStreamIntel/1.0 (university-research-project; contact: student@example.com)",
}

# Rate limit: Wikipedia cho phép ~200 req/min, ta dùng ~60/min cho an toàn
REQUEST_DELAY = 1.0  # giây giữa mỗi request


def get_diff(domain: str, rev_old: int, rev_new: int) -> dict:
    """Lấy diff giữa 2 revision từ Wikipedia API.
    
    Returns:
        {
            "diff_added": "text được thêm vào",
            "diff_removed": "text bị xóa",
            "diff_html": "raw HTML diff từ API",
            "error": None hoặc error message
        }
    """
    api_url = f"https://{domain}/w/api.php"
    params = {
        "action": "compare",
        "fromrev": rev_old,
        "torev": rev_new,
        "format": "json",
        "prop": "diff",
    }

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "compare" not in data:
            error = data.get("error", {}).get("info", "Unknown error")
            return {"diff_added": "", "diff_removed": "", "diff_html": "", "error": error}

        diff_html = data["compare"].get("body", "") or data["compare"].get("*", "")
        added, removed = parse_diff_html(diff_html)

        return {
            "diff_added": added,
            "diff_removed": removed,
            "diff_html": diff_html,
            "error": None,
        }

    except requests.RequestException as e:
        return {"diff_added": "", "diff_removed": "", "diff_html": "", "error": str(e)}


def parse_diff_html(html: str) -> tuple[str, str]:
    """Parse HTML diff từ Wikipedia API, trích xuất text thêm/xóa.
    
    Wikipedia diff HTML dùng:
    - <ins class="diffchange diffchange-inline"> cho text thêm vào
    - <del class="diffchange diffchange-inline"> cho text bị xóa
    - <td class="diff-addedline"> cho dòng mới
    - <td class="diff-deletedline"> cho dòng cũ
    """
    # Lấy text từ các dòng thêm vào (added lines)
    added_parts = []
    for match in re.finditer(r'<td class="diff-addedline[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL):
        text = strip_html(match.group(1))
        if text.strip():
            added_parts.append(text.strip())

    # Lấy text từ các dòng bị xóa (deleted lines)
    removed_parts = []
    for match in re.finditer(r'<td class="diff-deletedline[^"]*"[^>]*>(.*?)</td>', html, re.DOTALL):
        text = strip_html(match.group(1))
        if text.strip():
            removed_parts.append(text.strip())

    added = "\n".join(added_parts)
    removed = "\n".join(removed_parts)

    return added, removed


def strip_html(html: str) -> str:
    """Xóa tất cả HTML tags, giữ lại text thuần."""
    text = re.sub(r"<[^>]+>", "", html)
    text = unescape(text)
    # Dọn dẹp whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def process_scored_csv(csv_path: Path) -> Path:
    """Đọc scored CSV, lấy diff, lưu thành _03_enriched.csv."""
    # Xác định output path
    ts = csv_path.name.replace("_02_scored.csv", "")
    output_path = csv_path.parent / f"{ts}_03_enriched.csv"
    
    if output_path.exists():
        print(f"   ⏩ Skipping {csv_path.name} (already enriched)")
        return output_path

    edits = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        edits = list(reader)

    if not edits:
        print(f"   ⚠️ File trống: {csv_path.name}")
        return csv_path

    # Thêm fields mới
    new_fields = list(fieldnames)
    for col in ["diff_added", "diff_removed", "diff_error"]:
        if col not in new_fields:
            new_fields.append(col)

    total = len(edits)
    fetched = 0
    errors = 0

    for i, edit in enumerate(edits):
        score = float(edit.get("rule_score", 0))
        rev_old = edit.get("revision_old", "0")
        rev_new = edit.get("revision_new", "0")
        domain = edit.get("domain", "")

        # Lấy diff cho TẤT CẢ edits có score > 0 HOẶC có revision hợp lệ
        if score > 0 and rev_old != "0" and rev_new != "0" and domain:
            result = get_diff(domain, rev_old, rev_new)

            edit["diff_added"] = result["diff_added"][:2000]
            edit["diff_removed"] = result["diff_removed"][:2000]
            edit["diff_error"] = result["error"] or ""

            fetched += 1
            if result["error"]:
                errors += 1
                print(f"   ❌ [{i+1}/{total}] {edit.get('title', '')[:30]} — {result['error']}")
            else:
                added_len = len(result["diff_added"])
                removed_len = len(result["diff_removed"])
                print(f"   ✅ [{i+1}/{total}] {edit.get('title', '')[:30]} — +{added_len} -{removed_len} chars")

            time.sleep(REQUEST_DELAY)
        else:
            edit["diff_added"] = ""
            edit["diff_removed"] = ""
            edit["diff_error"] = ""

    # Lưu lại
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(edits)

    print(f"\n   💾 Saved: {output_path.name}")
    print(f"   📊 Fetched: {fetched} diffs ({errors} errors)")
    return output_path


def main():
    print("🔍 Wiki-Stream Diff Fetcher v2.0")
    print("   Cấu trúc: data/{lang}/processed/*_02_scored.csv -> *_03_enriched.csv")

    langs = ["en", "vi"]
    for lang in langs:
        folder = DATA_DIR / lang / "processed"
        if not folder.exists():
            continue

        scored_files = sorted(folder.glob("*_02_scored.csv"))
        if not scored_files:
            continue

        print(f"\n{'='*60}")
        print(f"📂 {lang}")
        print(f"{'='*60}")

        for sf in scored_files:
            process_scored_csv(sf)

    print(f"\n{'='*60}")
    print("✅ Xong! Diff data đã được lưu vào các file _03_enriched.csv")
    print("   → Bước tiếp: 04_nlp_analysis.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
