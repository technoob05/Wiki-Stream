"""
🧪 STAGE 04: STATISTICAL NLP ANALYSIS
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_03_diff.csv
Output: data/{lang}/processed/{timestamp}_04_final.csv
Goal:   Tính toán 7+ đặc trưng NLP (Gibberish, Punc density, Caps ratio)
        và tổng hợp thành NLP Score để bổ trợ cho Rule Engine.
────────────────────────────────────────────────────────────
"""

import csv
import re
import math
import zlib
from pathlib import Path
from collections import Counter

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"

# Trọng số kết hợp
RULE_WEIGHT = 0.4
NLP_WEIGHT = 0.6

# Danh sách từ thô tục mở rộng (EN + VI)
PROFANITY_SET = {
    # English
    "fuck", "fucking", "fucked", "shit", "shitting", "ass", "asshole",
    "dick", "penis", "vagina", "bitch", "nigger", "nigga", "faggot",
    "retard", "retarded", "cunt", "whore", "slut", "bastard",
    "poop", "boob", "boobs", "sexy", "porn", "nazi",
    "stupid", "idiot", "loser", "suck", "sucks",
    "die", "kill", "murder", "hate",
    # Vietnamese
    "đụ", "địt", "lồn", "cặc", "đéo", "đĩ", "ngu", "khốn",
    "mẹ mày", "con đĩ", "thằng ngu", "đồ chó", "chết đi",
}

# Từ khóa Wikipedia markup
WIKI_MARKUP_PATTERNS = [
    r"\[\[.*?\]\]",        # Internal links [[Page]]
    r"\{\{.*?\}\}",        # Templates {{template}}
    r"<ref[^>]*>.*?</ref>", # References
    r"<ref[^>]*/>",         # Self-closing refs
    r"\|",                  # Table/template pipes
    r"'''",                 # Bold
    r"''",                  # Italic
    r"==+",                 # Section headers
    r"\*",                  # List items
    r"#",                   # Numbered lists
]


# ══════════════════════════════════════════════════════════════
# NLP Features
# ══════════════════════════════════════════════════════════════

def feat_profanity_density(text: str) -> tuple[float, str]:
    """Tỷ lệ từ thô tục trong diff text."""
    if not text.strip():
        return 0.0, ""
    words = text.lower().split()
    if not words:
        return 0.0, ""
    found = [w for w in words if any(p in w for p in PROFANITY_SET)]
    density = len(found) / len(words)
    note = f"profanity_words:{','.join(found[:5])}" if found else ""
    return min(density * 20, 5.0), note  # Scale: 5% profanity = score 1.0


def feat_gibberish_score(text: str) -> tuple[float, str]:
    """Phát hiện text rác/gibberish bằng compression ratio.
    
    Text có ý nghĩa → nén tốt (ratio ~0.3-0.5)
    Text rác (aaaa, random) → nén rất tốt (<0.2) hoặc rất tệ (>0.8)
    """
    if len(text) < 20:
        return 0.0, ""

    original = len(text.encode("utf-8"))
    compressed = len(zlib.compress(text.encode("utf-8")))
    ratio = compressed / original

    # Text quá lặp lại (ratio < 0.15) = rác
    if ratio < 0.15:
        return 3.0, f"gibberish:very_repetitive(ratio={ratio:.2f})"
    # Text hơi lặp (ratio < 0.25) = đáng nghi
    elif ratio < 0.25:
        return 1.0, f"gibberish:repetitive(ratio={ratio:.2f})"
    return 0.0, ""


def feat_uppercase_abuse(text: str) -> tuple[float, str]:
    """Phát hiện lạm dụng chữ hoa (GÀO THÉT)."""
    if not text.strip():
        return 0.0, ""
    alpha = [c for c in text if c.isalpha()]
    if len(alpha) < 10:
        return 0.0, ""
    upper_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
    if upper_ratio > 0.7:
        return 2.5, f"uppercase_abuse:{upper_ratio:.0%}"
    elif upper_ratio > 0.5:
        return 1.0, f"uppercase_high:{upper_ratio:.0%}"
    return 0.0, ""


def feat_repeated_sequences(text: str) -> tuple[float, str]:
    """Phát hiện chuỗi ký tự lặp lại (hahaha, aaaa, !!!!)."""
    if not text:
        return 0.0, ""
    matches = re.findall(r"(.{1,3})\1{3,}", text)
    if matches:
        examples = [m[:5] for m in matches[:3]]
        return 2.0, f"repeated:{'|'.join(examples)}"
    return 0.0, ""


def feat_markup_destruction(diff_added: str, diff_removed: str) -> tuple[float, str]:
    """Phát hiện xóa markup Wikipedia (references, links, templates).
    Vandal thường xóa references để giấu nguồn, hoặc xóa internal links."""
    
    def count_markup(text):
        total = 0
        for pattern in WIKI_MARKUP_PATTERNS:
            total += len(re.findall(pattern, text))
        return total

    removed_markup = count_markup(diff_removed)
    added_markup = count_markup(diff_added)

    # Nếu xóa nhiều markup hơn thêm → đáng nghi
    if removed_markup > 5 and added_markup < removed_markup * 0.3:
        score = min((removed_markup - added_markup) * 0.3, 4.0)
        return score, f"markup_destruction:removed={removed_markup},added={added_markup}"
    return 0.0, ""


def feat_external_links_spam(text: str) -> tuple[float, str]:
    """Phát hiện spam external links."""
    urls = re.findall(r"https?://[^\s\]]+", text)
    if len(urls) >= 3:
        return 2.5, f"link_spam:{len(urls)}_urls"
    elif len(urls) >= 1:
        # Kiểm tra suspicious domains
        suspicious = [u for u in urls if any(d in u.lower() for d in 
                      [".xyz", ".tk", ".ml", "bit.ly", "tinyurl", "goo.gl",
                       "pastebin", "discord.gg"])]
        if suspicious:
            return 3.0, f"suspicious_links:{','.join(suspicious[:2])}"
    return 0.0, ""


def feat_sentiment_shift(diff_added: str, diff_removed: str) -> tuple[float, str]:
    """Phát hiện thay đổi giọng văn đáng nghi.
    Đơn giản: đếm các từ cảm tính mạnh được thêm vào."""
    
    negative_words = {
        "terrible", "horrible", "worst", "evil", "corrupt", "fraud", "liar",
        "criminal", "terrorist", "propaganda", "hoax", "conspiracy",
        "tồi", "tệ", "xấu", "dối", "gian", "lừa", "phản động",
    }
    pov_words = {
        "obviously", "clearly", "everyone knows", "undeniably", "best ever",
        "greatest", "most important", "legendary", "disgusting",
        "rõ ràng là", "ai cũng biết", "tuyệt vời nhất",
    }

    added_lower = diff_added.lower()
    found_neg = [w for w in negative_words if w in added_lower]
    found_pov = [w for w in pov_words if w in added_lower]

    score = 0.0
    notes = []
    if found_neg:
        score += min(len(found_neg) * 0.5, 2.0)
        notes.append(f"negative:{','.join(found_neg[:3])}")
    if found_pov:
        score += min(len(found_pov) * 0.7, 2.0)
        notes.append(f"pov:{','.join(found_pov[:3])}")

    return score, "; ".join(notes)


# ══════════════════════════════════════════════════════════════
# NEW: Structural NLP Features (align with LLM detections)
# ══════════════════════════════════════════════════════════════

def feat_content_blanking(edit: dict) -> tuple[float, str]:
    """Phát hiện blanking/mass deletion dựa trên length delta.
    LLM thường phát hiện cái này, nhưng NLP cũ bỏ sót."""
    old_len = int(edit.get("length_old", 0) or 0)
    new_len = int(edit.get("length_new", 0) or 0)
    
    if old_len < 100:
        return 0.0, ""
    
    delta_ratio = (old_len - new_len) / old_len if old_len > 0 else 0
    
    # Xóa >80% nội dung = blanking
    if delta_ratio >= 0.8:
        return 4.0, f"blanking:{delta_ratio:.0%}_removed({old_len}->{new_len})"
    # Xóa >50% = mass deletion
    elif delta_ratio >= 0.5:
        return 2.0, f"mass_deletion:{delta_ratio:.0%}_removed"
    # Xóa >30% = significant removal
    elif delta_ratio >= 0.3:
        return 0.8, f"large_removal:{delta_ratio:.0%}_removed"
    return 0.0, ""


def feat_added_removed_ratio(diff_added: str, diff_removed: str) -> tuple[float, str]:
    """Tỷ lệ nội dung thêm vs xóa. 
    Vandal thường: xóa nhiều + thêm ít (hoặc ngược lại: thêm rác, xóa ít)."""
    added_len = len(diff_added.strip())
    removed_len = len(diff_removed.strip())
    
    if added_len + removed_len < 50:
        return 0.0, ""
    
    # Case 1: Xóa rất nhiều, thêm rất ít → blanking/deletion attack
    if removed_len > 200 and added_len < removed_len * 0.1:
        return 2.0, f"delete_heavy:added={added_len},removed={removed_len}"
    
    # Case 2: Thêm rất nhiều, xóa rất ít → spam/hoax insertion
    if added_len > 500 and removed_len < added_len * 0.05:
        # Check if added content looks like spam (low entropy)
        return 0.8, f"insert_heavy:added={added_len},removed={removed_len}"
    
    return 0.0, ""


def feat_hoax_test_patterns(diff_added: str) -> tuple[float, str]:
    """Phát hiện hoax/test edits mà LLM thường bắt nhưng NLP cũ bỏ sót."""
    if not diff_added or len(diff_added) < 5:
        return 0.0, ""
    
    text_lower = diff_added.lower().strip()
    
    # Test edits
    test_patterns = [
        r"^test\b", r"^testing\b", r"^this is a test",
        r"^hello\b", r"^hi\b", r"^hey\b",
        r"^asdf", r"^qwerty", r"^1234",
    ]
    for pattern in test_patterns:
        if re.search(pattern, text_lower):
            return 2.5, f"test_edit:{text_lower[:30]}"
    
    # Hoax patterns (people claiming fake things)
    hoax_patterns = [
        r"\bis (?:secretly|actually|really) (?:a|an)\b",
        r"\bwas born in \d{4}\b.*\bdied\b",  # fake bio edits
        r"\bis dead\b", r"\bhas died\b",
        r"\bfake\b.*\bnews\b", r"\bnot real\b",
    ]
    for pattern in hoax_patterns:
        if re.search(pattern, text_lower):
            return 2.0, f"hoax_pattern:{pattern[:30]}"
    
    # Self-promotion / POV insertion patterns
    promo_patterns = [
        r"\b(?:best|greatest|most famous|legendary|iconic)\s+(?:\w+\s+){0,3}(?:in the world|ever|of all time)\b",
        r"\baccording to (?:many|most|some) (?:experts|people|sources)\b",
    ]
    for pattern in promo_patterns:
        if re.search(pattern, text_lower):
            return 1.5, f"promo_pov:{text_lower[:40]}"
    
    return 0.0, ""


def feat_edit_entropy(diff_added: str) -> tuple[float, str]:
    """Entropy thấp = nội dung lặp/rác. Entropy cao = nội dung đa dạng.
    Vandal thường có entropy rất thấp (repetitive) hoặc rất cao (random chars)."""
    if len(diff_added) < 30:
        return 0.0, ""
    
    # Character frequency
    freq = Counter(diff_added.lower())
    total = sum(freq.values())
    
    entropy = 0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    
    # Very low entropy (<2.5) = repetitive vandalism
    if entropy < 2.0 and len(diff_added) > 50:
        return 2.0, f"low_entropy:{entropy:.2f}(repetitive)"
    elif entropy < 2.5 and len(diff_added) > 100:
        return 1.0, f"low_entropy:{entropy:.2f}"
    
    return 0.0, ""


# ══════════════════════════════════════════════════════════════
# Engine chính
# ══════════════════════════════════════════════════════════════

def analyze_edit(edit: dict) -> tuple[float, list[str]]:
    """Chạy tất cả NLP features trên 1 edit, trả về (nlp_score, notes)."""
    diff_added = edit.get("diff_added", "")
    diff_removed = edit.get("diff_removed", "")
    combined_text = diff_added + " " + diff_removed

    total = 0.0
    notes = []

    features = [
        # Original 7 features (linguistic)
        feat_profanity_density(diff_added),
        feat_gibberish_score(diff_added),
        feat_uppercase_abuse(diff_added),
        feat_repeated_sequences(diff_added),
        feat_markup_destruction(diff_added, diff_removed),
        feat_external_links_spam(diff_added),
        feat_sentiment_shift(diff_added, diff_removed),
        # NEW 4 features (structural — align with LLM)
        feat_content_blanking(edit),
        feat_added_removed_ratio(diff_added, diff_removed),
        feat_hoax_test_patterns(diff_added),
        feat_edit_entropy(diff_added),
    ]

    for score, note in features:
        if score > 0:
            total += score
            if note:
                notes.append(note)

    return round(total, 1), notes


def classify_final(score: float) -> str:
    """Phân loại cuối cùng dựa trên final_score."""
    if score >= 7.0:
        return "🔴 CRITICAL"
    elif score >= 4.0:
        return "🟠 HIGH"
    elif score >= 2.0:
        return "🟡 MEDIUM"
    elif score > 0:
        return "🔵 LOW"
    else:
        return "⚪ CLEAN"


def process_enriched_csv(csv_path: Path):
    """Đọc enriched CSV, chạy NLP analysis, lưu thành _04_final.csv."""
    # Xác định output path
    ts = csv_path.name.replace("_03_enriched.csv", "")
    output_path = csv_path.parent / f"{ts}_04_final.csv"
    
    if output_path.exists():
        print(f"   ⏩ Skipping {csv_path.name} (already analyzed)")
        return output_path

    edits = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        edits = list(reader)

    if not edits:
        return

    # Thêm fields mới
    for col in ["nlp_score", "nlp_notes", "final_score", "final_risk"]:
        if col not in fieldnames:
            fieldnames.append(col)

    analyzed = 0
    for edit in edits:
        rule_score = float(edit.get("rule_score", 0))
        diff_added = edit.get("diff_added", "")
        diff_removed = edit.get("diff_removed", "")

        if diff_added or diff_removed:
            nlp_score, nlp_notes = analyze_edit(edit)
            analyzed += 1
        else:
            nlp_score = 0.0
            nlp_notes = []

        # Hybrid score: kết hợp rule + NLP
        final = round(rule_score * RULE_WEIGHT + nlp_score * NLP_WEIGHT, 1)

        edit["nlp_score"] = nlp_score
        edit["nlp_notes"] = "; ".join(nlp_notes)
        edit["final_score"] = final
        edit["final_risk"] = classify_final(final)

    # Lưu kết quả
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edits)

    print(f"   💾 Saved: {output_path.name}")
    print(f"   📊 NLP analyzed: {analyzed} edits")

    # Thống kê
    print_stats(edits)
    return output_path


def print_stats(edits: list[dict]):
    """In thống kê phân tích."""
    total = len(edits)
    if total == 0:
        return

    # Final risk distribution
    risk_counts = Counter(e["final_risk"] for e in edits)
    print(f"\n   📊 Final Risk Distribution:")
    for level in ["🔴 CRITICAL", "🟠 HIGH", "🟡 MEDIUM", "🔵 LOW", "⚪ CLEAN"]:
        count = risk_counts.get(level, 0)
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"      {level:15s} {count:4d} ({pct:5.1f}%) {bar}")

    # NLP features triggered
    all_notes = []
    for e in edits:
        notes = e.get("nlp_notes", "")
        if notes:
            all_notes.extend(notes.split("; "))
    note_types = Counter(n.split(":")[0] for n in all_notes if ":" in n)
    if note_types:
        print(f"\n   🧠 NLP Features Triggered:")
        for feat, count in note_types.most_common(10):
            print(f"      {feat:25s} {count:4d} ({count/total*100:.1f}%)")

    # Top suspicious (by final_score)
    suspicious = sorted(edits, key=lambda e: float(e.get("final_score", 0)), reverse=True)[:7]
    print(f"\n   🔍 Top edits đáng ngờ nhất (Hybrid Score):")
    for e in suspicious:
        final = float(e.get("final_score", 0))
        if final == 0:
            break
        rule = float(e.get("rule_score", 0))
        nlp = float(e.get("nlp_score", 0))
        title = e["title"][:30]
        user = e["user"][:15]
        notes = e.get("nlp_notes", "")[:45]
        print(f"      {e['final_risk']} Final={final:4.1f} (R={rule:.1f}+N={nlp:.1f}) | {title:30s} | {user:15s} | {notes}")


def main():
    print("🧠 Wiki-Stream NLP Analysis v2.0")
    print("   Cấu trúc: data/{lang}/processed/*_03_enriched.csv -> *_04_final.csv")

    langs = ["en", "vi"]
    for lang in langs:
        folder = DATA_DIR / lang / "processed"
        if not folder.exists():
            continue

        enriched_files = sorted(folder.glob("*_03_enriched.csv"))
        if not enriched_files:
            continue

        print(f"\n{'='*60}")
        print(f"📂 {lang}")
        print(f"{'='*60}")

        for ef in enriched_files:
            process_enriched_csv(ef)

    print(f"\n{'='*60}")
    print("✅ Xong! Kết quả final lưu trong các file _04_final.csv")
    print("   → Bước tiếp: 05_revert_check.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
