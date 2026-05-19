# Task 24: Competitor Analysis Doc

**File to create:**
- `docs/competitor-analysis.md`

---

## Goal

Write a structured competitive analysis of ad creative optimization tools. Covers: AppsFlyer, Singular, Adjust, Segwise, VidMob, MagicBrief vs Kochava Creative Intelligence Platform. Includes a PPT-ready feature gap table and strategic narrative for Sachin's US exec pitch.

---

## Step 1: Create `docs/competitor-analysis.md`

```markdown
# Competitor Analysis — Creative Optimization Platforms

**Purpose:** Executive pitch support for Sachin's US presentation. Identifies gaps where Kochava differentiates.

**Research date:** May 2026

---

## Competitive Landscape

### 1. AppsFlyer — Creative Management Hub

**Website:** appsflyer.com/products/creative-management

**What they have:**
- Automated creative performance aggregation (pulls from Facebook Ads, Google, TikTok, Snapchat via API)
- AI-powered element-level scoring: isolates which creative elements (headline, image, CTA, character) drive performance
- Full-funnel attribution: ties creative performance to installs, revenue, retention (not just CTR)
- Smart search: natural language query on creative assets ("show me top dog creatives from Q4")
- Asset library with tagging and version history
- Google Drive + Dropbox integration for creative upload
- Automated A/B test reporting
- Cross-network creative comparison in a single dashboard
- Partner integrations: Shutterstock, Getty, AI image generation tools

**What they lack:**
- AI explanation of WHY a creative scores well (descriptive analysis, not just rank)
- Bounding-box annotation (face detection, text detection, CTA localization)
- Duplicate/variant detection across platforms (pHash)
- Closed-loop optimization — no ability to push recommendations back to ad networks
- Works only with their attribution SDK — zero value for non-AppsFlyer customers
- On-premise/private model option — everything goes through their cloud

---

### 2. Singular — Creative IQ

**Website:** singular.net (launched May 2025)

**What they have:**
- 17 AI dimensions scored 0–10: composition, color harmony, motion intensity, brand presence, emotional tone, CTA clarity, etc.
- Cross-channel creative performance (attribution SDK required)
- Automated creative tagging from visual AI
- Performance vs. score correlation charts
- Bulk creative import

**What they lack:**
- No bounding-box annotation / visual heatmap overlay
- No duplicate detection
- No on-premise model option
- Attribution SDK dependency (same problem as AppsFlyer)
- No natural language AI explanation — scores only, no "why"

---

### 3. Adjust — Creative Performance

**What they have:**
- Creative performance dashboard tied to MMP attribution data
- Basic visual tagging
- A/B test reporting

**What they lack:**
- No AI scoring or element-level analysis
- No creative intelligence — pure performance reporting only
- Behind AppsFlyer and Singular significantly on AI capabilities

---

### 4. Segwise — AI Creative Analytics

**Website:** segwise.ai

**What they have:**
- AI-generated creative tags (200+ auto-tags: "outdoor", "female lead", "promotional price overlay", etc.)
- Tag-level performance correlation
- Unique: playable ad analysis (interactive ad format specific to mobile games)
- Anomaly detection — flags unusual spend or CTR changes
- Slack alerts for creative fatigue

**What they lack:**
- No holistic AI score (0–10) — only tag presence/absence
- No visual annotation overlay
- No duplicate detection
- Attribution SDK required

---

### 5. VidMob — Creative Intelligence Platform

**Website:** vidmob.com

**What they have:**
- Enterprise-grade creative scoring
- Frame-by-frame video analysis (attention, brand safety, emotional engagement)
- Creative benchmarks by vertical (retail, gaming, finance)
- Integration with Meta, Google, TikTok ad APIs

**What they lack:**
- Very expensive — enterprise contracts, not SMB/mid-market friendly
- Closed system — no API access, no self-serve
- No on-premise option
- No duplicate detection

---

### 6. MagicBrief — Creative Research

**Website:** magicbrief.com

**What they have:**
- Competitor creative ad library (swipe file)
- Performance data from your own Meta/Google accounts
- AI creative briefs

**What they lack:**
- No AI analysis of your own creatives
- No scoring
- Focused on research/inspiration, not performance optimization

---

## Feature Gap Table (PPT-Ready)

| Feature | AppsFlyer | Singular | Adjust | Segwise | VidMob | **Kochava** |
|---|---|---|---|---|---|---|
| AI creative scoring (0–10) | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Dimensions scored | ~5 | 17 | — | — | ~10 | **7** |
| Natural language explanation | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Bounding-box annotation | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Duplicate/variant detection | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Creative fatigue detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Video frame analysis | ❌ | partial | ❌ | ❌ | ✅ | **✅** |
| Playable ad analysis | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| On-premise / local model | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| MMP SDK required | ✅ required | ✅ required | ✅ required | ✅ required | ❌ | **❌** |
| Closed-loop optimization | ❌ | ❌ | ❌ | ❌ | ❌ | **Phase 2** |
| Competitive benchmark percentile | ❌ | ❌ | ❌ | ❌ | ✅ | **✅ (CVPR)** |
| Self-serve / SMB pricing | ❌ | partial | ❌ | ✅ | ❌ | **✅** |

---

## Kochava Differentiators (Pitch Points)

### 1. No MMP lock-in
Every competitor (AppsFlyer, Singular, Adjust, Segwise) requires their attribution SDK. Kochava Creative Intelligence works standalone — upload any creative, get instant analysis. Customers can use it alongside any MMP.

### 2. Visual annotation overlay
No competitor shows bounding boxes on the creative with face/text/CTA detection confidence scores. Kochava shows exactly what the model sees, making AI scoring explainable and trustworthy.

### 3. Duplicate detection across platforms
Advertisers routinely reuse resized variants across Facebook, TikTok, and Google. Nobody detects this. Kochava's pHash deduplication flags near-identical creatives before they dilute budget.

### 4. Natural language explanation
AppsFlyer and Singular give a number. Kochava gives a score + paragraph explaining why — written in plain English (Qwen2-VL). This is the "show your work" feature analysts want.

### 5. On-premise model (privacy-first)
Qwen2.5-VL runs locally via Ollama. Creative assets never leave the customer's environment. For enterprise / regulated industries, this is a non-negotiable advantage.

### 6. Closed-Loop Optimization (Phase 2)
Unique roadmap item: recommendations flowing back to ad networks (bid adjustments, creative swaps). No competitor has this. Positions Kochava as the intelligence layer that actually acts, not just reports.

---

## Gaps We Should Address

| Gap | Priority | Notes |
|---|---|---|
| Playable ad analysis | Low | Segwise-only, niche for mobile gaming |
| 17-dimension scoring parity | Medium | We have 7 — can expand post-MVP |
| Asset library + search | Medium | Not MVP — but AppsFlyer's "smart search" is popular |
| Google Drive / Dropbox integration | Low | Nice-to-have for creative teams |
| Slack alerts for fatigue | Medium | Easy win — webhook-based |

---

## Sources

- AppsFlyer Creative Management Hub product page (appsflyer.com, May 2026)
- Singular Creative IQ launch announcement (May 2025)
- Segwise.ai product documentation
- VidMob platform overview
- MagicBrief product page
```

---

## Step 2: Commit

```bash
git add docs/competitor-analysis.md
git commit -m "docs: add competitor analysis for creative optimization platforms"
```
