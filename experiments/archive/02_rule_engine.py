"""
🛡️ STAGE 02: RULE-BASED HEURISTICS ENGINE
────────────────────────────────────────────────────────────
Input:  data/{lang}/raw/{timestamp}.csv (Stage 1 Output)
Output: data/{lang}/processed/{timestamp}_02_scored.csv
Goal:   Áp dụng 13+ luật chấm điểm (Profanity, Blanking, Size, Caps)
        kết hợp Reputation Feedback Loop từ đợt phân tích trước.
────────────────────────────────────────────────────────────
"""

import csv
import re
import zlib
from datetime import datetime
from pathlib import Path
from collections import Counter
import json # Added for reputation loading

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPUTATION_FILE = Path(__file__).parent / "reputation.json"

# Trọng số thưởng/phạt cho Reputation
BONUS_SUSPECT_USER = 2.0
BONUS_HOTSPOT_ARTICLE = 1.5

# Danh sách từ khóa đáng ngờ (mở rộng được)
PROFANITY_WORDS = {
    # English
    "fuck", "shit", "ass", "dick", "penis", "vagina", "bitch", "nigger",
    "faggot", "retard", "cunt", "whore", "slut", "bastard", "damn",
    "poop", "butt", "boob", "sexy", "porn", "nazi", "stupid", "idiot",
    "loser", "suck", "haha", "lol", "lmao",
    # Vietnamese
    "đụ", "địt", "lồn", "cặc", "đéo", "đĩ", "chó", "ngu", "khốn",
    "mẹ mày", "con đĩ", "thằng ngu",
}

SPAM_PATTERNS = [
    r"https?://\S+",           # URLs trong edit comment
    r"\b\d{10,}\b",            # Chuỗi số dài (số điện thoại, spam)
    r"(.)\1{4,}",              # Ký tự lặp lại 5+ lần (aaaaa, !!!!!!)
    r"[A-Z]{10,}",             # Chữ hoa liên tục 10+ ký tự (GÀO THÉT)
]

REVERT_KEYWORDS = {"revert", "undo", "undid", "rv", "rollback", "reverted"}


# ══════════════════════════════════════════════════════════════
# Các Rules (mỗi rule trả về (score, label) hoặc None)
# ══════════════════════════════════════════════════════════════

def rule_content_blanking(edit: dict) -> tuple[float, str] | None:
    """Xóa >80% nội dung bài viết."""
    old, new = edit["length_old"], edit["length_new"]
    if old > 100 and new < old * 0.2:
        return (5.0, "content_blanking")
    return None


def rule_large_deletion(edit: dict) -> tuple[float, str] | None:
    """Xóa >5000 chars."""
    delta = edit["length_new"] - edit["length_old"]
    if delta < -5000:
        return (3.0, "large_deletion")
    return None


def rule_large_addition(edit: dict) -> tuple[float, str] | None:
    """Thêm >10000 chars (có thể spam/copy-paste)."""
    delta = edit["length_new"] - edit["length_old"]
    if delta > 10000:
        return (1.5, "large_addition")
    return None


def rule_empty_comment(edit: dict) -> tuple[float, str] | None:
    """Comment trống (không giải thích lý do)."""
    if not edit["comment"].strip():
        return (1.0, "empty_comment")
    return None


def rule_empty_comment_big_change(edit: dict) -> tuple[float, str] | None:
    """Comment trống VÀ thay đổi >500 chars → đáng ngờ hơn."""
    delta = abs(edit["length_new"] - edit["length_old"])
    if not edit["comment"].strip() and delta > 500:
        return (2.5, "empty_comment_big_change")
    return None


def rule_profanity(edit: dict) -> tuple[float, str] | None:
    """Comment hoặc title chứa từ thô tục (word boundary matching)."""
    text = (edit["comment"] + " " + edit["title"]).lower()
    found = []
    for w in PROFANITY_WORDS:
        # Dùng word boundary để tránh false positive (ví dụ: 'ngu' trong 'Hungarian')
        if re.search(r"\b" + re.escape(w) + r"\b", text):
            found.append(w)
    if found:
        return (4.0, f"profanity:{','.join(found[:3])}")
    return None


def rule_spam_patterns(edit: dict) -> tuple[float, str] | None:
    """Comment chứa URL spam, chuỗi số dài, ký tự lặp lại, hoặc GÀO THÉT."""
    text = edit["comment"]
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text):
            return (2.0, "spam_pattern")
    return None


def rule_revert_keyword(edit: dict) -> tuple[float, str] | None:
    """Comment chứa từ khóa revert/undo (dấu hiệu edit war)."""
    words = set(edit["comment"].lower().split())
    found = words & REVERT_KEYWORDS
    if found:
        return (1.0, f"revert:{','.join(found)}")
    return None


def rule_anonymous_user(edit: dict) -> tuple[float, str] | None:
    """User là IP address (anonymous, 10-20x nguy cơ)."""
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    ipv6_pattern = re.compile(r"^[0-9a-fA-F:]+$")
    user = edit["user"]
    if ip_pattern.match(user) or (ipv6_pattern.match(user) and ":" in user):
        return (2.0, "anonymous_ip")
    return None


def rule_uppercase_ratio(edit: dict) -> tuple[float, str] | None:
    """Comment có tỷ lệ chữ hoa bất thường (>60% trên 10+ ký tự)."""
    text = edit["comment"]
    alpha = [c for c in text if c.isalpha()]
    if len(alpha) >= 10:
        upper_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
        if upper_ratio > 0.6:
            return (1.5, f"uppercase_ratio:{upper_ratio:.0%}")
    return None


def rule_repeated_chars(edit: dict) -> tuple[float, str] | None:
    """Comment hoặc title có chuỗi ký tự lặp lại 5+ lần."""
    text = edit["comment"] + " " + edit["title"]
    match = re.search(r"(.)\1{4,}", text)
    if match:
        return (2.5, f"repeated_chars:'{match.group()[:10]}'")
    return None


def rule_digit_ratio(edit: dict) -> tuple[float, str] | None:
    """Comment có tỷ lệ số/chữ bất thường (>50% trên 10+ ký tự)."""
    text = edit["comment"]
    alnum = [c for c in text if c.isalnum()]
    if len(alnum) >= 10:
        digit_ratio = sum(1 for c in alnum if c.isdigit()) / len(alnum)
        if digit_ratio > 0.5:
            return (1.0, f"high_digit_ratio:{digit_ratio:.0%}")
    return None


def rule_minor_but_big(edit: dict) -> tuple[float, str] | None:
    """Đánh dấu 'minor' nhưng thay đổi >1000 chars (cố ý che giấu)."""
    if edit["minor"] and abs(edit["length_new"] - edit["length_old"]) > 1000:
        return (2.0, "minor_but_big_change")
    return None


# Danh sách tất cả rules
ALL_RULES = [
    rule_content_blanking,
    rule_large_deletion,
    rule_large_addition,
    rule_empty_comment,
    rule_empty_comment_big_change,
    rule_profanity,
    rule_spam_patterns,
    rule_revert_keyword,
    rule_anonymous_user,
    rule_uppercase_ratio,
    rule_repeated_chars,
    rule_digit_ratio,
    rule_minor_but_big,
]


# ══════════════════════════════════════════════════════════════
# Engine chính
# ══════════════════════════════════════════════════════════════

def load_reputation():
    """Load dữ liệu từ bước Intelligence Aggregator."""
    if REPUTATION_FILE.exists():
        try:
            with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"suspect_users": [], "hotspot_articles": []}


def score_edit(edit: dict, reputation: dict) -> tuple[float, list[str]]:
    """Chạy tất cả rules trên 1 edit, trả về (total_score, matched_rules).
    Cập nhật để tính toán điểm số dựa trên rules + reputation."""
    total = 0.0
    matched = []

    # 1. Check Reputation (New VIP Feature)
    if edit.get("user") in reputation.get("suspect_users", []):
        total += BONUS_SUSPECT_USER
        matched.append("reputation_suspect_user")
    
    if edit.get("title") in reputation.get("hotspot_articles", []):
        total += BONUS_HOTSPOT_ARTICLE
        matched.append("reputation_hotspot_article")

    # 2. Check Standard Rules
    for rule_fn in ALL_RULES:
        result = rule_fn(edit)
        if result:
            score, label = result
            total += score
            matched.append(label)
    return round(total, 1), matched


def classify_risk(score: float) -> str:
    """Phân loại mức nguy hiểm."""
    if score >= 6.0:
        return "🔴 CRITICAL"
    elif score >= 3.0:
        return "🟠 HIGH"
    elif score >= 1.5:
        return "🟡 MEDIUM"
    elif score > 0:
        return "🔵 LOW"
    else:
        return "⚪ CLEAN"


def load_csv(path: Path) -> list[dict]:
    """Đọc CSV và chuyển đổi kiểu dữ liệu."""
    edits = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["length_old"] = int(row.get("length_old", 0) or 0)
            row["length_new"] = int(row.get("length_new", 0) or 0)
            row["minor"] = row.get("minor", "").lower() == "true"
            row["bot"] = row.get("bot", "").lower() == "true"
            edits.append(row)
    return edits


def process_domain_folder(domain_folder: Path, reputation: dict):
    """Xử lý các file CSV raw trong một domain folder."""
    raw_dir = domain_folder / "raw"
    proc_dir = domain_folder / "processed"
    proc_dir.mkdir(exist_ok=True)

    raw_files = sorted(raw_dir.glob("*.csv"))
    if not raw_files:
        return

    print(f"\n{'='*60}")
    print(f"📂 {domain_folder.name}")
    print(f"{'='*60}")

    for rf in raw_files:
        # Tên file output dựa trên timestamp của file raw
        ts = rf.stem
        output_path = proc_dir / f"{ts}_02_scored.csv"

        if output_path.exists():
            print(f"   ⏩ Skipping {rf.name} (already scored)")
            continue

        print(f"\n📄 {rf.name} — Scoring...")
        
        edits = []
        with open(rf, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            edits = list(reader)

        if not edits:
            print(f"   ⚠️ No edits found in {rf.name}")
            continue

        # Convert types for rules
        for edit in edits:
            edit["length_old"] = int(edit.get("length_old", 0) or 0)
            edit["length_new"] = int(edit.get("length_new", 0) or 0)
            edit["minor"] = edit.get("minor", "").lower() == "true"
            edit["bot"] = edit.get("bot", "").lower() == "true"

        # Thêm fields score
        if "rule_score" not in fieldnames:
            fieldnames.append("rule_score")
        if "matched_rules" not in fieldnames:
            fieldnames.append("matched_rules")
        if "risk_level" not in fieldnames: # Added risk_level to fieldnames
            fieldnames.append("risk_level")

        for edit in edits:
            sc, mt = score_edit(edit, reputation)
            edit["rule_score"] = round(sc, 1) # Changed to 1 decimal place as per original score_edit
            edit["matched_rules"] = "; ".join(mt) # Changed to "; " as per original
            edit["risk_level"] = classify_risk(sc) # Added risk_level

        # Lưu kết quả
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edits)
        print(f"   💾 Saved: {output_path.name}")

        # Thống kê
        print_stats(edits) # Pass edits (which now contain results)


def print_stats(results: list[dict]):
    """In thống kê kết quả scoring."""
    total = len(results)
    if total == 0:
        return

    # Phân bố risk
    risk_counts = Counter(r["risk_level"] for r in results)
    print(f"\n   📊 Phân bố mức nguy hiểm:")
    for level in ["🔴 CRITICAL", "🟠 HIGH", "🟡 MEDIUM", "🔵 LOW", "⚪ CLEAN"]:
        count = risk_counts.get(level, 0)
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"      {level:15s} {count:4d} ({pct:5.1f}%) {bar}")

    # Top matched rules
    all_rules = []
    for r in results:
        if r["matched_rules"]:
            all_rules.extend(r["matched_rules"].split("; "))
    rule_counts = Counter(all_rules)
    print(f"\n   🎯 Top rules triggered:")
    for rule, count in rule_counts.most_common(10):
        print(f"      {rule:35s} {count:4d} ({count/total*100:.1f}%)")

    # Top nghi ngờ nhất
    suspicious = sorted(results, key=lambda r: r["rule_score"], reverse=True)[:5]
    print(f"\n   🔍 Top 5 edits đáng ngờ nhất:")
    for r in suspicious:
        score = r["rule_score"]
        if score == 0:
            break
        title = r["title"][:35]
        user = r["user"][:18]
        delta = r["length_new"] - r["length_old"]
        rules = r["matched_rules"][:50]
        print(f"      {r['risk_level']} Score={score:4.1f} | {title:35s} | {user:18s} | {delta:+6d} | {rules}")


def main():
    print("🧠 Wiki-Stream Rule Engine v2.1 (Feedback Loop Enabled)")
    print(f"   Cấu trúc: data/{{lang}}/raw/*.csv -> data/{{lang}}/processed/*_02_scored.csv")
    
    reputation = load_reputation()
    if reputation.get("suspect_users") or reputation.get("hotspot_articles"):
        print(f"   📡 Loaded reputation data: {len(reputation['suspect_users'])} suspects, {len(reputation['hotspot_articles'])} hotspots")

    langs = ["en", "vi"]
    
    found_any = False
    for lang in langs:
        lang_folder = DATA_DIR / lang
        if lang_folder.exists():
            process_domain_folder(lang_folder, reputation)
            found_any = True

    if not found_any:
        print(f"\n⚠️ Không tìm thấy folder en/vi trong {DATA_DIR}")
        print("   Chạy 01_collect_data.py trước!")
        return

    print(f"\n{'='*60}")
    print("✅ Xong! Kết quả lưu trong processed/ folder bài bản.")
    print("   → Bước tiếp: 03_diff_fetcher.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
