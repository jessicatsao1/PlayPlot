from elevenlabs_tts import ElevenLabsTTS
from pydub import AudioSegment
import os

def generate_couple_argument():
    # Initialize TTS client
    config = {
        "model_id": "eleven_multilingual_v2",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
    
    tts_client = ElevenLabsTTS(config)
    
    # Define character voices with specific voice IDs
    characters = {
        "Mike": {
            "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - Male voice
            "stability": 0.6,
            "similarity_boost": 0.8
        },
        "Emily": {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Rachel - Female voice
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    # Define the argument dialogue
    dialogue = [
        {
            "speaker": "Mike",
            "text": "Emily, we need to talk about last night's party.",
            "emotion": "serious"
        },
        {
            "speaker": "Emily",
            "text": "What about it? I was just having fun with my friends.",
            "emotion": "defensive"
        },
        {
            "speaker": "Mike",
            "text": "You were flirting with that guy from your office all night!",
            "emotion": "angry"
        },
        {
            "speaker": "Emily",
            "text": "Oh my god, are you serious? He's just a colleague!",
            "emotion": "frustrated"
        },
        {
            "speaker": "Mike",
            "text": "I saw how you were laughing at everything he said.",
            "emotion": "hurt"
        },
        {
            "speaker": "Emily",
            "text": "You're being completely ridiculous. I can't believe you don't trust me!",
            "emotion": "angry"
        }
    ]
    
    # Create output directory
    output_dir = "couple_argument_outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # Generate individual audio segments
        audio_segments = []
        
        for i, line in enumerate(dialogue):
            character = characters[line["speaker"]]
            
            # Adjust voice characteristics based on emotion
            stability = character["stability"]
            similarity_boost = character["similarity_boost"]
            
            # Modify voice characteristics based on emotion
            if line["emotion"] == "angry":
                stability *= 0.6  # More variation for anger
                similarity_boost *= 1.2  # More intensity
            elif line["emotion"] == "hurt":
                stability *= 0.8  # Slight variation for hurt
                similarity_boost *= 0.9  # Less intensity
            elif line["emotion"] == "frustrated":
                stability *= 0.7  # Moderate variation
                similarity_boost *= 1.1  # Moderate intensity
            
            # Generate audio for this line
            audio_data = tts_client.text_to_speech(
                text=line["text"],
                voice_id=character["voice_id"],
                stability=min(stability, 1.0),  # Ensure we don't exceed 1.0
                similarity_boost=min(similarity_boost, 1.0)
            )
            
            # Save individual line
            temp_path = os.path.join(output_dir, f"line_{i}.mp3")
            with open(temp_path, 'wb') as f:
                f.write(audio_data.getvalue())
            
            # Convert to AudioSegment
            audio_segments.append(AudioSegment.from_mp3(temp_path))
            
            # Add a short pause between lines (longer pause after angry lines)
            pause_duration = 1000 if line["emotion"] == "angry" else 600  # milliseconds
            pause = AudioSegment.silent(duration=pause_duration)
            audio_segments.append(pause)
        
        # Combine all segments
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined += segment
        
        # Export final dialogue
        output_path = os.path.join(output_dir, "couple_argument.mp3")
        combined.export(output_path, format="mp3")
        
        print(f"\nCouple argument generated successfully!")
        print("\nDialogue:")
        for line in dialogue:
            print(f"{line['speaker']} ({line['emotion']}): {line['text']}")
        print(f"\nOutput file: {output_path}")
        
        # Clean up individual line files
        for i in range(len(dialogue)):
            temp_path = os.path.join(output_dir, f"line_{i}.mp3")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"Error generating argument: {str(e)}")

if __name__ == "__main__":
    generate_couple_argument() 