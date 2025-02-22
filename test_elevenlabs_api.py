from src.models.elevenlabs_tts import ElevenLabsTTS
from io import BytesIO
from pydub import AudioSegment

def find_voice_by_characteristics(voices, desired_labels):
    """Find the first matching voice based on desired characteristics"""
    for voice in voices.get("voices", []):
        labels = voice.get("labels", {})
        if any(label in labels.items() for label in desired_labels):
            return {
                "name": voice.get("name"),
                "voice_id": voice.get("voice_id"),
                "labels": labels
            }
    return None

def combine_audio_with_background(main_audio_file, background_audio_file, output_path):
    """Combine main audio with background audio, overlaying them"""
    try:
        # Load the audio files
        main_audio = AudioSegment.from_mp3(main_audio_file)
        background_audio = AudioSegment.from_mp3(background_audio_file)
        
        # Lower the volume of background sound
        background_audio = background_audio - 10  # Reduce by 10dB
        
        # Overlay the sounds
        combined = main_audio.overlay(background_audio)
        
        # Export the result
        combined.export(output_path, format="mp3")
    except Exception as e:
        print(f"Error combining audio: {str(e)}")

def main():
    tts = ElevenLabsTTS({
        "model_id": "eleven_multilingual_v2",
    })

    try:
        voices = tts.get_available_voices()
        
        # Find woman voice
        woman_characteristics = [
            ("gender", "female"),
            ("accent", "strong")
        ]
        woman_voice = find_voice_by_characteristics(voices, woman_characteristics)

        if not woman_voice:
            print("Could not find suitable voice")
            return

        print(f"\nSelected woman's voice: {woman_voice['name']}")

        # Define speakers
        speakers = {
            "Woman": {
                "voice_id": woman_voice["voice_id"],
                "stability": 0.3,
                "similarity_boost": 0.85
            }
        }

        # Generate woman's speech
        print("\nGenerating woman's speech...")
        woman_text = "[concerned] Who's a good boy? Are you hungry? [playful] Want to go for a walk? [stern] But first, you need to sit! [happy] Good boy! Let's go!"
        woman_audio_path = "woman_speech.mp3"
        tts.text_to_speech(
            text=woman_text,
            output_path=woman_audio_path,
            voice_id=speakers["Woman"]["voice_id"],
            stability=speakers["Woman"]["stability"],
            similarity_boost=speakers["Woman"]["similarity_boost"]
        )

        # Generate dog sounds using TTS
        print("\nGenerating dog sounds...")
        dog_sounds_text = "[sound effect] woof woof! [panting] *excited dog noises* [bark bark] *playful barking*"
        dog_audio_path = "dog_sounds.mp3"
        tts.text_to_speech(  # Using regular TTS instead of sound effects
            text=dog_sounds_text,
            output_path=dog_audio_path,
            voice_id=woman_voice["voice_id"],  # Use the same voice but with different settings
            stability=0.1,  # Very low stability for more variation
            similarity_boost=0.3  # Lower similarity for more distortion
        )

        # Combine the audio files with dog sounds in background
        print("\nCombining audio files...")
        combine_audio_with_background(
            main_audio_file=woman_audio_path,
            background_audio_file=dog_audio_path,
            output_path="woman_and_dog_background.mp3"
        )
        
        print("Complete scene saved as 'woman_and_dog_background.mp3'")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 