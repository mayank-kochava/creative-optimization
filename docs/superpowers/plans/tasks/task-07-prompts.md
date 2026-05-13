# Task 07: Prompt Engineering

**Files to create:**
- `backend/app/services/prompts.py`
- `backend/tests/test_prompts.py`

**Prereq:** Task 06 complete (schemas exist).

---

## Step 1: Write failing test

```python
# backend/tests/test_prompts.py
from app.services.prompts import IMAGE_ANALYSIS_PROMPT, VIDEO_ANALYSIS_PROMPT, CONTENT_CLASSIFIER_PROMPT


def test_image_prompt_contains_all_7_dimensions():
    dimensions = [
        "hook_strength", "cta_clarity", "visual_quality", "message_clarity",
        "emotional_resonance", "social_proof", "brand_consistency"
    ]
    for dim in dimensions:
        assert dim in IMAGE_ANALYSIS_PROMPT, f"Missing dimension: {dim}"


def test_image_prompt_requires_json_only():
    assert "JSON" in IMAGE_ANALYSIS_PROMPT
    assert "respond ONLY" in IMAGE_ANALYSIS_PROMPT.lower() or "only" in IMAGE_ANALYSIS_PROMPT.lower()


def test_image_prompt_has_exactly_3_recommendations_constraint():
    assert "3" in IMAGE_ANALYSIS_PROMPT
    assert "recommendation" in IMAGE_ANALYSIS_PROMPT.lower()


def test_content_classifier_prompt_expects_yes_no():
    assert "YES" in CONTENT_CLASSIFIER_PROMPT
    assert "NO" in CONTENT_CLASSIFIER_PROMPT


def test_video_prompt_mentions_keyframes():
    assert "keyframe" in VIDEO_ANALYSIS_PROMPT.lower() or "frame" in VIDEO_ANALYSIS_PROMPT.lower()
```

Run: `cd backend && pytest tests/test_prompts.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/prompts.py`

```python
IMAGE_ANALYSIS_PROMPT = """You are an expert advertising creative analyst. Analyze this ad creative image and respond ONLY with valid JSON matching the exact schema below. No explanation outside the JSON.

JSON SCHEMA:
{
  "scores": {
    "hook_strength": <integer 0-10>,
    "cta_clarity": <integer 0-10>,
    "visual_quality": <integer 0-10>,
    "message_clarity": <integer 0-10>,
    "emotional_resonance": <integer 0-10>,
    "social_proof": <integer 0-10>,
    "brand_consistency": <integer 0-10>
  },
  "overall_score": <integer 0-10, average of 7 scores>,
  "persuasion_strategy": <one of: "fear_appeal", "fomo", "aspirational", "social_proof", "rational", "unknown">,
  "dominant_emotion": <one of: "excitement", "fear", "trust", "joy", "sadness", "neutral", "unknown">,
  "strengths": [<array of up to 5 strings>],
  "weaknesses": [<array of up to 5 strings>],
  "recommendations": [<EXACTLY 3 strings — specific actionable improvements>],
  "explanation": "<2-3 sentence natural language explanation of the creative's effectiveness>"
}

SCORING GUIDE:
- hook_strength (0-10): How well does the first 3 seconds or top-third of the image capture attention? 10=immediate, irresistible hook
- cta_clarity (0-10): How clear and prominent is the call-to-action? 10=unmissable, single clear CTA
- visual_quality (0-10): Image resolution, composition, color harmony, production value. 10=professional, polished
- message_clarity (0-10): Is the core message clear in under 3 seconds? 10=instantly understood
- emotional_resonance (0-10): Does it trigger an emotion that motivates action? 10=powerful emotional response
- social_proof (0-10): Ratings, testimonials, user counts, celebrity endorsement. 0=none visible
- brand_consistency (0-10): Logo visibility, consistent brand colors/fonts. 10=immediately recognizable brand

RULES:
- If you cannot determine a value, use 0 for scores and "unknown" for enum fields
- recommendations MUST be exactly 3 items — specific and actionable
- Respond ONLY with valid JSON. No markdown, no code blocks, no explanation outside JSON.

EXAMPLE OUTPUT:
{"scores":{"hook_strength":8,"cta_clarity":7,"visual_quality":9,"message_clarity":7,"emotional_resonance":8,"social_proof":4,"brand_consistency":6},"overall_score":7,"persuasion_strategy":"aspirational","dominant_emotion":"excitement","strengths":["Bold hero image captures attention","CTA button is prominent"],"weaknesses":["No social proof elements","Small text in bottom corner"],"recommendations":["Add user review count near CTA button","Increase CTA button size by 30%","Add a urgency element like limited-time offer"],"explanation":"This creative uses aspirational lifestyle imagery effectively to create desire. The visual quality is high with good color harmony, but the absence of social proof limits trust-building. The CTA is clear but could be more prominent."}"""


VIDEO_ANALYSIS_PROMPT = """You are an expert advertising creative analyst. You will see keyframes from a video ad creative. Analyze the sequence of frames and respond ONLY with valid JSON matching the exact schema below. No explanation outside the JSON.

The frames shown are: opening frame, mid-point frame, and closing frame of the video ad.

JSON SCHEMA:
{
  "scores": {
    "hook_strength": <integer 0-10, how captivating is the opening frame>,
    "cta_clarity": <integer 0-10, how clear is the CTA in the closing frame>,
    "visual_quality": <integer 0-10, production value across all frames>,
    "message_clarity": <integer 0-10, is the message clear across the video sequence>,
    "emotional_resonance": <integer 0-10, emotional journey through the frames>,
    "social_proof": <integer 0-10, any visible ratings/testimonials/user counts>,
    "brand_consistency": <integer 0-10, consistent brand identity across frames>
  },
  "overall_score": <integer 0-10>,
  "persuasion_strategy": <one of: "fear_appeal", "fomo", "aspirational", "social_proof", "rational", "unknown">,
  "dominant_emotion": <one of: "excitement", "fear", "trust", "joy", "sadness", "neutral", "unknown">,
  "strengths": [<up to 5 strings>],
  "weaknesses": [<up to 5 strings>],
  "recommendations": [<EXACTLY 3 strings>],
  "explanation": "<2-3 sentences about the video ad's effectiveness as a sequence>"
}

RULES:
- Analyze the narrative arc across keyframes — opening hook, middle development, closing CTA
- recommendations MUST be exactly 3 items
- Respond ONLY with valid JSON."""


CONTENT_CLASSIFIER_PROMPT = """Is this image an advertisement creative (ad banner, promotional image, or marketing material)?

Answer with ONLY one word: YES or NO

YES = The image is an advertisement, marketing banner, promotional creative, or product/app promotion
NO = The image is a personal photo, news image, artwork, or any non-advertising content"""
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_prompts.py -v
```

Expected: all 5 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/prompts.py backend/tests/test_prompts.py
git commit -m "feat: structured JSON prompts for Qwen2-VL analysis and content classification"
```
