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
  "recommendations": ["<string>", ...],
  "explanation": "<2-3 sentence summary of why this creative works or doesn't>"
}

Scoring guide:
- hook_strength: How quickly it grabs attention (0=boring, 10=instantly arresting)
- cta_clarity: How clear the call-to-action is (0=no CTA, 10=unmissable)
- visual_quality: Composition, color harmony, production quality (0=poor, 10=excellent)
- message_clarity: How clearly the value prop is communicated (0=confusing, 10=crystal clear)
- emotional_resonance: Emotional impact on target audience (0=flat, 10=highly emotional)
- social_proof: Presence of reviews, ratings, user counts (0=none, 10=strong proof)
- brand_consistency: Logo, colors, fonts match brand guidelines (0=off-brand, 10=perfectly on-brand)

Provide 2-3 strengths, 2-3 weaknesses, and 3 actionable recommendations.
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
  "recommendations": ["<string>", ...],
  "explanation": "<2-3 sentence summary of why this video creative works or doesn't>"
}

For video, additionally consider:
- hook_strength: Does the first 3 seconds grab attention?
- pacing and narrative arc across keyframes
- audio-visual alignment (inferred from visuals)

Return ONLY the JSON object. No explanation outside the JSON."""

CONTENT_CLASSIFIER_PROMPT = """Does this image contain adult, violent, or otherwise inappropriate content that should not be processed?

Answer with exactly one word: YES or NO"""
