"""
Stage 07: REPORT SYNTHESIS & DASHBOARD EXPORT
------------------------------------------------------------
Input:  reports/intelligence_master.json
Output: reports/final_forensic_report.md
        data/dashboard_export.json
------------------------------------------------------------
"""

import json
from pathlib import Path
from datetime import datetime

# -- Config --
REPORT_DIR = Path(__file__).parent / "reports"
DASH_DIR = Path(__file__).parent / "data"


def generate_report():
    master_f = REPORT_DIR / "intelligence_master.json"
    if not master_f.exists():
        print("  Master intelligence file not found.")
        return

    with open(master_f, "r", encoding="utf-8") as f:
        data = json.load(f)

    dist = data.get('distribution', {})
    stats = data.get('statistics', {})
    methodology = data.get('methodology', {})

    report_md = f"""# WIKI-STREAM FORENSIC INTELLIGENCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## OVERVIEW
- **Total Edits Analyzed**: {data['total']}
- **Threat Distribution**:
  - **BLOCK**: {dist.get('BLOCK', 0)}
  - **FLAG**: {dist.get('FLAG', 0)}
  - **REVIEW**: {dist.get('REVIEW', 0)}
  - **SAFE**: {dist.get('SAFE', 0)}

## FUSION STATISTICS
- **Mean Verdict Score**: {stats.get('mean_verdict', 'N/A')}
- **Average Uncertainty Width**: {stats.get('avg_uncertainty', 'N/A')}
- **Average Deng Entropy**: {stats.get('avg_deng_entropy', 'N/A')}
- **High-Conflict Edits** (k > 0.3): {stats.get('high_conflict_edits', 0)}
- **Fusion Methods**: {stats.get('fusion_methods', {})}

## HIGH-PRIORITY THREATS
| User | Title | Score | Action | DS Belief | Conflict |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for v in data.get('top_threats', [])[:20]:
        report_md += (
            f"| {v['user']} | {v['title'][:40]} | {v['score']}% | {v['action']} "
            f"| {v.get('ds_belief', 'N/A')} | {v.get('ds_conflict', 'N/A')} |\n"
        )

    report_md += f"""
## METHODOLOGY (ITEFB v3.0)

**Information-Theoretic Evidence Fusion Framework for Behavioral Threat Analysis**

This report was synthesized using a **3-layer theoretical framework** combining
Information Theory, Dempster-Shafer Evidence Theory, and Behavioral Modeling.

### Layer 1: Multi-Scale Information Theory (Feature Extraction)
- **Shannon Entropy** H(X) = -Σ p(x)·log₂(p(x)): classical randomness measure
- **Rényi Entropy** H_α(X) = 1/(1-α)·log₂(Σ p^α): parameterized generalization
  - α=0.5: amplifies rare characters (gibberish detection)
  - α=2 (collision entropy): penalizes dominant characters (spam detection)
  - Rényi spread (H₀.₅ - H₂): distribution shape anomaly indicator
- **Tsallis Entropy** S_q(X) = 1/(q-1)·(1 - Σ p^q): non-extensive, correlation-sensitive
- **KL-Divergence** D_KL(P||Q): distribution anomaly vs. legitimate Wikipedia text
- **Kolmogorov Complexity** (zlib proxy): compression ratio for structure detection
- **Normalized Compression Distance**: universal parameter-free similarity metric

### Layer 2: Advanced Evidence Theory (Fusion)
- **Adaptive DS Combination**: selects optimal rule based on conflict level:
  - Low conflict (k < 0.3): **Murphy's Modified Rule** (order-independent averaging)
  - High conflict (k ≥ 0.3): **PCR5** (Smarandache-Dezert proportional redistribution)
- **Evidence Discounting** (Shafer, 1976): dynamic per-source reliability weighting
- **Deng Entropy**: generalized Shannon entropy for DS mass functions — measures
  residual uncertainty AFTER fusion (feeds back to decision thresholds)
- **Pignistic Transformation** (Smets TBM, 1990): principled BPA → probability
  for decision-making (distributes uncertainty mass equally among hypotheses)
- **Belief/Plausibility Interval**: [Bel(V), Pl(V)] captures assessment certainty
- **{methodology.get('anomaly_detection', 'Isolation Forest')}**: extended 9-feature anomaly detection

### Layer 3: Behavioral Modeling
- **{methodology.get('reputation', 'Beta-Bayesian')}** reputation: user trust as Beta(α,β) distribution
- **Dual Graph Ranking**: SuspicionRank (PageRank) + HITS (Hub-Authority decomposition)
  - Hub score = user suspicion, Authority score = article vulnerability
- **Writeprints-MCD Attribution**: expanded stylometric features (11 ratios + bigrams + NCD)
  with Minimum Covariance Determinant robust estimation (Rousseeuw, 1984)
- **Benford's Law**: edit size distribution test for non-natural patterns

### Final Verdict Score
```
Verdict = BetP(vandalism) × 0.65 + IsolationForest × 0.10
        + Reputation × 0.10 + Graph(PageRank+HITS) × 0.10
        + ArticleAuthority × 0.05
```
Where BetP is the Pignistic probability, and action thresholds are
dynamically adjusted by Deng entropy (high uncertainty → more conservative).
"""

    with open(REPORT_DIR / "final_forensic_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    # Dashboard export
    dash_data = {
        "stats": dist,
        "methodology": methodology,
        "statistics": stats,
        "alerts": data.get('top_threats', [])[:30],
    }
    with open(DASH_DIR / "dashboard_export.json", "w", encoding="utf-8") as f:
        json.dump(dash_data, f, indent=4, ensure_ascii=False)

    print(f"  Report: reports/final_forensic_report.md")
    print(f"  Dashboard: data/dashboard_export.json")


if __name__ == "__main__":
    generate_report()
