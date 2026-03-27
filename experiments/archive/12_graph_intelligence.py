"""
🕸️ STAGE 12: GRAPH INTELLIGENCE ENGINE
────────────────────────────────────────────────────────────
Input:  data/{lang}/processed/{timestamp}_08_attributed.csv
        reports/temporal_analysis.json
Output: reports/graph_intelligence.json + graph_vandal_network.png
Goal:   Xây dựng đồ thị Bipartite (User ↔ Article) và áp dụng:
        1. SuspicionRank  — PageRank lan truyền nghi ngờ qua graph
        2. Community Detection (Louvain) — Phát hiện cụm sockpuppet
        3. Label Propagation — Bán giám sát: lan nhãn vandal → hàng xóm
        4. Graph Metrics — Degree, Betweenness, Clustering Coefficient
        
Methods: NetworkX + Louvain + matplotlib
Novel:   Biến bài toán NLP/Rules → bài toán Graph Mining
────────────────────────────────────────────────────────────
"""
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

import networkx as nx
from networkx.algorithms import bipartite
try:
    import community as community_louvain  # python-louvain
except ImportError:
    community_louvain = None

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Config ──
DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def load_all_data():
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


# ═══════════════════════════════════════════════════════════
# 1. BUILD BIPARTITE GRAPH
# ═══════════════════════════════════════════════════════════
def build_bipartite_graph(edits):
    """
    Xây dựng đồ thị 2 phía (Bipartite Graph):
      - Node loại 1: USER  (bipartite=0)
      - Node loại 2: ARTICLE (bipartite=1)
      - Edge: User edits Article, trọng số = suspicion level
    
    Node features:
      User:    avg_rule_score, vandal_count, edit_count
      Article: times_vandalized, unique_editors
    """
    G = nx.Graph()

    user_stats = defaultdict(lambda: {
        "rule_scores": [], "vandal": 0, "suspicious": 0,
        "edits": 0, "fp_matches": 0,
    })
    article_stats = defaultdict(lambda: {
        "vandal": 0, "suspicious": 0, "editors": set(), "edits": 0,
    })

    for e in edits:
        user = f"U:{e['user']}"
        article = f"A:{e.get('title', 'unknown')}"
        
        rule_score = float(e.get("rule_score", 0))
        cls = e.get("llm_classification", "")
        is_fp = e.get("is_serial_vandal") == "True"

        # Update stats
        u = user_stats[user]
        u["rule_scores"].append(rule_score)
        u["edits"] += 1
        if cls == "VANDALISM": u["vandal"] += 1
        elif cls == "SUSPICIOUS": u["suspicious"] += 1
        if is_fp: u["fp_matches"] += 1

        a = article_stats[article]
        a["edits"] += 1
        a["editors"].add(user)
        if cls == "VANDALISM": a["vandal"] += 1
        elif cls == "SUSPICIOUS": a["suspicious"] += 1

        # Edge weight = suspicion aggregation
        edge_weight = rule_score
        if cls == "VANDALISM": edge_weight += 5.0
        elif cls == "SUSPICIOUS": edge_weight += 2.0
        if is_fp: edge_weight += 3.0

        if G.has_edge(user, article):
            G[user][article]["weight"] += edge_weight
            G[user][article]["edit_count"] += 1
        else:
            G.add_edge(user, article, weight=edge_weight, edit_count=1)

    # Set node attributes
    for user, stats in user_stats.items():
        avg_rule = sum(stats["rule_scores"]) / len(stats["rule_scores"]) if stats["rule_scores"] else 0
        suspicion = (stats["vandal"] * 3 + stats["suspicious"]) / max(stats["edits"], 1)
        G.nodes[user]["bipartite"] = 0
        G.nodes[user]["type"] = "user"
        G.nodes[user]["avg_rule_score"] = round(avg_rule, 2)
        G.nodes[user]["vandal_count"] = stats["vandal"]
        G.nodes[user]["suspicious_count"] = stats["suspicious"]
        G.nodes[user]["edit_count"] = stats["edits"]
        G.nodes[user]["suspicion_seed"] = round(suspicion, 3)
        G.nodes[user]["fp_matches"] = stats["fp_matches"]

    for article, stats in article_stats.items():
        vulnerability = (stats["vandal"] * 3 + stats["suspicious"]) / max(stats["edits"], 1)
        G.nodes[article]["bipartite"] = 1
        G.nodes[article]["type"] = "article"
        G.nodes[article]["vandal_count"] = stats["vandal"]
        G.nodes[article]["unique_editors"] = len(stats["editors"])
        G.nodes[article]["vulnerability"] = round(vulnerability, 3)

    return G


# ═══════════════════════════════════════════════════════════
# 2. SUSPICIONRANK (PageRank variant)
# ═══════════════════════════════════════════════════════════
def suspicion_rank(G):
    """
    SuspicionRank: Biến thể của PageRank dùng cho lan truyền nghi ngờ.
    
    Ý tưởng: User nghi ngờ → bài viết họ edit cũng nghi ngờ → 
             các user KHÁC edit cùng bài đó cũng bị tăng suspicion.
    
    Personalization vector: dùng suspicion_seed (từ Rule+LLM) 
    làm "khởi tạo" để PageRank lan truyền.
    """
    # Build personalization vector từ suspicion seeds
    personalization = {}
    for node in G.nodes():
        if G.nodes[node].get("type") == "user":
            seed = G.nodes[node].get("suspicion_seed", 0)
            personalization[node] = max(seed, 0.01)  # Minimum non-zero
        else:
            vuln = G.nodes[node].get("vulnerability", 0)
            personalization[node] = max(vuln, 0.01)

    # Run Personalized PageRank
    try:
        pr = nx.pagerank(G, alpha=0.85, personalization=personalization,
                         weight="weight", max_iter=100)
    except nx.PowerIterationFailedConvergence:
        pr = nx.pagerank(G, alpha=0.85, max_iter=50)

    # Normalize scores to 0-100 range
    max_pr = max(pr.values()) if pr else 1
    for node in pr:
        pr[node] = round(pr[node] / max_pr * 100, 2)

    # Extract user rankings
    user_ranks = []
    for node, score in sorted(pr.items(), key=lambda x: -x[1]):
        if G.nodes[node].get("type") == "user":
            user_ranks.append({
                "user": node.replace("U:", ""),
                "suspicion_rank": score,
                "edit_count": G.nodes[node].get("edit_count", 0),
                "vandal_count": G.nodes[node].get("vandal_count", 0),
                "degree": G.degree(node),
            })

    # Extract article rankings
    article_ranks = []
    for node, score in sorted(pr.items(), key=lambda x: -x[1]):
        if G.nodes[node].get("type") == "article":
            article_ranks.append({
                "article": node.replace("A:", ""),
                "risk_rank": score,
                "vandal_count": G.nodes[node].get("vandal_count", 0),
                "unique_editors": G.nodes[node].get("unique_editors", 0),
            })

    return pr, user_ranks[:20], article_ranks[:15]


# ═══════════════════════════════════════════════════════════
# 3. USER-USER PROJECTION + COMMUNITY DETECTION (Louvain)
# ═══════════════════════════════════════════════════════════
def project_user_graph(G):
    """
    User-User Projection: Biến Bipartite Graph → User-only Graph.
    
    Hai user được NỐI VỚI NHAU nếu cùng edit 1 bài.
    Edge weight = tổng suspicion trên bài chung.
    
    Ví dụ: UserA edit "Article X", UserB cũng edit "Article X"
           → thêm edge (UserA, UserB, weight = suspicion_of_article_X)
    
    Kết quả: Đồ thị ĐẶC HƠN rất nhiều → Louvain work hiệu quả hơn.
    """
    user_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "user"]
    article_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "article"]
    
    UG = nx.Graph()
    
    # For each article, connect all pairs of users who edited it
    for article in article_nodes:
        editors = list(G.neighbors(article))
        if len(editors) < 2:
            continue
        
        article_vuln = G.nodes[article].get("vulnerability", 0)
        
        for i in range(len(editors)):
            for j in range(i + 1, len(editors)):
                u1, u2 = editors[i], editors[j]
                
                # Edge weight = sum of both users' edge weights to this article
                w1 = G[u1][article].get("weight", 1)
                w2 = G[u2][article].get("weight", 1)
                shared_weight = (w1 + w2) * (1 + article_vuln)
                
                shared_article = article.replace("A:", "")
                
                if UG.has_edge(u1, u2):
                    UG[u1][u2]["weight"] += shared_weight
                    UG[u1][u2]["shared_articles"].append(shared_article)
                else:
                    UG.add_edge(u1, u2, weight=shared_weight, 
                               shared_articles=[shared_article])
    
    # Copy user attributes
    for node in user_nodes:
        if node in UG.nodes():
            for key, val in G.nodes[node].items():
                UG.nodes[node][key] = val
        else:
            # Isolated users (only edited unique articles)
            UG.add_node(node)
            for key, val in G.nodes[node].items():
                UG.nodes[node][key] = val
    
    return UG


def detect_communities(G, UG, pr):
    """
    Louvain Community Detection trên User-User Projection Graph.
    
    So với chạy trên Bipartite:
    - Bipartite: 344 components, graph quá thưa → Louvain yếu
    - Projected: Users nối trực tiếp qua shared articles → Louvain mạnh hơn rất nhiều
    """
    if community_louvain is None:
        return [], {}

    # Run Louvain on the PROJECTED User-User graph (denser!)
    # Only on connected subgraph
    connected_nodes = [n for n in UG.nodes() if UG.degree(n) > 0]
    if len(connected_nodes) < 2:
        return [], {}
    
    subUG = UG.subgraph(connected_nodes).copy()
    partition = community_louvain.best_partition(subUG, weight="weight", resolution=1.0)

    # Analyze each community
    communities = defaultdict(lambda: {
        "users": [], "total_suspicion": 0,
        "vandal_users": 0, "total_edits": 0,
        "shared_articles": set(),
    })

    for node, comm_id in partition.items():
        c = communities[comm_id]
        node_data = UG.nodes[node]
        node_pr = pr.get(node, 0)

        c["users"].append({
            "name": node.replace("U:", ""),
            "rank": node_pr,
            "vandal": node_data.get("vandal_count", 0),
            "edits": node_data.get("edit_count", 0),
        })
        c["total_suspicion"] += node_pr
        c["total_edits"] += node_data.get("edit_count", 0)
        if node_data.get("vandal_count", 0) > 0:
            c["vandal_users"] += 1
        
        # Collect shared articles from edges
        for neighbor in subUG.neighbors(node):
            if partition.get(neighbor) == comm_id:
                edge_data = subUG[node][neighbor]
                for art in edge_data.get("shared_articles", []):
                    c["shared_articles"].add(art)

    # Classify communities
    community_list = []
    for comm_id, c in communities.items():
        if len(c["users"]) < 2:
            continue

        avg_suspicion = c["total_suspicion"] / max(len(c["users"]), 1)
        vandal_ratio = c["vandal_users"] / max(len(c["users"]), 1)

        if vandal_ratio >= 0.5:
            threat = "🔴 SOCKPUPPET RING"
        elif vandal_ratio > 0 or avg_suspicion > 30:
            threat = "🟠 SUSPICIOUS CLUSTER"
        elif avg_suspicion > 15:
            threat = "🟡 WATCH LIST"
        else:
            threat = "🟢 NORMAL"

        community_list.append({
            "community_id": comm_id,
            "threat": threat,
            "user_count": len(c["users"]),
            "vandal_users": c["vandal_users"],
            "vandal_ratio": round(vandal_ratio * 100, 1),
            "avg_suspicion_rank": round(avg_suspicion, 1),
            "total_edits": c["total_edits"],
            "shared_articles": list(c["shared_articles"])[:8],
            "top_users": sorted(c["users"], key=lambda x: -x["rank"])[:5],
        })

    community_list.sort(key=lambda x: -x["avg_suspicion_rank"])
    return community_list[:15], partition


# ═══════════════════════════════════════════════════════════
# 4. LABEL PROPAGATION (Semi-supervised)
# ═══════════════════════════════════════════════════════════
def label_propagation(G):
    """
    Label Propagation Algorithm (Bán giám sát):
    
    - Khởi tạo: User có vandal_count > 0 → label "VANDAL"
    - Lan truyền: Qua các article nodes → user hàng xóm 
      cũng bị "nhiễm" nhãn VANDAL nếu đa số hàng xóm là VANDAL.
    
    Output: Danh sách user bị "nhiễm" vandal label qua propagation
    (= potential undiscovered vandals)
    """
    # Seed labels
    labels = {}
    for node in G.nodes():
        if G.nodes[node].get("type") == "user":
            if G.nodes[node].get("vandal_count", 0) > 0:
                labels[node] = "VANDAL"
            elif G.nodes[node].get("suspicious_count", 0) > 0:
                labels[node] = "SUSPICIOUS"
            else:
                labels[node] = "CLEAN"
        else:
            labels[node] = "ARTICLE"

    # Propagation iterations
    newly_flagged = []
    for iteration in range(3):  # 3 rounds of propagation
        new_labels = dict(labels)
        
        for node in G.nodes():
            if G.nodes[node].get("type") != "user":
                continue
            if labels[node] == "VANDAL":
                continue  # Already labeled

            # Check neighbors (articles this user edited)
            neighbor_vandal_count = 0
            neighbor_total = 0
            for article_neighbor in G.neighbors(node):
                # Check other users who also edited this article
                for user_neighbor in G.neighbors(article_neighbor):
                    if user_neighbor == node: continue
                    if G.nodes[user_neighbor].get("type") != "user": continue
                    neighbor_total += 1
                    if labels[user_neighbor] == "VANDAL":
                        # Weight by edge strength
                        edge_w = G[user_neighbor][article_neighbor].get("weight", 1)
                        neighbor_vandal_count += min(edge_w / 5, 1)

            # Propagation rule: >40% vandal neighbors → flag
            if neighbor_total > 0:
                vandal_ratio = neighbor_vandal_count / neighbor_total
                if vandal_ratio >= 0.4 and labels[node] == "CLEAN":
                    new_labels[node] = "PROPAGATED_SUSPICIOUS"
                    newly_flagged.append({
                        "user": node.replace("U:", ""),
                        "iteration": iteration + 1,
                        "vandal_neighbor_ratio": round(vandal_ratio * 100, 1),
                        "total_neighbors": neighbor_total,
                        "original_label": labels[node],
                    })

        labels = new_labels

    return newly_flagged, labels


# ═══════════════════════════════════════════════════════════
# 5. GRAPH VISUALIZATION
# ═══════════════════════════════════════════════════════════
def visualize_graph(G, pr, partition, communities):
    """
    Tạo visualization cho vandal network graph.
    Chỉ hiển thị nodes có suspicion > threshold.
    """
    # Filter: only show high-suspicion nodes
    threshold = 10  # Top percentile
    high_nodes = [n for n, score in pr.items() if score >= threshold]
    
    if len(high_nodes) < 3:
        high_nodes = sorted(pr, key=lambda x: -pr[x])[:30]

    subG = G.subgraph(high_nodes).copy()
    
    if len(subG.nodes()) < 2:
        print("   ⚠️ Not enough high-suspicion nodes for visualization")
        return None

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    # Layout
    pos = nx.spring_layout(subG, k=2.5, iterations=60, weight="weight", seed=42)

    # Node colors & sizes
    node_colors = []
    node_sizes = []
    for node in subG.nodes():
        node_data = subG.nodes[node]
        score = pr.get(node, 0)
        
        if node_data.get("type") == "user":
            vandal = node_data.get("vandal_count", 0)
            if vandal > 0:
                node_colors.append("#ff4444")  # Red = confirmed vandal
            elif node_data.get("suspicious_count", 0) > 0:
                node_colors.append("#ff8c00")  # Orange = suspicious
            else:
                node_colors.append("#58a6ff")  # Blue = normal user
            node_sizes.append(max(score * 8, 80))
        else:
            if node_data.get("vandal_count", 0) > 0:
                node_colors.append("#ffd700")  # Gold = attacked article
            else:
                node_colors.append("#238636")  # Green = normal article
            node_sizes.append(max(score * 6, 60))

    # Edge colors
    edge_colors = []
    edge_widths = []
    for u, v, data in subG.edges(data=True):
        w = data.get("weight", 1)
        if w > 5:
            edge_colors.append("#ff4444")
            edge_widths.append(min(w / 3, 4))
        elif w > 2:
            edge_colors.append("#ff8c00")
            edge_widths.append(min(w / 2, 3))
        else:
            edge_colors.append("#30363d")
            edge_widths.append(0.5)

    # Draw
    nx.draw_networkx_edges(subG, pos, edge_color=edge_colors,
                           width=edge_widths, alpha=0.6, ax=ax)
    nx.draw_networkx_nodes(subG, pos, node_color=node_colors,
                           node_size=node_sizes, alpha=0.9, ax=ax,
                           edgecolors="#c9d1d9", linewidths=0.5)

    # Labels for high-rank nodes only
    labels = {}
    for node in subG.nodes():
        if pr.get(node, 0) >= 20:
            short_name = node.replace("U:", "").replace("A:", "")
            if len(short_name) > 18:
                short_name = short_name[:16] + ".."
            labels[node] = short_name

    nx.draw_networkx_labels(subG, pos, labels, font_size=7,
                            font_color="#e6edf3", font_weight="bold", ax=ax)

    # Legend
    legend_elements = [
        mpatches.Patch(color="#ff4444", label="Confirmed Vandal"),
        mpatches.Patch(color="#ff8c00", label="Suspicious User"),
        mpatches.Patch(color="#58a6ff", label="Normal User"),
        mpatches.Patch(color="#ffd700", label="Attacked Article"),
        mpatches.Patch(color="#238636", label="Normal Article"),
    ]
    ax.legend(handles=legend_elements, loc="upper left",
              facecolor="#161b22", edgecolor="#30363d",
              labelcolor="#e6edf3", fontsize=9)

    ax.set_title("🕸️ Wikipedia Vandal Network Graph\n(SuspicionRank + Louvain Communities)",
                 fontsize=14, color="#e6edf3", fontweight="bold", pad=15)
    ax.axis("off")

    output_path = REPORT_DIR / "graph_vandal_network.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    return output_path


# ═══════════════════════════════════════════════════════════
# REPORT & MAIN
# ═══════════════════════════════════════════════════════════
def save_report(graph_stats, user_ranks, article_ranks, communities, propagated):
    report = {
        "generated_at": datetime.now().isoformat(),
        "graph_stats": graph_stats,
        "suspicion_rank": {
            "top_users": user_ranks,
            "top_articles": article_ranks,
        },
        "communities": communities,
        "label_propagation": {
            "newly_flagged": len(propagated),
            "details": propagated[:20],
        },
    }
    with open(REPORT_DIR / "graph_intelligence.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def print_summary(graph_stats, user_ranks, article_ranks, communities, propagated):
    print(f"\n   {'='*55}")
    print(f"   🕸️ GRAPH INTELLIGENCE RESULTS")
    print(f"   {'='*55}")

    print(f"\n   📐 BIPARTITE GRAPH:")
    print(f"      Nodes: {graph_stats['total_nodes']} "
          f"(Users: {graph_stats['user_nodes']}, Articles: {graph_stats['article_nodes']})")
    print(f"      Edges: {graph_stats['total_edges']} | "
          f"Density: {graph_stats['density']} | Components: {graph_stats['components']}")

    print(f"\n   🔗 USER-USER PROJECTION:")
    print(f"      Co-editing Edges: {graph_stats.get('projection_edges', 0)} "
          f"(vs {graph_stats['total_edges']} bipartite)")
    print(f"      Connected Users: {graph_stats.get('projection_connected', 0)} "
          f"/ {graph_stats['user_nodes']}")

    print(f"\n   🏆 SUSPICIONRANK (Top 5 Users):")
    for u in user_ranks[:5]:
        print(f"      [{u['suspicion_rank']:.1f}/100] {u['user']} "
              f"(degree: {u['degree']}, vandal: {u['vandal_count']})")

    print(f"\n   🎯 MOST AT-RISK ARTICLES (Top 5):")
    for a in article_ranks[:5]:
        print(f"      [{a['risk_rank']:.1f}/100] {a['article'][:40]} "
              f"(vandal: {a['vandal_count']}, editors: {a['unique_editors']})")

    print(f"\n   🕵️ LOUVAIN COMMUNITIES (on Projected Graph):")
    print(f"      Clusters Found: {len(communities)}")
    for c in communities[:5]:
        top_users = ", ".join(u["name"] for u in c["top_users"][:3])
        articles = ", ".join(c.get("shared_articles", [])[:3])
        print(f"      {c['threat']} | {c['user_count']} users | "
              f"Vandal: {c['vandal_ratio']}% | {top_users}")
        if articles:
            print(f"         Shared: {articles}")

    print(f"\n   🔮 LABEL PROPAGATION:")
    print(f"      Newly Flagged (via graph): {len(propagated)}")
    for p in propagated[:5]:
        print(f"      ⚠️ {p['user']} (iter {p['iteration']}, "
              f"{p['vandal_neighbor_ratio']}% vandal neighbors)")


def main():
    print("🕸️ Graph Intelligence Engine Running...")
    edits = load_all_data()
    if not edits:
        print("   ⚠️ No data. Run previous stages.")
        return

    print(f"   📂 Loaded {len(edits)} edits")

    # 1. Build Bipartite Graph
    print("   🔨 Building Bipartite Graph...")
    G = build_bipartite_graph(edits)
    
    user_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "user"]
    article_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "article"]

    # 2. Project to User-User Graph
    print("   🔗 Projecting to User-User Co-editing Graph...")
    UG = project_user_graph(G)
    projection_edges = UG.number_of_edges()
    projection_connected = sum(1 for n in UG.nodes() if UG.degree(n) > 0)
    print(f"      → {projection_edges} co-editing edges, {projection_connected} connected users")
    
    graph_stats = {
        "total_nodes": G.number_of_nodes(),
        "user_nodes": len(user_nodes),
        "article_nodes": len(article_nodes),
        "total_edges": G.number_of_edges(),
        "density": round(nx.density(G), 6),
        "components": nx.number_connected_components(G),
        "projection_edges": projection_edges,
        "projection_connected": projection_connected,
        "projection_density": round(nx.density(UG) if UG.number_of_nodes() > 1 else 0, 6),
    }

    # 3. SuspicionRank (on Bipartite)
    print("   📊 Computing SuspicionRank (Personalized PageRank)...")
    pr, user_ranks, article_ranks = suspicion_rank(G)

    # 4. Community Detection (on PROJECTED graph)
    print("   🕵️ Running Louvain on User-User Projection...")
    communities, partition = detect_communities(G, UG, pr)

    # 5. Label Propagation (on Bipartite)
    print("   🔮 Running Label Propagation...")
    propagated, labels = label_propagation(G)

    # 6. Visualization
    print("   🎨 Generating Network Visualization...")
    viz_path = visualize_graph(G, pr, partition, communities)
    if viz_path:
        print(f"   ✅ Graph saved: {viz_path}")

    # 7. Save & Print
    report = save_report(graph_stats, user_ranks, article_ranks, communities, propagated)
    print_summary(graph_stats, user_ranks, article_ranks, communities, propagated)
    print(f"\n   ✅ Graph intelligence saved to: {REPORT_DIR / 'graph_intelligence.json'}")


if __name__ == "__main__":
    main()

