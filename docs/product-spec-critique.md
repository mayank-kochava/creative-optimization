---
id: product-spec-critique
title: Product Specification Critique
---

# Spec Critique: Creative Intelligence Platform

**Spec Version:** PRD-creative-intelligence-platform.md  
**Reviewed By:** AI QA Architect  
**Date:** 2026-05-14

## Summary

- **Critical Issues:** 5
- **High Issues:** 6
- **Medium Issues:** 4
- **Blocking:** Yes — 3 issues will break the live demo if unaddressed

---

## 1. Critical Logic Gaps

| ID | Issue | Severity | Section | Suggested Fix |
|----|-------|----------|---------|---------------|
| CG-001 | **Qwen2-VL malformed JSON output.** The Analysis Engine sends to Ollama and parses structured JSON — but LLMs occasionally return truncated, invalid, or schema-violating JSON (especially under load or first cold start). No retry logic or schema validation defined. During a live demo, one bad response breaks the entire analysis flow. | Critical | Analysis Engine | Define: JSON schema validation on every response. On parse failure: retry up to 3 times with temperature=0. On third failure: return graceful error with partial data (show whatever scores parsed, flag rest as unavailable). |
| CG-002 | **Ollama not running / model not loaded.** The PRD assumes Ollama is always available at its local HTTP endpoint. No health-check on startup, no user-facing error if model is absent. Demo starts, upload succeeds, analysis call hangs or 500s with no explanation. | Critical | Analysis Engine | Define: `/health` endpoint checks Ollama availability on API startup. Analysis endpoint returns 503 with `model_unavailable: true` if Ollama unreachable. Frontend shows "Model loading…" not a blank spinner. |
| CG-003 | **Fatigue detection on insufficient data.** WoW CTR decline requires at least 14 days of daily data (2 full weeks). The PRD doesn't define behavior for creatives with < 14 days of data. All seed creatives on Day 1 of demo will have insufficient data — fatigue feature appears broken. | Critical | Fatigue Detection Module | Define: minimum 7 days required for fatigue computation. Under 7 days: status = `insufficient_data`, badge = "Collecting data…". Seed data must span 30-day synthetic window. |
| CG-004 | **Benchmark corpus not initialised on first run.** The Benchmark Module queries the CVPR 2017 corpus for percentile ranking — but there is no spec for how/when that corpus is indexed into the DB. If Docker Compose starts fresh with empty DB, first analysis call finds no benchmark data and returns null percentile. Demo shows "N/A" for every creative. | Critical | Benchmark Module | Define: Docker Compose `db:seed` step that pre-indexes benchmark corpus before API starts. Spec must include corpus initialisation as a required startup step, not an optional background job. |
| CG-005 | **Race condition on duplicate detection.** If two identical creatives are uploaded simultaneously (or rapidly in sequence), both pass the pHash check before either is committed to DB. Both are inserted as non-duplicates. The duplicate pair is never detected. | Critical | Deduplication Module | Define: pHash lookup + insert must be a single DB transaction with a unique constraint on the hash column (within Hamming distance — use advisory lock or serialisable isolation for the lookup-then-insert). |

---

## 2. Testability Review

### Vague Requirements Found

| FR ID | Original Text | Problem | Suggested Rewrite (Gherkin) |
|-------|---------------|---------|----------------------------|
| US-10 | "analysis to complete within 30 seconds of upload" | Ambiguous: 30s from upload complete? From API call? Until UI renders? Not tied to hardware spec. Not reproducible across environments. | **Given** an image creative under 5MB is uploaded, **When** the `/creatives/{id}` analysis endpoint is polled, **Then** the response must include all 7 dimension scores within 30 seconds of the POST `/campaigns/{id}/creatives` returning 201, measured on M4 Pro 24GB with Qwen2-VL-7B Q4 loaded. |
| US-3 | "annotated with bounding boxes highlighting detected faces, text regions, CTA elements, and product placement" | "Product placement" detection has no ground truth. Cannot write a passing/failing automated test. | Remove "product placement" from the automated test scope. **Given** an image containing a human face, **When** the annotation pipeline runs, **Then** at least one annotation of type `face` with confidence > 0.6 must be returned. Test CTA detection separately with a fixture image containing known button text. |
| US-5 | "Top 28% of gaming app creatives" | Percentile value is an example, not a requirement. Benchmark corpus composition unstated. Will break if corpus changes. | **Given** the benchmark corpus contains ≥ 1,000 indexed creatives, **When** a creative analysis completes, **Then** the response must include `benchmark_percentile` as an integer 1–100 and `benchmark_corpus_size` as an integer ≥ 1,000. |
| Impl | "Resistant to resize, recompression, watermarks" (pHash spec) | No tolerance defined. Recompressed to JPEG quality 10? Quality 80? These have very different Hamming distances. | **Given** the same image saved at JPEG quality 80 and quality 40, **When** pHash is computed for both, **Then** Hamming distance must be ≤ 10. **Given** the same image with a 50×50 pixel logo watermark added, **When** pHash is computed for both, **Then** Hamming distance must be ≤ 10. |
| Impl | "No creative data leaves Kochava infrastructure" | Not testable without network monitoring. Zero enforcement mechanism in the spec. | Add explicit requirement: the Docker Compose network must set `external: false` for all services except the DB seed download. Integration test must assert no outbound HTTP calls are made during analysis (mock Ollama at network layer and assert no other external calls). |

---

## 3. Risk Mitigation Audit

| Risk | Mitigation in Spec? | Verdict | Notes |
|------|---------------------|---------|-------|
| CVPR 2017 dataset requires registration/academic form to download | No | **FAIL** | Spec assumes dataset is downloadable. In practice, [https://people.cs.pitt.edu/~kovashka/ads/](https://people.cs.pitt.edu/~kovashka/ads/) requires a form request. Download may take 24–48h. No fallback corpus defined if download is delayed. Mitigation needed: define a minimal fallback corpus of 500 public-domain ad images that can be bundled with the repo. |
| Qwen2-VL-7B cold start latency | No | **FAIL** | First inference after model load takes 30–60s on M4 Pro (memory mapping). During demo, if Ollama restarts, first analysis will dramatically exceed the 30s SLA. Spec must require model pre-warming: a dummy inference on API startup. |
| Synthetic KPI seed data looks fake | No | **FAIL** | Exec audience will notice if every creative has suspiciously round numbers (CTR: 3.00%, CVR: 25.00%). No spec for seed data realism. Mitigation: define seed data generation with realistic noise (CTR 2.8–4.1%, daily variance ±15%). |
| Video codec incompatibility with ffmpeg | No | **FAIL** | PRD says "accepts MP4/MOV/AVI" but doesn't specify which codecs. H.265/HEVC, VP9, AV1 may fail silently with older ffmpeg. No fallback to re-encode. Mitigation: spec must define supported codec list and return 415 Unsupported Media Type for others. |
| Demo machine runs out of RAM | No | **FAIL** | Qwen2-VL-7B Q4 = ~8GB. PostgreSQL = ~500MB. Next.js dev server = ~500MB. Docker overhead = ~1GB. Total ≈ 10GB. M4 Pro 24GB has headroom, but if Chrome + Slack + Xcode are running during demo, OOM is possible. Mitigation: spec must define minimum free RAM requirement (12GB) and include pre-demo checklist. |

---

## 4. Missed Edge Cases (Top 3)

1. **Same creative uploaded to the same campaign twice by the same user.** Duplicate detection will correctly flag it as a duplicate — of itself (its own `creative_id`). The response will say "this creative already exists as Creative ID 47." UX is confusing: the user just uploaded it, of course it exists. Spec needs to distinguish between *self-duplicate* (same campaign, same user, seconds apart) and *cross-platform duplicate* (same creative fingerprint found on a different campaign/platform). These are different UX messages and different severities.

2. **Video shorter than 3 seconds.** The ingestion module extracts keyframes at `0s, 3s, 50%, end`. A 2-second video has no frame at 3s. ffmpeg will either error or silently skip. The analysis engine then receives fewer keyframes than expected, and the prompt (written for 4 keyframes) will produce degraded output. Spec must define minimum video duration (e.g. 3 seconds) with a clear rejection message, and the prompt must be resilient to 1–4 keyframes.

3. **Benchmark corpus percentile for non-advertising images.** Nothing in the spec prevents a user from uploading a photo of their lunch. The analysis engine will score it (probably low across most dimensions), and it will receive a benchmark percentile against real ad creatives. The output will be nonsensical but not obviously wrong. For a demo this could be embarrassing if someone uploads a test image. Mitigation: add a pre-analysis content check — if Qwen2-VL confidence on "is this an advertisement?" is below a threshold, reject with a clear message before running full analysis.

---

## Recommendations

1. **(Blocking — fix before Day 2)** Define JSON schema validation + retry logic for the Analysis Engine (CG-001). This is the single most likely demo failure mode. Write the Pydantic response model first, before any other analysis code.
2. **(Blocking — fix before Day 3)** Specify Docker Compose seed step that pre-indexes benchmark corpus and pre-generates synthetic KPI data with realistic noise spanning 30 days. Without this, both fatigue detection and benchmark percentile appear broken on first run (CG-003, CG-004).
3. **(Blocking — fix before Day 6)** Add Ollama health-check + model pre-warming to API startup (CG-002). Demo machine must not cold-start the model during the pitch.
4. **(High — fix in spec before eng-plan)** Define supported video codec list and minimum duration. Reject early with clear error. Prevents silent ffmpeg failures.
5. **(High — add to seed data spec)** Ensure at least 3 creatives in seed data are in "fatiguing" state (WoW CTR decline > 20%) so the fatigue detection feature is visibly demonstrated during the pitch.
6. **(Medium — add to testing spec)** Define network isolation requirement and add to Docker Compose config. Supports the "no data leaves our infra" claim with verifiable enforcement.
