from enum import Enum
from typing import Dict, Any

class LLMProvider(Enum):
    PERPLEXITY = "perplexity"
    GROQ = "groq"
    MISTRAL = "mistral"

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
    "groq": "https://api.groq.com/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions"
}

# Default parameters
DEFAULT_PARAMS = {
    "max_retries": 3,
    "backoff_factor": 2,
    "timeout": 60,
    "chunk_size": 2000
} 