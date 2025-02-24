"""Prompt templates for various agents"""

DIALOGUE_ANALYSIS_PROMPTS = {
    "system_message": """You are an expert at analyzing dialogue and emotional context in scenes.
Your role is to:
1. Extract and structure dialogue from narrative text
2. Analyze emotional context and intensity
3. Determine appropriate voice tones
4. Maintain consistency in character voices
5. Format output in clean JSON structure""",

    "user_template": """Analyze the following scene and extract dialogue segments with emotional context.
For each line of dialogue, determine:
1. The speaker
2. Their emotional state (use simple emotions like: excited, happy, sad, angry, concerned, neutral)
3. The context of their speech
4. The tone of their voice (use simple tones like: normal, whisper, shout, enthusiastic, serious)
5. The emotional intensity (0.0 to 1.0)

Scene:
{scene_text}

Return the analysis as a JSON array of dialogue segments.
Each segment should have: text, speaker, emotion, context, tone, and intensity.
Use lowercase for emotions and tones.

Required format for each segment:
{{
    "text": "actual dialogue text",
    "speaker": "character name",
    "emotion": "lowercase emotion",
    "context": "brief context description",
    "tone": "lowercase tone",
    "intensity": float between 0 and 1
}}"""
}

VOICE_SETTINGS_PROMPTS = {
    "system_message": """You are an expert at voice modulation and emotional expression in speech.
Your role is to translate emotional context into specific voice parameters.""",

    "user_template": """Given the following dialogue segment, recommend voice settings:
Dialogue: {text}
Speaker: {speaker}
Emotion: {emotion}
Tone: {tone}
Intensity: {intensity}

Provide voice settings as JSON with:
- stability (0.0-1.0)
- similarity_boost (0.0-1.0)
- speaking_rate (0.5-2.0)"""
}

# Validation criteria for emotions and tones
VALID_EMOTIONS = [
    "excited", "happy", "sad", "angry", "concerned", 
    "neutral", "scared", "surprised", "determined"
]

VALID_TONES = [
    "normal", "whisper", "shout", "enthusiastic", 
    "serious", "trembling", "firm"
]

# Mapping of emotions to voice settings
EMOTION_VOICE_MAPPINGS = {
    "excited": {
        "stability": 0.7,
        "speaking_rate": 1.2
    },
    "sad": {
        "stability": 0.9,
        "speaking_rate": 0.9
    },
    "angry": {
        "stability": 0.5,
        "speaking_rate": 1.1
    },
    # Add more mappings as needed
} 