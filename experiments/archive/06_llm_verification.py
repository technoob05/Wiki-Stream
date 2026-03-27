"""
🤖 STAGE 06: LLM VERIFICATION & ENSEMBLE SCORING
────────────────────────────────────────────────────────────
Input:  {timestamp}_04_final.csv (Stage 4 Output)
Output: {timestamp}_06_llm.csv
Goal:   Sử dụng Gemma 2 (Local) để xác thực ngữ nghĩa và tính toán 
        Ensemble Confidence Score (%) dựa trên 3 tầng (Heuristic, NLP, LLM).
────────────────────────────────────────────────────────────
"""

import csv
import json
import time
import re
from pathlib import Path

import requests

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2:latest"

# Chỉ gửi edits có final_score >= threshold cho LLM (tiết kiệm GPU)
SCORE_THRESHOLD = 0.0  # Gửi tất cả edits có điểm > 0
REQUEST_TIMEOUT = 60   # seconds
MAX_DIFF_CHARS = 800   # Giới hạn diff gửi cho LLM để tránh quá dài


SYSTEM_PROMPT = """You are a Senior Wikipedia Security Analyst.
Your job is to provide high-fidelity classification and CATEGORIZATION of Wikipedia edits.

Classification Tiers:
- VANDALISM: Deliberate damage (Spam, Profanity, Blanking, Hoax, Malicious bias).
- SUSPICIOUS: Likely bad-faith or problematic (POV pushing, unsourced sensitive info, subtle vandalism).
- SAFE: Good-faith edit (typo fix, sourced info, normal content growth).

Categorization (Choose the most fitting for VANDALISM/SUSPICIOUS):
- "SPAM": Commercial links or promotion.
- "SENSELESS": Gibberish, keyboard smashing, or "leetspeak".
- "BLANKING": Removing significant valid content without reason.
- "HOAX/SLANDER": Inserting false facts, libeling individuals, or misinformation.
- "POV_BIAS": Non-neutral language or removing balanced viewpoints.
- "MARKUP_DAMAGE": Deliberately breaking templates, links, or citations.
- "UNKNOWN": None of the above.

IMPORTANT: Respond ONLY with valid JSON."""

USER_PROMPT_TEMPLATE = """Detailed Edit Analysis Request:

**Article**: {title}
**Editor**: {user} | **Comment**: {comment}
**Size Change**: {delta:+d} characters

**TEXT ADDED**:
{diff_added}

**TEXT REMOVED**:
{diff_removed}

**Context Flags**: {matched_rules}
**Heuristic Risk**: Rule_Score={rule_score}, NLP_Score={nlp_score}, Final={final_score}

Output JSON format:
{{
  "classification": "VANDALISM|SUSPICIOUS|SAFE",
  "category": "category_name",
  "confidence": 0.0-1.0,
  "reasoning_vi": "Giải thích chi tiết bằng tiếng Việt về lý do tại sao (tối đa 2 câu)",
  "vandalism_type": "specific sub-type (optional)"
}}"""


def query_ollama(title: str, user: str, comment: str,
                 diff_added: str, diff_removed: str,
                 matched_rules: str, rule_score: float,
                 nlp_score: float, final_score: float) -> dict:
    """Gọi Ollama API với structured prompt."""
    
    # Giới hạn diff length
    added_short = diff_added[:MAX_DIFF_CHARS] + ("..." if len(diff_added) > MAX_DIFF_CHARS else "")
    removed_short = diff_removed[:MAX_DIFF_CHARS] + ("..." if len(diff_removed) > MAX_DIFF_CHARS else "")
    
    delta = len(diff_added) - len(diff_removed)
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        user=user,
        comment=comment or "(empty)",
        delta=delta,
        diff_added=added_short or "(no text added)",
        diff_removed=removed_short or "(no text removed)",
        matched_rules=matched_rules or "none",
        rule_score=rule_score,
        nlp_score=nlp_score,
        final_score=final_score,
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n\n{user_prompt}",
        "stream": False,
        "options": {
            "temperature": 0.1,      # Deterministic
            "num_predict": 200,       # Giới hạn output tokens
            "top_p": 0.9,
        }
    }
    
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        raw_response = result.get("response", "")
        
        # Parse JSON từ response
        parsed = parse_llm_response(raw_response)
        parsed["raw_response"] = raw_response[:300]
        parsed["eval_duration_ms"] = result.get("eval_duration", 0) // 1_000_000

        # ── Ensemble Scoring Logic (Consensus) ──
        llm_classification = parsed["classification"]
        llm_conf = parsed["confidence"]

        # Tính toán ensemble consensus
        consensus_score = 0
        if llm_classification == "VANDALISM":
            consensus_score = 0.6  # Base for LLM confirmation
            if rule_score > 3.0: consensus_score += 0.2
            if nlp_score > 0.7: consensus_score += 0.2
        elif llm_classification == "SUSPICIOUS":
            consensus_score = 0.4
            if rule_score > 2.0: consensus_score += 0.1
        else:
            consensus_score = 0.1
            
        parsed["ensemble_confidence"] = consensus_score
        return parsed
        
    except requests.exceptions.Timeout:
        return {"classification": "ERROR", "category": "ERROR", "confidence": 0, "reasoning_vi": "Timeout",
                "raw_response": "", "eval_duration_ms": 0, "ensemble_confidence": 0}
    except requests.RequestException as e:
        return {"classification": "ERROR", "category": "ERROR", "confidence": 0, "reasoning_vi": str(e)[:100],
                "raw_response": "", "eval_duration_ms": 0, "ensemble_confidence": 0}


def parse_llm_response(text: str) -> dict:
    """Parse LLM JSON response, xử lý trường hợp response không chuẩn."""
    try:
        # Tìm JSON object trong response
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "classification": data.get("classification", "UNKNOWN").upper(),
                "category": data.get("category", "UNKNOWN").upper(),
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning_vi": str(data.get("reasoning_vi", ""))[:250],
            }
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fallback
    return {"classification": "UNKNOWN", "category": "UNKNOWN", "confidence": 0, "reasoning_vi": f"Lỗi parse: {text[:50]}"}


def process_final_csv(csv_path: Path):
    """Đọc final CSV, gửi edits đáng ngờ cho LLM, lưu kết quả."""
    # Xác định output path
    ts = csv_path.name.replace("_04_final.csv", "")
    output_path = csv_path.parent / f"{ts}_06_llm.csv"
    
    if output_path.exists():
        print(f"   ⏩ Skipping {csv_path.name} (already LLM-verified)")
        return output_path

    edits = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        edits = list(reader)

    if not edits:
        return

    # Thêm fields mới (bao gồm ensemble_confidence cho Consensus Scoring)
    for col in ["llm_classification", "llm_category", "llm_confidence", "ensemble_confidence", "llm_reasoning_vi", "llm_time_ms"]:
        if col not in fieldnames:
            fieldnames.append(col)

    # Đếm edits cần xử lý
    to_analyze = [e for e in edits if float(e.get("final_score", 0)) > SCORE_THRESHOLD]
    total_to_analyze = len(to_analyze)
    
    print(f"\n📄 {csv_path.name} — {len(edits)} edits, {total_to_analyze} cần LLM analysis")
    
    analyzed = 0
    vandalism_count = 0
    suspicious_count = 0
    safe_count = 0
    error_count = 0
    total_time = 0

    for i, edit in enumerate(edits):
        final_score = float(edit.get("final_score", 0))

        if final_score > SCORE_THRESHOLD:
            analyzed += 1
            print(f"   🤖 [{analyzed}/{total_to_analyze}] {edit.get('title', '')[:35]}...", end=" ", flush=True)
            
            result = query_ollama(
                title=edit.get("title", ""),
                user=edit.get("user", ""),
                comment=edit.get("comment", ""),
                diff_added=edit.get("diff_added", ""),
                diff_removed=edit.get("diff_removed", ""),
                matched_rules=edit.get("matched_rules", ""),
                rule_score=float(edit.get("rule_score", 0)),
                nlp_score=float(edit.get("nlp_score", 0)),
                final_score=final_score,
            )

            edit["llm_classification"] = result["classification"]
            edit["llm_category"] = result["category"]
            edit["llm_confidence"] = f"{int(result['confidence'] * 100)}%"
            edit["ensemble_confidence"] = f"{int(result['ensemble_confidence'] * 100)}%"
            edit["llm_reasoning_vi"] = result["reasoning_vi"]
            edit["llm_time_ms"] = result["eval_duration_ms"]
            total_time += result["eval_duration_ms"]
            
            cls = result["classification"]
            cat = result["category"]
            if cls == "VANDALISM":
                vandalism_count += 1
                print(f"🔴 VANDALISM [{cat}] ({result['confidence']:.0%}) — {result['reasoning_vi'][:60]}")
            elif cls == "SUSPICIOUS":
                suspicious_count += 1
                print(f"🟡 SUSPICIOUS [{cat}] ({result['confidence']:.0%}) — {result['reasoning_vi'][:60]}")
            elif cls == "SAFE":
                safe_count += 1
                print(f"✅ SAFE ({result['confidence']:.0%})")
            else:
                error_count += 1
                print(f"❓ {cls} — {result['reasoning_vi'][:50]}")
        else:
            edit["llm_classification"] = ""
            edit["llm_category"] = ""
            edit["llm_confidence"] = ""
            edit["llm_reasoning_vi"] = ""
            edit["llm_time_ms"] = ""

    # Lưu kết quả
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edits)

    print(f"\n   💾 Saved: {output_path.name}")
    print(f"   📊 Analyzed: {analyzed} edits in {total_time/1000:.1f}s")
    print(f"      🔴 VANDALISM:  {vandalism_count}")
    print(f"      🟡 SUSPICIOUS: {suspicious_count}")
    print(f"      ✅ SAFE:       {safe_count}")
    print(f"      ❓ ERROR:      {error_count}")

    # So sánh với Ground Truth (nếu có verified data)
    print_accuracy_comparison(edits)
    return output_path


def print_accuracy_comparison(edits: list[dict]):
    """So sánh LLM decisions với Ground Truth (is_reverted)."""
    # Chỉ tính edits đã qua LLM
    llm_edits = [e for e in edits if e.get("llm_classification") in ("VANDALISM", "SUSPICIOUS", "SAFE")]
    
    if not llm_edits:
        return

    print(f"\n   {'='*55}")
    print(f"   📈 SO SÁNH VỚI GROUND TRUTH")
    print(f"   {'='*55}")

    # Tính accuracy metrics
    has_revert_data = any(e.get("is_reverted") for e in llm_edits)
    
    if has_revert_data:
        # LLM flagged = VANDALISM hoặc SUSPICIOUS
        llm_flagged = [e for e in llm_edits if e["llm_classification"] in ("VANDALISM", "SUSPICIOUS")]
        llm_safe = [e for e in llm_edits if e["llm_classification"] == "SAFE"]
        
        # True Positive: LLM nói VANDALISM/SUSPICIOUS + thực sự bị revert
        tp = sum(1 for e in llm_flagged if e.get("is_reverted") == "True")
        # False Positive: LLM nói VANDALISM/SUSPICIOUS nhưng không bị revert
        fp = sum(1 for e in llm_flagged if e.get("is_reverted") == "False")
        # False Negative: LLM nói SAFE nhưng thực sự bị revert
        fn = sum(1 for e in llm_safe if e.get("is_reverted") == "True")
        # True Negative: LLM nói SAFE và đúng là không bị revert
        tn = sum(1 for e in llm_safe if e.get("is_reverted") == "False")
        
        total = tp + fp + fn + tn
        
        llm_precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
        llm_recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
        
        # So sánh với Rule Engine precision (tất cả flagged = TP + FP)
        rule_flagged = len(llm_edits)
        rule_tp = sum(1 for e in llm_edits if e.get("is_reverted") == "True")
        rule_precision = rule_tp / rule_flagged * 100 if rule_flagged > 0 else 0
        
        print(f"\n   Rule Engine (baseline):")
        print(f"      Flagged: {rule_flagged} | TP: {rule_tp} | Precision: {rule_precision:.1f}%")
        print(f"\n   LLM (Gemma 2):")
        print(f"      Flagged: {len(llm_flagged)} | TP: {tp} | FP: {fp}")
        print(f"      Precision: {llm_precision:.1f}% | Recall: {llm_recall:.1f}%")
        
        if rule_precision > 0:
            improvement = llm_precision / rule_precision
            print(f"\n   🚀 Precision improvement: {improvement:.1f}x")
        
        # Chi tiết
        if tp > 0:
            print(f"\n   ✅ LLM correctly caught:")
            reverted_and_flagged = [e for e in llm_flagged if e.get("is_reverted") == "True"]
            for e in reverted_and_flagged[:5]:
                print(f"      🔴 {e['title'][:35]} — {e['llm_reasoning_vi'][:40]}")
        
        if fn > 0:
            print(f"\n   ❌ LLM missed (False Negative):")
            missed = [e for e in llm_safe if e.get("is_reverted") == "True"]
            for e in missed[:5]:
                print(f"      ⚠️  {e['title'][:35]} — LLM said SAFE but was reverted")
    else:
        print(f"\n   ⚠️  Chưa có dữ liệu revert. Chạy 05_revert_check.py trước!")
        print(f"\n   LLM Classification Summary:")
        for cls in ["VANDALISM", "SUSPICIOUS", "SAFE"]:
            count = sum(1 for e in llm_edits if e["llm_classification"] == cls)
            print(f"      {cls:12s}: {count}")


def main():
    print("🤖 Wiki-Stream LLM Verification v1.0")
    print(f"   Model: {MODEL_NAME} (via Ollama)")
    print(f"   Score threshold: > {SCORE_THRESHOLD}")
    print(f"   Max diff chars: {MAX_DIFF_CHARS}")

    # Check Ollama connection
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"   Available models: {', '.join(models)}")
        if MODEL_NAME not in models:
            print(f"   ⚠️  {MODEL_NAME} not found! Run: ollama pull gemma2")
            return
    except requests.RequestException:
        print("   ❌ Ollama not running! Start with: ollama serve")
        return

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
    print("✅ LLM Verification hoàn tất!")
    print("   Kết quả lưu trong các file _06_llm.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
