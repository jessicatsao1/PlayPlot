from src.models.elevenlabs_tts import ElevenLabsTTS
import requests

def find_voice_by_description(tts, description):
    """Find a voice using natural language description
    
    Args:
        tts: ElevenLabsTTS instance
        description: Natural language description of desired voice
        
    Returns:
        dict: Voice data if successful, None if failed
    """
    try:
        url = f"{tts.base_url}/voice-lab/generate"
        response = requests.post(
            url,
            headers=tts.get_headers(),
            json={
                "description": description,
                "name": "Generated Voice"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def main():
    # Initialize TTS client
    tts = ElevenLabsTTS({
        "model_id": "eleven_multilingual_v2",
    })

    try:
        # Test different voice descriptions
        voice_descriptions = [
            {
                "name": "professional_narrator",
                "description": "A warm, professional male voice with perfect enunciation. Ideal for documentaries.",
            },
            {
                "name": "friendly_teacher",
                "description": "A gentle, patient female voice that sounds encouraging and clear.",
            },
            {
                "name": "elder_storyteller",
                "description": "An elderly voice with wisdom and character, perfect for telling folk tales.",
            },
            {
                "name": "child_character",
                "description": "A young, energetic voice that sounds like a 10-year-old child.",
            }
        ]

        # Generate voices from descriptions
        for voice_desc in voice_descriptions:
            print(f"\nGenerating voice for: {voice_desc['name']}")
            print(f"Description: {voice_desc['description']}")
            
            result = find_voice_by_description(tts, voice_desc['description'])
            
            if result:
                print(f"Successfully generated voice:")
                print(f"Voice ID: {result.get('voice_id')}")
                print(f"Settings: {result.get('settings', {})}")
            else:
                print("Failed to generate voice")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 