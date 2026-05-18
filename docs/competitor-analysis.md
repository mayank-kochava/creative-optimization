# Competitor Analysis — Creative Optimization Platforms

**Purpose:** Executive pitch support for Sachin's US presentation. Identifies gaps where Kochava differentiates.

**Research date:** May 2026

---

## Competitive Landscape

### 1. AppsFlyer — Creative Management Hub

**Website:** appsflyer.com/products/measurement/creative-optimization/

**What they have:**
- AI element analysis: breaks creatives into scenes, text, visuals, and audio components
- Creative similarity analysis: groups variants by visual attributes across channels
- Full-funnel performance tracking: impressions → clicks → installs → in-app events → LTV
- Smart search and tagging by visuals, text, themes, or performance
- Automated creative library organization with naming convention bypass
- BI tool and data warehouse export (seamless streaming analytics)
- Historical performance validation for concept testing
- Claimed results: 50% CTR improvement, 15% ROAS improvement, 10% CPI decrease, 2x faster iteration

**What they lack:**
- No natural language explanation of WHY a creative scores well — element breakdown only
- No bounding-box annotation (no visual overlay showing what the model sees)
- No true duplicate detection — similarity grouping ≠ pHash (groups themes, not near-identical images)
- Requires AppsFlyer attribution SDK — zero value for non-AppsFlyer customers
- No on-premise / local model option — all data goes through their cloud

---

### 2. Singular — Creative IQ

**Website:** singular.net

**What they have:**
- 17 AI dimensions scored 0–10: composition, color harmony, motion intensity, brand presence, emotional tone, CTA clarity, etc.
- Cross-channel creative performance correlation
- Automated creative tagging from visual AI
- Performance vs. score correlation charts
- Bulk creative import

**What they lack:**
- No natural language explanation — scores only, no "why"
- No bounding-box annotation / visual heatmap overlay
- No duplicate detection (pHash or otherwise)
- Requires Singular attribution SDK
- No on-premise model option

---

### 3. Segwise — AI Creative Analytics

**Website:** segwise.ai

**What they have:**
- 200+ AI-generated creative tags ("outdoor", "female lead", "promotional price overlay", "urgency text", etc.)
- Tag-level performance correlation across campaigns
- Unique: playable ad analysis — only tool supporting interactive ad format analysis for mobile games
- Supports 15+ ad networks and all 4 major MMPs (AppsFlyer, Adjust, Singular, Kochava)
- Anomaly detection — flags unusual spend or CTR changes
- Slack and webhook alerts for creative fatigue
- AI creative generation (beta)

**What they lack:**
- No holistic AI score (0–10) — tag presence/absence only, no composite scoring
- No visual annotation overlay
- No pHash duplicate detection
- Requires MMP integration (aggregates from your existing MMP, but data still flows through their cloud)
- No on-premise model option

---

### 4. VidMob — Creative Intelligence Platform

**Website:** vidmob.com

**What they have:**
- Enterprise-grade AI creative scoring
- Frame-by-frame video analysis (attention, brand safety, emotional engagement)
- Creative benchmarks by vertical (retail, gaming, finance)
- Integration with Meta, Google, TikTok ad APIs (direct, no MMP required)
- Maddie AI assistant for creative insights
- Creator marketplace connecting brands with vetted creators
- Brand safety and compliance scoring

**What they lack:**
- Enterprise-only, very expensive — no self-serve / SMB tier
- Closed system — no API, no data export
- No on-premise option
- No pHash duplicate detection
- No natural language "why" explanation

---

### 5. CreativeX — Creative Quality & Governance

**Website:** creativex.com

**What they have:**
- Creative Quality Score (CQS) measuring brand and platform best practices
- Pre-flight quality check before ads go live
- Brand consistency and compliance scoring
- Integration with major ad platforms
- Used by enterprise regulated brands (CPG, pharma, finance)

**What they lack:**
- Focused on governance and compliance, not performance optimization
- No AI scoring tied to CTR/ROAS outcomes
- No bounding-box annotation
- No duplicate detection
- No on-premise option
- Enterprise-only pricing

---

### 6. Motion — Creative Analytics Dashboard

**Website:** motionapp.com

**What they have:**
- Clean analytics dashboard aggregating creative performance from Meta, TikTok, YouTube, LinkedIn
- Creative reporting with CTR, spend, ROAS breakdowns
- Team collaboration and creative review workflows
- Starts at ~$250/month — accessible to SMB and mid-market

**What they lack:**
- No AI scoring or element-level analysis — pure performance reporting
- No creative intelligence (no "why does this work")
- No bounding-box annotation
- No duplicate detection
- No on-premise option
- No fatigue detection beyond raw metric trends

---

## Feature Gap Table (PPT-Ready)

| Feature | AppsFlyer | Singular | Segwise | VidMob | CreativeX | **Kochava** |
|---|---|---|---|---|---|---|
| AI creative scoring (0–10) | ✅ | ✅ | ❌ | ✅ | partial | ✅ |
| Dimensions scored | ~4 (element) | 17 | — (tags) | ~10 | CQS only | **7** |
| Natural language explanation | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Bounding-box annotation | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Duplicate/variant detection (pHash) | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Creative fatigue detection | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Video frame analysis | ✅ (element) | partial | ❌ | ✅ | ❌ | **✅** |
| Playable ad analysis | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| On-premise / local model | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Own SDK / MMP required | ✅ required | ✅ required | MMP needed | ❌ | ❌ | **❌** |
| Closed-loop optimization | ❌ | ❌ | ❌ | ❌ | ❌ | **Phase 2** |
| Competitive benchmark percentile | ❌ | ❌ | ❌ | ✅ | ❌ | **✅ (CVPR)** |
| Self-serve / SMB pricing | ❌ | partial | ✅ | ❌ | ❌ | **✅** |

---

## Kochava Differentiators (Pitch Points)

### 1. No MMP lock-in
AppsFlyer and Singular require their own attribution SDK — zero value for customers not on their platform. Kochava Creative Intelligence works standalone: upload any creative, get instant analysis. Works alongside any MMP.

### 2. Visual annotation overlay
No competitor shows bounding boxes on the creative with face/text/CTA detection confidence scores. Kochava shows exactly what the model sees, making AI scoring explainable and auditable — not a black box.

### 3. True duplicate detection (pHash)
AppsFlyer has "similarity grouping" (themes/attributes) — not the same as pHash. pHash detects near-identical images differing only by resize, recolor, or compression. Kochava catches these before they dilute budget across platforms.

### 4. Natural language explanation
Every competitor gives a number or a tag list. Kochava gives a score + paragraph explaining why in plain English (Qwen2.5-VL). This is the "show your work" feature that analysts and creative teams actually need.

### 5. On-premise model (privacy-first)
Qwen2.5-VL runs locally via Ollama. Creative assets never leave the customer's environment. For enterprise and regulated industries, this is a non-negotiable advantage that no competitor can match.

### 6. Closed-Loop Optimization (Phase 2)
Unique roadmap item: recommendations flowing back to ad networks (bid adjustments, creative swaps). No competitor can act on their analysis — Kochava will.

---

## Gaps We Should Address

| Gap | Priority | Notes |
|---|---|---|
| Playable ad analysis | Low | Segwise-only niche, mobile gaming specific |
| 17-dimension scoring parity | Medium | We have 7 — can expand post-MVP |
| Asset library + smart search | Medium | AppsFlyer's most popular feature with creative teams |
| Slack/webhook fatigue alerts | Medium | Easy win — Segwise has this, we don't yet |
| Google Drive / Dropbox upload | Low | Creative team workflow convenience |

---

## Sources

- AppsFlyer Creative Management Hub product page (appsflyer.com/products/measurement/creative-optimization/, May 2026)
- Singular Creative IQ product page (singular.net, May 2026)
- Segwise.ai product documentation (segwise.ai, May 2026)
- VidMob platform overview (vidmob.com, May 2026)
- CreativeX platform overview (creativex.com, May 2026)
- Motion analytics platform (motionapp.com, May 2026)
