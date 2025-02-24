from typing import Dict, List, Any, Optional
import json
from io import BytesIO
import asyncio
import os
import logging
from datetime import datetime
from elevenlabs_tts import ElevenLabsTTS
from setup_utils import check_ffmpeg
from dotenv import load_dotenv
from pydub import AudioSegment
from llm_factory import LLMFactory, LLMManager
from config import LLM_CONFIG, AgentType, SPEECH_CONFIG

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
VALID_EMOTIONS = ["happy", "sad", "angry", "neutral", "excited", "concerned", "determined"]
VALID_TONES = ["normal", "whisper", "shouting", "calm", "firm", "trembling"]

class SpeechValidationError(Exception):
    """Custom exception for speech validation errors"""
    pass

class SpeechGenerationError(Exception):
    """Custom exception for speech generation errors"""
    pass

class SpeechAgent:
    """Speech Agent for converting story scenes into audio using ElevenLabs TTS"""
    
    def __init__(self, llm_factory: LLMFactory, db=None):
        """Initialize speech agent with LLM factory"""
        self.llm_factory = llm_factory
        self.db = db
        # Get config from LLM_CONFIG
        config = LLM_CONFIG[AgentType.SPEECH]["primary"]
        # Add API key to config
        config["api_key"] = os.getenv("GROQ_API_KEY")
        # Create LLM manager for fallback support
        self.llm_manager = LLMManager(config)
        self.logger = logging.getLogger(__name__)
        
        # Initialize ElevenLabs
        self.eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.eleven_api_key:
            raise SpeechValidationError("ELEVENLABS_API_KEY not found in environment variables")
            
        # Initialize TTS client
        self.tts_client = ElevenLabsTTS({
            "api_key": self.eleven_api_key,
            "model_id": "eleven_monolingual_v1"
        })
        
        # Load speech config
        self.speech_config = SPEECH_CONFIG["default"]
        
    async def process_task(
        self,
        task_data: Dict[str, Any],
        story_scene: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process speech generation task"""
        try:
            # Log input data types
            logger.info("=== Speech Agent Input Data ===")
            logger.info(f"Task Data Type: {type(task_data)}")
            logger.info(f"Story Scene Type: {type(story_scene)}")
            logger.info(f"Context Type: {type(context)}")

            # Validate inputs
            if not isinstance(task_data, dict):
                raise SpeechGenerationError("task_data must be a dictionary")
            if not isinstance(story_scene, str):
                raise SpeechGenerationError("story_scene must be a string")
            if not isinstance(context, dict):
                raise SpeechGenerationError("context must be a dictionary")

            # Extract story ID and scene number
            story_id = context.get("story_id")
            scene_number = context.get("scene_number")
            user_id = context.get("user_id")
            if not all([story_id, scene_number, user_id]):
                raise SpeechGenerationError("Missing required context fields: story_id, scene_number, or user_id")

            # Get characters from database
            characters = await self.db.get_characters(user_id)
            if not characters:
                logger.warning("No characters found in database")
                return {
                    "status": "error",
                    "error": "No characters available for speech generation"
                }

            # Log character data for debugging
            logger.info("=== Character Data ===")
            for char in characters:
                logger.info(f"Character: {json.dumps(char, indent=2)}")

            # Validate character data
            for char in characters:
                if not char.get("voice_id"):
                    logger.warning(f"Character {char.get('name')} missing voice_id, assigning default")
                    char["voice_id"] = "ErXwobaYiN019PkySvjV"  # Default voice ID

            # Generate dialogue segments
            dialogue_segments = await self._generate_dialogue_segments(
                story_scene=story_scene,
                characters=characters,
                task_analysis=task_data.get("task_analysis", {})
            )

            # Validate dialogue segments
            valid_segments = []
            for segment in dialogue_segments:
                speaker = segment.get("speaker")
                if not speaker:
                    logger.warning("Segment missing speaker, skipping")
                    continue
                
                # Find matching character
                matching_char = next(
                    (char for char in characters if char["name"].lower() == speaker.lower()),
                    None
                )
                
                if not matching_char:
                    logger.warning(f"No matching character found for speaker: {speaker}")
                    continue
                
                # Add voice ID to segment
                segment["voice_id"] = matching_char["voice_id"]
                valid_segments.append(segment)

            if not valid_segments:
                logger.error("No valid dialogue segments generated")
                return {
                    "status": "error",
                    "error": "Failed to generate valid dialogue segments"
                }

            # Generate speech for segments
            output_dir = os.path.join("output", "audio", story_id)
            os.makedirs(output_dir, exist_ok=True)
            
            speech_result = await self._generate_speech(
                valid_segments,
                context,
                output_dir
            )

            # Update scene with speech output
            scene_data = {
                "story_id": story_id,
                "scene_number": scene_number,
                "speech_api_call": json.dumps(valid_segments),
                "speech_url": speech_result.get("metadata", {}).get("combined_audio_path")
            }
            await self.db.save_scene(scene_data)
            logger.info(f"Updated scene {scene_number} with speech output")

            return speech_result

        except Exception as e:
            logger.error(f"Error processing speech: {str(e)}")
            return {
                "status": "error",
                "error": f"Failed to process speech: {str(e)}"
            }

    async def _generate_dialogue_segments(
        self,
        story_scene: str,
        characters: List[Dict[str, Any]],
        task_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate dialogue segments from story scene"""
        try:
            logger.info("=== Starting Dialogue Generation ===")
            logger.info(f"Story scene length: {len(story_scene)}")
            logger.info(f"Number of characters: {len(characters)}")

            # Prepare character info with exact names to use
            character_info = []
            available_names = []
            for char in characters:
                name = char.get("name", "")
                if name:
                    available_names.append(name)
                    char_desc = [
                        f"Name: {name}",
                        f"Physical Description: {char.get('description_physical', 'No description')}",
                        f"Voice Description: {char.get('voice_description', 'No voice description')}"
                    ]
                    character_info.append("\n".join(char_desc))

            character_info_str = "\n\n".join(character_info)
            logger.info("Character info prepared for prompt")
            logger.info(f"Available character names: {available_names}")

            # Prepare prompt with explicit character names
            prompt = f"""Given this story scene and character information, create speech segments for text-to-speech generation.
IMPORTANT: Only use these exact character names: {', '.join(available_names)}

Story Scene:
{story_scene}

Available Characters:
{character_info_str}

Task Analysis:
{json.dumps(task_analysis, indent=2)}

Create a JSON array of speech segments. Each segment MUST use one of the available character names exactly as listed above.
Each segment must have:
{{
    "text": "the text to be spoken",
    "speaker": "MUST be one of: {', '.join(available_names)}",
    "emotion": "one of: {', '.join(VALID_EMOTIONS)}",
    "tone": "one of: {', '.join(VALID_TONES)}",
    "intensity": number between 0.1 and 2.0
}}"""

            # Get LLM response
            logger.info("Requesting dialogue segmentation from LLM")
            llm_response = await self.llm_manager.execute_with_fallback(
                prompt,
                system_message="""You are an expert at analyzing dialogue and emotional context for speech synthesis.
CRITICAL: Only use character names from the provided list. Do not invent new characters.""",
                response_type="dialogue_segments"
            )

            # Parse response
            segments = self._parse_llm_response(llm_response)
            logger.info(f"Parsed {len(segments)} dialogue segments")

            # Validate segments against available characters
            valid_segments = []
            for segment in segments:
                speaker = segment.get("speaker", "")
                if not speaker:
                    logger.warning("Segment missing speaker, skipping")
                    continue
                
                if speaker not in available_names:
                    logger.warning(f"Speaker '{speaker}' not in available characters, skipping")
                    continue
                
                # Find matching character
                matching_char = next(
                    (char for char in characters if char["name"] == speaker),
                    None
                )
                
                if not matching_char:
                    logger.warning(f"No matching character found for speaker: {speaker}")
                    continue
                
                # Add voice ID to segment
                segment["voice_id"] = matching_char.get("voice_id", "ErXwobaYiN019PkySvjV")
                valid_segments.append(segment)

            if not valid_segments:
                logger.error("No valid dialogue segments generated")
                raise ValueError("Failed to generate valid dialogue segments")

            logger.info(f"Generated {len(valid_segments)} valid dialogue segments")
            return valid_segments

        except Exception as e:
            logger.error(f"Error generating dialogue segments: {str(e)}")
            raise SpeechGenerationError(f"Failed to generate dialogue segments: {str(e)}")

    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> List[Dict]:
        """Parse LLM response into structured segments"""
        try:
            # Get content from response
            content = llm_response.get("content", "")
            logger.info(f"Raw LLM response content: {content}")
            
            # If content is a string, clean and parse it
            if isinstance(content, str):
                # Remove markdown code blocks if present
                content = content.strip()
                if content.startswith("```") and content.endswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                # Try to find JSON array in the content
                try:
                    # Look for array pattern [...] if content contains other text
                    import re
                    array_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if array_match:
                        content = array_match.group(0)
                    
                    content = json.loads(content)
                    logger.info(f"Successfully parsed JSON content: {json.dumps(content, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse content as JSON: {str(e)}")
                    logger.error(f"Raw content after cleaning: {content}")
                    # Try to create a basic structure from the text
                    if isinstance(content, str):
                        # Create a simple dialogue segment
                        content = [{
                            "text": content,
                            "speaker": "Protagonist",
                            "emotion": "neutral",
                            "tone": "normal",
                            "intensity": 1.0
                        }]
                        logger.info("Created fallback dialogue segment")
            
            # Ensure content is a list
            if isinstance(content, dict):
                content = [content]
            elif not isinstance(content, list):
                raise ValueError(f"Expected list or dict, got {type(content)}")
            
            # Validate and normalize segments
            normalized = []
            for segment in content:
                if not isinstance(segment, dict):
                    logger.warning(f"Skipping invalid segment: {segment}")
                    continue
                    
                # Ensure required fields with defaults
                normalized_segment = {
                    "text": str(segment.get("text", "")),
                    "speaker": str(segment.get("speaker", "Protagonist")),
                    "emotion": str(segment.get("emotion", "neutral")).lower(),
                    "tone": str(segment.get("tone", "normal")).lower(),
                    "intensity": float(segment.get("intensity", 1.0))
                }
                
                # Validate fields
                if not normalized_segment["text"].strip():
                    logger.warning("Skipping segment with empty text")
                    continue
                    
                if normalized_segment["emotion"] not in VALID_EMOTIONS:
                    logger.warning(f"Invalid emotion {normalized_segment['emotion']}, using neutral")
                    normalized_segment["emotion"] = "neutral"
                    
                if normalized_segment["tone"] not in VALID_TONES:
                    logger.warning(f"Invalid tone {normalized_segment['tone']}, using normal")
                    normalized_segment["tone"] = "normal"
                    
                # Clamp intensity
                normalized_segment["intensity"] = max(0.1, min(2.0, normalized_segment["intensity"]))
                
                normalized.append(normalized_segment)
            
            if not normalized:
                logger.warning("No valid segments after normalization")
                # Create a default segment
                normalized = [{
                    "text": "I understand.",
                    "speaker": "Protagonist",
                    "emotion": "neutral",
                    "tone": "normal",
                    "intensity": 1.0
                }]
            
            logger.info(f"Normalized {len(normalized)} segments")
            return normalized
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            logger.error(f"Full LLM response: {json.dumps(llm_response, indent=2)}")
            # Return a basic fallback segment
            return [{
                "text": "I understand.",
                "speaker": "Protagonist",
                "emotion": "neutral",
                "tone": "normal",
                "intensity": 1.0
            }]

    async def _generate_speech(
        self,
        segments: List[Dict[str, Any]],
        context: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """Generate speech for all segments"""
        try:
            logger.info("=== Starting Speech Generation ===")
            logger.info(f"Processing {len(segments)} segments")
            audio_segments = []
            scene_id = context.get("scene_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
            story_id = context.get("story_id")
            
            if not story_id:
                raise ValueError("Missing story_id in context")
            
            # Create output directory structure
            audio_dir = os.path.join("output", "audio", story_id)
            os.makedirs(audio_dir, exist_ok=True)
            
            # Get characters from database again to ensure fresh data
            user_id = context.get("user_id")
            if not user_id:
                raise ValueError("Missing user_id in context")
                
            characters = await self.db.get_characters(user_id)
            if not characters:
                raise ValueError("No characters found in database")
                
            logger.info("Available characters for speech generation:")
            for char in characters:
                logger.info(f"Character: {char['name']} (Voice ID: {char.get('voice_id', 'MISSING')})")
            
            # Initialize combined audio
            combined_audio = None
            
            for i, segment in enumerate(segments):
                try:
                    logger.info(f"Processing segment {i + 1}/{len(segments)}")
                    speaker = segment["speaker"]
                    
                    # Find matching character with case-insensitive comparison
                    matching_char = next(
                        (char for char in characters 
                         if char.get("name", "").lower() == speaker.lower()),
                        None
                    )
                    
                    if not matching_char:
                        logger.warning(f"No exact match found for speaker: {speaker}")
                        # Try partial match
                        matching_char = next(
                            (char for char in characters 
                             if speaker.lower() in char.get("name", "").lower() or 
                             char.get("name", "").lower() in speaker.lower()),
                            None
                        )
                        
                    if not matching_char:
                        logger.error(f"No character match found for {speaker}, using default voice")
                        voice_id = "ErXwobaYiN019PkySvjV"  # Default voice ID
                    else:
                        voice_id = matching_char.get("voice_id", "ErXwobaYiN019PkySvjV")
                        logger.info(f"Found voice ID {voice_id} for character {speaker}")
                    
                    # Get voice settings
                    voice_settings = self._get_voice_settings(segment)
                    logger.info(f"Voice settings: {voice_settings}")
                    
                    # Generate speech
                    logger.info("Calling ElevenLabs API...")
                    audio_data = self.tts_client.text_to_speech(
                        text=segment["text"],
                        voice_id=voice_id,
                        **voice_settings
                    )
                    logger.info("Received audio data from ElevenLabs")
                    
                    # Save individual segment
                    filename = f"{scene_id}_{i}_{speaker.replace(' ', '_')}.mp3"
                    filepath = os.path.join(audio_dir, filename)
                    logger.info(f"Saving audio to {filepath}")
                    
                    # Handle BytesIO object properly
                    if isinstance(audio_data, BytesIO):
                        audio_data.seek(0)
                        audio_data = audio_data.read()
                    
                    with open(filepath, "wb") as f:
                        f.write(audio_data)
                    logger.info("Audio file saved successfully")
                    
                    # Create relative URL path for the audio file
                    relative_url = f"audio/{story_id}/{filename}"
                    
                    # Add segment info
                    audio_segments.append({
                        "url": relative_url,
                        "speaker": speaker,
                        "text": segment["text"],
                        "emotion": segment["emotion"],
                        "tone": segment["tone"],
                        "voice_id": voice_id,
                        "duration": 0,  # Will be updated after combining
                        "metadata": {
                            "format": "mp3",
                            "sample_rate": 44100
                        }
                    })
                    
                    # Add to combined audio
                    try:
                        segment_audio = AudioSegment.from_file(filepath, format="mp3")
                        # Update duration in the segment info
                        audio_segments[-1]["duration"] = len(segment_audio) / 1000.0
                        
                        if combined_audio is None:
                            combined_audio = segment_audio
                        else:
                            # Add pause between segments
                            pause_duration = self._calculate_pause_duration(
                                segment, 
                                segments[i + 1] if i < len(segments) - 1 else None
                            )
                            combined_audio += AudioSegment.silent(duration=int(pause_duration * 1000))
                            combined_audio += segment_audio
                    except Exception as e:
                        logger.error(f"Error combining audio segment {i}: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error processing segment {i}: {str(e)}")
                    continue
            
            # Save combined audio if we have it
            combined_filepath = None
            combined_url = None
            if combined_audio is not None and audio_segments:
                combined_filename = f"{scene_id}_combined.mp3"
                combined_filepath = os.path.join(audio_dir, combined_filename)
                combined_url = f"audio/{story_id}/{combined_filename}"
                logger.info(f"Saving combined audio to {combined_filepath}")
                try:
                    combined_audio.export(combined_filepath, format="mp3")
                    logger.info("Combined audio saved successfully")
                except Exception as e:
                    logger.error(f"Error saving combined audio: {str(e)}")
            
            logger.info(f"Successfully processed {len(audio_segments)} segments")
            return {
                "status": "success",
                "audio_segments": audio_segments,
                "metadata": {
                    "total_segments": len(segments),
                    "successful_segments": len([s for s in audio_segments if s.get("duration", 0) > 0]),
                    "scene_id": scene_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "combined_audio_path": combined_url
                }
            }
            
        except Exception as e:
            logger.error(f"Error in speech generation: {str(e)}")
            raise SpeechGenerationError(f"Failed to generate speech: {str(e)}")

    def _get_voice_id(self, speaker: str, characters: List[Dict[str, Any]]) -> str:
        """Get voice ID for speaker"""
        try:
            # Try exact match first
            for char in characters:
                if isinstance(char, dict) and char.get("name") == speaker:
                    if voice_id := char.get("voice_id"):
                        return voice_id
                    raise ValueError(f"No voice ID found for character: {speaker}")

            # Try case-insensitive match
            speaker_lower = speaker.lower()
            for char in characters:
                if isinstance(char, dict) and char.get("name", "").lower() == speaker_lower:
                    if voice_id := char.get("voice_id"):
                        return voice_id
                    raise ValueError(f"No voice ID found for character: {char.get('name')}")

            raise ValueError(f"Character not found: {speaker}")

        except Exception as e:
            logger.error(f"Error getting voice ID: {str(e)}")
            raise SpeechValidationError(f"Failed to get voice ID for {speaker}: {str(e)}")

    def _get_voice_settings(self, segment: Dict[str, Any]) -> Dict[str, float]:
        """Get voice settings based on emotion and tone"""
        settings = self.speech_config.get("default_voice_settings", {}).copy()
        
        # Get base emotion settings
        emotion = segment["emotion"].lower()
        emotion_settings = self.speech_config.get("emotion_settings", {}).get(emotion, {})
        settings.update(emotion_settings)
        
        # Get base tone settings
        tone = segment["tone"].lower()
        tone_settings = self.speech_config.get("tone_settings", {}).get(tone, {})
        
        # Blend tone settings with current settings
        for key in ["stability", "similarity_boost", "speaking_rate"]:
            if key in tone_settings and key in settings:
                settings[key] = (settings[key] + tone_settings[key]) / 2
        
        # Adjust for intensity
        intensity = float(segment.get("intensity", 1.0))
        if intensity > 1.0:
            settings["stability"] = max(0.3, settings.get("stability", 0.7) - 0.1)
            settings["speaking_rate"] = min(2.0, settings.get("speaking_rate", 1.0) * 1.2)
        elif intensity < 0.5:
            settings["stability"] = min(0.9, settings.get("stability", 0.7) + 0.1)
            settings["speaking_rate"] = max(0.8, settings.get("speaking_rate", 1.0) * 0.9)
        
        # Ensure all required settings exist with defaults
        settings.setdefault("stability", 0.7)
        settings.setdefault("similarity_boost", 0.75)
        settings.setdefault("speaking_rate", 1.0)
        
        return settings

    def _calculate_pause_duration(
        self,
        current: Dict[str, Any],
        next_segment: Dict[str, Any]
    ) -> float:
        """Calculate pause duration between segments"""
        base_duration = 0.5
        
        # Adjust for emotional transition
        if current["emotion"] != next_segment["emotion"]:
            base_duration *= 1.2
        
        # Adjust for speaker change
        if current["speaker"] != next_segment["speaker"]:
            base_duration *= 1.3
        
        # Adjust for intensity change
        intensity_diff = abs(float(current["intensity"]) - float(next_segment["intensity"]))
        if intensity_diff > 0.3:
            base_duration *= 1.2
        
        # Adjust for punctuation
        if current["text"].endswith((".", "!", "?")):
            base_duration *= 1.2
        elif current["text"].endswith(","):
            base_duration *= 0.8
        
        # Clamp final duration
        return min(max(base_duration, 0.3), 2.0) 