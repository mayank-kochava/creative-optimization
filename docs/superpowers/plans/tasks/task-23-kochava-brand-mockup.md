# Task 23: Kochava Brand Mockup + Performance Page

**File to update:**
- `docs/superpowers/mockups/ui-mockup-light.html`

---

## Goal

Update the mockup to feel like part of the Kochava product (K4A / frontend-mos) so it can be shown to the CEO and board. Add a new Performance page (top/bottom performers comparison).

---

## Step 1: Update CSS variables and fonts

Replace the current design tokens with Kochava brand tokens extracted from `k4a/frontend-mos/packages/app/src/plugins/vuetify.ts` and `settings.scss`:

```css
/* Replace :root block */
:root {
  --bg: #EDF1F7;              /* brand_background1 */
  --surface: #FFFFFF;
  --surface-2: #F4F6FA;
  --surface-3: #E8ECF3;
  --border: #E1E1E1;          /* grey_scale-grey4 */
  --border-h: #C4C9D4;
  --text: #1A1B1C;            /* grey_scale-black */
  --text-2: #575B5E;          /* grey_scale-grey1 */
  --text-3: #9DA3AE;
  --blue: #0C72EE;            /* brand_secondary (CTA blue) */
  --blue-10: rgba(12,114,238,.08);
  --blue-20: rgba(12,114,238,.18);
  --blue-50: rgba(12,114,238,.5);
  --navy: #1E4B97;            /* brand_primary_1 */
  --amber: #B07A00;
  --amber-bg: #FFF8E7;
  --amber-border: #F0C040;
  --green: #427900;           /* alerts_text-green */
  --green-bg: #F3FAE8;
  --green-border: #4D840B;    /* alerts_border-green */
  --red: #BE202E;             /* alerts_text-red */
  --red-bg: #FFF3F2;
  --red-border: #E57373;
  --r: 8px; --r-lg: 12px; --r-xl: 16px;
  --shadow: 0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,.10),0 2px 4px rgba(0,0,0,.06);
  --shadow-lg: 0 8px 30px rgba(0,0,0,.12);
  --font: 'Inter', sans-serif;       /* K4A uses Inter throughout */
  --font-h: 'Inter', sans-serif;     /* same — no display font in K4A */
  --font-m: 'JetBrains Mono', monospace;
}
```

Update Google Fonts link to load Inter (drop Syne and DM Sans):

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

---

## Step 2: Update header

Change header background from `#001529` to `#0F1E34` (K4A `page_fade-1`).

Replace logo orb gradient (currently blue) with navy: `linear-gradient(135deg,#1E4B97,#0C72EE)`.

Add a third nav item **Performance** between Campaigns and any future items:

```html
<button class="nav-btn" id="nav-perf" onclick="show('perf')">Performance</button>
```

Nav should be: Dashboard · Campaigns · Performance

---

## Step 3: Add Performance screen HTML

Insert this new screen after the `s-camp` screen and before `s-creat`:

```html
<!-- ═══ SCREEN: PERFORMANCE ═══ -->
<div class="screen" id="s-perf">
  <div class="pg-hdr">
    <div>
      <div class="pg-title">Performance</div>
      <div class="pg-sub">Compare top and bottom performing creatives across your portfolio</div>
    </div>
  </div>

  <!-- Controls row -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;flex-wrap:wrap">
    <div style="display:flex;gap:4px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:3px;box-shadow:var(--shadow)">
      <button class="dur-btn on" onclick="setDur(this,'3mo')">3 months</button>
      <button class="dur-btn" onclick="setDur(this,'6mo')">6 months</button>
      <button class="dur-btn" onclick="setDur(this,'1yr')">1 year</button>
    </div>
    <div style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-2)">
      Show top/bottom
      <select id="topN-select" onchange="renderPerf()" style="border:1px solid var(--border);border-radius:var(--r);padding:5px 10px;font-size:13px;background:var(--surface);color:var(--text);cursor:pointer">
        <option value="4">4</option>
        <option value="6" selected>6</option>
        <option value="8">8</option>
        <option value="10">10</option>
      </select>
      creatives
    </div>
  </div>

  <!-- Top performers -->
  <div style="margin-bottom:32px">
    <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px">
      <span style="width:4px;height:20px;background:var(--green-border);border-radius:2px;display:inline-block"></span>
      Top Performers
    </div>
    <div class="cr-grid" id="top-grid"></div>
  </div>

  <!-- Needs attention -->
  <div>
    <div style="font-size:13px;font-weight:700;color:var(--text);margin-bottom:14px;display:flex;align-items:center;gap:8px">
      <span style="width:4px;height:20px;background:var(--red-border);border-radius:2px;display:inline-block"></span>
      Needs Attention
    </div>
    <div class="cr-grid" id="bot-grid"></div>
  </div>
</div>
```

---

## Step 4: Add Performance CSS

Add to the `<style>` block:

```css
/* ── DURATION TOGGLE ── */
.dur-btn {
  padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: none; background: transparent; color: var(--text-2);
  font-family: var(--font); transition: all .15s;
}
.dur-btn:hover { color: var(--text); background: var(--surface-2); }
.dur-btn.on { background: var(--blue); color: #fff; font-weight: 600; }

/* ── PERFORMANCE CARD ACCENT ── */
.cr-card.top-card { border-left: 3px solid var(--green-border); }
.cr-card.bot-card { border-left: 3px solid var(--red-border); }
```

---

## Step 5: Add Performance data + JS

Performance data — add to the `<script>` block. Use a pool of 20 creatives with CTR and AI score so the top/bottom N picker works:

```js
const perfCreatives = [
  {id:1, name:'fitness_hero_01.jpg',      fmt:'JPG',  ctr:3.82, score:8, status:'healthy', dup:false, campaign:'Summer Fitness App'},
  {id:2, name:'gaming_install_v3.png',    fmt:'PNG',  ctr:3.61, score:9, status:'healthy', dup:false, campaign:'Gaming App Install Push'},
  {id:3, name:'b2b_linkedin_q3.jpg',      fmt:'JPG',  ctr:3.44, score:8, status:'healthy', dup:false, campaign:'B2B SaaS Q3 Pipeline'},
  {id:4, name:'mobile_game_pass.webp',    fmt:'WEBP', ctr:3.21, score:8, status:'healthy', dup:false, campaign:'Mobile Game Season Pass'},
  {id:5, name:'fintech_hero_v2.jpg',      fmt:'JPG',  ctr:3.10, score:7, status:'healthy', dup:false, campaign:'Fintech Onboarding Flow'},
  {id:6, name:'food_promo_square.jpg',    fmt:'JPG',  ctr:2.95, score:7, status:'healthy', dup:false, campaign:'Food Delivery App Launch'},
  {id:7, name:'travel_banner_v1.jpg',     fmt:'JPG',  ctr:2.84, score:6, status:'healthy', dup:false, campaign:'Travel Rewards Card'},
  {id:8, name:'fitness_square_v2.webp',   fmt:'WEBP', ctr:2.71, score:5, status:'healthy', dup:false, campaign:'Summer Fitness App'},
  {id:9, name:'ride_recruit_v2.png',      fmt:'PNG',  ctr:2.60, score:6, status:'healthy', dup:false, campaign:'Ride-Share Driver Recruit'},
  {id:10,name:'stream_retarget.jpg',      fmt:'JPG',  ctr:2.48, score:5, status:'healthy', dup:false, campaign:'Streaming Service Retarget'},
  {id:11,name:'ecom_flash_banner.jpg',    fmt:'JPG',  ctr:1.92, score:5, status:'healthy', dup:false, campaign:'E-commerce Holiday Flash'},
  {id:12,name:'fitness_cta_variant_a.jpg',fmt:'JPG',  ctr:1.74, score:4, status:'healthy', dup:true,  campaign:'Summer Fitness App'},
  {id:13,name:'gaming_15s_reel.mp4',      fmt:'MP4',  ctr:1.61, score:4, status:'fatiguing',dup:false, campaign:'Gaming App Install Push'},
  {id:14,name:'food_15s_promo.mp4',       fmt:'MP4',  ctr:1.44, score:4, status:'fatiguing',dup:false, campaign:'Food Delivery App Launch'},
  {id:15,name:'travel_social_v3.jpg',     fmt:'JPG',  ctr:1.30, score:3, status:'fatiguing',dup:false, campaign:'Travel Rewards Card'},
  {id:16,name:'ecom_carousel_a.jpg',      fmt:'JPG',  ctr:1.18, score:3, status:'fatiguing',dup:false, campaign:'E-commerce Holiday Flash'},
  {id:17,name:'stream_promo_v2.webp',     fmt:'WEBP', ctr:1.05, score:3, status:'fatiguing',dup:false, campaign:'Streaming Service Retarget'},
  {id:18,name:'fintech_banner_old.jpg',   fmt:'JPG',  ctr:0.92, score:2, status:'fatiguing',dup:false, campaign:'Fintech Onboarding Flow'},
  {id:19,name:'b2b_generic_v1.png',       fmt:'PNG',  ctr:0.81, score:2, status:'fatiguing',dup:true,  campaign:'B2B SaaS Q3 Pipeline'},
  {id:20,name:'fitness_video_15s.mp4',    fmt:'MP4',  ctr:0.68, score:2, status:'fatiguing',dup:false, campaign:'Summer Fitness App'},
];

// Grad pool for performance cards (index maps to perfCreatives index)
const PERF_GRADS = [
  'linear-gradient(135deg,#060e1a,#1253cc)',
  'linear-gradient(135deg,#1B0033,#4c1d95)',
  'linear-gradient(135deg,#071121,#1e3a5f)',
  'linear-gradient(135deg,#1a1a2e,#6B21A8)',
  'linear-gradient(135deg,#071121,#0d52d0)',
  'linear-gradient(135deg,#0B1C0B,#14532D)',
  'linear-gradient(135deg,#1a0a0a,#7f1d1d)',
  'linear-gradient(135deg,#071121,#1e3a5f)',
  'linear-gradient(135deg,#1a1a2e,#1e3a5f)',
  'linear-gradient(135deg,#060e1a,#162744)',
];

function renderPerfCards(list, gridId, cardCls) {
  const BADGE = {
    healthy: `<span class="badge badge-h">● Healthy</span>`,
    fatiguing: `<span class="badge badge-f">⚠ Fatiguing</span>`,
  };
  const isVid = f => ['MP4','MOV'].includes(f);
  document.getElementById(gridId).innerHTML = list.map((c, i) => {
    const cls = c.score >= 7 ? 'hi' : c.score >= 4 ? 'md' : 'lo';
    const grad = PERF_GRADS[i % PERF_GRADS.length];
    const thumbContent = isVid(c.fmt)
      ? `<div class="cr-play">▶</div>`
      : `<div style="width:100%;height:100%;background:${grad}"></div>`;
    return `<div class="cr-card ${cardCls}" onclick="openCreative(${c.id},${c.dup})">
      <div class="cr-thumb" style="background:${grad}">
        ${thumbContent}
        <span class="cr-fmt-ov">${c.fmt}</span>
        ${c.dup ? `<span class="cr-dup-ov">DUPE</span>` : ''}
        <span style="position:absolute;bottom:12px;left:12px;font-family:var(--font-m);font-size:11px;font-weight:700;color:rgba(255,255,255,.9);background:rgba(0,0,0,.55);padding:3px 8px;border-radius:5px;backdrop-filter:blur(4px)">CTR ${c.ctr.toFixed(2)}%</span>
      </div>
      <div class="cr-body">
        <div class="cr-fname">${c.name}</div>
        <div style="font-size:11px;color:var(--text-3);margin-top:-4px">${c.campaign}</div>
        <div class="sbar"><div class="sbar-t"><div class="sbar-f ${cls}" style="width:${c.score*10}%"></div></div><span class="sn">${c.score}/10</span></div>
        <div class="cr-foot">${BADGE[c.status]}</div>
      </div>
    </div>`;
  }).join('');
}

function renderPerf() {
  const n = parseInt(document.getElementById('topN-select').value);
  const sorted = [...perfCreatives].sort((a,b) => b.ctr - a.ctr);
  renderPerfCards(sorted.slice(0, n), 'top-grid', 'top-card');
  renderPerfCards(sorted.slice(-n).reverse(), 'bot-grid', 'bot-card');
}

function setDur(btn, _dur) {
  document.querySelectorAll('.dur-btn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  renderPerf(); // In real app would re-fetch; for mockup just re-render
}
```

Update the `show()` function to call `renderPerf()` when the perf screen is shown:

```js
function show(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('on'));
  document.getElementById('s-' + name).classList.add('on');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('on'));
  const nb = document.getElementById('nav-' + name);
  if (nb) nb.classList.add('on');
  if (name === 'perf') renderPerf();
  window.scrollTo(0, 0);
}
```

Also call `renderPerf()` at the bottom of the script (after `renderCampaigns(); drawRadar();`).

---

## Step 6: Verify in browser

Open `docs/superpowers/mockups/ui-mockup-light.html` in a browser.

- Header background should be `#0F1E34` (dark navy, not black)
- Body background should be `#EDF1F7` (light grey-blue, not white-grey)
- CTA buttons / blue accents should be `#0C72EE` (Kochava blue, not Ant blue `#1677FF`)
- Nav shows: Dashboard · Campaigns · Performance
- Click Performance → see duration picker + Top/Bottom grids
- Change N selector → grids update
- Switch duration → grids re-render (same data, just visual confirm)
- Cards have green left border (top) / red left border (bottom)
- CTR shown as overlay on thumbnail

---

## Step 7: Commit

```bash
git add docs/superpowers/mockups/ui-mockup-light.html
git commit -m "feat: rebrand mockup to Kochava design tokens + add Performance page"
```
