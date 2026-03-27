"""
Stage 04: LLM CLASSIFICATION + CALIBRATED MASS FUNCTIONS
------------------------------------------------------------
Input:  data/{lang}/processed/{timestamp}_truth.csv
Output: data/{lang}/processed/{timestamp}_classified.csv

Theoretical Foundation:
- LLM provides semantic understanding that heuristics cannot capture
- Raw LLM confidence is uncalibrated; we apply Platt-style mapping
  to convert (classification, confidence) -> DS mass function
- Mass function preserves uncertainty: low-confidence LLM outputs
  produce high theta (uncertainty) rather than false precision
------------------------------------------------------------
"""

import csv
import json
import requests
import re
from pathlib import Path

# -- Config --
DATA_DIR = Path(__file__).parent / "data"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma2:latest"
REQUEST_TIMEOUT = 60

SYSTEM_PROMPT = """You are a Wikipedia Security Analyst. Classify edits as VANDALISM, SUSPICIOUS, or SAFE.
Pay SPECIAL ATTENTION to:
- ned:* signals (Named Entity changes): changes to names, dates, years, locations are HIGH RISK
- ned:bio_year_change = someone changed a birth/death year -> almost always vandalism
- ned:name_tamper = someone altered a proper noun slightly -> likely typo-vandalism
- ned:location_change = someone changed a birthplace/hometown -> requires human review
- it:* signals (Information Theory): high entropy or KL-divergence = anomalous content
Output JSON."""


# ================================================================
# LLM QUERY
# ================================================================

def query_llm(edit: dict) -> dict:
    # NOTE: Do NOT include rule/NLP signals in the prompt.
    # Dempster-Shafer requires independent evidence sources.
    # If the LLM sees our pre-computed signals, its output is no longer
    # independent, and DS combination would double-count evidence.
    prompt = f"""
Analyze this Wikipedia edit for vandalism:

Title: {edit['title']}
Comment: {edit['comment']}
Added text: {edit['diff_added'][:500]}
Removed text: {edit['diff_removed'][:500]}

Look for: inappropriate content, factual tampering (changed names/dates/numbers),
blanking, spam, test edits, bias injection, or other signs of vandalism.

Respond with ONLY a JSON object:
{{"classification": "VANDALISM|SUSPICIOUS|SAFE", "confidence": 0.0-1.0, "reason": "brief explanation"}}
"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME, "prompt": prompt, "system": SYSTEM_PROMPT,
            "stream": False, "options": {"temperature": 0.1}
        }, timeout=REQUEST_TIMEOUT)

        raw = resp.json().get("response", "")
        # Non-greedy match to avoid capturing multiple JSON-like structures
        match = re.search(r'\{[^{}]*"classification"[^{}]*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "class": data.get("classification", "UNKNOWN").upper(),
                "conf": float(data.get("confidence", 0.5)),
                "reason": data.get("reason", "")
            }
    except Exception as e:
        return {"class": "ERROR", "conf": 0, "reason": str(e)[:100]}
    return {"class": "ERROR", "conf": 0, "reason": "No valid JSON in response"}


# ================================================================
# CALIBRATED MASS FUNCTION
# ================================================================

def llm_to_mass(classification: str, confidence: float) -> dict:
    """
    Convert LLM output to a calibrated Dempster-Shafer mass function.

    Rationale: Raw LLM confidence is uncalibrated — a model saying
    "90% confident" doesn't mean P(correct) = 0.9. We apply a
    conservative mapping that:
    1. Caps maximum belief at 0.80 (no single source should dominate)
    2. Reserves minimum 0.10 uncertainty (epistemic humility)
    3. Maps confidence non-linearly (low conf -> high uncertainty)

    Mapping table (classification x confidence -> mass):
    VANDALISM + high(>0.8): {v:0.70, s:0.05, t:0.25}
    VANDALISM + med(0.5-0.8): {v:0.45, s:0.05, t:0.50}
    VANDALISM + low(<0.5): {v:0.25, s:0.10, t:0.65}
    SUSPICIOUS + any: {v:0.30, s:0.15, t:0.55}
    SAFE + high(>0.8): {v:0.03, s:0.65, t:0.32}
    SAFE + med(0.5-0.8): {v:0.05, s:0.40, t:0.55}
    SAFE + low(<0.5): {v:0.10, s:0.20, t:0.70}
    """
    conf = max(0.0, min(1.0, confidence))

    if classification == "VANDALISM":
        if conf > 0.8:
            return {"v": 0.70, "s": 0.05, "t": 0.25}
        elif conf > 0.5:
            return {"v": 0.45, "s": 0.05, "t": 0.50}
        else:
            return {"v": 0.25, "s": 0.10, "t": 0.65}

    elif classification == "SAFE":
        if conf > 0.8:
            return {"v": 0.03, "s": 0.65, "t": 0.32}
        elif conf > 0.5:
            return {"v": 0.05, "s": 0.40, "t": 0.55}
        else:
            return {"v": 0.10, "s": 0.20, "t": 0.70}

    elif classification == "SUSPICIOUS":
        # SUSPICIOUS is inherently uncertain — high theta
        if conf > 0.7:
            return {"v": 0.35, "s": 0.10, "t": 0.55}
        else:
            return {"v": 0.25, "s": 0.15, "t": 0.60}

    else:
        # ERROR / UNKNOWN — maximum uncertainty (vacuous mass)
        return {"v": 0.0, "s": 0.0, "t": 1.0}


# ================================================================
# MAIN PROCESSING
# ================================================================

def process_lang(lang: str):
    folder = DATA_DIR / lang / "processed"
    if not folder.exists():
        return

    for rf in sorted(folder.glob("*_truth.csv")):
        output_path = folder / f"{rf.stem.replace('_truth', '')}_classified.csv"
        if output_path.exists():
            continue

        print(f"\n  LLM Classifying: {rf.name}")
        with open(rf, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            edits = list(reader)
            fieldnames = list(reader.fieldnames)

        for col in ["llm_class", "llm_conf", "llm_reason", "mass_llm"]:
            if col not in fieldnames:
                fieldnames.append(col)

        from tqdm import tqdm
        pbar = tqdm(edits, desc=f"   {lang.upper()} Classifying", unit="edit")
        for edit in pbar:
            # Only query LLM for edits with some signal
            has_signal = (
                float(edit.get("rule_score", 0)) > 0 or
                float(edit.get("nlp_score", 0)) > 0
            )

            if has_signal:
                res = query_llm(edit)
                edit["llm_class"] = res["class"]
                edit["llm_conf"] = round(res["conf"], 3)
                edit["llm_reason"] = res["reason"]

                # Calibrated mass function
                mass = llm_to_mass(res["class"], res["conf"])
                edit["mass_llm"] = json.dumps(mass)

                pbar.write(f"   [{res['class']}] {edit['title'][:30]} | Conf: {res['conf']:.0%}")
            else:
                # No signal -> skip LLM, assign safe-leaning mass
                edit["llm_class"] = ""
                edit["llm_conf"] = ""
                edit["llm_reason"] = ""
                edit["mass_llm"] = json.dumps({"v": 0.0, "s": 0.3, "t": 0.7})

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(edits)


def main():
    print("WIKI-STREAM LLM CLASSIFIER v2.0 (Calibrated Mass Functions)")
    for lang in ["en", "vi"]:
        process_lang(lang)


if __name__ == "__main__":
    main()
