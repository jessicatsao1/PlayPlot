import os
from typing import Dict, Any, Optional
import requests
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ElevenLabsError(Exception):
    """Custom exception for ElevenLabs API errors"""
    pass

class ElevenLabsTTS:
    def __init__(self, config: Dict[str, Any]):
        """Initialize ElevenLabs TTS client
        
        Args:
            config: Configuration dictionary containing:
                - model_id (optional): ID of the TTS model to use
                - voice_id (optional): ID of the voice to use
                - stability (optional): Voice stability (0-1)
                - similarity_boost (optional): Voice similarity boost (0-1)
                - api_key (optional): ElevenLabs API key. If not provided, will look for ELEVENLABS_API_KEY in environment
        """
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ElevenLabsError("ElevenLabs API key not found in environment variables")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.model_id = config.get("model_id", "eleven_monolingual_v1")
        self.voice_id = config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # Default voice
        self.stability = config.get("stability", 0.5)
        self.similarity_boost = config.get("similarity_boost", 0.75)

    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def format_request(self, text: str, **kwargs) -> Dict[str, Any]:
        """Format request body for text-to-speech conversion
        
        Args:
            text: Text to convert to speech
            **kwargs: Additional parameters to override defaults
        """
        return {
            "text": text,
            "model_id": kwargs.get("model_id", self.model_id),
            "voice_settings": {
                "stability": kwargs.get("stability", self.stability),
                "similarity_boost": kwargs.get("similarity_boost", self.similarity_boost)
            }
        }

    def text_to_speech(self, text: str, output_path: Optional[str] = None, **kwargs) -> BytesIO:
        """Convert text to speech
        
        Args:
            text: Text to convert to speech
            output_path: Optional path to save the audio file
            **kwargs: Additional parameters to override defaults
        
        Returns:
            BytesIO object containing the audio data if output_path is None,
            otherwise saves to file and returns None
        """
        try:
            url = f"{self.base_url}/text-to-speech/{kwargs.get('voice_id', self.voice_id)}"
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=self.format_request(text, **kwargs)
            )
            
            if response.status_code != 200:
                raise ElevenLabsError(
                    f"API request failed with status {response.status_code}: {response.text}"
                )

            # Get audio data
            audio_data = BytesIO(response.content)
            
            # Save to file if output path is provided
            if output_path:
                with open(output_path, 'wb') as audio_file:
                    audio_file.write(audio_data.getvalue())
                return None
                
            return audio_data

        except Exception as e:
            raise ElevenLabsError(f"Text-to-speech conversion failed: {str(e)}")

    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices"""
        try:
            response = requests.get(
                f"{self.base_url}/voices",
                headers=self.get_headers()
            )
            
            if response.status_code != 200:
                raise ElevenLabsError(
                    f"Failed to get voices. Status: {response.status_code}: {response.text}"
                )
                
            return response.json()
            
        except Exception as e:
            raise ElevenLabsError(f"Failed to get voices: {str(e)}")

    def generate_sound_effect(self, text: str, output_path: str) -> None:
        """Generate a sound effect using ElevenLabs API
        
        Args:
            text: Description of the sound effect
            output_path: Path to save the generated audio
        """
        try:
            url = f"{self.base_url}/sfx/generate"
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )
            
            if response.status_code != 200:
                raise ElevenLabsError(
                    f"Sound effect generation failed with status {response.status_code}: {response.text}"
                )

            # Save audio to file
            with open(output_path, 'wb') as audio_file:
                audio_file.write(response.content)

        except Exception as e:
            raise ElevenLabsError(f"Sound effect generation failed: {str(e)}") 