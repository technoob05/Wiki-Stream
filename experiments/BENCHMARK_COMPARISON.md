# BENCHMARK COMPARISON GUIDE — ITEFB v3.0

## Mục tiêu

So sánh ITEFB (hệ thống của mình) với các hệ thống vandalism detection hiện có,
trên CÙNG dataset, CÙNG metric, để chứng minh methodology chuẩn.

---

## 1. Dataset chuẩn để benchmark

### PAN-WVC-10 (KHUYÊN DÙNG — dataset chuẩn nhất)

| Field | Value |
|-------|-------|
| Tên | PAN Wikipedia Vandalism Corpus 2010 |
| Size | **32,452 edits** trên 28,468 articles |
| Vandalism | **2,391** (tỉ lệ **7.4%**) |
| Ngôn ngữ | English Wikipedia only |
| Ground truth | `gold-annotations.csv` — binary: `"regular"` hoặc `"vandalism"` |
| Annotation | 753 crowdworkers (AMT), >150,000 votes, ≥3 annotators/edit |
| Download | https://zenodo.org/records/3341488 |
| File size | 459.4 MB |
| License | CC-BY-4.0 |
| Metric chính thức | **ROC-AUC** |

**Format:**
```
edits.csv:        editid, oldrevisionid, newrevisionid, edittime, editor, articletitle, editcomment
gold-annotations.csv:  editid, class ("regular" / "vandalism")
article-revisions/     thư mục chứa revision text files
```

### PAN-WVC-11 (Multilingual — nếu muốn test Vietnamese pipeline)

| Field | Value |
|-------|-------|
| Size | **29,949 edits** trên 24,351 articles |
| Vandalism | **2,813** (tỉ lệ **9.4%**) |
| Ngôn ngữ | English (9,985) + German (9,990) + Spanish (9,974) |
| Download | https://zenodo.org/records/3342157 |
| File size | 388.8 MB |
| Metric chính thức | **PR-AUC** (đổi từ ROC-AUC vì class imbalance) |

### Webis-WVC-07 (Nhỏ — chỉ dùng quick test)

| Field | Value |
|-------|-------|
| Size | 940 edits, 301 vandalism (32%) |
| Download | https://zenodo.org/records/3341473 |
| Note | Outdated, chỉ dùng để sanity check |

---

## 2. Baselines cần so sánh

### A. PAN 2010 Leaderboard (ROC-AUC)

| Rank | ROC-AUC | Team | Method |
|------|---------|------|--------|
| 1 | **0.9224** | Mola-Velasco | Random Forest 1000 trees, metadata+text+language features |
| 2 | **0.9035** | Adler et al. (WikiTrust) | Reputation-based, Recall 83.5%, Precision 48.5% |
| 3 | **0.8986** | Javanmardi et al. | UC Irvine |
| 4 | **0.8938** | Chichkov | SC Software Inc. |
| 5 | **0.8799** | Seaward | Univ. Ottawa |

**Paper baseline #1:** Mola-Velasco (arXiv:1210.5560) — "Wikipedia Vandalism Detection Through Machine Learning"

### B. PAN 2011 Leaderboard (PR-AUC)

| Language | Best PR-AUC | Team |
|----------|-------------|------|
| English | **0.8223** | West & Lee (UPenn) — STiki + WikiTrust + NLP |
| German | **0.7059** | West & Lee |
| Spanish | **0.4894** | West & Lee |

### C. ORES/Lift Wing (Wikimedia production system)

| Metric | Value |
|--------|-------|
| ROC-AUC | ~0.95-0.97 (reported) |
| Recall (high-recall mode) | ~90-95% |
| Precision (high-recall mode) | ~30-40% |
| Recall (high-precision mode) | ~50-60% |
| Precision (high-precision mode) | ~90% |

**API (query per revision):**
```
GET https://ores.wikimedia.org/v3/scores/enwiki/{rev_id}?models=damaging|goodfaith
```

**Lift Wing API (mới):**
```bash
curl https://api.wikimedia.org/service/lw/inference/v1/models/enwiki-damaging:predict \
  -X POST -d '{"rev_id": 123456789}'
```

### D. ClueBotNG

| Metric | Value |
|--------|-------|
| Precision | ~95% |
| Recall | ~40-50% |
| FP Rate | <0.1% |
| Design | High-precision bot, auto-reverts |

---

## 3. Evaluation Protocol (phải làm đúng)

### Metrics phải report:
1. **ROC-AUC** — so sánh trực tiếp với PAN 2010
2. **PR-AUC** — so sánh trực tiếp với PAN 2011, metric tốt hơn cho imbalanced data
3. **F1-score** — bổ sung
4. **Precision / Recall** tại các threshold: BLOCK (>72), FLAG (>48), REVIEW (>24)

### Cross-validation:
- **10-fold stratified cross-validation** (chuẩn trong literature)
- Hoặc dùng official PAN train/test split nếu có

### Class imbalance:
- PAN-WVC-10 có 7.4% vandalism → imbalanced
- **KHÔNG** oversample/undersample khi report chính — report trên original distribution
- Có thể report thêm balanced results riêng

### Mapping ITEFB output → binary prediction:
```
ITEFB verdict_score → P(vandalism)
  - Normalize verdict_score/100 → probability [0, 1]
  - Dùng probability này để tính ROC curve và PR curve
  - BLOCK/FLAG → "vandalism", REVIEW/SAFE → "regular" (tại threshold tối ưu F1)
```

---

## 4. So sánh Methodology (bảng cho paper)

| Component | ORES | ClueBotNG | PAN 2010 Winner | PAN 2011 Winner | **ITEFB (Ours)** |
|-----------|------|-----------|-----------------|-----------------|-----------------|
| **Feature Extraction** | | | | | |
| Shannon Entropy | ✗ | ✗ | ✗ | ✗ | ✓ |
| Rényi Entropy (α=0.5,2) | ✗ | ✗ | ✗ | ✗ | ✓ |
| Tsallis Entropy (q=0.5) | ✗ | ✗ | ✗ | ✗ | ✓ |
| KL-Divergence | ✗ | ✗ | ✗ | ✗ | ✓ |
| Kolmogorov (compression) | ✗ | ✗ | ✗ | ✗ | ✓ |
| NCD | ✗ | ✗ | ✗ | ✗ | ✓ |
| Character/word features | ✓ (60-80) | ✓ (100+) | ✓ | ✓ | ✓ |
| **Fusion** | | | | | |
| Supervised ML (RF/GBT/NN) | ✓ (GBT) | ✓ (NN) | ✓ (RF) | ✓ (ensemble) | ✗ |
| Dempster-Shafer | ✗ | ✗ | ✗ | ✗ | ✓ |
| Murphy's Rule | ✗ | ✗ | ✗ | ✗ | ✓ |
| PCR5 (Smarandache-Dezert) | ✗ | ✗ | ✗ | ✗ | ✓ |
| Deng Entropy | ✗ | ✗ | ✗ | ✗ | ✓ |
| Pignistic Transform | ✗ | ✗ | ✗ | ✗ | ✓ |
| Evidence Discounting | ✗ | ✗ | ✗ | ✗ | ✓ |
| **Behavioral** | | | | | |
| User reputation | ✓ (features) | ✗ | ✗ | ✓ (WikiTrust) | ✓ (Beta-Bayesian) |
| Graph ranking | ✗ | ✗ | ✗ | ✗ | ✓ (PageRank+HITS) |
| Stylometry/Fingerprinting | ✗ | ✗ | ✗ | ✗ | ✓ (MCD+NCD) |
| IsolationForest | ✗ | ✗ | ✗ | ✗ | ✓ |
| LLM classification | ✗ | ✗ | ✗ | ✗ | ✓ (Gemma 2) |
| Benford's Law | ✗ | ✗ | ✗ | ✗ | ✓ |
| **Output** | | | | | |
| Point probability | ✓ | ✓ | ✓ | ✓ | ✓ (BetP) |
| Uncertainty interval | ✗ | ✗ | ✗ | ✗ | ✓ ([Bel, Pl]) |
| Conflict measurement | ✗ | ✗ | ✗ | ✗ | ✓ (k coefficient) |
| Residual uncertainty | ✗ | ✗ | ✗ | ✗ | ✓ (Deng entropy) |
| Explainability/provenance | Low | Low | Low | Low | **High** (per-source mass) |

---

## 5. Bạn cần làm gì

### Bước 1: Tải PAN-WVC-10
```bash
wget https://zenodo.org/records/3341488/files/pan-wikipedia-vandalism-corpus-2010.zip
unzip pan-wikipedia-vandalism-corpus-2010.zip
```

### Bước 2: Adapt pipeline cho PAN format
- Map `edits.csv` → pipeline input format
- `oldrevisionid` / `newrevisionid` → dùng Wikipedia API lấy diff (giống Stage 02)
- `editor` → user
- `articletitle` → title
- Ground truth: `gold-annotations.csv` (class = "vandalism" / "regular")

### Bước 3: Chạy pipeline trên PAN-WVC-10
- Chạy 7 stages trên 32,452 edits
- Output: verdict_score cho mỗi edit

### Bước 4: Compute metrics
```python
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score

# verdict_score normalized to [0,1]
scores = [v['score'] / 100 for v in verdicts]
labels = [1 if pan_label == 'vandalism' else 0 for pan_label in pan_labels]

roc_auc = roc_auc_score(labels, scores)      # so sánh PAN 2010
pr_auc = average_precision_score(labels, scores)  # so sánh PAN 2011
```

### Bước 5: So sánh

| System | ROC-AUC | PR-AUC |
|--------|---------|--------|
| PAN 2010 Winner (Mola-Velasco) | 0.9224 | — |
| PAN 2011 Winner (West & Lee) | — | 0.8223 |
| WikiTrust | 0.9035 | — |
| ORES | ~0.96 | — |
| **ITEFB v3.0 (Ours)** | **???** | **???** |

### Có cần tỉa dataset không?
- **KHÔNG** — chạy trên TOÀN BỘ PAN-WVC-10 (32,452 edits)
- Report trên original distribution (7.4% vandalism)
- Dataset đã được thiết kế cho benchmark — đừng filter/sample

### Lưu ý quan trọng:
1. **LLM stage sẽ tốn thời gian** — 32K edits × ~5s/edit = ~45 giờ với Gemma 2 local
   - Có thể skip LLM stage và report "ITEFB without LLM" riêng
   - Hoặc sample 5K edits và note trong paper
2. **Wikipedia API rate limit** — 32K diff fetches cần ~9 giờ (1 req/s)
3. **Fair comparison**: ITEFB là unsupervised/semi-supervised, PAN winners là supervised
   - Đây là **advantage** của ITEFB: không cần training data
   - Nên note rõ trong paper: "Our approach requires no labeled training data"

---

## 6. Novelty Claim (cho paper)

> "To the best of our knowledge, ITEFB is the first Wikipedia vandalism detection
> framework that combines: (1) multi-scale information-theoretic features
> (Shannon, Rényi, Tsallis entropy + KL-divergence + NCD), (2) Dempster-Shafer
> evidence fusion with adaptive combination rules (Murphy/PCR5), pignistic
> decision-making, and Deng entropy uncertainty quantification, (3) behavioral
> modeling through stylometric fingerprinting (MCD-Mahalanobis + NCD), dual graph
> ranking (PageRank + HITS), and Beta-Bayesian reputation, in a unified,
> training-free framework with full decision provenance."

---

## 7. References

- Mola-Velasco (2012). "Wikipedia Vandalism Detection." arXiv:1210.5560
- West & Lee (2011). PAN 2011 Wikipedia Vandalism Detection. CLEF 2011
- Potthast et al. (2010). "Crowdsourcing a Wikipedia Vandalism Corpus." SIGIR 2010
- Halfaker & Geiger (2020). "ORES: Participatory Machine Learning in Wikipedia." CSCW
- PAN 2010 Task: https://pan.webis.de/clef10/pan10-web/wikipedia-vandalism-detection.html
- PAN 2011 Task: https://pan.webis.de/clef11/pan11-web/wikipedia-vandalism-detection.html
- PAN-WVC-10: https://zenodo.org/records/3341488
- PAN-WVC-11: https://zenodo.org/records/3342157
