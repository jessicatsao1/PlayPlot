from typing import Dict, Any, List
import os
from pydantic import BaseModel, Field

class VoiceSettings(BaseModel):
    stability: float = Field(ge=0.0, le=1.0, default=0.7)
    similarity_boost: float = Field(ge=0.0, le=1.0, default=0.75)
    speaking_rate: float = Field(ge=0.5, le=2.0, default=1.0)

class DialogueSegment(BaseModel):
    text: str
    speaker: str
    emotion: str
    context: str = ""

def validate_scene_content(scene_content: str) -> bool:
    """Validate scene content format
    
    Args:
        scene_content: Raw scene content text
    
    Returns:
        bool: True if content is valid, False otherwise
    """
    if not scene_content or not isinstance(scene_content, str):
        return False
    
    # Check for minimum content
    if len(scene_content.strip()) < 10:
        return False
    
    # Check for dialogue markers
    if '"' not in scene_content:
        return False
    
    return True

def validate_output_directory(output_dir: str) -> bool:
    """Validate and create output directory if needed
    
    Args:
        output_dir: Path to output directory
    
    Returns:
        bool: True if directory is valid and accessible
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return os.access(output_dir, os.W_OK)
    except Exception:
        return False

def format_audio_metadata(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format audio segment metadata for output
    
    Args:
        segments: List of audio segments
    
    Returns:
        Dictionary containing formatted metadata
    """
    metadata = {
        "total_segments": len(segments),
        "total_duration": sum(s.get("duration", 0.5) for s in segments),
        "dialogue_count": sum(1 for s in segments if s["type"] == "dialogue"),
        "effect_count": sum(1 for s in segments if s["type"] != "dialogue"),
        "speakers": list(set(s["speaker"] for s in segments if "speaker" in s)),
        "segments": []
    }
    
    for segment in segments:
        if segment["type"] == "dialogue":
            metadata["segments"].append({
                "type": "dialogue",
                "speaker": segment["speaker"],
                "text": segment["text"],
                "file_path": segment.get("file_path")
            })
        else:
            metadata["segments"].append({
                "type": segment["type"],
                "duration": segment.get("duration", 0.5)
            })
    
    return metadata 