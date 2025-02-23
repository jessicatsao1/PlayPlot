# Speech Agent Development Requirements

## Overview
The Speech Agent converts story scenes into natural-sounding audio by extracting dialogue, applying emotional context, and generating voice outputs using ElevenLabs TTS API.

## Input Example & Expected Output
```python
# INPUT EXAMPLE
# 1. Scene Content
scene_content = """
John looked at Mary with concern. "Are you sure about this?" he asked.
"Absolutely," Mary replied confidently. "We have to try."
The wind howled through the trees as they stood there.
John sighed deeply. "Then let's do it," he said with determination.
"""

# 2. Manager Recommendations
manager_recommendations = """
Apply tense atmosphere for John's dialogue.
Mary's voice should be confident and assertive.
Add subtle wind effects between dialogues.
Speaking rate should be moderate to build tension.
"""

# EXPECTED OUTPUT
# - A sequence of audio files that when played in order creates:
#   1. John's concerned "Are you sure about this?" (~2s)
#   2. Brief pause with subtle wind (~0.5s)
#   3. Mary's confident "Absolutely. We have to try." (~2.5s)
#   4. Wind effect with tension (~1s)
#   5. John's determined "Then let's do it" (~2s)
```

## Processing Steps

1. **Dialogue Extraction (Using LLM)**
   ```python
   # Input: Raw scene content
   # Output: Structured dialogue segments
   extracted_dialogue = [
       {
           "text": "Are you sure about this?",
           "speaker": "John",
           "emotion": "concerned",
           "context": "looking at Mary with concern"
       },
       {
           "text": "Absolutely. We have to try.",
           "speaker": "Mary",
           "emotion": "confident",
           "context": "replied confidently"
       },
       {
           "text": "Then let's do it",
           "speaker": "John",
           "emotion": "determined",
           "context": "sighed deeply, with determination"
       }
   ]
   ```

2. **Voice Settings Generation**
   ```python
   # Combine dialogue context with manager recommendations
   voice_settings = {
       "John": {
           "dialogues": [
               {
                   "text": "Are you sure about this?",
                   "settings": {
                       "stability": 0.7,        # More variation for concern
                       "similarity_boost": 0.75,
                       "speaking_rate": 0.9,    # Slightly slower for tension
                       "emotion": "concerned"
                   }
               },
               # ... other dialogues
           ]
       },
       "Mary": {
           "dialogues": [
               {
                   "text": "Absolutely. We have to try.",
                   "settings": {
                       "stability": 0.8,        # More consistent for confidence
                       "similarity_boost": 0.7,
                       "speaking_rate": 1.1,    # Slightly faster for assertiveness
                       "emotion": "confident"
                   }
               }
           ]
       }
   }
   ```

3. **Audio Generation Sequence**
   ```python
   # Generate audio segments in sequence
   async def generate_scene_audio(voice_settings):
       audio_segments = []
       
       for speaker, dialogues in voice_settings.items():
           voice_id = character_voice_map[speaker]
           
           for dialogue in dialogues["dialogues"]:
               # Generate speech segment
               audio = await elevenlabs_client.generate_speech(
                   text=dialogue["text"],
                   voice_id=voice_id,
                   settings=dialogue["settings"]
               )
               
               # Add to sequence
               audio_segments.append({
                   "audio": audio,
                   "duration": len(audio) / SAMPLE_RATE,
                   "type": "dialogue"
               })
               
               # Add pause/effect if needed
               if needs_effect(dialogue):
                   effect = generate_effect()
                   audio_segments.append({
                       "audio": effect,
                       "duration": 0.5,  # 0.5s effects
                       "type": "effect"
                   })
       
       return audio_segments
   ```

## Audio Requirements

1. **Timing Guidelines**
   - Dialogue segments: 2-5 seconds each
   - Effect/pause segments: 0.5-1 second each
   - Total scene audio: ≤ 30 seconds

2. **Voice Quality Requirements**
   - Clear pronunciation
   - Natural emotional expression
   - Consistent character voices
   - Appropriate pacing based on context

3. **Audio Technical Specs**
   - Sample rate: 44.1kHz
   - Format: MP3
   - Bit rate: 192kbps
   - Channels: Mono

## ElevenLabs Integration
```python
async def generate_speech_segment(segment):
    voice_id = character_voice_map[segment["speaker"]]
    
    tts_request = {
        "text": segment["text"],
        "voice_settings": {
            "stability": segment["voice_settings"]["stability"],
            "similarity_boost": segment["voice_settings"]["similarity_boost"],
            "speaking_rate": segment["voice_settings"]["speaking_rate"]
        },
        "model_id": "eleven_monolingual_v1"
    }
    
    return await elevenlabs_client.generate_speech(voice_id, tts_request)
```

## Testing Focus Areas

1. **Dialogue Extraction Testing**
   ```python
   test_scene = '''
   "Hello!" said John.
   Mary smiled. "Hi there."
   '''
   # Verify:
   # - All dialogues extracted
   # - Correct speaker attribution
   # - Emotional context captured
   ```

2. **Audio Quality Testing**
   ```python
   test_segment = {
       "text": "Hello!",
       "speaker": "John",
       "emotion": "happy"
   }
   # Verify:
   # - Clear pronunciation
   # - Correct emotion
   # - Appropriate duration
   # - No audio artifacts
   ```

## Error Handling

1. **Critical Errors (Stop Processing)**
   - Failed dialogue extraction
   - Voice generation failure
   - Invalid emotion mapping

2. **Non-Critical Errors (Continue with Defaults)**
   - Missing emotional context → use neutral tone
   - Unclear speaker → use narrator voice
   - Long pauses → trim to max 1s

## Development Guidelines

### Code Structure
```
speech_agent/
├── __init__.py
├── agent.py           # Main agent logic
├── elevenlabs.py     # API integration
├── processors/       
│   ├── text.py       # Text processing
│   └── audio.py      # Audio processing
└── utils/
    ├── validation.py
    └── storage.py
```

### Processing Rules
1. **Text Segmentation**
   - Split by dialogue/narrative
   - Respect punctuation
   - Maximum segment length: 1000 chars

2. **Voice Selection**
   - Match character voices consistently
   - Use narrative voice for descriptions
   - Apply emotional context

3. **Performance Optimization**
   - Parallel processing where possible
   - Cache voice selections
   - Batch API requests

## Testing Requirements
1. **Unit Tests**
   - Text processing functions
   - Voice selection logic
   - Storage utilities

2. **Integration Tests**
   - ElevenLabs API integration
   - Database operations
   - End-to-end flow

## Monitoring
- Log all API calls
- Track processing time
- Monitor error rates
- Record audio generation stats

## Dependencies
```requirements.txt
aiohttp>=3.8.0
elevenlabs-python>=0.1.0
pydantic>=2.0.0
``` 