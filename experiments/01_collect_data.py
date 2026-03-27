"""
📡 STAGE 01: REAL-TIME DATA COLLECTION
────────────────────────────────────────────────────────────
Input:  Wikipedia SSE Stream (https://stream.wikimedia.org)
Output: data/{lang}/raw/{timestamp}.csv
Goal:   Kết nối stream, lọc Bot, lách namespace=0 (Article)
        và thu thập edits thời gian thực từ 'en' và 'vi'.
────────────────────────────────────────────────────────────
"""

import json
import time
import csv
import re
from datetime import datetime
from pathlib import Path

import requests

# ── Config ──
SSE_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
TARGET_COUNT = 300
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# Chỉ lấy các Wikipedia này (dễ mở rộng sau)
ALLOWED_DOMAINS = {
    "en.wikipedia.org",
    "vi.wikipedia.org",
}

HEADERS = {
    "Accept": "text/event-stream",
    "User-Agent": "WikiStreamIntel/1.0 (university-research-project; contact: student@example.com)",
}

FIELDS = [
    "id", "title", "user", "bot", "timestamp", "domain",
    "namespace", "comment", "length_old", "length_new",
    "revision_old", "revision_new", "minor", "patrolled",
    "wiki", "title_url", "wiki_url",
]


def collect_edits(target: int = TARGET_COUNT) -> list[dict]:
    """Kết nối SSE stream và thu thập edits (chỉ en + vi, article, không bot).
    Có chế độ tự động kết nối lại nếu bị ngắt quãng.
    """
    print(f"🔗 Đang kết nối tới Wikipedia SSE stream...")
    print(f"   Nguồn: {', '.join(ALLOWED_DOMAINS)}")
    print(f"   Lọc: namespace=0 (Article), bỏ bot")
    print(f"   Mục tiêu: {target} edits\n")

    edits = []
    skipped = {"domain": 0, "namespace": 0, "bot": 0, "type": 0}
    max_retries = 3
    retry_count = 0
    start_time = time.time()

    while len(edits) < target and retry_count < max_retries:
        try:
            if retry_count > 0:
                print(f"\n🔄 Đang thử kết nối lại (Lần {retry_count}/{max_retries})...")
            
            response = requests.get(SSE_URL, stream=True, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                print(f"❌ Lỗi kết nối! Status: {response.status_code}")
                retry_count += 1
                time.sleep(2)
                continue

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue

                try:
                    data = json.loads(line[5:].strip())
                except (json.JSONDecodeError, TypeError):
                    continue

                # Lọc type
                if data.get("type") != "edit":
                    skipped["type"] += 1
                    continue

                # Lọc domain
                domain = data.get("server_name", "")
                if domain not in ALLOWED_DOMAINS:
                    skipped["domain"] += 1
                    continue

                # Lọc namespace (chỉ Article = 0)
                if data.get("namespace", -1) != 0:
                    skipped["namespace"] += 1
                    continue

                # Lọc bot
                if data.get("bot", False):
                    skipped["bot"] += 1
                    continue

                length_info = data.get("length") or {}
                revision_info = data.get("revision") or {}

                edit = {
                    "id": data.get("id"),
                    "title": data.get("title", ""),
                    "user": data.get("user", ""),
                    "bot": False,
                    "timestamp": data.get("timestamp", 0),
                    "domain": domain,
                    "namespace": 0,
                    "comment": data.get("comment", ""),
                    "length_old": length_info.get("old", 0) or 0,
                    "length_new": length_info.get("new", 0) or 0,
                    "revision_old": revision_info.get("old", 0) or 0,
                    "revision_new": revision_info.get("new", 0) or 0,
                    "minor": data.get("minor", False),
                    "patrolled": data.get("patrolled", False),
                    "wiki": data.get("wiki", ""),
                    "title_url": data.get("title_url", ""),
                    "wiki_url": f"https://{domain}/w/index.php?diff={revision_info.get('new', '')}&oldid={revision_info.get('old', '')}",
                }
                edits.append(edit)

                count = len(edits)
                if count % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = count / max(elapsed, 0.1) * 60
                    print(f"   📥 {count}/{target} edits ({rate:.0f} edits/min)")

                if count >= target:
                    break
            
            # Nếu vòng lặp iter_lines kết thúc mà chưa đủ target, tăng retry
            if len(edits) < target:
                retry_count += 1
                time.sleep(1)

        except (requests.exceptions.RequestException, Exception) as e:
            print(f"\n⚠️ Lỗi stream: {e}")
            retry_count += 1
            time.sleep(2)

    elapsed = time.time() - start_time
    print(f"\n✅ Thu thập xong! {len(edits)} edits trong {elapsed:.1f}s")
    print(f"   Đã bỏ qua: {skipped['domain']} domain khác, {skipped['namespace']} namespace khác, "
          f"{skipped['bot']} bot, {skipped['type']} non-edit")
    return edits


# Domain mapping cho folder gọn gàng
DOMAIN_MAP = {
    "en.wikipedia.org": "en",
    "vi.wikipedia.org": "vi",
}


def save_data(edits: list[dict]):
    """Lưu data chia theo domain vào cấu trúc: data/{lang}/raw/{ts}.csv"""
    if not edits:
        print("⚠️ Không có data để lưu!")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Chia theo domain
    by_domain: dict[str, list[dict]] = {}
    for e in edits:
        d = e["domain"]
        by_domain.setdefault(d, []).append(e)

    for domain, domain_edits in by_domain.items():
        lang = DOMAIN_MAP.get(domain)
        if not lang:
            print(f"⚠️ Skipping unknown domain: {domain} ({len(domain_edits)} edits)")
            continue
        folder = OUTPUT_DIR / lang / "raw"
        folder.mkdir(parents=True, exist_ok=True)
        
        path = folder / f"{ts}.csv"
        _write_csv(path, domain_edits)
        print(f"📁 {domain}: {path} ({len(domain_edits)} edits)")


def _write_csv(path: Path, edits: list[dict]):
    """Ghi list edits ra CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(edits)


def explore_data(edits: list[dict]):
    """In thống kê cơ bản."""
    print("\n" + "=" * 60)
    print("📊 KHÁM PHÁ DỮ LIỆU")
    print("=" * 60)

    total = len(edits)
    print(f"\n📌 Tổng edits: {total}")
    if total == 0:
        print("⚠️ Không có data!")
        return

    # Domain
    domains: dict[str, int] = {}
    for e in edits:
        domains[e["domain"]] = domains.get(e["domain"], 0) + 1
    print(f"\n🌐 Phân bố theo domain:")
    for d, c in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(c / total * 40)
        print(f"   {d:25s} {c:4d} ({c/total*100:.1f}%) {bar}")

    # Anonymous
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    anon = sum(1 for e in edits if ip_pattern.match(e["user"]))
    print(f"\n👤 Registered: {total - anon} | 🔒 Anonymous (IP): {anon}")

    # Size changes
    changes = [e["length_new"] - e["length_old"] for e in edits if e["length_old"] and e["length_new"]]
    if changes:
        avg = sum(changes) / len(changes)
        big_add = sum(1 for c in changes if c > 5000)
        big_del = sum(1 for c in changes if c < -5000)
        blanking = sum(1 for e in edits if e["length_old"] > 100
                       and e["length_new"] < e["length_old"] * 0.2)
        print(f"\n📏 Size: avg {avg:+.0f} chars | +5k: {big_add} | -5k: {big_del} | blanking: {blanking}")

    # Comments
    empty = sum(1 for e in edits if not e["comment"].strip())
    reverts = sum(1 for e in edits if any(w in e["comment"].lower()
                  for w in ["revert", "undo", "rv", "undid", "rollback"]))
    minor = sum(1 for e in edits if e["minor"])
    print(f"\n💬 Empty comment: {empty} | Revert/Undo: {reverts} | Minor: {minor}")

    # Suspicious samples
    print(f"\n🔍 Edits đáng ngờ (comment trống + thay đổi >500 chars):")
    sus = [e for e in edits if not e["comment"].strip()
           and abs(e["length_new"] - e["length_old"]) > 500]
    for e in sus[:5]:
        ch = e["length_new"] - e["length_old"]
        print(f"   [{e['domain'][:2]}] {e['title'][:40]:40s} | {e['user'][:20]:20s} | {ch:+6d}")
    if not sus:
        print("   (Không có — data sạch!)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    edits = collect_edits()
    save_data(edits)
    explore_data(edits)
