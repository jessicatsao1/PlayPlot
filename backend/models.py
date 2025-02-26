from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field
from config import TaskFlow

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(str, Enum):
    STORY = "story"
    IMAGE = "image"
    SPEECH = "speech"
    VIDEO = "video"

class Character(BaseModel):
    """Character model for story characters"""
    character_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    personality: str
    background: str
    speaking_style: str
    voice_id: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)  # character_id -> relationship
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Story(BaseModel):
    story_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: Optional[str] = None
    current_scene: int = 1
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    characters: Dict[str, Character] = Field(default_factory=dict)  # character_id -> Character
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Character: lambda v: v.dict()
        }

class Scene(BaseModel):
    scene_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    story_id: str
    scene_number: int
    content: Optional[str] = None
    manager_output: Dict[str, Any] = Field(default_factory=dict)
    story_output: Dict[str, Any] = Field(default_factory=dict)
    image_output: Dict[str, Any] = Field(default_factory=dict)
    speech_output: Dict[str, Any] = Field(default_factory=dict)
    character_profiles: Dict[str, Any] = Field(default_factory=dict)
    visual_analysis: Dict[str, Any] = Field(default_factory=dict)
    audio_direction: Dict[str, Any] = Field(default_factory=dict)
    scene_analysis: Dict[str, Any] = Field(default_factory=dict)
    media: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskAnalysis(BaseModel):
    flow_type: TaskFlow
    context: Dict[str, Any] = Field(default_factory=dict)
    recommendations: str
    reasoning: str

    class Config:
        json_encoders = {
            TaskFlow: lambda v: v.value,
            datetime: lambda v: v.isoformat()
        }
        
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d['flow_type'] = self.flow_type.value
        return d

class ComplianceResult(BaseModel):
    is_safe: bool
    explanation: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Task(BaseModel):
    """In-memory task model for processing (not persisted)"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    story_id: Optional[str] = None
    scene_id: Optional[str] = None
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    content: Dict[str, Any]
    compliance_result: Optional[ComplianceResult] = None
    task_analysis: Optional[TaskAnalysis] = None
    parent_task_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            TaskType: lambda v: v.value,
            TaskStatus: lambda v: v.value,
            TaskFlow: lambda v: v.value
        }
        
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        if d.get('task_type'):
            d['task_type'] = self.task_type.value
        if d.get('status'):
            d['status'] = self.status.value
        return d 