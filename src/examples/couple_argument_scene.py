import os
from pathlib import Path
from dotenv import load_dotenv
from src.models.speech_agent import SpeechAgent
from src.models.llm_client import GroqLLMClient, MistralLLMClient
from src.utils.audio_utils import validate_scene_content, validate_output_directory

# Load environment variables
load_dotenv()

def main():
    # Get API keys from environment
    groq_api_key = os.getenv("GROQ_API_KEY")
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    
    # Scene content - A young couple arguing
    scene_content = """
    Sarah stormed into the living room, her face flushed with anger. "You forgot our anniversary, didn't you?" she demanded.
    "What? No, I..." Tom stammered, looking up from his phone. "I just got caught up at work."
    "You're always 'caught up at work'!" Sarah's voice cracked with emotion. "Do you even care anymore?"
    Tom stood up, his expression shifting from defensive to hurt. "Of course I care!" he said firmly. "How can you even say that?"
    Sarah wiped a tear. "Then why does it feel like you're never really here?" she whispered.
    The silence hung heavy between them. Tom's shoulders slumped. "I'm sorry," he said softly. "You're right. I've been distant."
    """

    # Manager recommendations for voice modulation and emotional expression
    manager_recommendations = """
    Sarah's dialogue should express increasing emotional intensity:
    - First line: Sharp anger and accusation
    - Second line: Bitter frustration with rising volume
    - Third line: Vulnerability and hurt in whispered tone
    
    Tom's dialogue progression:
    - First line: Defensive and stammering
    - Second line: Strong and assertive defense
    - Third line: Gentle and remorseful
    
    Add subtle ambient tension between dialogues.
    Maintain natural pauses for emotional impact.
    Voice modulation should reflect the emotional arc of the argument.
    """

    # Configuration for the speech agent
    config = {
        "tts_config": {
            "model_id": "eleven_monolingual_v1",
            "stability": 0.7,
            "similarity_boost": 0.75
        },
        "character_voices": {
            "Sarah": "21m00Tcm4TlvDq8ikWAM",  # Female voice ID
            "Tom": "pNInz6obpgDQGcFmaJgB"     # Male voice ID
        },
        "default_voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.75,
            "speaking_rate": 1.0
        }
    }
    
    # Add LLM client if API keys are available
    if groq_api_key:
        config["llm_client"] = GroqLLMClient(api_key=groq_api_key)
        output_dir = "output/couple_argument_groq"
    elif mistral_api_key:
        config["llm_client"] = MistralLLMClient(api_key=mistral_api_key)
        output_dir = "output/couple_argument_mistral"
    else:
        print("Warning: No API keys found. SpeechAgent will use fallback mechanisms.")
        output_dir = "output/couple_argument_fallback"

    # Create output directory
    if not validate_output_directory(output_dir):
        print(f"Error: Could not create or access output directory: {output_dir}")
        return

    # Validate scene content
    if not validate_scene_content(scene_content):
        print("Error: Invalid scene content")
        return

    try:
        # Initialize speech agent
        agent = SpeechAgent(config)

        # Process scene and generate audio
        audio_segments = agent.process_scene(
            scene_content=scene_content,
            manager_recommendations=manager_recommendations,
            output_dir=output_dir
        )

        # Print summary
        print("\nAudio generation complete!")
        print(f"Generated {len(audio_segments)} segments")
        print(f"Audio files saved to: {output_dir}")

        # Print detailed segment information
        for i, segment in enumerate(audio_segments):
            if segment["type"] == "dialogue":
                print(f"\nSegment {i + 1}:")
                print(f"Speaker: {segment['speaker']}")
                print(f"Text: {segment['text']}")
                if "emotion" in segment:
                    print(f"Emotion: {segment['emotion']}")
                if "tone" in segment:
                    print(f"Tone: {segment['tone']}")
                print(f"File: {segment.get('file_path', 'Not saved')}")
            else:
                print(f"\nEffect/Pause {i + 1}:")
                print(f"Type: {segment['type']}")
                print(f"Duration: {segment.get('duration', 0.5)}s")

    except Exception as e:
        print(f"Error processing scene: {str(e)}")

if __name__ == "__main__":
    main() 