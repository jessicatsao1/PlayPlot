from typing import Dict, List, Any, Optional
import json
from io import BytesIO
import asyncio
import os
import subprocess
import platform
from src.models.elevenlabs_tts import ElevenLabsTTS
from src.models.llm_client import (
    BaseLLMClient,
    GroqLLMClient,
    MistralLLMClient,
    DialogueAnalysis
)
from dotenv import load_dotenv
from pydub import AudioSegment
import tempfile

load_dotenv()

def check_ffmpeg():
    """Check if ffmpeg is installed and install if needed."""
    try:
        # Try to run ffmpeg
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        system = platform.system().lower()
        try:
            if system == 'darwin':  # macOS
                try:
                    # First try normal install
                    subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        # Try installing from source if bottle not available
                        print("Attempting to install ffmpeg from source (this may take a while)...")
                        subprocess.run(['brew', 'install', '--build-from-source', 'ffmpeg'], check=True)
                    except subprocess.CalledProcessError:
                        # If both methods fail, try using conda
                        try:
                            subprocess.run(['conda', 'install', '-y', 'ffmpeg', '-c', 'conda-forge'], check=True)
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            print("Failed to install ffmpeg. Please try one of the following:")
                            print("1. Install using Homebrew: brew install --build-from-source ffmpeg")
                            print("2. Install using Conda: conda install -y ffmpeg -c conda-forge")
                            print("3. Download from https://ffmpeg.org/download.html")
                            return False
            elif system == 'linux':
                try:
                    subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                    subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True)
                except subprocess.CalledProcessError:
                    try:
                        # Try using conda if apt fails
                        subprocess.run(['conda', 'install', '-y', 'ffmpeg', '-c', 'conda-forge'], check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print("Failed to install ffmpeg. Please try one of the following:")
                        print("1. Install using apt: sudo apt-get install -y ffmpeg")
                        print("2. Install using Conda: conda install -y ffmpeg -c conda-forge")
                        print("3. Download from https://ffmpeg.org/download.html")
                        return False
            else:
                print("Please install ffmpeg using one of the following methods:")
                print("1. Install using Conda: conda install -y ffmpeg -c conda-forge")
                print("2. Download from https://ffmpeg.org/download.html")
                return False
            
            # Verify installation
            try:
                subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return True
            except FileNotFoundError:
                print("ffmpeg was installed but is not accessible. Please try restarting your terminal.")
                return False
                
        except Exception as e:
            print(f"Failed to install ffmpeg: {str(e)}")
            print("Please install ffmpeg manually using one of the following methods:")
            print("1. Using Homebrew (macOS): brew install --build-from-source ffmpeg")
            print("2. Using apt (Linux): sudo apt-get install -y ffmpeg")
            print("3. Using Conda: conda install -y ffmpeg -c conda-forge")
            print("4. Download from https://ffmpeg.org/download.html")
            return False

class SpeechAgent:
    def __init__(self, config: Dict[str, Any]):
        """Initialize Speech Agent
        
        Args:
            config: Configuration dictionary containing:
                - tts_config: Configuration for ElevenLabs TTS
                - character_voices: Mapping of character names to voice IDs
                - default_voice_settings: Default voice settings for characters
                - llm_client: Optional LLM client instance (if not provided, will try Groq, then Mistral)
        """
        # Check ffmpeg installation
        if not check_ffmpeg():
            raise RuntimeError("ffmpeg is required but not available. Please install it manually.")

        self.tts_client = ElevenLabsTTS(config.get("tts_config", {}))
        self.character_voices = config.get("character_voices", {})
        self.default_voice_settings = config.get("default_voice_settings", {
            "stability": 0.7,
            "similarity_boost": 0.75,
            "speaking_rate": 1.0
        })
        
        # Get or create LLM client with Groq prioritized
        self.llm_client = config.get("llm_client")
        if not isinstance(self.llm_client, BaseLLMClient):
            groq_api_key = os.getenv("GROQ_API_KEY")
            mistral_api_key = os.getenv("MISTRAL_API_KEY")
            
            if groq_api_key:
                self.llm_client = GroqLLMClient(api_key=groq_api_key)
            elif mistral_api_key:
                self.llm_client = MistralLLMClient(api_key=mistral_api_key)
            else:
                raise ValueError("No LLM client provided and no API keys found in environment")

    def extract_dialogue(self, scene_content: str) -> List[Dict[str, Any]]:
        """Extract dialogue segments from scene content using LLM
        
        Args:
            scene_content: Raw scene content text
        
        Returns:
            List of dialogue segments with speaker, text, emotion, and context
        """
        try:
            # Use LLM to analyze dialogue
            dialogue_analysis = self.llm_client.analyze_dialogue(scene_content)
            
            # Convert DialogueAnalysis objects to dictionary format
            dialogue_segments = []
            for analysis in dialogue_analysis:
                dialogue_segments.append({
                    "text": analysis.text,
                    "speaker": analysis.speaker,
                    "emotion": analysis.emotion,
                    "context": analysis.context,
                    "tone": analysis.tone,
                    "intensity": analysis.intensity
                })
            
            return dialogue_segments
            
        except Exception as e:
            raise Exception(f"Failed to extract dialogue: {str(e)}")

    def generate_voice_settings(self, dialogue_segments: List[Dict[str, Any]], 
                              manager_recommendations: Optional[str] = None) -> Dict[str, Any]:
        """Generate voice settings for each dialogue segment using LLM
        
        Args:
            dialogue_segments: List of extracted dialogue segments
            manager_recommendations: Optional string containing voice recommendations
        
        Returns:
            Dictionary containing sequential dialogue settings
        """
        try:
            # Convert dialogue segments to DialogueAnalysis objects
            dialogue_analysis = []
            for segment in dialogue_segments:
                analysis = DialogueAnalysis(
                    text=segment["text"],
                    speaker=segment["speaker"],
                    emotion=segment["emotion"],
                    context=segment["context"],
                    tone=segment.get("tone", "normal"),
                    intensity=segment.get("intensity", 0.5)
                )
                dialogue_analysis.append(analysis)
            
            # Get LLM recommendations
            llm_recommendations = self.llm_client.generate_voice_recommendations(dialogue_analysis)
            
            # Format voice settings as sequential list
            voice_settings = {
                "sequence": []
            }
            
            # Process each segment in order
            for segment in dialogue_segments:
                speaker = segment["speaker"]
                
                # Get speaker-specific settings from LLM recommendations
                speaker_settings = llm_recommendations.get(speaker, self.default_voice_settings)
                
                # Combine with intensity-based adjustments
                intensity = segment.get("intensity", 0.7)
                settings = {
                    "stability": speaker_settings.get("stability", 0.7),
                    "similarity_boost": speaker_settings.get("similarity_boost", 0.75),
                    "speaking_rate": speaker_settings.get("speaking_rate", 1.0)
                }
                
                # Add to sequential settings
                voice_settings["sequence"].append({
                    "speaker": speaker,
                    "text": segment["text"],
                    "settings": settings,
                    "emotion": segment["emotion"],
                    "tone": segment.get("tone")
                })
            
            return voice_settings
            
        except Exception as e:
            raise Exception(f"Failed to generate voice settings: {str(e)}")

    def _calculate_pause_duration(self, current_dialogue: Dict[str, Any], next_dialogue: Optional[Dict[str, Any]] = None) -> float:
        """Calculate appropriate pause duration based on emotion and context
        
        Args:
            current_dialogue: Current dialogue segment
            next_dialogue: Next dialogue segment (if any)
            
        Returns:
            Pause duration in seconds
        """
        base_duration = 0.5  # Base pause duration
        
        # Adjust for emotional intensity
        intensity = float(current_dialogue.get("intensity", 0.5))
        if intensity > 0.7:  # High intensity emotions need shorter pauses
            base_duration *= 0.7
        elif intensity < 0.3:  # Low intensity emotions need longer pauses
            base_duration *= 1.3
            
        # Adjust for specific emotions
        emotion = current_dialogue.get("emotion", "").lower()
        if emotion in ["sad", "contemplative", "concerned"]:
            base_duration *= 1.5  # Longer pauses for somber emotions
        elif emotion in ["angry", "excited", "happy"]:
            base_duration *= 0.8  # Shorter pauses for energetic emotions
            
        # Adjust for tone
        tone = current_dialogue.get("tone", "").lower()
        if tone == "whisper":
            base_duration *= 1.2
        elif tone == "shout":
            base_duration *= 0.7
            
        # If we have next dialogue, adjust for conversation flow
        if next_dialogue:
            # If same speaker continues, shorter pause
            if current_dialogue["speaker"] == next_dialogue["speaker"]:
                base_duration *= 0.8
            
            # If it's a response to a question, shorter pause
            if current_dialogue["text"].endswith("?") and not next_dialogue["text"].endswith("?"):
                base_duration *= 0.7
            
            # If emotions change dramatically, longer pause
            current_intensity = float(current_dialogue.get("intensity", 0.5))
            next_intensity = float(next_dialogue.get("intensity", 0.5))
            if abs(current_intensity - next_intensity) > 0.3:
                base_duration *= 1.3
        
        # Ensure reasonable bounds
        return min(max(base_duration, 0.3), 2.0)

    async def generate_scene_audio(self, voice_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate audio segments for the entire scene
        
        Args:
            voice_settings: Dictionary containing sequential dialogue settings
        
        Returns:
            List of audio segments with audio data and metadata in sequential order
        """
        audio_segments = []
        sequence = voice_settings["sequence"]
        
        # Process each dialogue in sequence
        for i, dialogue in enumerate(sequence):
            speaker = dialogue["speaker"]
            voice_id = self.character_voices.get(speaker, self.tts_client.voice_id)
            
            # Generate speech segment
            audio_data = self.tts_client.text_to_speech(
                text=dialogue["text"],
                voice_id=voice_id,
                **dialogue["settings"]
            )
            
            audio_segments.append({
                "audio": audio_data,
                "speaker": speaker,
                "text": dialogue["text"],
                "type": "dialogue",
                "emotion": dialogue["emotion"],
                "tone": dialogue.get("tone"),
                "intensity": dialogue.get("intensity", 0.5)
            })
            
            # Add dynamic pause after each dialogue (except the last one)
            if i < len(sequence) - 1:
                next_dialogue = sequence[i + 1]
                pause_duration = self._calculate_pause_duration(dialogue, next_dialogue)
                audio_segments.append({
                    "type": "pause",
                    "duration": pause_duration,
                    "reason": f"Emotional transition: {dialogue['emotion']} ({dialogue['speaker']}) -> {next_dialogue['emotion']} ({next_dialogue['speaker']})"
                })
        
        return audio_segments

    def process_scene(self, scene_content: str, 
                     manager_recommendations: Optional[str] = None,
                     output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """Process a complete scene and generate audio
        
        Args:
            scene_content: Raw scene content text
            manager_recommendations: Optional voice/emotion recommendations
            output_dir: Optional directory to save audio files
        
        Returns:
            List of generated audio segments with metadata and path to combined audio file
        """
        try:
            # Extract dialogue segments
            dialogue_segments = self.extract_dialogue(scene_content)
            
            # Generate voice settings
            voice_settings = self.generate_voice_settings(dialogue_segments, manager_recommendations)
            
            # Generate audio segments
            audio_segments = asyncio.run(self.generate_scene_audio(voice_settings))
            
            if output_dir and audio_segments:
                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                try:
                    # Initialize combined audio
                    combined_audio = None
                    
                    # Process each segment
                    for i, segment in enumerate(audio_segments):
                        if segment["type"] == "dialogue" and isinstance(segment["audio"], BytesIO):
                            # Save individual segment
                            segment_path = f"{output_dir}/segment_{i}.mp3"
                            with open(segment_path, "wb") as f:
                                f.write(segment["audio"].getvalue())
                            segment["file_path"] = segment_path
                            
                            try:
                                # Add to combined audio
                                segment_audio = AudioSegment.from_file(segment_path, format="mp3")
                                
                                if combined_audio is None:
                                    combined_audio = segment_audio
                                else:
                                    combined_audio += AudioSegment.silent(duration=500)  # Add 0.5s pause
                                    combined_audio += segment_audio
                            except Exception as e:
                                print(f"Warning: Failed to process segment {i}: {str(e)}")
                        
                        elif segment["type"] == "pause":
                            # Add pause between segments
                            if combined_audio is not None:
                                combined_audio += AudioSegment.silent(duration=int(segment["duration"] * 1000))
                    
                    # Export combined audio
                    if combined_audio is not None:
                        combined_path = f"{output_dir}/combined_scene.mp3"
                        combined_audio.export(combined_path, format="mp3")
                        
                        # Add combined file path to the result
                        for segment in audio_segments:
                            segment["combined_file"] = combined_path
                
                except Exception as e:
                    print(f"Warning: Failed to combine audio segments: {str(e)}")
                    # Continue without combined audio
            
            return audio_segments
            
        except Exception as e:
            raise Exception(f"Error processing scene: {str(e)}") 