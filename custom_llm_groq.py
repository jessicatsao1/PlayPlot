import os
from typing import Dict, Any, List
from custom_llm_base import BaseLLM, LLMValidationError
from config import API_ENDPOINTS, ERROR_MESSAGES

class GroqLLM(BaseLLM):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_endpoint = API_ENDPOINTS["groq"]
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise LLMValidationError("Groq API key not found in environment variables")

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def format_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Format prompt for Groq API"""
        messages = []
        
        # Add system message if provided
        system_message = kwargs.get("system_message")
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }

    async def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Groq API response"""
        try:
            choices = response.get("choices", [])
            if not choices:
                raise LLMValidationError(
                    ERROR_MESSAGES["validation"].format(
                        details="No choices in response"
                    )
                )
            
            first_choice = choices[0]
            message = first_choice.get("message", {})
            
            return {
                "content": message.get("content", ""),
                "role": message.get("role", "assistant"),
                "finish_reason": first_choice.get("finish_reason"),
                "model": response.get("model", self.model),
                "usage": response.get("usage", {}),
                "raw_response": response
            }
            
        except Exception as e:
            raise LLMValidationError(
                ERROR_MESSAGES["validation"].format(
                    details=f"Failed to parse response: {str(e)}"
                )
            ) 