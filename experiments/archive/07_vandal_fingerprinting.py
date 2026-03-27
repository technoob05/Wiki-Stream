"""
🕵️ STAGE 07: VANDAL FINGERPRINTING
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_06_llm.csv
Output: vandal_fingerprints.json (Fingerprint Database)
Goal:   Trích xuất "Dấu vân tay số" (Stylometry) từ các phá hoại viên 
        đã được xác định để truy vết xuyên IP.
────────────────────────────────────────────────────────────
"""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict
DATA_DIR = Path(__file__).parent / "data"
FINGERPRINT_DB = Path(__file__).parent / "vandal_fingerprints.json"

def extract_features(text: str) -> dict:
    """Trích xuất đặc trưng phong cách viết (Stylometry)."""
    if not text:
        return {
            "punc_density": 0, "cap_ratio": 0, "avg_word_len": 0,
            "digit_ratio": 0, "exclaim_count": 0, "markup_density": 0
        }
    
    total_chars = len(text)
    words = text.split()
    word_count = len(words)
    
    # Dấu câu đặc biệt
    exclaim_count = text.count("!")
    q_count = text.count("?")
    punc_count = len(re.findall(r'[^\w\s]', text))
    
    # Chữ hoa
    cap_count = len(re.findall(r'[A-Z]', text))
    
    # Chữ số
    digit_count = len(re.findall(r'\d', text))
    
    # Markup patterns (links, brackets)
    markup_count = text.count("[") + text.count("]") + text.count("{") + text.count("}")
    
    return {
        "punc_density": round(punc_count / total_chars, 4) if total_chars > 0 else 0,
        "cap_ratio": round(cap_count / total_chars, 4) if total_chars > 0 else 0,
        "avg_word_len": round(total_chars / word_count, 2) if word_count > 0 else 0,
        "digit_ratio": round(digit_count / total_chars, 4) if total_chars > 0 else 0,
        "exclaim_ratio": round(exclaim_count / total_chars, 4) if total_chars > 0 else 0,
        "markup_ratio": round(markup_count / total_chars, 4) if total_chars > 0 else 0
    }

def generate_fingerprints():
    """Đọc dữ liệu LLM-verified và tạo signatures cho từng vandal."""
    print("🕵️ Đang tạo Vandal Fingerprints...")
    
    # Gom dữ liệu từ tất cả các file _06_llm.csv
    vandal_data = defaultdict(list)
    
    for lang_dir in DATA_DIR.glob("*"):
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
        
        for csv_file in proc_dir.glob("*_06_llm.csv"):
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("llm_classification") == "VANDALISM":
                        # Kết hợp Text Added + Text Removed để lấy phong cách
                        full_content = (row.get("diff_added", "") + " " + row.get("diff_removed", "")).strip()
                        features = extract_features(full_content)
                        vandal_data[row["user"]].append(features)
    
    if not vandal_data:
        print("   ⚠️ Không tìm thấy dữ liệu Vandalism đã xác nhận.")
        return

    # Trung bình hóa các đặc trưng cho mỗi user
    fingerprints = {}
    for user, feature_list in vandal_data.items():
        avg_features = {}
        for key in feature_list[0].keys():
            avg_features[key] = round(sum(f[key] for f in feature_list) / len(feature_list), 4)
        
        fingerprints[user] = {
            "signature": avg_features,
            "sample_count": len(feature_list),
            "last_seen_user": user
        }
        
    # Lưu vào JSON
    with open(FINGERPRINT_DB, "w", encoding="utf-8") as f:
        json.dump(fingerprints, f, indent=4, ensure_ascii=False)
    
    print(f"   ✅ Đã tạo {len(fingerprints)} signatures trong {FINGERPRINT_DB.name}")

if __name__ == "__main__":
    generate_fingerprints()
