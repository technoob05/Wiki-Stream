# WIKI-STREAM FORENSIC INTELLIGENCE REPORT
Generated: 2026-03-26 23:55:22

## OVERVIEW
- **Total Edits Analyzed**: 4596
- **Threat Distribution**:
  - **BLOCK**: 18
  - **FLAG**: 147
  - **REVIEW**: 416
  - **SAFE**: 4015

## FUSION STATISTICS
- **Mean Verdict Score**: 9.9
- **Average Uncertainty Width**: 0.598
- **Average Deng Entropy**: 1.948
- **High-Conflict Edits** (k > 0.3): 0
- **Fusion Methods**: {'Murphy': 1615, 'single': 195, 'none': 2786}

## HIGH-PRIORITY THREATS
| User | Title | Score | Action | DS Belief | Conflict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Rht bd | Demolition of Dhanmondi 32 | 83.0% | BLOCK | 0.9007 | 0.0271 |
| TonySt | Negro National League (1920–1931) | 77.9% | BLOCK | 0.7777 | 0.045 |
| Montell 74 | National records in the 200 metres | 77.9% | BLOCK | 0.7659 | 0.0408 |
| Bonaldo ronaldo | Negro National League (1920–1931) | 77.3% | BLOCK | 0.7396 | 0.0621 |
| KeystoneUEA | Tariq Ramadan | 77.3% | BLOCK | 0.7883 | 0.0458 |
| Clariniie | Corpse Party | 77.3% | BLOCK | 0.7713 | 0.0445 |
| ~2026-18527-24 | Kaghan Valley | 75.6% | BLOCK | 0.732 | 0.044 |
| Mixinlord | Cabinet of Morocco | 75.4% | BLOCK | 0.7407 | 0.0592 |
| LionmerterTHE | Classic FM (UK) | 75.4% | BLOCK | 0.6942 | 0.0551 |
| Ldm1954 | Friction | 74.7% | BLOCK | 0.7293 | 0.0581 |
| B.J | Surfside condominium collapse | 74.4% | BLOCK | 0.7734 | 0.0954 |
| ~2026-18440-56 | Surfside condominium collapse | 74.3% | BLOCK | 0.7734 | 0.0954 |
| Sxg169 | Esteri Tebandeke | 74.1% | BLOCK | 0.7655 | 0.0942 |
| Solitude6nv5 | Machines (Biffy Clyro song) | 74.0% | BLOCK | 0.6756 | 0.0453 |
| PizzaKing13 | Medal of the Knesset | 74.0% | BLOCK | 0.6649 | 0.0252 |
| Robby.is.on | Klaas-Jan Huntelaar | 74.0% | BLOCK | 0.7139 | 0.0482 |
| EmyGF | Ikariam | 72.3% | BLOCK | 0.6909 | 0.0464 |
| ~2026-16457-05 | The Captive (2014 film) | 72.2% | BLOCK | 0.6893 | 0.057 |
| ~2026-12083-3 | Esteri Tebandeke | 71.7% | FLAG | 0.7415 | 0.0904 |
| Stepwise Continuous Dysfunction | Januarius Jingwa Asongu | 71.0% | FLAG | 0.6272 | 0.0423 |

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
- **Isolation Forest (extended feature set)**: extended 9-feature anomaly detection

### Layer 3: Behavioral Modeling
- **Beta-Bayesian** reputation: user trust as Beta(α,β) distribution
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
