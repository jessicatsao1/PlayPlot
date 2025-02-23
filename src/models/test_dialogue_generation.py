from elevenlabs_tts import ElevenLabsTTS
from pydub import AudioSegment
import os

def generate_dialogue():
    # Initialize TTS client
    config = {
        "model_id": "eleven_multilingual_v2",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
    
    tts_client = ElevenLabsTTS(config)
    
    # Define character voices
    characters = {
        "John": {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Josh voice
            "stability": 0.6,
            "similarity_boost": 0.8
        },
        "Sarah": {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Rachel voice
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    # Define dialogue script
    dialogue = [
        {
            "speaker": "John",
            "text": "Hey Sarah, can we talk about what happened last night?",
            "emotion": "concerned"
        },
        {
            "speaker": "Sarah",
            "text": "I don't know what you're talking about.",
            "emotion": "defensive"
        },
        {
            "speaker": "John",
            "text": "The party. You were completely ignoring me the whole time.",
            "emotion": "hurt"
        },
        {
            "speaker": "Sarah",
            "text": "Oh, so now I can't even talk to other people? Is that what you're saying?",
            "emotion": "angry"
        }
    ]
    
    # Create output directory
    output_dir = "dialogue_outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # Generate individual audio segments
        audio_segments = []
        
        for i, line in enumerate(dialogue):
            character = characters[line["speaker"]]
            
            # Adjust voice characteristics based on emotion
            stability = character["stability"]
            if line["emotion"] in ["angry", "hurt"]:
                stability *= 0.7  # More variation for emotional lines
            
            # Generate audio for this line
            audio_data = tts_client.text_to_speech(
                text=line["text"],
                voice_id=character["voice_id"],
                stability=stability,
                similarity_boost=character["similarity_boost"]
            )
            
            # Save individual line
            temp_path = os.path.join(output_dir, f"line_{i}.mp3")
            with open(temp_path, 'wb') as f:
                f.write(audio_data.getvalue())
            
            # Convert to AudioSegment
            audio_segments.append(AudioSegment.from_mp3(temp_path))
            
            # Add a short pause between lines
            pause = AudioSegment.silent(duration=800)  # 800ms pause
            audio_segments.append(pause)
        
        # Combine all segments
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined += segment
        
        # Export final dialogue
        output_path = os.path.join(output_dir, "full_dialogue.mp3")
        combined.export(output_path, format="mp3")
        
        print(f"\nDialogue generated successfully!")
        print(f"Output file: {output_path}")
        
        # Clean up individual line files
        for i in range(len(dialogue)):
            temp_path = os.path.join(output_dir, f"line_{i}.mp3")
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"Error generating dialogue: {str(e)}")

if __name__ == "__main__":
    generate_dialogue() 