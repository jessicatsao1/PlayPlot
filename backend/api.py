from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
import json
import os
from database import Database
from manager_agent import ManagerAgent
from story_agent import StoryAgent
from image_agent import ImageAgent
from speech_agent import SpeechAgent
from llm_factory import LLMFactory
from config import TaskFlow
import mimetypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create required directories
REQUIRED_DIRS = [
    "static",
    "output",
    "output/audio",
    "output/images",
    "output/videos"
]

# Initialize FastAPI app
app = FastAPI(title="Story Generation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

# Add MIME types for audio files
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/wav", ".wav")

# Request Models
class MessageRequest(BaseModel):
    content: str
    timestamp: str
    isSender: bool = True
    type: str = "message"
    story_id: Optional[str] = None
    scene_number: Optional[int] = None

# Response Models
class ImageMetadata(BaseModel):
    width: int
    height: int
    model: str

class ImageData(BaseModel):
    url: str
    thumbnail_url: str
    prompt_used: str
    style: str
    metadata: ImageMetadata

class AudioSpeaker(BaseModel):
    character_id: str
    voice_id: str
    emotion: str

class AudioMetadata(BaseModel):
    format: str
    sample_rate: int

class AudioData(BaseModel):
    url: str
    duration: float
    speaker: AudioSpeaker
    metadata: AudioMetadata

class MediaMessage(BaseModel):
    status: str
    story_id: str
    scene_id: str
    isSender: bool
    timestamp: str
    type: str = "media"
    media: Dict[str, List[Union[ImageData, AudioData]]]

class StoryMetadata(BaseModel):
    word_count: int
    tone: str
    emotional_context: str
    setting_description: str
    options: Optional[List[str]] = None

class StoryMessage(BaseModel):
    content: str
    timestamp: str
    isSender: bool
    type: str = "message"
    story_id: str
    scene_number: int
    metadata: StoryMetadata

class APIResponse(BaseModel):
    status: str
    messages: List[Union[StoryMessage, MediaMessage]]

# Database instance
db = Database()

@app.on_event("startup")
async def startup_event():
    """Initialize database and required directories on startup"""
    # Create required directories
    for directory in REQUIRED_DIRS:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")
    
    # Initialize database
    await db.init_db()
    logger.info("Database initialized")

@app.post("/api/chat", response_model=APIResponse)
async def continue_story(request: MessageRequest):
    """
    Continue the story based on user input
    
    Args:
        request: MessageRequest containing user input and context
        
    Returns:
        APIResponse containing generated story content and media
    """
    try:
        # Initialize response messages list
        messages = []
        current_time = datetime.now().strftime("%H:%M")
        
        # Process through manager agent
        async with ManagerAgent(db) as manager:
            manager_output = await manager.process_request(
                user_id="test_user",  # Replace with actual user ID in production
                content={"user_input": request.content},
                flow_type=TaskFlow.STORY_MEDIA,
                story_id=request.story_id
            )
            
            if manager_output["status"] != "success":
                raise HTTPException(status_code=500, detail=manager_output.get("error", "Failed to process request"))
            
            # Process story task
            story_tasks = [task for task in manager_output["tasks"] if task["task_type"] == "story"]
            story_result = None
            if story_tasks:
                llm_factory = LLMFactory()
                async with StoryAgent(llm_factory, db=db) as story_agent:
                    story_result = await story_agent.process_manager_output(manager_output)
                    
                    # Add story message
                    if story_result["status"] == "success":
                        story_message = StoryMessage(
                            content=story_result["content"],
                            timestamp=current_time,
                            isSender=False,
                            story_id=manager_output["story_id"],
                            scene_number=manager_output["scene_number"],
                            metadata=StoryMetadata(
                                word_count=len(story_result["content"].split()),
                                tone=story_result["metadata"].get("tone", "neutral"),
                                emotional_context=story_result["metadata"].get("emotional_context", ""),
                                setting_description=story_result["metadata"].get("setting_description", ""),
                                options=story_result["metadata"].get("options", [])
                            )
                        )
                        messages.append(story_message)
            
            # Process image and speech tasks concurrently
            image_tasks = [task for task in manager_output["tasks"] if task["task_type"] == "image"]
            speech_tasks = [task for task in manager_output["tasks"] if task["task_type"] == "speech"]
            
            # Initialize agents
            llm_factory = LLMFactory()
            image_agent = ImageAgent(llm_factory) if image_tasks else None
            speech_agent = SpeechAgent(llm_factory, db=db) if speech_tasks else None
            
            # Process media tasks
            media_message = None
            if image_tasks or speech_tasks:
                media_message = MediaMessage(
                    status="success",
                    story_id=manager_output["story_id"],
                    scene_id=f"{manager_output['story_id']}_{manager_output['scene_number']}",
                    isSender=False,
                    timestamp=current_time,
                    media={"images": [], "audio": []}
                )
                
                # Process image
                if image_tasks and story_result:
                    image_result = await image_agent.process_task(
                        task_data=image_tasks[0],
                        story_scene=story_result["content"],
                        context=image_tasks[0]["content"]["context"]
                    )
                    
                    if image_result and "image_url" in image_result:
                        media_message.media["images"].append(ImageData(
                            url=image_result["image_url"],
                            thumbnail_url=image_result["image_url"],
                            prompt_used=image_result.get("prompt", ""),
                            style=image_result.get("style", "default"),
                            metadata=ImageMetadata(
                                width=1024,
                                height=1024,
                                model=image_result.get("models_used", {}).get("endpoint", "unknown")
                            )
                        ))
                
                # Process speech
                if speech_tasks and story_result:
                    speech_result = await speech_agent.process_task(
                        task_data=speech_tasks[0],
                        story_scene=story_result["content"],
                        context=speech_tasks[0]["content"]["context"]
                    )
                    
                    if speech_result and speech_result.get("metadata", {}).get("combined_audio_path"):
                        audio_path = speech_result["metadata"]["combined_audio_path"]
                        media_message.media["audio"].append(AudioData(
                            url=audio_path,
                            duration=0,  # Calculate actual duration
                            speaker=AudioSpeaker(
                                character_id="default",
                                voice_id="default",
                                emotion="neutral"
                            ),
                            metadata=AudioMetadata(
                                format="mp3",
                                sample_rate=44100
                            )
                        ))
                
                if media_message.media["images"] or media_message.media["audio"]:
                    messages.append(media_message)
        
        return APIResponse(
            status="success",
            messages=messages
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{story_id}/{filename}")
async def get_audio_file(story_id: str, filename: str):
    """Serve audio files with proper MIME type"""
    file_path = os.path.join("output", "audio", story_id, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    # Get the correct MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    return FileResponse(
        file_path,
        media_type=mime_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={filename}"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 