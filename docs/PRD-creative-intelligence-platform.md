# PRD: Creative Intelligence Platform

**Status:** Draft  
**Author:** mukey@kochava.com  
**Date:** 2026-05-14  
**Timeline:** 1-week MVP for executive pitch

---

## Problem Statement

Mobile marketers running paid acquisition campaigns across Facebook, Google, TikTok, and other platforms have hundreds or thousands of active ad creatives simultaneously. They face four compounding problems:

1. **No unified view** — performance data (CTR, CVR, CPI, ROAS) is siloed per platform. There is no single place to compare creative performance across networks.
2. **Duplicate waste** — the same creative is often uploaded in multiple resized or recompressed variants across platforms, fragmenting attribution data and making performance analysis misleading.
3. **No creative understanding** — marketers know *which* creative performs better, but not *why*. They cannot identify which visual elements, hooks, CTAs, or emotional signals drive performance.
4. **Late fatigue detection** — teams discover a creative has burned out only after CTR has already crashed. By then, budget has been wasted and better creatives were not ready in time.

Competitors (Appsflyer, Singular, Motion App) offer partial solutions to some of these problems. Kochava does not have a native creative intelligence capability today.

---

## Solution

A Creative Intelligence Platform that ingests ad creatives (images and videos), runs local AI analysis to explain *why* a creative works or doesn't, detects duplicate creatives across platforms, and alerts on fatigue before performance crashes.

The platform surfaces actionable insights per creative: a scored report card across 7 dimensions, an annotated visual highlighting detected elements, natural language explanations, competitive benchmarking against 64,000 real ad creatives, and specific improvement recommendations.

All analysis runs on-premise using a local vision-language model (Qwen2-VL-7B via Ollama). No creative data leaves Kochava infrastructure.

---

## User Stories

### Creative Analysis

1. As a mobile marketer, I want to upload an image creative and receive a scored analysis across 7 dimensions, so that I understand at a glance where the creative is strong and where it is weak.
2. As a mobile marketer, I want to see a natural language explanation of why a creative works or doesn't, so that I can communicate the reasoning to my creative team without interpreting raw scores.
3. As a mobile marketer, I want to see my creative annotated with bounding boxes highlighting detected faces, text regions, CTA elements, and product placement, so that I can visually understand what the AI found.
4. As a mobile marketer, I want to upload a video creative and receive analysis of its opening scene, hook type, pacing, and key frames, so that I can improve video ad performance.
5. As a mobile marketer, I want to see a competitive benchmark percentile for my creative (e.g. "Top 28% of gaming ads"), so that I can calibrate my creative quality against industry data.
6. As a mobile marketer, I want to receive 3 specific, actionable recommendations for improving a creative, so that I can brief my design team with clear direction.
7. As a mobile marketer, I want to upload a batch of creatives and see them ranked by predicted effectiveness, so that I can prioritise which creatives to run first.
8. As a creative strategist, I want to see the detected persuasion strategy for each creative (fear appeal, FOMO, aspirational, social proof, rational), so that I can ensure portfolio variety across campaigns.
9. As a creative strategist, I want to see the detected dominant emotion for each creative, so that I can align creative tone with campaign objectives.
10. As a mobile marketer, I want the analysis to complete within 30 seconds of upload, so that the tool fits into my workflow without blocking me.

### Duplicate Detection

11. As a campaign manager, I want the platform to automatically detect when I upload a creative that is a duplicate or near-duplicate of one already in the system, so that I avoid fragmented attribution data.
12. As a campaign manager, I want to see which existing creatives a new upload is a duplicate of, including which platforms those duplicates are running on, so that I can make an informed decision about whether to proceed.
13. As a campaign manager, I want duplicates detected even when the creative has been resized, recompressed, or had a watermark added, so that detection is robust to common platform processing.
14. As a data analyst, I want duplicate creative groups consolidated in reporting, so that performance metrics reflect the true creative concept rather than platform variants.

### Fatigue Detection

15. As a campaign manager, I want the platform to automatically flag creatives where CTR has declined more than 20% week-over-week, so that I am alerted to fatigue before it significantly impacts campaign cost.
16. As a campaign manager, I want fatiguing creatives visually distinguished in the dashboard (red badge, warning icon), so that I can triage them at a glance.
17. As a campaign manager, I want to see the fatigue trend chart (CTR over the last 30 days) for any creative, so that I can judge how fast the decline is accelerating.
18. As a campaign manager, I want to receive a recommendation to refresh or pause a fatiguing creative, so that I know what action to take.

### KPI Dashboard

19. As a mobile marketer, I want a unified dashboard showing CTR, CVR, CPI, and ROAS per creative across all platforms, so that I have a single source of truth for creative performance.
20. As a mobile marketer, I want to filter the dashboard by campaign, platform, creative format (image/video), and date range, so that I can drill into specific segments.
21. As a mobile marketer, I want to sort creatives by any KPI column (best CTR, worst CPI, highest ROAS), so that I can quickly identify winners and underperformers.
22. As a marketing lead, I want to see aggregate KPIs per campaign (not just per creative), so that I can report campaign-level efficiency.
23. As a marketing lead, I want to see which creative in a campaign is responsible for the most spend and the most conversions, so that I can make budget reallocation decisions.

### Campaign Management

24. As a campaign manager, I want to organise creatives into campaigns, so that analysis and KPIs are grouped by campaign context.
25. As a campaign manager, I want to create a new campaign and upload multiple creatives to it in one step, so that onboarding a new campaign is fast.
26. As a campaign manager, I want to see a campaign-level summary card (# creatives, avg effectiveness score, # fatiguing, top performer), so that I can monitor campaign health at a glance.

---

## Implementation Decisions

### Modules

**1. Creative Ingestion Module**
- Accepts image (JPG/PNG/WebP/GIF) and video (MP4/MOV/AVI) uploads via multipart form
- Stores original file in local filesystem (configurable base path)
- Extracts metadata: format, dimensions, duration (video), file size
- For video: extracts keyframes at 0s, 3s, 50%, end using ffmpeg
- Computes pHash immediately on ingestion

**2. Analysis Engine**
- Sends image (or video keyframes) to Qwen2-VL-7B via Ollama HTTP API
- Uses structured prompt with few-shot examples drawn from A³ dataset
- Returns structured JSON: 7 dimension scores (0–10), persuasion strategy, dominant emotion, strengths list, weaknesses list, recommendations list, raw explanation text
- For video: analyses opening keyframe (hook), mid keyframe (body), final keyframe (CTA); synthesises into single report
- Normalises scores against ADS16 human ratings for calibration

**3. Deduplication Module**
- Computes 64-bit perceptual hash (DCT-based pHash) for every ingested creative
- On new upload: queries all existing hashes, computes Hamming distance
- Hamming distance ≤ 10 = duplicate; returns matched creative IDs and platform metadata
- Resistant to resize, recompression, watermark

**4. Fatigue Detection Module**
- Reads per-creative CTR time-series (daily granularity, 30-day window)
- Computes week-over-week CTR change: (current_week_avg − prior_week_avg) / prior_week_avg
- Flags creative as fatiguing if WoW decline ≥ 20%
- Runs as background job (daily recalculation)
- Stores fatigue status + trend data per creative

**5. Benchmark Module**
- Indexes CVPR 2017 dataset (64K ad images) with pre-computed analysis scores
- On new creative analysis completion: computes percentile rank across benchmark corpus by overall effectiveness score
- Returns: percentile, category (if detectable), top-3 similar high-performing creatives from corpus

**6. KPI Aggregation Module**
- Stores per-creative daily metrics: impressions, clicks, installs, spend, revenue
- Computes derived KPIs: CTR = clicks/impressions, CVR = installs/clicks, CPI = spend/installs, ROAS = revenue/spend
- Aggregates to campaign level
- Seeded with synthetic time-series data for demo

**7. REST API Layer (FastAPI)**
- `POST /campaigns` — create campaign
- `GET /campaigns` — list campaigns with aggregate KPIs
- `POST /campaigns/{id}/creatives` — upload creative(s) to campaign
- `GET /campaigns/{id}/creatives` — list creatives with scores + KPIs + fatigue status
- `GET /creatives/{id}` — full creative detail (analysis + KPIs + annotations + benchmark)
- `GET /creatives/{id}/fatigue` — fatigue trend time-series
- `GET /creatives/{id}/duplicates` — duplicate matches

**8. Annotation Pipeline**
- Runs OpenCV on ingested image to detect: face regions (Haar cascade), text bounding boxes (EAST or Tesseract layout), dominant colour regions
- CTA detection: text region with highest contrast + lowest position in frame (heuristic)
- Returns list of annotation objects: {type, bbox: {x, y, w, h}, label, confidence}

### Data Schema (key tables)
- `campaigns`: id, name, platform_tags, created_at
- `creatives`: id, campaign_id, filename, format, dimensions, duration, phash, fatigue_status, created_at
- `creative_analyses`: creative_id, scores (JSON), explanation, persuasion_strategy, emotion, strengths, weaknesses, recommendations, benchmark_percentile, analysed_at
- `creative_annotations`: creative_id, annotation_type, bbox (JSON), label, confidence
- `creative_metrics`: creative_id, date, impressions, clicks, installs, spend, revenue
- `duplicate_pairs`: creative_id_a, creative_id_b, hamming_distance, detected_at

### Tech Stack
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 15, Alembic
- **ML/Vision:** Ollama (Qwen2-VL-7B), OpenCV, Pillow, imagehash, ffmpeg
- **Frontend:** React 18, Next.js 14, Ant Design 5
- **Infrastructure:** Docker Compose (one-command local setup)

---

## Testing Decisions

Good tests verify observable behaviour through public interfaces only. They do not test implementation details, internal state, or private methods.

**What makes a good test here:**
- Input: a real or fixture creative file (image/video)
- Assert: the output JSON structure, score ranges, flag values — not which model was called or how many times

**Modules to test:**

| Module | Test type | What to test |
|---|---|---|
| Deduplication Module | Unit | Same image → Hamming distance 0. Resized version → distance ≤ 10. Completely different image → distance > 10. |
| Fatigue Detection Module | Unit | CTR series with >20% WoW drop → status = fatiguing. CTR series flat → status = healthy. |
| KPI Aggregation Module | Unit | Daily metrics → correct CTR/CVR/CPI/ROAS derivation. Campaign rollup sums correctly. |
| REST API Layer | Integration | Upload creative → 201 + creative ID. Get creative detail → full analysis JSON. Duplicate upload → duplicate flag in response. |
| Analysis Engine | Integration (with Ollama mock) | Structured JSON output schema validated. All 7 scores present and in 0–10 range. Recommendations list non-empty. |
| Annotation Pipeline | Unit | Image with known face → face annotation present. Image with text → text annotation present. |

---

## Out of Scope

- **Live platform connectors** (Facebook Ads API, Google Ads API, TikTok Marketing API) — Phase 1
- **Thompson Sampling / Multi-Armed Bandit traffic optimisation** — needs live traffic data, Phase 1
- **A/B test management** — Phase 1
- **Real-time Kafka/Kinesis streaming pipeline** — Phase 1
- **User authentication and multi-tenancy** — demo uses single-tenant setup
- **Fine-tuning Qwen2-VL on ad datasets** — Phase 1 (MVP uses pre-trained model with few-shot prompting)
- **SKAdNetwork / privacy-preserving attribution** — Phase 2
- **Budget optimisation and bid management** — Phase 2
- **Contextual bandits by geo/device** — Phase 2
- **External cloud deployment** — demo runs locally on M4 Pro

---

## Further Notes

**Datasets used:**
- CVPR 2017 Ads Dataset (64K images + 3.5K videos) — benchmark corpus + persuasion strategy labels
- A³-Dataset (30K images, 120K CoT instruction pairs) — few-shot prompt examples
- Ads-1k (1K videos, multi-modal features) — video seed data
- ADS16 (300 ads, human ratings) — score calibration
- MAdVerse (50K ads, hierarchical classification) — category benchmarks
- AdImageNet (9K display ads, OCR text) — supplementary display ad coverage

**Model:** Qwen2-VL-7B at 4-bit quantisation via Ollama. Runs on M4 Pro 24GB in ~10–15 seconds per image creative. No data leaves local machine.

**Demo strategy:** All demo creatives are pre-analysed and cached. One "live" analysis moment during pitch (fresh creative upload) to demonstrate real capability. Sachin to rehearse demo flow before pitch.

**Architecture principle:** Analysis Engine is model-agnostic behind a clean interface. Swap from Qwen2-VL to any other VLM (cloud or local) by changing one config value. This enables fine-tuned model in Phase 1 without touching product code.
