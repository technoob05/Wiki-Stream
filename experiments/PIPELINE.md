# 🛡️ Wiki-Stream Intelligence Pipeline v3.0

> 7-Stage Production Pipeline for Real-Time Wikipedia Edit Analysis

## Architecture

```
📥 01 Collect → 🔍 02 Extract → ⚖️ 03 Truth → 🤖 04 LLM → 🕵️ 05 Attrib → 🧬 06 Fusion → 📊 07 Report
```

## Stages

### Stage 01: Data Collection (`01_collect_data.py`)
- SSE stream from `stream.wikimedia.org`
- Filters: article namespace only, bots excluded
- Output: `data/{lang}/raw/{timestamp}.csv`

### Stage 02: Feature Extraction (`02_feature_extraction.py`)
Three-pass analysis in a single script:

**[A] Rule Engine** (7 rules):
- `rule:blanking` — Content reduced below 20% of original
- `rule:large_del` — Deletion exceeding 5000 characters
- `rule:no_comment` / `rule:no_comment_big` — No edit summary
- `rule:profanity` — Toxic language detection (EN + VI)
- `rule:anon_ip` — Anonymous IP editor
- `rule:minor_abuse` — "Minor edit" flag with large changes

**[B] Named Entity Diff (NED)** (5 detectors):
- `ned:bio_year_change` — Birth/death year tampering (4.0 pts)
- `ned:name_tamper` — Proper noun near-match alteration (4.0 pts)
- `ned:date_change` — Full date modification (3.5 pts)
- `ned:location_change` — Biographical location swap (3.5 pts)
- `ned:year_change` / `ned:number_change` — General changes (1.0 pts)

**[C] NLP Analysis** (9 checks):
- `nlp:repetitive` / `nlp:random` — Compression-based gibberish
- `nlp:toxic(N)` — Profanity density analysis
- `nlp:markup_del` — Wiki markup destruction
- `nlp:pov_shift` — Sentiment bias injection
- `nlp:test_edit` — Hoax/test patterns
- `nlp:citation_strip(N)` — Source reference removal
- `nlp:ext_link(domain)` — External spam link injection
- `nlp:sneaky_redirect` — Article-to-redirect hijacking

### Stage 03: Ground Truth (`03_ground_truth.py`)
- Wikipedia API verification: was the edit reverted?
- Checks 5 subsequent revisions for revert keywords
- Provides `is_reverted` ground truth label

### Stage 04: LLM Classification (`04_llm_classification.py`)
- Gemma 2 via Ollama (local inference)
- Classifies: `VANDALISM` / `SUSPICIOUS` / `SAFE`
- NED-aware prompt: elevated priority for factual changes
- Ensemble score combining rule + NLP + LLM signals

### Stage 05: User Attribution (`05_user_attribution.py`)
- Stylometric fingerprinting (punctuation, caps, digits, markup ratios)
- Serial vandal matching against fingerprint database
- Similarity threshold: 0.85

### Stage 06: Intelligence Fusion (`06_intelligence_fusion.py`)
- **SuspicionRank**: PageRank-based graph analysis
- **Bayesian Reputation**: Probabilistic user trust scoring
- **Dempster-Shafer**: Evidence combination rule
- **Unified Verdict**: Weighted score → BLOCK / FLAG / REVIEW / SAFE

### Stage 07: Report Generator (`07_report_generator.py`)
- `reports/final_forensic_report.md` — Human-readable report
- `reports/intelligence_master.json` — Machine-readable data
- `data/dashboard_export.json` — Frontend-ready payload

## Execution

```bash
python 00_pipeline_manager.py
```

## Requirements
- Python 3.10+
- Ollama with `gemma2:latest` running on port 11434
- Dependencies: `requests`, `tqdm`, `numpy`, `networkx`, `scikit-learn`
