"""
⚖️ STAGE 05: REVERT VERIFICATION (GROUND TRUTH)
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_04_final.csv
Output: {timestamp}_05_revert.csv (Updated with accuracy metadata)
Goal:   Kiểm tra xem edit có bị Revert thực tế trên Wikipedia không.
        Đây là căn cứ tối thượng (Ground Truth) để đo độ chính xác.
────────────────────────────────────────────────────────────
"""

import csv
import re
import time
import json
from pathlib import Path

import requests

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"

HEADERS = {
    "User-Agent": "WikiStreamIntel/1.0 (university-research-project; contact: student@example.com)",
}

REQUEST_DELAY = 1.0  # giây giữa mỗi request
REVERT_KEYWORDS = {"revert", "undo", "undid", "rv", "rollback", "reverted"}


def check_if_reverted(domain: str, title: str, rev_new: int) -> dict:
    """Kiểm tra xem 1 edit có bị revert hay không.
    
    Trả về:
        {
            "is_reverted": True/False,
            "current_rev": ID revision hiện tại,
            "revert_by": user đã revert (nếu có),
            "revert_comment": comment khi revert,
            "error": None hoặc error message
        }
    """
    api_url = f"https://{domain}/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvlimit": "5",  # Lấy 5 revision gần nhất
        "rvprop": "ids|user|comment|timestamp",
        "format": "json",
    }

    try:
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return {"is_reverted": False, "current_rev": 0, "revert_by": "",
                    "revert_comment": "", "error": "No pages found"}

        page = list(pages.values())[0]
        if "revisions" not in page:
            return {"is_reverted": False, "current_rev": 0, "revert_by": "",
                    "revert_comment": "", "error": "No revisions"}

        revisions = page["revisions"]
        latest_rev = revisions[0]["revid"]

        # Nếu revision mới nhất = edit của ta → chưa bị thay đổi
        if latest_rev == rev_new:
            return {"is_reverted": False, "current_rev": latest_rev,
                    "revert_by": "", "revert_comment": "", "error": None}

        # Kiểm tra xem có revision nào sau edit chứa keyword revert
        is_reverted = False
        revert_by = ""
        revert_comment = ""

        for rev in revisions:
            if rev["revid"] <= rev_new:
                break  # Đã qua các revision sau edit

            comment = rev.get("comment", "").lower()
            words = set(comment.split())
            if words & REVERT_KEYWORDS:
                is_reverted = True
                revert_by = rev.get("user", "")
                revert_comment = rev.get("comment", "")
                break

            # Cũng check nếu parentid = revision trước edit (quanh ngược)
            if rev.get("parentid", 0) and rev["parentid"] < rev_new:
                is_reverted = True
                revert_by = rev.get("user", "")
                revert_comment = rev.get("comment", "Overwritten (no revert keyword)")
                break

        return {
            "is_reverted": is_reverted,
            "current_rev": latest_rev,
            "revert_by": revert_by,
            "revert_comment": revert_comment,
            "error": None,
        }

    except requests.RequestException as e:
        return {"is_reverted": False, "current_rev": 0, "revert_by": "",
                "revert_comment": "", "error": str(e)}


def process_final_csv(csv_path: Path):
    """Verify các edits đáng ngờ bằng revert check, lưu thành _05_verified.csv."""
    # Xác định output path
    ts = csv_path.name.replace("_04_final.csv", "")
    output_path = csv_path.parent / f"{ts}_05_verified.csv"
    
    if output_path.exists():
        print(f"   ⏩ Skipping {csv_path.name} (already verified)")
        return output_path

    edits = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        edits = list(reader)

    if not edits:
        return

    # Thêm fields mới
    for col in ["is_reverted", "revert_by", "revert_comment", "verify_error"]:
        if col not in fieldnames:
            fieldnames.append(col)

    checked = 0
    reverted = 0
    errors = 0

    for i, edit in enumerate(edits):
        final_score = float(edit.get("final_score", 0))
        domain = edit.get("domain", "")
        title = edit.get("title", "")
        rev_new = edit.get("revision_new", "0")

        # Chỉ verify edits có score > 0
        if final_score > 0 and domain and title and rev_new != "0":
            result = check_if_reverted(domain, title, int(rev_new))

            edit["is_reverted"] = str(result["is_reverted"])
            edit["revert_by"] = result["revert_by"]
            edit["revert_comment"] = result["revert_comment"][:200]
            edit["verify_error"] = result["error"] or ""

            checked += 1
            if result["error"]:
                errors += 1
            elif result["is_reverted"]:
                reverted += 1
                print(f"   🔄 [{i+1}] REVERTED: {title[:35]} by {result['revert_by']}")
            else:
                print(f"   ✅ [{i+1}] Still live: {title[:35]}")

            time.sleep(REQUEST_DELAY)
        else:
            edit["is_reverted"] = ""
            edit["revert_by"] = ""
            edit["revert_comment"] = ""
            edit["verify_error"] = ""

    # Lưu kết quả
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edits)

    print(f"\n   💾 Saved: {output_path.name}")
    print(f"   📊 Checked: {checked} | Reverted: {reverted} | Errors: {errors}")

    # Đánh giá accuracy
    if checked > 0:
        print_accuracy(edits, checked, reverted)

    return output_path


def print_accuracy(edits: list[dict], checked: int, reverted_count: int):
    """Đánh giá accuracy của hệ thống."""
    print(f"\n   {'='*50}")
    print(f"   📈 ĐÁNH GIÁ HỆ THỐNG")
    print(f"   {'='*50}")

    # Phân loại: TRUE POSITIVE = score > 0 VÀ bị revert
    tp = 0  # True Positive: flagged + reverted
    fp = 0  # False Positive: flagged + NOT reverted
    
    scored_edits = [e for e in edits if float(e.get("final_score", 0)) > 0 and e.get("is_reverted")]
    
    for e in scored_edits:
        if e["is_reverted"] == "True":
            tp += 1
        else:
            fp += 1

    total_flagged = tp + fp
    if total_flagged > 0:
        precision = tp / total_flagged * 100
        print(f"\n   Flagged edits:    {total_flagged}")
        print(f"   True Positive:    {tp} (đã bị revert — đúng là vandalism)")
        print(f"   False Positive:   {fp} (chưa bị revert — có thể sai)")
        print(f"   Precision:        {precision:.1f}%")
    else:
        print(f"\n   Không đủ data để tính accuracy.")

    # Top reverted edits
    reverted_edits = [e for e in edits if e.get("is_reverted") == "True"]
    if reverted_edits:
        print(f"\n   🔄 Edits đã bị revert (= Ground Truth vandalism):")
        for e in reverted_edits[:5]:
            title = e["title"][:30]
            score = float(e.get("final_score", 0))
            risk = e.get("final_risk", "")
            by = e.get("revert_by", "")[:15]
            print(f"      {risk} Score={score:.1f} | {title:30s} | reverted by {by}")


def main():
    print("🔎 Wiki-Stream Revert Verification v2.0")
    print("   Cấu trúc: data/{lang}/processed/*_04_final.csv -> *_05_verified.csv")

    langs = ["en", "vi"]
    for lang in langs:
        folder = DATA_DIR / lang / "processed"
        if not folder.exists():
            continue

        final_files = sorted(folder.glob("*_04_final.csv"))
        if not final_files:
            continue

        print(f"\n{'='*60}")
        print(f"📂 {lang}")
        print(f"{'='*60}")

        for ff in final_files:
            process_final_csv(ff)

    print(f"\n{'='*60}")
    print("✅ Verification hoàn tất!")
    print("   Kết quả lưu trong các file _05_verified.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
