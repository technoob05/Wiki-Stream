"""
🎯 STAGE 08: ATTRIBUTION ENGINE (MASTER)
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_06_llm.csv
Output: data/{lang}/processed/{timestamp}_08_attributed.csv
Goal:   Sử dụng Cosine Similarity để đối soát phong cách viết của 
        edits từ nội dung DIFF thực tế với Database (Stage 07).
────────────────────────────────────────────────────────────
"""
import csv
import json
import re
from pathlib import Path

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
FINGERPRINT_DB = Path(__file__).parent / "vandal_fingerprints.json"
MATCH_THRESHOLD = 0.82  # Ngưỡng tương đồng (Slightly relaxed for Diff)

def calculate_similarity(sig1, sig2):
    """Tính toán độ tương đồng giữa 2 signatures (relative difference)."""
    keys = sig1.keys()
    diffs = []
    for k in keys:
        v1 = sig1[k]
        v2 = sig2.get(k, 0)
        denom = max(v1, v2, 0.0001)
        relative_diff = abs(v1 - v2) / denom
        diffs.append(min(relative_diff, 1.0))
    return 1.0 - (sum(diffs) / len(diffs))

def extract_features(text: str) -> dict:
    """Trích xuất phong cách viết từ nội dung text."""
    if not text or len(text) < 5: return None
    total_chars = len(text)
    words = text.split()
    word_count = len(words)
    punc_count = len(re.findall(r'[^\w\s]', text))
    cap_count = len(re.findall(r'[A-Z]', text))
    digit_count = len(re.findall(r'\d', text))
    exclaim_ratio = text.count("!") / total_chars
    markup_count = text.count("[") + text.count("]") + text.count("{") + text.count("}")

    return {
        "punc_density": round(punc_count / total_chars, 4),
        "cap_ratio": round(cap_count / total_chars, 4),
        "avg_word_len": round(total_chars / word_count, 2) if word_count > 0 else 0,
        "digit_ratio": round(digit_count / total_chars, 4),
        "exclaim_ratio": round(exclaim_ratio, 4),
        "markup_ratio": round(markup_count / total_chars, 4)
    }

def load_fingerprints():
    if FINGERPRINT_DB.exists():
        with open(FINGERPRINT_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def process_attribution():
    print("🎯 Stage 08: Attribution Engine Running...")
    fingerprints = load_fingerprints()
    if not fingerprints:
        print("   ⚠️ Fingerprint database not found. Run Stage 07 first.")
        return

    for lang_dir in DATA_DIR.glob("*"):
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
        
        for csv_file in proc_dir.glob("*_06_llm.csv"):
            ts = csv_file.name.replace("_06_llm.csv", "")
            output_path = proc_dir / f"{ts}_08_attributed.csv"
            
            if output_path.exists():
                print(f"   ⏩ Skipping {csv_file.name} (already attributed)")
                continue

            print(f"   🕵️ Matching: {csv_file.name}")
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames)
                edits = list(reader)

            for col in ["fingerprint_match", "fingerprint_similarity", "is_serial_vandal"]:
                if col not in fieldnames: fieldnames.append(col)

            match_count = 0
            for edit in edits:
                # Chỉ soi những edit bị LLM gắn cờ VANDALISM/SUSPICIOUS hoặc Rule Score cao
                score = float(edit.get("rule_score", 0))
                is_flagged = edit.get("llm_classification") in ["VANDALISM", "SUSPICIOUS"] or score > 2.0
                
                if not is_flagged:
                    edit["fingerprint_match"] = ""
                    edit["fingerprint_similarity"] = 0
                    edit["is_serial_vandal"] = "False"
                    continue

                # Sử dụng cả Added + Removed content để lấy signature
                content = (edit.get("diff_added", "") + " " + edit.get("diff_removed", "")).strip()
                features = extract_features(content)
                
                if not features:
                    edit["fingerprint_match"] = ""
                    edit["fingerprint_similarity"] = 0
                    edit["is_serial_vandal"] = "False"
                    continue

                best_match, max_sim = None, 0
                for name, data in fingerprints.items():
                    sim = calculate_similarity(features, data["signature"])
                    if sim > max_sim:
                        max_sim, best_match = sim, name
                
                if max_sim > MATCH_THRESHOLD:
                    edit["fingerprint_match"] = best_match
                    edit["fingerprint_similarity"] = round(max_sim, 3)
                    edit["is_serial_vandal"] = "True"
                    match_count += 1
                else:
                    edit["fingerprint_match"] = ""
                    edit["fingerprint_similarity"] = round(max_sim, 3)
                    edit["is_serial_vandal"] = "False"

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(edits)
            
            print(f"   ✅ Done: {lang_dir.name} | Found {match_count} matches.")

if __name__ == '__main__':
    process_attribution()
