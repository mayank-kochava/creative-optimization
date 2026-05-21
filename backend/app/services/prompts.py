IMAGE_ANALYSIS_PROMPT = """Analyze this advertisement creative and return ONLY a JSON object with no markdown fencing.

JSON schema:
{
  "scores": {
    "hook_strength": <0-10 float>,
    "cta_clarity": <0-10 float>,
    "visual_quality": <0-10 float>,
    "message_clarity": <0-10 float>,
    "emotional_resonance": <0-10 float>,
    "social_proof": <0-10 float>,
    "brand_consistency": <0-10 float>
  },
  "persuasion_strategy": "<one of: fear_of_missing_out, social_proof, authority, scarcity, reciprocity, liking, unity, unknown>",
  "dominant_emotion": "<one of: excitement, trust, fear, surprise, sadness, disgust, anticipation, joy, unknown>",
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "recommendations": [
    {
      "text": "<specific actionable recommendation>",
      "metric": "<one of: ctr, ipm, cvr, roas>",
      "lift_min": <estimated minimum % improvement as integer, e.g. 3>,
      "lift_max": <estimated maximum % improvement as integer, e.g. 8>
    }
  ],
  "explanation": "<2-3 sentence summary of why this creative works or doesn't>",
  "search_tags": ["<visual descriptor>", ...]
}

Scoring guide:
- hook_strength: How quickly it grabs attention (0=boring, 10=instantly arresting)
- cta_clarity: How clear the call-to-action is (0=no CTA, 10=unmissable)
- visual_quality: Composition, color harmony, production quality (0=poor, 10=excellent)
- message_clarity: How clearly the value prop is communicated (0=confusing, 10=crystal clear)
- emotional_resonance: Emotional impact on target audience (0=flat, 10=highly emotional)
- social_proof: Presence of reviews, ratings, user counts (0=none, 10=strong proof)
- brand_consistency: Logo, colors, fonts match brand guidelines (0=off-brand, 10=perfectly on-brand)

For recommendations: provide exactly 3. Each must include an estimated CTR/IPM/CVR/ROAS lift range based on the specific weakness being addressed. Be specific: "Adding a 5-star rating badge typically lifts CTR by 3-6% in mobile gaming ads."

For search_tags: provide 8-12 short visual descriptors that describe what someone might search for — background colors, scene types, character descriptions, visual elements, mood, style. Examples: "red background", "outdoor scene", "male character", "minimal text", "product close-up", "dark theme", "urban setting", "action shot".

Return ONLY the JSON object. No explanation outside the JSON."""

VIDEO_ANALYSIS_PROMPT = """Analyze these keyframes from an advertisement video and return ONLY a JSON object with no markdown fencing.

JSON schema:
{
  "scores": {
    "hook_strength": <0-10 float>,
    "cta_clarity": <0-10 float>,
    "visual_quality": <0-10 float>,
    "message_clarity": <0-10 float>,
    "emotional_resonance": <0-10 float>,
    "social_proof": <0-10 float>,
    "brand_consistency": <0-10 float>
  },
  "persuasion_strategy": "<one of: fear_of_missing_out, social_proof, authority, scarcity, reciprocity, liking, unity, unknown>",
  "dominant_emotion": "<one of: excitement, trust, fear, surprise, sadness, disgust, anticipation, joy, unknown>",
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "recommendations": [
    {
      "text": "<specific actionable recommendation>",
      "metric": "<one of: ctr, ipm, cvr, roas>",
      "lift_min": <estimated minimum % improvement as integer>,
      "lift_max": <estimated maximum % improvement as integer>
    }
  ],
  "explanation": "<2-3 sentence summary of why this video creative works or doesn't>",
  "search_tags": ["<visual descriptor>", ...]
}

For video, additionally consider:
- hook_strength: Does the first 3 seconds grab attention?
- pacing and narrative arc across keyframes
- audio-visual alignment (inferred from visuals)

For recommendations: provide exactly 3 with estimated metric lift ranges (e.g. "Adding end-card CTA text typically lifts CTR by 4-9% in video ads").
For search_tags: 8-12 visual descriptors — scene types, character descriptions, visual style, mood, colors.

Return ONLY the JSON object. No explanation outside the JSON."""

CONTENT_CLASSIFIER_PROMPT = (
    "Is this image an advertisement creative (banner ad, social media ad, "
    "display ad, video ad thumbnail, or promotional creative)? "
    "Answer with a single word: YES or NO."
)
