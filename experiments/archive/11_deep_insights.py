"""
🔬 STAGE 11: DEEP INSIGHT SYNTHESIZER
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_08_attributed.csv
        reports/temporal_analysis.json
        vandal_fingerprints.json
Output: reports/deep_insights.json + sections in insights.md
Goal:   Kết hợp TẤT CẢ tín hiệu (Rule, NLP, LLM, Fingerprint, Temporal)
        để tạo ra các insight cấp chiến lược:
        1. Unified Threat Profile (Hồ sơ đe dọa toàn diện per user)
        2. Coordinated Campaign Detection (Phát hiện tấn công phối hợp)
        3. Topic Vulnerability Analysis (Chủ đề dễ bị tấn công nhất)
        4. Risk Heatmap by Hour (Giờ nào Wikipedia dễ bị tấn công nhất)
        5. Cross-Signal Correlation (Khi nào Rule+NLP+LLM đồng ý nhất)
────────────────────────────────────────────────────────────
"""
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)
FINGERPRINT_DB = Path(__file__).parent / "vandal_fingerprints.json"


def load_all_data():
    """Load tất cả _08_attributed.csv."""
    all_edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir(): continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
        files = list(proc_dir.glob("*_08_attributed.csv"))
        if not files:
            files = list(proc_dir.glob("*_06_llm.csv"))
        for f in files:
            with open(f, "r", encoding="utf-8") as csvfile:
                for row in csv.DictReader(csvfile):
                    row["lang"] = lang_dir.name
                    all_edits.append(row)
    return all_edits


def load_temporal():
    p = REPORT_DIR / "temporal_analysis.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}


def load_fingerprints():
    return json.load(open(FINGERPRINT_DB, encoding="utf-8")) if FINGERPRINT_DB.exists() else {}


# ═══════════════════════════════════════════════════════════
# 1. UNIFIED THREAT PROFILE
# ═══════════════════════════════════════════════════════════
def build_threat_profiles(edits, temporal):
    """
    Xây dựng hồ sơ đe dọa toàn diện cho mỗi user.
    Kết hợp: Rule Score + NLP Score + LLM Classification + Fingerprint + Burst + Periodicity
    → Unified Threat Level (0-100).
    """
    user_data = defaultdict(lambda: {
        "edits": [], "rule_scores": [], "nlp_scores": [],
        "llm_vandal": 0, "llm_suspicious": 0, "llm_safe": 0,
        "fingerprint_matches": 0, "is_burst": False, "is_periodic": False,
        "articles": set(), "langs": set(),
        "chars_added": 0, "chars_deleted": 0,
    })

    for e in edits:
        u = e["user"]
        d = user_data[u]
        d["edits"].append(e)
        d["rule_scores"].append(float(e.get("rule_score", 0)))
        d["nlp_scores"].append(float(e.get("nlp_score", 0)))
        d["articles"].add(e.get("title", ""))
        d["langs"].add(e.get("lang", ""))

        cls = e.get("llm_classification", "")
        if cls == "VANDALISM": d["llm_vandal"] += 1
        elif cls == "SUSPICIOUS": d["llm_suspicious"] += 1
        elif cls == "SAFE": d["llm_safe"] += 1

        if e.get("is_serial_vandal") == "True":
            d["fingerprint_matches"] += 1

        l_old = int(float(e.get("length_old", 0)))
        l_new = int(float(e.get("length_new", 0)))
        delta = l_new - l_old
        if delta > 0: d["chars_added"] += delta
        else: d["chars_deleted"] += abs(delta)

    # Enrich with temporal data
    burst_users = set()
    periodic_users = set()
    if temporal:
        for b in temporal.get("burst_detection", {}).get("details", []):
            burst_users.add(b["user"])
        for p in temporal.get("periodicity_detection", {}).get("details", []):
            periodic_users.add(p["user"])

    profiles = []
    for user, d in user_data.items():
        total = len(d["edits"])
        if total < 1: continue

        d["is_burst"] = user in burst_users
        d["is_periodic"] = user in periodic_users

        # ── Calculate Unified Threat Score (0-100) ──
        # Component 1: Rule Signal (0-25)
        avg_rule = sum(d["rule_scores"]) / total
        rule_signal = min(avg_rule / 5.0, 1.0) * 25

        # Component 2: NLP Signal (0-20)
        avg_nlp = sum(d["nlp_scores"]) / total if d["nlp_scores"] else 0
        nlp_signal = min(avg_nlp / 5.0, 1.0) * 20

        # Component 3: LLM Signal (0-30) — heaviest weight
        vandal_ratio = d["llm_vandal"] / total if total > 0 else 0
        suspicious_ratio = d["llm_suspicious"] / total if total > 0 else 0
        llm_signal = (vandal_ratio * 30) + (suspicious_ratio * 15)
        llm_signal = min(llm_signal, 30)

        # Component 4: Fingerprint Signal (0-15)
        fp_signal = min(d["fingerprint_matches"] / max(total, 1), 1.0) * 15

        # Component 5: Temporal Signal (0-10)
        temporal_signal = 0
        if d["is_burst"]: temporal_signal += 5
        if d["is_periodic"]: temporal_signal += 5

        threat_score = round(rule_signal + nlp_signal + llm_signal + fp_signal + temporal_signal, 1)
        threat_score = min(threat_score, 100)

        # Classify threat level
        if threat_score >= 70: threat_level = "🔴 CRITICAL"
        elif threat_score >= 50: threat_level = "🟠 HIGH"
        elif threat_score >= 30: threat_level = "🟡 MEDIUM"
        elif threat_score >= 15: threat_level = "🔵 LOW"
        else: threat_level = "🟢 MINIMAL"

        # Build breakdown
        signals_active = []
        if rule_signal > 5: signals_active.append(f"Rule({avg_rule:.1f})")
        if nlp_signal > 5: signals_active.append(f"NLP({avg_nlp:.1f})")
        if d["llm_vandal"] > 0: signals_active.append(f"LLM-V({d['llm_vandal']})")
        if d["llm_suspicious"] > 0: signals_active.append(f"LLM-S({d['llm_suspicious']})")
        if d["fingerprint_matches"] > 0: signals_active.append(f"FP({d['fingerprint_matches']})")
        if d["is_burst"]: signals_active.append("⚡Burst")
        if d["is_periodic"]: signals_active.append("🔄Periodic")

        profiles.append({
            "user": user,
            "threat_score": threat_score,
            "threat_level": threat_level,
            "total_edits": total,
            "articles_count": len(d["articles"]),
            "vandal_count": d["llm_vandal"],
            "suspicious_count": d["llm_suspicious"],
            "fingerprint_hits": d["fingerprint_matches"],
            "is_burst": d["is_burst"],
            "is_periodic": d["is_periodic"],
            "chars_added": d["chars_added"],
            "chars_deleted": d["chars_deleted"],
            "net_impact": d["chars_added"] - d["chars_deleted"],
            "signals_active": signals_active,
            "signal_breakdown": {
                "rule": round(rule_signal, 1),
                "nlp": round(nlp_signal, 1),
                "llm": round(llm_signal, 1),
                "fingerprint": round(fp_signal, 1),
                "temporal": round(temporal_signal, 1),
            }
        })

    profiles.sort(key=lambda x: -x["threat_score"])
    return profiles


# ═══════════════════════════════════════════════════════════
# 2. COORDINATED CAMPAIGN DETECTION
# ═══════════════════════════════════════════════════════════
def detect_campaigns(edits, profiles):
    """
    Phát hiện tấn công phối hợp: Nhiều user tấn công cùng 1 bài trong thời gian ngắn.
    Hoặc nhiều user cùng fingerprint signature.
    """
    # Method 1: Article-Time Clustering
    article_edits = defaultdict(list)
    for e in edits:
        ts = int(float(e.get("timestamp", 0)))
        cls = e.get("llm_classification", "")
        if cls in ("VANDALISM", "SUSPICIOUS") and ts > 0:
            article_edits[e["title"]].append({
                "user": e["user"],
                "timestamp": ts,
                "classification": cls,
            })

    campaigns = []
    for article, edit_list in article_edits.items():
        if len(edit_list) < 2: continue
        users = set(e["user"] for e in edit_list)
        if len(users) < 2: continue  # Cần ít nhất 2 user khác nhau

        # Check timing (within 30 min)
        edit_list.sort(key=lambda x: x["timestamp"])
        time_span = edit_list[-1]["timestamp"] - edit_list[0]["timestamp"]
        if time_span <= 1800:  # 30 phút
            campaigns.append({
                "article": article,
                "users_involved": list(users),
                "edit_count": len(edit_list),
                "time_span_min": round(time_span / 60, 1),
                "type": "🎯 TARGETED ARTICLE ATTACK",
            })

    # Method 2: Fingerprint-based Campaign (same signature, different users)
    fp_groups = defaultdict(list)
    for e in edits:
        match = e.get("fingerprint_match", "")
        if match and e.get("is_serial_vandal") == "True":
            fp_groups[match].append(e["user"])

    for signature, users in fp_groups.items():
        unique_users = set(users)
        if len(unique_users) >= 2:
            campaigns.append({
                "article": f"Multiple (via signature: {signature})",
                "users_involved": list(unique_users),
                "edit_count": len(users),
                "time_span_min": "N/A",
                "type": "🕵️ SOCKPUPPET NETWORK",
            })

    campaigns.sort(key=lambda x: -x["edit_count"])
    return campaigns


# ═══════════════════════════════════════════════════════════
# 3. TOPIC VULNERABILITY ANALYSIS
# ═══════════════════════════════════════════════════════════
def analyze_topic_vulnerability(edits):
    """
    Phân tích chủ đề nào dễ bị tấn công nhất dựa trên:
    - Số lần bị vandal
    - Tỉ lệ vandal/total edits
    - Mức độ thiệt hại (chars deleted)
    """
    article_stats = defaultdict(lambda: {
        "total_edits": 0, "vandal_edits": 0, "suspicious_edits": 0,
        "chars_deleted": 0, "unique_attackers": set(), "categories": [],
    })

    for e in edits:
        title = e.get("title", "")
        a = article_stats[title]
        a["total_edits"] += 1

        cls = e.get("llm_classification", "")
        if cls == "VANDALISM":
            a["vandal_edits"] += 1
            a["unique_attackers"].add(e["user"])
            a["categories"].append(e.get("llm_category", "UNKNOWN"))
        elif cls == "SUSPICIOUS":
            a["suspicious_edits"] += 1

        l_old = int(float(e.get("length_old", 0)))
        l_new = int(float(e.get("length_new", 0)))
        if l_new < l_old:
            a["chars_deleted"] += (l_old - l_new)

    vulnerabilities = []
    for title, a in article_stats.items():
        if a["vandal_edits"] + a["suspicious_edits"] == 0: continue

        attack_ratio = (a["vandal_edits"] + a["suspicious_edits"]) / max(a["total_edits"], 1)
        risk_score = (a["vandal_edits"] * 3 + a["suspicious_edits"]) * (1 + attack_ratio)
        top_category = Counter(a["categories"]).most_common(1)

        vulnerabilities.append({
            "article": title,
            "total_edits": a["total_edits"],
            "vandal_edits": a["vandal_edits"],
            "suspicious_edits": a["suspicious_edits"],
            "attack_ratio": round(attack_ratio * 100, 1),
            "unique_attackers": len(a["unique_attackers"]),
            "chars_lost": a["chars_deleted"],
            "top_attack_type": top_category[0][0] if top_category else "N/A",
            "risk_score": round(risk_score, 1),
        })

    vulnerabilities.sort(key=lambda x: -x["risk_score"])
    return vulnerabilities[:20]


# ═══════════════════════════════════════════════════════════
# 4. RISK HEATMAP BY HOUR
# ═══════════════════════════════════════════════════════════
def build_risk_heatmap(edits):
    """
    Xây dựng bản đồ nhiệt rủi ro theo giờ UTC.
    Giờ nào Wikipedia dễ bị tấn công nhất?
    """
    hour_data = defaultdict(lambda: {"total": 0, "vandal": 0, "suspicious": 0, "chars_deleted": 0})

    for e in edits:
        ts = int(float(e.get("timestamp", 0)))
        if ts <= 0: continue
        dt = datetime.utcfromtimestamp(ts)
        h = dt.hour
        hour_data[h]["total"] += 1

        cls = e.get("llm_classification", "")
        if cls == "VANDALISM": hour_data[h]["vandal"] += 1
        elif cls == "SUSPICIOUS": hour_data[h]["suspicious"] += 1

        l_old = int(float(e.get("length_old", 0)))
        l_new = int(float(e.get("length_new", 0)))
        if l_new < l_old:
            hour_data[h]["chars_deleted"] += (l_old - l_new)

    heatmap = []
    for h in range(24):
        d = hour_data[h]
        if d["total"] == 0: continue
        danger_ratio = (d["vandal"] + d["suspicious"]) / d["total"]
        heatmap.append({
            "hour_utc": f"{h:02d}:00",
            "total_edits": d["total"],
            "vandal": d["vandal"],
            "suspicious": d["suspicious"],
            "danger_ratio": round(danger_ratio * 100, 1),
            "chars_deleted": d["chars_deleted"],
            "risk_bar": "█" * int(danger_ratio * 20),  # Visual bar
        })

    return heatmap


# ═══════════════════════════════════════════════════════════
# 5. CROSS-SIGNAL CORRELATION
# ═══════════════════════════════════════════════════════════
def cross_signal_analysis(edits):
    """
    Phân tích sự đồng thuận giữa các tín hiệu:
    - Khi nào Rule + NLP + LLM cùng đồng ý?
    - "Consensus Strength" = bao nhiêu % edits mà >2 signals cùng flag
    """
    consensus = {"all_agree": 0, "two_agree": 0, "one_only": 0, "none": 0}
    signal_pairs = defaultdict(int)
    total_flagged = 0

    for e in edits:
        rule_flag = float(e.get("rule_score", 0)) > 2.0
        nlp_flag = float(e.get("nlp_score", 0)) > 2.0
        llm_flag = e.get("llm_classification", "") in ("VANDALISM", "SUSPICIOUS")

        flags = [rule_flag, nlp_flag, llm_flag]
        count = sum(flags)

        if count >= 3: consensus["all_agree"] += 1
        elif count == 2: consensus["two_agree"] += 1
        elif count == 1: consensus["one_only"] += 1
        else: consensus["none"] += 1

        if count >= 1: total_flagged += 1

        # Track which pairs agree
        if rule_flag and nlp_flag: signal_pairs["Rule+NLP"] += 1
        if rule_flag and llm_flag: signal_pairs["Rule+LLM"] += 1
        if nlp_flag and llm_flag: signal_pairs["NLP+LLM"] += 1

    total = len(edits)
    return {
        "total_edits": total,
        "total_flagged": total_flagged,
        "consensus_all_3": consensus["all_agree"],
        "consensus_2_of_3": consensus["two_agree"],
        "single_signal": consensus["one_only"],
        "clean": consensus["none"],
        "consensus_rate": round((consensus["all_agree"] + consensus["two_agree"]) / max(total_flagged, 1) * 100, 1),
        "strongest_pair": max(signal_pairs.items(), key=lambda x: x[1]) if signal_pairs else ("N/A", 0),
        "pair_details": dict(signal_pairs),
    }


# ═══════════════════════════════════════════════════════════
# REPORT & MAIN
# ═══════════════════════════════════════════════════════════
def save_deep_insights(profiles, campaigns, topics, heatmap, correlation):
    report = {
        "generated_at": datetime.now().isoformat(),
        "threat_profiles": profiles[:30],
        "campaigns": campaigns[:15],
        "topic_vulnerability": topics,
        "risk_heatmap": heatmap,
        "cross_signal_correlation": correlation,
    }
    with open(REPORT_DIR / "deep_insights.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    return report


def print_summary(profiles, campaigns, topics, heatmap, correlation):
    print(f"\n   {'='*55}")
    print(f"   🔬 DEEP INSIGHT SYNTHESIS RESULTS")
    print(f"   {'='*55}")

    # Threat Profiles
    critical = [p for p in profiles if "CRITICAL" in p["threat_level"]]
    high = [p for p in profiles if "HIGH" in p["threat_level"]]
    print(f"\n   👤 UNIFIED THREAT PROFILES:")
    print(f"      Total Users Profiled: {len(profiles)}")
    print(f"      🔴 Critical Threats: {len(critical)} | 🟠 High: {len(high)}")
    for p in profiles[:5]:
        signals = " + ".join(p["signals_active"][:4])
        print(f"        {p['threat_level']} [{p['threat_score']}/100] {p['user']} "
              f"({p['total_edits']} edits) → {signals}")

    # Campaigns
    print(f"\n   🎯 COORDINATED CAMPAIGNS:")
    print(f"      Campaigns Detected: {len(campaigns)}")
    for c in campaigns[:5]:
        print(f"        {c['type']} → {c['article'][:40]} "
              f"({len(c['users_involved'])} users, {c['edit_count']} edits)")

    # Topic Vulnerabilities
    print(f"\n   📰 TOPIC VULNERABILITY (Top 5):")
    for t in topics[:5]:
        print(f"        Risk={t['risk_score']:.1f} | {t['article'][:35]} "
              f"({t['vandal_edits']}V/{t['suspicious_edits']}S, "
              f"{t['attack_ratio']}% attack rate, -{t['chars_lost']} chars)")

    # Heatmap
    print(f"\n   🗺️ RISK HEATMAP (Hour UTC):")
    for h in heatmap:
        if h["vandal"] + h["suspicious"] > 0:
            print(f"        {h['hour_utc']} | {h['risk_bar']} {h['danger_ratio']}% "
                  f"({h['vandal']}V + {h['suspicious']}S / {h['total_edits']} total)")

    # Correlation
    print(f"\n   🔗 CROSS-SIGNAL CORRELATION:")
    print(f"      All 3 signals agree: {correlation['consensus_all_3']} edits")
    print(f"      2 of 3 agree:        {correlation['consensus_2_of_3']} edits")
    print(f"      Consensus Rate:      {correlation['consensus_rate']}%")
    pair, count = correlation["strongest_pair"]
    print(f"      Strongest Pair:      {pair} ({count} co-detections)")


def main():
    print("🔬 Deep Insight Synthesizer Running...")
    edits = load_all_data()
    if not edits:
        print("   ⚠️ No data. Run previous stages first.")
        return

    temporal = load_temporal()
    print(f"   📂 Loaded {len(edits)} edits + temporal data")

    # Run all analyses
    profiles = build_threat_profiles(edits, temporal)
    campaigns = detect_campaigns(edits, profiles)
    topics = analyze_topic_vulnerability(edits)
    heatmap = build_risk_heatmap(edits)
    correlation = cross_signal_analysis(edits)

    # Save & Print
    save_deep_insights(profiles, campaigns, topics, heatmap, correlation)
    print_summary(profiles, campaigns, topics, heatmap, correlation)

    print(f"\n   ✅ Deep insights saved to: {REPORT_DIR / 'deep_insights.json'}")


if __name__ == "__main__":
    main()
