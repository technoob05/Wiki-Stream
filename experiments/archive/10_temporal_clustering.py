"""
⏱️ STAGE 10: TEMPORAL CLUSTERING INTELLIGENCE
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_08_attributed.csv
Output: reports/temporal_analysis.json + insights in final report
Goal:   Phát hiện 3 loại hành vi phá hoại dựa trên thời gian:
        1. Burst Detection: Đột biến edit (>5 edits / 3 phút)
        2. Velocity Analysis: Tốc độ xóa nội dung bất thường
        3. Periodicity Detection: Phát hiện chu kỳ hoạt động lặp lại
────────────────────────────────────────────────────────────
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import math

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# Thresholds
BURST_WINDOW_SEC = 180       # 3 phút
BURST_MIN_EDITS = 3          # Tối thiểu 3 edits trong cửa sổ để coi là Burst
VELOCITY_WINDOW_SEC = 600    # 10 phút
VELOCITY_DELETE_THRESHOLD = 5000  # 5000 chars xóa trong 10 phút = Mass Deletion
PERIODICITY_MIN_EDITS = 3    # Tối thiểu 3 lần mới tính chu kỳ


def load_all_data():
    """Load tất cả _08_attributed.csv (hoặc _06_llm.csv fallback)."""
    all_edits = []
    for lang_dir in DATA_DIR.iterdir():
        if not lang_dir.is_dir():
            continue
        proc_dir = lang_dir / "processed"
        if not proc_dir.exists():
            continue

        files = list(proc_dir.glob("*_08_attributed.csv"))
        if not files:
            files = list(proc_dir.glob("*_06_llm.csv"))

        for f in files:
            with open(f, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    row["lang"] = lang_dir.name
                    all_edits.append(row)
    return all_edits


def detect_bursts(edits):
    """
    📊 BURST DETECTION
    Phát hiện user thực hiện nhiều edits liên tục trong thời gian ngắn.
    Thuật toán: Sliding Window (3 phút) trên timeline của mỗi user.
    """
    # Nhóm edits theo user
    user_edits = defaultdict(list)
    for e in edits:
        ts = int(float(e.get("timestamp", 0)))
        if ts > 0:
            user_edits[e["user"]].append({
                "timestamp": ts,
                "title": e.get("title", ""),
                "rule_score": float(e.get("rule_score", 0)),
                "llm_classification": e.get("llm_classification", ""),
                "lang": e.get("lang", "en"),
            })

    bursts = []
    for user, user_edit_list in user_edits.items():
        if len(user_edit_list) < BURST_MIN_EDITS:
            continue

        # Sắp xếp theo thời gian
        user_edit_list.sort(key=lambda x: x["timestamp"])

        # Sliding window
        for i in range(len(user_edit_list)):
            window = []
            for j in range(i, len(user_edit_list)):
                if user_edit_list[j]["timestamp"] - user_edit_list[i]["timestamp"] <= BURST_WINDOW_SEC:
                    window.append(user_edit_list[j])
                else:
                    break

            if len(window) >= BURST_MIN_EDITS:
                # Tính threat level
                avg_score = sum(w["rule_score"] for w in window) / len(window)
                vandal_count = sum(1 for w in window if w["llm_classification"] == "VANDALISM")
                articles_hit = list(set(w["title"] for w in window))
                duration_sec = window[-1]["timestamp"] - window[0]["timestamp"]
                rate = len(window) / max(duration_sec / 60, 0.1)  # edits/min

                threat = "🟢 LOW"
                if vandal_count >= 2 or avg_score > 3.0:
                    threat = "🔴 CRITICAL"
                elif vandal_count >= 1 or avg_score > 2.0:
                    threat = "🟠 HIGH"
                elif len(window) >= 5:
                    threat = "🟡 MEDIUM"

                bursts.append({
                    "user": user,
                    "edit_count": len(window),
                    "duration_sec": duration_sec,
                    "rate_per_min": round(rate, 1),
                    "avg_rule_score": round(avg_score, 2),
                    "vandal_in_burst": vandal_count,
                    "articles_targeted": articles_hit,
                    "threat_level": threat,
                    "start_time": window[0]["timestamp"],
                    "end_time": window[-1]["timestamp"],
                })
                break  # Chỉ lấy burst lớn nhất của mỗi user

    # Sắp xếp theo threat level
    threat_order = {"🔴 CRITICAL": 0, "🟠 HIGH": 1, "🟡 MEDIUM": 2, "🟢 LOW": 3}
    bursts.sort(key=lambda x: (threat_order.get(x["threat_level"], 99), -x["edit_count"]))
    return bursts


def detect_velocity(edits):
    """
    🚀 VELOCITY ANALYSIS
    Phát hiện tốc độ xóa nội dung bất thường (Mass Deletion Campaign).
    Thuật toán: Tính tổng chars_deleted trong sliding window 10 phút.
    """
    # Nhóm edits theo user, chỉ lấy edits có diff data
    user_edits = defaultdict(list)
    for e in edits:
        ts = int(float(e.get("timestamp", 0)))
        len_old = int(float(e.get("length_old", 0)))
        len_new = int(float(e.get("length_new", 0)))
        delta = len_new - len_old  # Âm = xóa

        if ts > 0:
            user_edits[e["user"]].append({
                "timestamp": ts,
                "title": e.get("title", ""),
                "delta_chars": delta,
                "chars_deleted": abs(delta) if delta < 0 else 0,
                "chars_added": delta if delta > 0 else 0,
                "llm_classification": e.get("llm_classification", ""),
            })

    velocity_alerts = []
    for user, user_edit_list in user_edits.items():
        if len(user_edit_list) < 2:
            continue

        user_edit_list.sort(key=lambda x: x["timestamp"])

        # Sliding window velocity
        for i in range(len(user_edit_list)):
            window = []
            for j in range(i, len(user_edit_list)):
                if user_edit_list[j]["timestamp"] - user_edit_list[i]["timestamp"] <= VELOCITY_WINDOW_SEC:
                    window.append(user_edit_list[j])
                else:
                    break

            if len(window) >= 2:
                total_deleted = sum(w["chars_deleted"] for w in window)
                total_added = sum(w["chars_added"] for w in window)
                net_change = total_added - total_deleted
                articles_hit = list(set(w["title"] for w in window))

                if total_deleted >= VELOCITY_DELETE_THRESHOLD:
                    duration_min = max((window[-1]["timestamp"] - window[0]["timestamp"]) / 60, 0.1)
                    delete_rate = total_deleted / duration_min

                    velocity_alerts.append({
                        "user": user,
                        "total_deleted_chars": total_deleted,
                        "total_added_chars": total_added,
                        "net_change": net_change,
                        "delete_rate_per_min": round(delete_rate, 0),
                        "duration_min": round(duration_min, 1),
                        "articles_affected": articles_hit,
                        "edit_count": len(window),
                        "assessment": "🔴 MASS DELETION" if total_deleted > 10000 else "🟠 HIGH DELETION",
                    })
                    break  # Lấy window tệ nhất

    velocity_alerts.sort(key=lambda x: -x["total_deleted_chars"])
    return velocity_alerts


def detect_periodicity(edits):
    """
    🔄 PERIODICITY DETECTION
    Phát hiện user có thói quen phá hoại vào cùng 1 khung giờ.
    Thuật toán: Phân tích phân phối hour-of-day cho mỗi user.
    """
    user_hours = defaultdict(list)
    for e in edits:
        ts = int(float(e.get("timestamp", 0)))
        if ts > 0:
            dt = datetime.utcfromtimestamp(ts)
            user_hours[e["user"]].append({
                "hour": dt.hour,
                "weekday": dt.strftime("%A"),
                "title": e.get("title", ""),
                "llm_classification": e.get("llm_classification", ""),
                "rule_score": float(e.get("rule_score", 0)),
            })

    periodicity_results = []
    for user, entries in user_hours.items():
        if len(entries) < PERIODICITY_MIN_EDITS:
            continue

        # Phân tích hour distribution
        hour_counts = Counter(e["hour"] for e in entries)
        total = len(entries)
        peak_hour, peak_count = hour_counts.most_common(1)[0]
        concentration = peak_count / total  # 1.0 = tất cả cùng 1 giờ

        # Phân tích weekday
        weekday_counts = Counter(e["weekday"] for e in entries)
        peak_day, peak_day_count = weekday_counts.most_common(1)[0]

        # Chỉ báo cáo nếu concentration > 50% (>50% edits cùng 1 khung giờ)
        if concentration >= 0.5 and peak_count >= PERIODICITY_MIN_EDITS:
            # Tính suspicious ratio
            vandal_ratio = sum(1 for e in entries if e["llm_classification"] in ("VANDALISM", "SUSPICIOUS")) / total

            pattern_type = "🔴 BOT-LIKE"
            if concentration >= 0.8:
                pattern_type = "🔴 BOT-LIKE"
            elif concentration >= 0.6:
                pattern_type = "🟠 SCRIPTED"
            else:
                pattern_type = "🟡 HABITUAL"

            periodicity_results.append({
                "user": user,
                "total_edits": total,
                "peak_hour_utc": f"{peak_hour:02d}:00-{peak_hour:02d}:59",
                "concentration": round(concentration * 100, 1),
                "peak_weekday": peak_day,
                "peak_day_count": peak_day_count,
                "vandal_ratio": round(vandal_ratio * 100, 1),
                "pattern_type": pattern_type,
                "hour_distribution": dict(hour_counts),
            })

    periodicity_results.sort(key=lambda x: (-x["concentration"], -x["vandal_ratio"]))
    return periodicity_results


def generate_temporal_report(bursts, velocity, periodicity):
    """Tổng hợp kết quả temporal analysis thành JSON và summary."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "burst_detection": {
            "total_bursts": len(bursts),
            "critical": sum(1 for b in bursts if "CRITICAL" in b["threat_level"]),
            "high": sum(1 for b in bursts if "HIGH" in b["threat_level"]),
            "details": bursts[:20],  # Top 20
        },
        "velocity_analysis": {
            "total_alerts": len(velocity),
            "mass_deletions": sum(1 for v in velocity if "MASS" in v["assessment"]),
            "details": velocity[:15],
        },
        "periodicity_detection": {
            "total_patterns": len(periodicity),
            "bot_like": sum(1 for p in periodicity if "BOT" in p["pattern_type"]),
            "scripted": sum(1 for p in periodicity if "SCRIPTED" in p["pattern_type"]),
            "details": periodicity[:15],
        },
    }

    # Save JSON
    output_path = REPORT_DIR / "temporal_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def print_summary(report):
    """In tóm tắt kết quả lên console."""
    burst = report["burst_detection"]
    vel = report["velocity_analysis"]
    peri = report["periodicity_detection"]

    print(f"\n   {'='*55}")
    print(f"   📊 TEMPORAL CLUSTERING RESULTS")
    print(f"   {'='*55}")

    # Burst
    print(f"\n   ⚡ BURST DETECTION:")
    print(f"      Total Bursts Found: {burst['total_bursts']}")
    print(f"      🔴 Critical: {burst['critical']} | 🟠 High: {burst['high']}")
    if burst["details"]:
        print(f"      Top Offenders:")
        for b in burst["details"][:5]:
            print(f"        {b['threat_level']} {b['user']}: {b['edit_count']} edits in {b['duration_sec']}s "
                  f"({b['rate_per_min']} edits/min) → {', '.join(b['articles_targeted'][:2])}")

    # Velocity
    print(f"\n   🚀 VELOCITY ANALYSIS:")
    print(f"      Mass Deletion Alerts: {vel['total_alerts']}")
    if vel["details"]:
        for v in vel["details"][:5]:
            print(f"        {v['assessment']} {v['user']}: -{v['total_deleted_chars']} chars "
                  f"in {v['duration_min']} min → {', '.join(v['articles_affected'][:2])}")

    # Periodicity
    print(f"\n   🔄 PERIODICITY DETECTION:")
    print(f"      Patterns Found: {peri['total_patterns']}")
    print(f"      🔴 Bot-like: {peri['bot_like']} | 🟠 Scripted: {peri['scripted']}")
    if peri["details"]:
        for p in peri["details"][:5]:
            print(f"        {p['pattern_type']} {p['user']}: {p['concentration']}% active at "
                  f"UTC {p['peak_hour_utc']} ({p['total_edits']} edits, "
                  f"{p['vandal_ratio']}% suspicious)")


def main():
    print("⏱️ Temporal Clustering Intelligence Running...")
    edits = load_all_data()
    if not edits:
        print("   ⚠️ No data found. Run earlier stages first.")
        return

    print(f"   📂 Loaded {len(edits)} edits for temporal analysis")

    bursts = detect_bursts(edits)
    velocity = detect_velocity(edits)
    periodicity = detect_periodicity(edits)

    report = generate_temporal_report(bursts, velocity, periodicity)
    print_summary(report)

    print(f"\n   ✅ Temporal report saved to: {REPORT_DIR / 'temporal_analysis.json'}")


if __name__ == "__main__":
    main()
