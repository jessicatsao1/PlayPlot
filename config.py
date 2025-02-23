from enum import Enum
from typing import Dict, Any
import os
from pydantic import BaseModel

class LLMProvider(str, Enum):
    OPENAI = "openai"
    GROQ = "groq"
    OAI_CUSTOM = "oai_custom"
    SCALEWAY = "scaleway"
    ALIYUN = "aliyun"
    GROK = "grok"
    MISTRAL = "mistral"
    PERPLEXITY = "perplexity"

# Add video provider enum
class VideoProvider(str, Enum):
    FAL_SKYREELS = "fal-ai/skyreels-i2v"
    FAL_PIXVERSE = "fal-ai/pixverse/v3.5/image-to-video/fast"
    FAL_MINIMAX = "fal-ai/minimax-video"
    FAL_LUMA = "fal-ai/luma-dream-machine"
    FAL_KLING = "fal-ai/kling-video/v1/standard"

class AgentType(Enum):
    MANAGER = "manager"
    STORY = "story"
    IMAGE = "image"
    SPEECH = "speech"
    VIDEO = "video"

class TaskFlow(Enum):
    STORY_MEDIA = "story_media"
    VIDEO = "video"

LLM_CONFIG = {
    AgentType.MANAGER: {
        "primary": {
            "provider": LLMProvider.GROQ,
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout": 60,
            "retry_count": 3,
            "system_message": "You are an expert story analysis system. Follow the exact format specified in prompts."
        },
        "fallback": {
            "provider": LLMProvider.MISTRAL,
            "model": "mistral-large-latest",
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout": 60,
            "retry_count": 3,
            "system_message": "You are an expert story analysis system. Follow the exact format specified in prompts."
        }
    },
    AgentType.STORY: {
        "primary": {
            "provider": LLMProvider.GROQ,
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.8,
            "max_tokens": 4000,
            "timeout": 60,
            "retry_count": 3,
            "system_message": "You are a creative story generation expert."
        },
        "fallback": {
            "provider": LLMProvider.MISTRAL,
            "model": "mistral-medium",
            "temperature": 0.8,
            "max_tokens": 4000,
            "timeout": 60,
            "retry_count": 3,
            "system_message": "You are a creative story generation expert."
        }
    }
}

# Base prompts for different tasks
PROMPT_TEMPLATES = {
    "compliance_check": """
    Task: Analyze the following content for compliance with content guidelines.
    Content: {content}
    Guidelines: {guidelines}
    
    Analyze for:
    1. Age-appropriate content
    2. Safe themes and topics
    3. Appropriate language
    4. Cultural sensitivity
    
    You MUST return your response in the following JSON format ONLY:
    {{
        "is_safe": "yes" or "no",
        "explanation": "Detailed explanation of compliance analysis",
        "concerns": ["List of specific concerns if any"],
        "suggestions": ["List of suggestions for improvement if needed"]
    }}

    Do not include any other text, markdown formatting, or additional content.
    Just return the JSON object.
    """,
    
    "story_analysis": """
    Task: Analyze the story requirements and provide recommendations for each agent type.
    Content: {content}
    
    Analyze the content and provide specific recommendations for each agent type.
    You MUST return your analysis in the following JSON format ONLY:
    {{
        "story_agent": {{
            "recommendations": "A detailed paragraph describing the story elements, plot points, character development, and narrative structure",
            "reasoning": "A clear explanation of why these story recommendations will enhance the narrative"
        }},
        "image_agent": {{
            "recommendations": "A detailed paragraph describing the visual elements, scenes, style, and atmosphere to create",
            "reasoning": "A clear explanation of why these visual elements will enhance the story"
        }},
        "speech_agent": {{
            "recommendations": "A detailed paragraph describing the audio elements, character voices, sound effects, and music to include",
            "reasoning": "A clear explanation of why these audio elements will enhance the experience"
        }}
    }}

    Focus on actionable recommendations that each agent can implement.
    Do not include any other text, markdown formatting, or additional content.
    Just return the JSON object.
    """
}

# Error messages
ERROR_MESSAGES = {
    "api_error": "API call failed: {error}",
    "timeout": "Request timed out after {timeout} seconds",
    "validation": "Validation failed: {details}",
    "compliance": "Content compliance check failed: {reason}",
    "llm_error": "LLM processing failed: {error}",
    "parsing_error": "Failed to parse LLM response: {error}",
    "schema_error": "Response does not match required schema: {details}"
}

# API endpoints
API_ENDPOINTS = {
    "perplexity": "https://api.perplexity.ai/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "fal_video": {
        "skyreels": "fal-ai/skyreels-i2v",
        "pixverse": "fal-ai/pixverse/v3.5/image-to-video/fast",
        "minimax": "fal-ai/minimax-video",
        "luma": "fal-ai/luma-dream-machine",
        "kling": "fal-ai/kling-video/v1/standard"
    }
}

# Add video configuration
VIDEO_MODELS = {
    "skyreels": {
        "provider": VideoProvider.FAL_SKYREELS,
        "endpoint": "skyreels",
        "settings": {
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
            "aspect_ratio": "16:9"
        }
    },
    "pixverse": {
        "provider": VideoProvider.FAL_PIXVERSE,
        "endpoint": "pixverse",
        "settings": {
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
            "aspect_ratio": "16:9",
            "resolution": "720p"
        }
    },
    "minimax": {
        "provider": VideoProvider.FAL_MINIMAX,
        "endpoint": "minimax",
        "settings": {
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
            "aspect_ratio": "16:9"
        }
    },
    "luma": {
        "provider": VideoProvider.FAL_LUMA,
        "endpoint": "luma",
        "settings": {
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
            "aspect_ratio": "16:9"
        }
    },
    "kling": {
        "provider": VideoProvider.FAL_KLING,
        "endpoint": "kling",
        "settings": {
            "guidance_scale": 6.0,
            "num_inference_steps": 30,
            "aspect_ratio": "16:9"
        }
    }
}

# Add video agent configuration with default settings
VIDEO_AGENT_CONFIG = {
    "primary": {
        "provider": VideoProvider.FAL_SKYREELS,
        "model": "skyreels",
        "settings": VIDEO_MODELS["skyreels"]["settings"]
    },
    "fallback": {
        "provider": VideoProvider.FAL_PIXVERSE,
        "model": "pixverse",
        "settings": VIDEO_MODELS["pixverse"]["settings"]
    }
}

# Default parameters
DEFAULT_PARAMS = {
    "max_retries": 3,
    "backoff_factor": 2,
    "timeout": 60,
    "chunk_size": 2000
}

# Add provider timeouts
PROVIDER_TIMEOUTS = {
    LLMProvider.PERPLEXITY: 60,
    LLMProvider.GROQ: 60,
    LLMProvider.MISTRAL: 60
}

class APIConfig(BaseModel):
    """API Configuration Settings"""
    # ... existing fields ...

    # FAL AI Video Configuration
    fal_api_key: str = os.getenv("FAL_API_KEY")
    video_model: str = VIDEO_AGENT_CONFIG["primary"]["model"]
    video_settings: Dict[str, Any] = VIDEO_AGENT_CONFIG["primary"]["settings"]
    video_fallback_model: str = VIDEO_AGENT_CONFIG["fallback"]["model"]
    video_fallback_settings: Dict[str, Any] = VIDEO_AGENT_CONFIG["fallback"]["settings"]

    @classmethod
    def load_from_env(cls) -> 'APIConfig':
        """Load configuration from environment variables"""
        return cls(
            fal_api_key=os.getenv("FAL_API_KEY"),
            video_model=VIDEO_AGENT_CONFIG["primary"]["model"],
            video_settings=VIDEO_AGENT_CONFIG["primary"]["settings"].copy(),
            video_fallback_model=VIDEO_AGENT_CONFIG["fallback"]["model"],
            video_fallback_settings=VIDEO_AGENT_CONFIG["fallback"]["settings"].copy()
        )

    def get_video_config(self, use_fallback: bool = False) -> Dict[str, Any]:
        """Get video generation configuration"""
        model_key = self.video_fallback_model if use_fallback else self.video_model
        model_config = VIDEO_MODELS[model_key]
        
        if not self.fal_api_key:
            raise ValueError("FAL API key not found in environment variables")
            
        # Get endpoint path
        endpoint = API_ENDPOINTS["fal_video"][model_config["endpoint"]]
            
        return {
            "provider": model_config["provider"].value,
            "api_key": self.fal_api_key,
            "settings": self.video_fallback_settings if use_fallback else self.video_settings,
            "endpoint": endpoint
        }

    def set_video_model(self, model_name: str, is_fallback: bool = False) -> None:
        """Set video model and its settings"""
        if model_name not in VIDEO_MODELS:
            raise ValueError(f"Invalid video model: {model_name}")
            
        if is_fallback:
            self.video_fallback_model = model_name
            self.video_fallback_settings = VIDEO_MODELS[model_name]["settings"].copy()
        else:
            self.video_model = model_name
            self.video_settings = VIDEO_MODELS[model_name]["settings"].copy()

    def update_video_settings(self, settings: Dict[str, Any], is_fallback: bool = False) -> None:
        """Update video settings"""
        target_settings = self.video_fallback_settings if is_fallback else self.video_settings
        target_settings.update(settings)

# ... rest of the existing code ... 