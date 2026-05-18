"""Generate Creative Intelligence Platform PPT for Sachin's exec pitch."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.oxml.ns as nsmap
from lxml import etree

# ── Brand colors ──────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x1E, 0x4B, 0x97)
BLUE   = RGBColor(0x0C, 0x72, 0xEE)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
TEXT   = RGBColor(0x1A, 0x1B, 0x1C)
TEXT2  = RGBColor(0x57, 0x5B, 0x5E)
BG     = RGBColor(0xED, 0xF1, 0xF7)
GREEN  = RGBColor(0x42, 0x79, 0x00)
RED    = RGBColor(0xBE, 0x20, 0x2E)
AMBER  = RGBColor(0xB0, 0x7A, 0x00)
LIGHT  = RGBColor(0xF4, 0xF6, 0xFA)

W = Inches(13.33)   # widescreen 16:9
H = Inches(7.5)


def prs() -> Presentation:
    p = Presentation()
    p.slide_width  = W
    p.slide_height = H
    return p


def blank(p: Presentation):
    return p.slides.add_slide(p.slide_layouts[6])   # blank layout


def fill_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def box(slide, left, top, width, height,
        fill=None, line=None, line_width=Pt(0)):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.line.fill.background()
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = line
        shape.line.width = line_width
    else:
        shape.line.fill.background()
    return shape


def txt(slide, text, left, top, width, height,
        size=Pt(14), bold=False, color=TEXT, align=PP_ALIGN.LEFT,
        italic=False, wrap=True):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.italic = italic
    return tb


def bullet_slide(prs_obj, title_text, bullets, subtitle=None):
    """Dark navy header + bullet list."""
    slide = blank(prs_obj)
    fill_bg(slide, WHITE)

    # Header bar
    box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
    txt(slide, title_text,
        Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
        size=Pt(30), bold=True, color=WHITE)

    if subtitle:
        txt(slide, subtitle,
            Inches(0.5), Inches(1.5), Inches(12), Inches(0.4),
            size=Pt(15), color=TEXT2, italic=True)

    top = Inches(1.55) if not subtitle else Inches(2.0)
    for i, (icon, line) in enumerate(bullets):
        # Bullet dot
        b = box(slide, Inches(0.5), top + i * Inches(0.72),
                Inches(0.08), Inches(0.08), fill=BLUE)
        txt(slide, f"{icon}  {line}",
            Inches(0.7), top + i * Inches(0.72) - Inches(0.04),
            Inches(11.8), Inches(0.65),
            size=Pt(17), color=TEXT)

    return slide


def two_col(prs_obj, title_text, left_items, right_items,
            left_title="", right_title=""):
    slide = blank(prs_obj)
    fill_bg(slide, WHITE)
    box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
    txt(slide, title_text,
        Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
        size=Pt(30), bold=True, color=WHITE)

    mid = W / 2 + Inches(0.1)
    col_w = W / 2 - Inches(0.6)

    for col_x, col_title, items in [
        (Inches(0.4), left_title, left_items),
        (mid, right_title, right_items),
    ]:
        if col_title:
            txt(slide, col_title, col_x, Inches(1.55), col_w, Inches(0.4),
                size=Pt(13), bold=True, color=BLUE)
        for i, (icon, line) in enumerate(items):
            txt(slide, f"{icon}  {line}",
                col_x, Inches(1.95 if col_title else 1.55) + i * Inches(0.65),
                col_w, Inches(0.6),
                size=Pt(15), color=TEXT)

    # Divider
    divider = slide.shapes.add_shape(1, mid - Inches(0.15),
                                     Inches(1.4), Inches(0.02), H - Inches(1.4))
    divider.fill.solid()
    divider.fill.fore_color.rgb = LIGHT
    divider.line.fill.background()

    return slide


# ── BUILD SLIDES ──────────────────────────────────────────────────────────────
p = prs()

# ── 1. TITLE SLIDE ─────────────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, NAVY)

# Accent bar
box(slide, 0, H - Inches(0.12), W, Inches(0.12), fill=BLUE)

# Logo / wordmark area
box(slide, Inches(0.5), Inches(1.6), Inches(0.55), Inches(0.55), fill=BLUE)
txt(slide, "✦", Inches(0.5), Inches(1.6), Inches(0.55), Inches(0.55),
    size=Pt(22), color=WHITE, align=PP_ALIGN.CENTER)

txt(slide, "KOCHAVA",
    Inches(1.2), Inches(1.62), Inches(5), Inches(0.45),
    size=Pt(13), bold=True, color=RGBColor(0x8A, 0xAD, 0xD8), align=PP_ALIGN.LEFT)

txt(slide, "Creative Intelligence Platform",
    Inches(0.5), Inches(2.2), Inches(12), Inches(1.1),
    size=Pt(46), bold=True, color=WHITE, align=PP_ALIGN.LEFT)

txt(slide, "AI-powered creative analysis · Fatigue detection · Duplicate deduplication",
    Inches(0.5), Inches(3.4), Inches(11), Inches(0.5),
    size=Pt(17), color=RGBColor(0xA8, 0xC4, 0xE8), align=PP_ALIGN.LEFT)

txt(slide, "Executive Preview  ·  May 2026",
    Inches(0.5), Inches(6.6), Inches(8), Inches(0.4),
    size=Pt(13), color=RGBColor(0x6A, 0x8A, 0xC8), italic=True)

# ── 2. PROBLEM SLIDE ───────────────────────────────────────────────────────
bullet_slide(p, "The Problem",
    [
        ("💸", "Up to 40% of ad spend goes to creatives that are fatigued or already running elsewhere"),
        ("🙈", "No visibility into WHY a creative performs or fails — just metrics"),
        ("🔁", "Same creative resized and re-uploaded across platforms, diluting budgets"),
        ("⏱",  "Performance data arrives days after spend decisions are made"),
        ("🔒", "Every competitor's solution requires their own attribution SDK"),
    ],
    subtitle="Advertisers are flying blind on creative performance"
)

# ── 3. SOLUTION OVERVIEW ───────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, WHITE)
box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
txt(slide, "Our Solution",
    Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
    size=Pt(30), bold=True, color=WHITE)
txt(slide, "Three capabilities — deployable in 7 days, runs 100% on-premise",
    Inches(0.5), Inches(1.5), Inches(12), Inches(0.4),
    size=Pt(15), color=TEXT2, italic=True)

cards = [
    (Inches(0.4),  BLUE,  "🔍", "AI Creative Scoring",
     "7-dimension analysis (0-10): Hook, CTA, Visual, Message,\nEmotion, Social Proof, Brand.\nNatural language explanation + bounding-box annotation."),
    (Inches(4.7),  GREEN, "🔎", "Duplicate Detection",
     "pHash fingerprinting detects resized/recolored variants\nacross platforms before they waste budget.\nHamming distance threshold configurable."),
    (Inches(9.0),  RED,   "📉", "Fatigue Detection",
     "Flags creatives with >20% WoW CTR decline.\nPer-creative fatigue badge in dashboard.\nPrevents dead creatives from burning budget."),
]

for x, color, icon, title, body in cards:
    box(slide, x, Inches(2.1), Inches(3.9), Inches(4.8),
        fill=WHITE, line=color, line_width=Pt(2))
    box(slide, x, Inches(2.1), Inches(3.9), Inches(0.65), fill=color)
    txt(slide, f"{icon}  {title}",
        x + Inches(0.15), Inches(2.18), Inches(3.6), Inches(0.5),
        size=Pt(15), bold=True, color=WHITE)
    txt(slide, body,
        x + Inches(0.2), Inches(2.9), Inches(3.55), Inches(3.8),
        size=Pt(13.5), color=TEXT)

# ── 4. ARCHITECTURE ────────────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, WHITE)
box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
txt(slide, "Architecture",
    Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
    size=Pt(30), bold=True, color=WHITE)

# Pipeline boxes
pipe_items = [
    (Inches(0.35), "#0F1E34", "Ad Networks\n(Meta · Google\n TikTok · Snap)",    WHITE),
    (Inches(2.85), "#1E4B97", "Ingest + Store\n(FastAPI · S3\n PostgreSQL)",      WHITE),
    (Inches(5.35), "#0C72EE", "Creative Intelligence\nEngine\n(Qwen2.5-VL 7B)",  WHITE),
    (Inches(7.85), "#1E4B97", "Dashboard\n(Next.js 14\n React 18)",               WHITE),
    (Inches(10.35),"#0F1E34", "Kochava\nAttribution\n(MMP data)",                 WHITE),
]

for x, col, label, tc in pipe_items:
    c = RGBColor(int(col[1:3],16), int(col[3:5],16), int(col[5:7],16))
    box(slide, x, Inches(2.2), Inches(2.2), Inches(2.4), fill=c)
    txt(slide, label, x + Inches(0.1), Inches(2.35),
        Inches(2.0), Inches(2.1),
        size=Pt(13), bold=False, color=WHITE, align=PP_ALIGN.CENTER)

# Arrows
for ax in [Inches(2.55), Inches(5.05), Inches(7.55), Inches(10.05)]:
    txt(slide, "→", ax, Inches(3.0), Inches(0.3), Inches(0.5),
        size=Pt(22), color=NAVY, align=PP_ALIGN.CENTER)

# Bidirectional arrow note for Phase 2
txt(slide, "⟵ Phase 2: Closed-Loop Optimization (recommendations back to ad networks)",
    Inches(0.35), Inches(4.85), Inches(12.6), Inches(0.45),
    size=Pt(13), color=BLUE, italic=True, align=PP_ALIGN.CENTER)

# Feature pipelines label
txt(slide, "F1: Content Classification   F2: Visual Analysis + Annotation   F3: Deduplication + Fatigue",
    Inches(5.0), Inches(5.45), Inches(5.0), Inches(0.4),
    size=Pt(11), color=TEXT2, align=PP_ALIGN.CENTER)

# On-premise badge
box(slide, Inches(5.0), Inches(5.9), Inches(3.3), Inches(0.45), fill=LIGHT, line=GREEN, line_width=Pt(1.5))
txt(slide, "🔒  Runs 100% on-premise via Ollama — no data leaves your environment",
    Inches(5.1), Inches(5.92), Inches(3.1), Inches(0.4),
    size=Pt(11), color=GREEN, align=PP_ALIGN.CENTER)

# ── 5. COMPETITOR TABLE ────────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, WHITE)
box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
txt(slide, "Competitive Landscape",
    Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
    size=Pt(30), bold=True, color=WHITE)

headers = ["Feature", "AppsFlyer", "Singular", "Segwise", "VidMob", "Kochava ✦"]
col_widths = [Inches(3.2), Inches(1.6), Inches(1.6), Inches(1.6), Inches(1.6), Inches(1.8)]
rows = [
    ["AI Scoring (0–10)",          "✅", "✅", "❌", "✅", "✅"],
    ["Natural Language Why",       "❌", "❌", "❌", "❌", "✅"],
    ["Bounding-Box Annotation",    "❌", "❌", "❌", "❌", "✅"],
    ["Duplicate Detection",        "❌", "❌", "❌", "❌", "✅"],
    ["Video Frame Analysis",       "❌", "partial","❌", "✅", "✅"],
    ["On-Premise Model",           "❌", "❌", "❌", "❌", "✅"],
    ["No MMP SDK Required",        "❌", "❌", "❌", "✅", "✅"],
    ["Closed-Loop Optimization",   "❌", "❌", "❌", "❌", "Ph2"],
]

row_h = Inches(0.46)
start_y = Inches(1.5)
start_x = Inches(0.25)

# Header row
x = start_x
for i, (h, w) in enumerate(zip(headers, col_widths)):
    hcol = NAVY if i < len(headers) - 1 else BLUE
    box(slide, x, start_y, w, row_h, fill=hcol)
    txt(slide, h, x + Inches(0.08), start_y + Inches(0.07),
        w - Inches(0.1), row_h - Inches(0.1),
        size=Pt(12), bold=True, color=WHITE, align=PP_ALIGN.CENTER if i > 0 else PP_ALIGN.LEFT)
    x += w

# Data rows
for ri, row in enumerate(rows):
    y = start_y + (ri + 1) * row_h
    x = start_x
    for ci, (cell, w) in enumerate(zip(row, col_widths)):
        bg = LIGHT if ri % 2 == 0 else WHITE
        if ci == len(col_widths) - 1:
            bg = RGBColor(0xEE, 0xF6, 0xFF)  # highlight Kochava col
        box(slide, x, y, w, row_h, fill=bg, line=RGBColor(0xE1,0xE1,0xE1), line_width=Pt(0.5))
        color = GREEN if cell == "✅" else (RED if cell == "❌" else BLUE)
        if ci == 0:
            color = TEXT
        aln = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
        txt(slide, cell, x + Inches(0.08), y + Inches(0.08),
            w - Inches(0.1), row_h - Inches(0.1),
            size=Pt(12 if ci > 0 else 12), bold=(ci == len(col_widths) - 1 and cell not in ("❌",)),
            color=color, align=aln)
        x += w

# ── 6. DIFFERENTIATORS ─────────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, WHITE)
box(slide, 0, 0, W, Inches(1.4), fill=NAVY)
txt(slide, "Kochava Differentiators",
    Inches(0.5), Inches(0.28), Inches(12), Inches(0.85),
    size=Pt(30), bold=True, color=WHITE)

diffs = [
    ("🔓", "No MMP Lock-in",
     "Works standalone — customers can use alongside any MMP. Every competitor requires their own SDK."),
    ("🎯", "Visual Annotation",
     "Bounding boxes on face / text / CTA with confidence scores. No competitor shows what the AI sees."),
    ("🔍", "Duplicate Detection",
     "pHash fingerprinting catches resized variants across platforms before they dilute budget."),
    ("💬", "Natural Language Why",
     "Score + paragraph explanation in plain English. Analysts want 'show your work,' not just a number."),
    ("🔒", "On-Premise Model",
     "Qwen2.5-VL via Ollama — creative assets never leave customer environment. Enterprise/regulated friendly."),
    ("🔄", "Closed-Loop (Phase 2)",
     "Recommendations flow back to ad networks. No competitor can act — Kochava can."),
]

for i, (icon, title, body) in enumerate(diffs):
    col = i % 3
    row = i // 3
    x = Inches(0.35) + col * Inches(4.3)
    y = Inches(1.6) + row * Inches(2.6)
    box(slide, x, y, Inches(4.1), Inches(2.3),
        fill=WHITE, line=BLUE, line_width=Pt(1.5))
    txt(slide, f"{icon}  {title}",
        x + Inches(0.2), y + Inches(0.2), Inches(3.7), Inches(0.5),
        size=Pt(14), bold=True, color=NAVY)
    txt(slide, body,
        x + Inches(0.2), y + Inches(0.75), Inches(3.7), Inches(1.4),
        size=Pt(12.5), color=TEXT2)

# ── 7. DEMO + NEXT STEPS ───────────────────────────────────────────────────
slide = blank(p)
fill_bg(slide, NAVY)
box(slide, 0, H - Inches(0.12), W, Inches(0.12), fill=BLUE)

txt(slide, "Demo + Next Steps",
    Inches(0.5), Inches(0.6), Inches(12), Inches(0.8),
    size=Pt(36), bold=True, color=WHITE)

txt(slide, "Live demo available — runs locally on M4 Pro 24GB, no cloud dependencies",
    Inches(0.5), Inches(1.55), Inches(12), Inches(0.45),
    size=Pt(15), color=RGBColor(0xA8, 0xC4, 0xE8), italic=True)

left_items = [
    ("✅", "AI creative scoring (7 dimensions)"),
    ("✅", "Bounding-box annotation overlay"),
    ("✅", "Duplicate detection (pHash)"),
    ("✅", "Fatigue detection per creative"),
    ("✅", "KPI dashboard (CTR, CVR, CPI, ROAS)"),
    ("✅", "Performance comparison page"),
]

right_items = [
    ("→", "Expand to 17 AI scoring dimensions"),
    ("→", "Slack/webhook fatigue alerts"),
    ("→", "Asset library + smart search"),
    ("→", "Google Drive / Dropbox upload integration"),
    ("→", "Closed-Loop Optimization (Phase 2)"),
    ("→", "Productize for customer self-serve"),
]

for i, (icon, line) in enumerate(left_items):
    txt(slide, f"{icon}  {line}",
        Inches(0.5), Inches(2.2) + i * Inches(0.65),
        Inches(6.0), Inches(0.6),
        size=Pt(15), color=WHITE)

txt(slide, "Roadmap",
    Inches(7.0), Inches(2.0), Inches(5.8), Inches(0.4),
    size=Pt(13), bold=True, color=BLUE)

for i, (icon, line) in enumerate(right_items):
    txt(slide, f"{icon}  {line}",
        Inches(7.0), Inches(2.4) + i * Inches(0.65),
        Inches(5.8), Inches(0.6),
        size=Pt(14), color=RGBColor(0xA8, 0xC4, 0xE8))

# ── SAVE ───────────────────────────────────────────────────────────────────
out = "docs/Creative-Intelligence-Platform-Pitch.pptx"
p.save(out)
print(f"Saved: {out}")
