from elevenlabs_tts import ElevenLabsTTS
import random
import os

def generate_random_audio():
    # Initialize the TTS client
    config = {
        "model_id": "eleven_multilingual_v2",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
    
    tts_client = ElevenLabsTTS(config)
    
    # Sample texts with different emotions
    texts = [
        "I'm so excited to share this amazing news with you!",
        "I can't believe this is happening right now.",
        "Sometimes life takes unexpected turns, but we must stay strong.",
        "The sunset was absolutely breathtaking today.",
        "This is the most incredible experience of my life!"
    ]
    
    # Available voices with their characteristics
    voices = [
        {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Josh
            "name": "Josh",
            "style_range": (0.3, 0.7)
        },
        {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Rachel
            "name": "Rachel",
            "style_range": (0.4, 0.8)
        }
    ]
    
    # Create output directory if it doesn't exist
    output_dir = "random_audio_outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Select random text and voice
    text = random.choice(texts)
    voice = random.choice(voices)
    
    # Generate random characteristics
    characteristics = {
        "stability": random.uniform(0.3, 0.8),
        "similarity_boost": random.uniform(0.5, 0.9),
        "style": random.uniform(*voice["style_range"]),
        "speaker_boost": True
    }
    
    try:
        # Generate the audio
        output_path = os.path.join(output_dir, f"random_{voice['name']}.mp3")
        audio_data = tts_client.text_to_speech(
            text=text,
            voice_id=voice["voice_id"],
            **characteristics
        )
        
        # Save the audio
        with open(output_path, 'wb') as f:
            f.write(audio_data.getvalue())
            
        print(f"\nRandom audio generated successfully!")
        print(f"Voice: {voice['name']}")
        print(f"Text: {text}")
        print(f"Characteristics: {characteristics}")
        print(f"Output file: {output_path}")
        
    except Exception as e:
        print(f"Error generating audio: {str(e)}")

if __name__ == "__main__":
    generate_random_audio() 