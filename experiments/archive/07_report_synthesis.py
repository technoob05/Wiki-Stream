"""
🧠 STAGE 09: INTELLIGENCE AGGREGATOR (FINAL)
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_08_attributed.csv
        reports/temporal_analysis.json (if Stage 10 ran before)
Output: reports/insights.md & intelligence_summary.json
Goal:   Tổng hợp toàn bộ Insight từ Rule, NLP, LLM, Fingerprinting,
        và Temporal Clustering thành báo cáo cuối cùng.
────────────────────────────────────────────────────────────
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

def load_all_processed_data():
    """Load các file _08_attributed.csv mới nhất làm nguồn dữ liệu chính."""
    all_edits = []
    found_any = False
    
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir(): continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists(): continue
        
        # Ưu tiên lấy file _08_attributed.csv (đầu ra cuối cùng)
        files = list(proc_dir.glob("*_08_attributed.csv"))
        # Fallback về _06_llm.csv nếu chưa chạy Stage 8
        if not files:
            files = list(proc_dir.glob("*_06_llm.csv"))
            
        for f in files:
            found_any = True
            with open(f, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    row["lang"] = lang_dir.name
                    row["source_file"] = f.name
                    all_edits.append(row)
    return all_edits


def load_temporal_data():
    """Load temporal analysis results nếu đã chạy Stage 10 trước đó."""
    temporal_path = REPORT_DIR / "temporal_analysis.json"
    if temporal_path.exists():
        with open(temporal_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def analyze_intelligence(edits):
    if not edits: return None

    # Lấy các ca phá hoại có độ tin cậy cao
    vandalism_cases = [e for e in edits if e.get("llm_classification") == "VANDALISM"]
    attribution_matches = [e for e in edits if e.get("is_serial_vandal") == "True"]

    stats = {
        "total_edits": len(edits),
        "flagged_edits": sum(1 for e in edits if float(e.get("rule_score", 0)) > 0),
        "lang_dist": dict(Counter(e["lang"] for e in edits)),
        "top_articles": Counter(e["title"] for e in edits if float(e.get("rule_score", 0)) > 2.0).most_common(5),
        "top_users": Counter(e["user"] for e in edits if float(e.get("rule_score", 0)) > 1.0).most_common(5),
        "vandalism_count": len(vandalism_cases),
        "suspicious_count": sum(1 for e in edits if e.get("llm_classification") == "SUSPICIOUS"),
        "vandalism_details": [
            {
                "title": e["title"],
                "user": e["user"],
                "reason": e.get("llm_reasoning_vi", "N/A"),
                "category": e.get("llm_category", "UNKNOWN"),
                "confidence": e.get("ensemble_confidence", e.get("llm_confidence", "0%")),
                "time": e["timestamp"],
                "lang": e["lang"]
            } for e in vandalism_cases
        ],
        "attribution_matches": [
            {
                "title": e["title"],
                "user": e["user"],
                "match": e["fingerprint_match"],
                "similarity": e["fingerprint_similarity"],
                "time": e["timestamp"]
            } for e in attribution_matches
        ]
    }
    return stats

def generate_markdown_report(stats, temporal=None, deep=None, graph=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# 🧠 Wikipedia Intelligence Report (VIP Master)
*Generated at: {now}*

## 📊 System Overview
- **Total Edits Scanned:** {stats['total_edits']}
- **Suspicious/Flagged:** {stats['flagged_edits']}
- **Language Distribution:** {stats['lang_dist']}

## 🧠 Ensemble Intelligence (Consensus)
- 🔴 **VANDALISM (Confirmed):** {stats['vandalism_count']}
- 🟡 **SUSPICIOUS (Alert):** {stats['suspicious_count']}
- 🛡️ **Confidence Model:** Rule + NLP + LLM Ensemble (Gemma 2)

---

## 🕵️ Serial Vandal Attribution (Stage 08)
*Identify repeat offenders by writing style fingerprints.*

| Timestamp | Current User | Targeted Article | Matched Signature | Similarity |
|---|---|---|---|---|
"""
    for a in stats["attribution_matches"]:
        md += f"| {a['time']} | `{a['user']}` | {a['title']} | **{a['match']}** | `{float(a['similarity']):.1%}` |\n"

    if not stats["attribution_matches"]:
        md += "| - | - | - | No serial matches found | - |\n"

    # ── TEMPORAL CLUSTERING SECTION ──
    if temporal:
        md += "\n---\n\n## ⏱️ Temporal Clustering Intelligence (Stage 10)\n"
        md += "*Forensic time-series analysis: Bursts, Velocity, Periodicity.*\n\n"

        # Burst Detection
        burst = temporal.get("burst_detection", {})
        md += f"### ⚡ Burst Detection\n"
        md += f"- **Total Bursts:** {burst.get('total_bursts', 0)}\n"
        md += f"- 🔴 Critical: {burst.get('critical', 0)} | 🟠 High: {burst.get('high', 0)}\n\n"
        
        if burst.get("details"):
            md += "| Threat | User | Edits | Duration | Rate (edits/min) | Articles Targeted |\n"
            md += "|---|---|---|---|---|---|\n"
            for b in burst["details"][:10]:
                articles = ", ".join(b["articles_targeted"][:3])
                if len(b["articles_targeted"]) > 3:
                    articles += f" +{len(b['articles_targeted'])-3} more"
                md += f"| {b['threat_level']} | `{b['user']}` | {b['edit_count']} | {b['duration_sec']}s | {b['rate_per_min']} | {articles} |\n"
            md += "\n"

        # Velocity Analysis
        vel = temporal.get("velocity_analysis", {})
        md += f"### 🚀 Mass Deletion Velocity\n"
        md += f"- **Deletion Alerts:** {vel.get('total_alerts', 0)}\n"
        md += f"- 🔴 Mass Deletions: {vel.get('mass_deletions', 0)}\n\n"

        if vel.get("details"):
            md += "| Assessment | User | Chars Deleted | Duration | Delete Rate (/min) | Articles |\n"
            md += "|---|---|---|---|---|---|\n"
            for v in vel["details"][:10]:
                articles = ", ".join(v["articles_affected"][:3])
                md += f"| {v['assessment']} | `{v['user']}` | {v['total_deleted_chars']:,} | {v['duration_min']} min | {v['delete_rate_per_min']:,.0f} | {articles} |\n"
            md += "\n"

        # Periodicity
        peri = temporal.get("periodicity_detection", {})
        md += f"### 🔄 Periodicity Patterns\n"
        md += f"- **Patterns Found:** {peri.get('total_patterns', 0)}\n"
        md += f"- 🔴 Bot-like: {peri.get('bot_like', 0)} | 🟠 Scripted: {peri.get('scripted', 0)}\n\n"

        if peri.get("details"):
            md += "| Pattern | User | Peak Hour (UTC) | Concentration | Edits | Vandal Ratio |\n"
            md += "|---|---|---|---|---|---|\n"
            for p in peri["details"][:10]:
                md += f"| {p['pattern_type']} | `{p['user']}` | {p['peak_hour_utc']} | {p['concentration']}% | {p['total_edits']} | {p['vandal_ratio']}% |\n"
            md += "\n"

    md += """
---

## 🔍 Confirmed Vandalism Log (High Performance)
| Timestamp | User | Article | Category | Reliability | Reason |
|---|---|---|---|---|---|
"""
    for v in stats["vandalism_details"]:
        md += f"| {v['time']} | {v['user']} | [{v['title']}](https://en.wikipedia.org/wiki/{v['title'].replace(' ', '_')}) | **{v['category']}** | `{v['confidence']}` | {v['reason']} |\n"

    md += f"""
---

## 🔥 Risk Hotspots
### Top Target Articles
{chr(10).join([f"- **{k}**: {v} detections" for k, v in stats['top_articles']])}

### Top Suspect Users
{chr(10).join([f"- **{k}**: {v} detections" for k, v in stats['top_users']])}

---
## 💡 AI Strategy & Recommendations
1. **Decision Authority:** {stats['vandalism_count']} edits marked for immediate revert based on high ensemble confidence.
2. **Campaign Alert:** """
    # Campaign logic
    signatures = [a["match"] for a in stats["attribution_matches"]]
    campaigns = Counter(signatures)
    campaign_found = False
    for sig, count in campaigns.items():
        if count >= 2:
            md += f"Warning! Coordinate attack detected from signature **{sig}** across multiple pages. "
            campaign_found = True
    if not campaign_found: md += "No coordinated campaigns detected in this batch."

    md += f"\n3. **Trend:** Significant activity observed in {stats['lang_dist']} stream."

    # Temporal recommendations
    if temporal:
        burst = temporal.get("burst_detection", {})
        vel = temporal.get("velocity_analysis", {})
        if burst.get("critical", 0) > 0:
            md += f"\n4. **⚡ Temporal Alert:** {burst['critical']} CRITICAL burst(s) detected — recommend immediate rate-limiting."
        if vel.get("mass_deletions", 0) > 0:
            md += f"\n5. **🚀 Velocity Alert:** {vel['mass_deletions']} mass deletion campaign(s) detected — recommend content rollback."

    # ── DEEP INSIGHTS SECTION ──
    if deep:
        md += "\n\n---\n\n## 🔬 Deep Intelligence Synthesis (Stage 11)\n"
        md += "*Cross-signal correlation + strategic threat analysis.*\n\n"

        # Threat Profiles
        profiles = deep.get("threat_profiles", [])
        critical_profiles = [p for p in profiles if "CRITICAL" in p.get("threat_level", "")]
        high_profiles = [p for p in profiles if "HIGH" in p.get("threat_level", "")]
        md += f"### 👤 Unified Threat Profiles\n"
        md += f"- **Users Profiled:** {len(profiles)}\n"
        md += f"- 🔴 Critical: {len(critical_profiles)} | 🟠 High: {len(high_profiles)}\n\n"

        top_threats = (critical_profiles + high_profiles)[:10]
        if top_threats:
            md += "| Threat | Score | User | Edits | Articles | Signals Active |\n"
            md += "|---|---|---|---|---|---|\n"
            for p in top_threats:
                signals = " + ".join(p.get("signals_active", [])[:4])
                md += f"| {p['threat_level']} | **{p['threat_score']}/100** | `{p['user']}` | {p['total_edits']} | {p['articles_count']} | {signals} |\n"
            md += "\n"

        # Campaigns
        campaigns = deep.get("campaigns", [])
        if campaigns:
            md += f"### 🎯 Coordinated Campaigns Detected: {len(campaigns)}\n\n"
            md += "| Type | Target | Users | Edits |\n"
            md += "|---|---|---|---|\n"
            for c in campaigns[:8]:
                users_str = ", ".join(f"`{u}`" for u in c["users_involved"][:4])
                if len(c["users_involved"]) > 4:
                    users_str += f" +{len(c['users_involved'])-4}"
                md += f"| {c['type']} | {c['article'][:50]} | {users_str} | {c['edit_count']} |\n"
            md += "\n"

        # Topic Vulnerability
        topics = deep.get("topic_vulnerability", [])
        if topics:
            md += f"### 📰 Most Vulnerable Articles (Top 10)\n\n"
            md += "| Risk | Article | Attack Rate | Vandal | Suspicious | Chars Lost | Top Attack |\n"
            md += "|---|---|---|---|---|---|---|\n"
            for t in topics[:10]:
                md += f"| **{t['risk_score']}** | {t['article'][:40]} | {t['attack_ratio']}% | {t['vandal_edits']} | {t['suspicious_edits']} | {t['chars_lost']:,} | {t['top_attack_type']} |\n"
            md += "\n"

        # Risk Heatmap
        heatmap = deep.get("risk_heatmap", [])
        if heatmap:
            md += f"### 🗺️ Risk Heatmap by Hour (UTC)\n\n"
            md += "| Hour | Danger | Total | Vandal | Suspicious | Chars Lost | Visual |\n"
            md += "|---|---|---|---|---|---|---|\n"
            for h in heatmap:
                md += f"| **{h['hour_utc']}** | {h['danger_ratio']}% | {h['total_edits']} | {h['vandal']} | {h['suspicious']} | {h['chars_deleted']:,} | {h['risk_bar']} |\n"
            md += "\n"

        # Cross-Signal Correlation
        corr = deep.get("cross_signal_correlation", {})
        if corr:
            pair_name, pair_count = corr.get("strongest_pair", ("N/A", 0))
            md += f"### 🔗 Cross-Signal Correlation\n"
            md += f"- **All 3 Signals Agree:** {corr.get('consensus_all_3', 0)} edits (highest confidence)\n"
            md += f"- **2 of 3 Agree:** {corr.get('consensus_2_of_3', 0)} edits\n"
            md += f"- **Consensus Rate:** {corr.get('consensus_rate', 0)}%\n"
            md += f"- **Strongest Signal Pair:** {pair_name} ({pair_count} co-detections)\n\n"

    # ── GRAPH INTELLIGENCE SECTION ──
    if graph:
        gs = graph.get("graph_stats", {})
        md += "\n---\n\n## 🕸️ Graph Intelligence (Stage 12)\n"
        md += "*Bipartite Graph Mining: SuspicionRank + Community Detection + Label Propagation*\n\n"

        md += f"### 📐 Graph Structure\n"
        md += f"- **Nodes:** {gs.get('total_nodes', 0)} (Users: {gs.get('user_nodes', 0)}, Articles: {gs.get('article_nodes', 0)})\n"
        md += f"- **Edges:** {gs.get('total_edges', 0)} | Density: {gs.get('density', 0)} | Components: {gs.get('components', 0)}\n\n"

        # SuspicionRank
        sr = graph.get("suspicion_rank", {})
        top_users = sr.get("top_users", [])
        if top_users:
            md += f"### 🏆 SuspicionRank (Personalized PageRank)\n\n"
            md += "| Rank | User | Score | Degree | Vandal Count |\n"
            md += "|---|---|---|---|---|\n"
            for i, u in enumerate(top_users[:10], 1):
                md += f"| {i} | `{u['user']}` | **{u['suspicion_rank']}/100** | {u['degree']} | {u['vandal_count']} |\n"
            md += "\n"

        # Communities
        comms = graph.get("communities", [])
        if comms:
            md += f"### 🕵️ Louvain Community Detection (User-User Projection)\n\n"
            md += "| Threat | Users | Vandal Ratio | Shared Articles | Key Members |\n"
            md += "|---|---|---|---|---|\n"
            for c in comms[:8]:
                members = ", ".join(f"`{u['name']}`" for u in c.get("top_users", [])[:3])
                articles = ", ".join(c.get("shared_articles", [])[:3])
                md += f"| {c['threat']} | {c['user_count']} | {c['vandal_ratio']}% | {articles[:50]} | {members} |\n"
            md += "\n"

        # Label Propagation
        lp = graph.get("label_propagation", {})
        propagated = lp.get("details", [])
        md += f"### 🔮 Label Propagation (Semi-supervised Discovery)\n"
        md += f"- **Newly Flagged via Graph:** {lp.get('newly_flagged', 0)} users\n\n"
        if propagated:
            md += "| User | Iteration | Vandal Neighbor Ratio | Original Label |\n"
            md += "|---|---|---|---|\n"
            for p in propagated[:10]:
                md += f"| `{p['user']}` | {p['iteration']} | {p['vandal_neighbor_ratio']}% | {p['original_label']} |\n"
            md += "\n"

    # ── ADVANCED FUSION (Stage 13) ──
    fusion = load_advanced_fusion()
    if fusion:
        md += "---\n## 🧬 Stage 13: Advanced Intelligence Fusion\n\n"
        
        ds = fusion.get("dempster_shafer", {})
        ds_cls = ds.get("classifications", {})
        md += "### 📐 Dempster-Shafer Evidence Fusion\n\n"
        md += "| Classification | Count | Description |\n|---|---|---|\n"
        md += f"| HIGH_CONFIDENCE_VANDAL | {ds_cls.get('HIGH_CONFIDENCE_VANDAL', 0)} | Belief ≥ 0.7 |\n"
        md += f"| LIKELY_VANDAL | {ds_cls.get('LIKELY_VANDAL', 0)} | Belief ≥ 0.4 |\n"
        md += f"| UNCERTAIN | {ds_cls.get('UNCERTAIN', 0)} | No clear evidence |\n"
        md += f"| LIKELY_SAFE | {ds_cls.get('LIKELY_SAFE', 0)} | Safe belief ≥ 0.3 |\n"
        md += f"| HIGH_CONFIDENCE_SAFE | {ds_cls.get('HIGH_CONFIDENCE_SAFE', 0)} | Safe belief ≥ 0.6 |\n\n"
        
        top_v = ds.get("top_vandals", [])[:5]
        if top_v:
            md += "**Top High-Confidence Vandals:**\n\n"
            md += "| User | Article | Belief | Plausibility | Uncertainty |\n|---|---|---|---|---|\n"
            for v in top_v:
                md += f"| `{v['user']}` | {v['title'][:35]} | {v['belief_vandal']:.3f} | {v['plausibility_vandal']:.3f} | {v['uncertainty']:.3f} |\n"
            md += "\n"
        
        iso = fusion.get("isolation_forest", {})
        iso_stats = iso.get("stats", {})
        if iso_stats:
            md += "### 🌲 Isolation Forest Anomaly Detection\n\n"
            md += f"- **Total Edits:** {iso_stats.get('total', 0)}\n"
            md += f"- **Anomalies Detected:** {iso_stats.get('anomalies', 0)} ({iso_stats.get('anomaly_rate', 0)}%)\n\n"
        
        cross = fusion.get("cross_method", {})
        if cross:
            md += "### 🔄 Cross-Method Agreement\n\n"
            md += f"- ALL 3 methods agree: **{cross.get('all_three_agree', 0)}** edits\n"
            md += f"- D-S new discoveries: **{cross.get('ds_new_discoveries', 0)}**\n"
            md += f"- IF new discoveries: **{cross.get('if_new_discoveries', 0)}**\n\n"

    return md


def load_deep_insights():
    """Load deep insights nếu đã chạy Stage 11."""
    p = REPORT_DIR / "deep_insights.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_graph_intelligence():
    """Load graph intelligence nếu đã chạy Stage 12."""
    p = REPORT_DIR / "graph_intelligence.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_advanced_fusion():
    """Load advanced fusion nếu đã chạy Stage 13."""
    p = REPORT_DIR / "advanced_fusion.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    print("🧠 Intelligence Aggregator (VIP Master) Running...")
    edits = load_all_processed_data()
    if not edits:
        print("   ⚠️ No attributed data found. Run Stage 08 first.")
        return

    stats = analyze_intelligence(edits)
    temporal = load_temporal_data()
    deep = load_deep_insights()
    graph = load_graph_intelligence()
    
    if temporal:
        print("   📊 Temporal data found — integrating into report.")
    if deep:
        print("   🔬 Deep insights found — integrating into report.")
    if graph:
        print("   🕸️ Graph intelligence found — integrating into report.")
    
    fusion = load_advanced_fusion()
    if fusion:
        print("   🧬 Advanced fusion found — integrating into report.")
    
    report_md = generate_markdown_report(stats, temporal, deep, graph)
    
    with open(REPORT_DIR / "insights.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"   ✅ Master Report generated at: {REPORT_DIR / 'insights.md'}")

if __name__ == "__main__":
    main()
