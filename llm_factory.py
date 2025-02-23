from typing import Dict, Any, Optional, List, Type
import logging
import aiohttp
from config import LLMProvider, LLM_CONFIG, AgentType, PROMPT_TEMPLATES
from custom_llm_perplexity import PerplexityLLM
from custom_llm_groq import GroqLLM
from custom_llm_mistral import MistralLLM
from custom_llm_base import BaseLLM, LLMValidationError, LLMError
import os
import importlib
import json
from groq import Groq
import re

logger = logging.getLogger(__name__)

class ResponseValidator:
    """Validator for LLM responses"""
    
    @staticmethod
    def validate_story_analysis(content: str) -> Dict[str, Any]:
        """Validate and parse story analysis response"""
        try:
            # Remove any markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            
            # Required agent types and their fields
            required_agents = {
                "story_agent": ["recommendations", "reasoning"],
                "image_agent": ["recommendations", "reasoning"],
                "speech_agent": ["recommendations", "reasoning"]
            }
            
            # Validate each agent's recommendations
            for agent_name, required_fields in required_agents.items():
                if agent_name not in result:
                    raise LLMValidationError(f"Missing required agent: {agent_name}")
                
                agent_data = result[agent_name]
                for field in required_fields:
                    if field not in agent_data:
                        raise LLMValidationError(f"Missing required field '{field}' for {agent_name}")
                    
                    # Validate field is a non-empty string with meaningful content
                    if not isinstance(agent_data[field], str):
                        raise LLMValidationError(f"Field '{field}' for {agent_name} must be a string")
                    if len(agent_data[field].strip()) < 50:  # Ensure meaningful content length
                        raise LLMValidationError(f"Field '{field}' for {agent_name} must contain a detailed description (at least 50 characters)")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse story analysis JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(f"Invalid JSON format in story analysis response: {str(e)}")
        except Exception as e:
            logger.error(f"Story analysis validation failed: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(str(e))

    @staticmethod
    def validate_compliance_check(content: str) -> Dict[str, Any]:
        """Validate and parse compliance check response"""
        try:
            # Remove any markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            
            # Required fields and their types
            schema = {
                "is_safe": str,
                "explanation": str,
                "concerns": list,
                "suggestions": list
            }
            
            # Validate required fields and their types
            for field, field_type in schema.items():
                if field not in result:
                    raise LLMValidationError(f"Missing required field: {field}")
                if not isinstance(result[field], field_type):
                    raise LLMValidationError(f"Field '{field}' must be of type {field_type.__name__}")
                # Only check for empty fields on is_safe and explanation
                if field in ["is_safe", "explanation"] and not result[field]:
                    raise LLMValidationError(f"Empty field: {field}")
            
            # Validate is_safe values
            if result["is_safe"].lower() not in ["yes", "no"]:
                raise LLMValidationError("Field 'is_safe' must be 'yes' or 'no'")
                
            # Validate array fields
            for field in ["concerns", "suggestions"]:
                if not all(isinstance(item, str) for item in result[field]):
                    raise LLMValidationError(f"All items in '{field}' must be strings")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse compliance check JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(f"Invalid JSON format in compliance check response: {str(e)}")
        except Exception as e:
            logger.error(f"Compliance check validation failed: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(str(e))

class LLMFactory:
    """Factory class for creating LLM instances"""
    
    @staticmethod
    def create_llm(provider: LLMProvider, config: Dict[str, Any]) -> BaseLLM:
        """
        Create an LLM instance based on the provider
        
        Args:
            provider: LLM provider enum
            config: Configuration dictionary for the LLM
            
        Returns:
            BaseLLM: An instance of the specified LLM
            
        Raises:
            LLMValidationError: If provider is unknown
        """
        if provider == LLMProvider.PERPLEXITY:
            return PerplexityLLM(config)
        elif provider == LLMProvider.GROQ:
            return GroqLLM(config)
        elif provider == LLMProvider.MISTRAL:
            return MistralLLM(config)
        else:
            raise LLMValidationError(f"Unknown LLM provider: {provider}")

class LLMManager:
    """Manager class for handling LLM operations with fallback"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.api_keys = {
            LLMProvider.GROQ: os.getenv("GROQ_API_KEY"),
            LLMProvider.PERPLEXITY: os.getenv("PERPLEXITY_API_KEY"),
            LLMProvider.MISTRAL: os.getenv("MISTRAL_API_KEY")
        }
        self.validator = ResponseValidator()
        
    async def execute_with_fallback(
        self,
        prompt: str,
        system_message: str,
        agent_type: AgentType = AgentType.MANAGER,
        response_type: str = None
    ) -> Dict[str, Any]:
        """Execute LLM call with fallback strategy"""
        config = LLM_CONFIG[agent_type]
        
        # Try primary model (Groq)
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                model=config["primary"]["model"],
                temperature=config["primary"]["temperature"],
                max_tokens=config["primary"]["max_tokens"]
            )
            
            content = chat_completion.choices[0].message.content
            logger.debug(f"Raw LLM response:\n{content}")
            
            # Validate response based on type
            if response_type == "story_analysis":
                content = self.validator.validate_story_analysis(content)
            elif response_type == "compliance_check":
                content = self.validator.validate_compliance_check(content)
            
            return {
                "content": content,
                "provider": "groq",
                "usage": {
                    "prompt_tokens": chat_completion.usage.prompt_tokens,
                    "completion_tokens": chat_completion.usage.completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"Primary model (Groq) failed: {str(e)}")
            
            # Try fallback model
            try:
                result = await self._call_mistral(
                    prompt=prompt,
                    system_message=system_message,
                    config=config["fallback"]
                )
                
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"Raw Mistral response:\n{content}")
                
                # Validate response based on type
                if response_type == "story_analysis":
                    content = self.validator.validate_story_analysis(content)
                elif response_type == "compliance_check":
                    content = self.validator.validate_compliance_check(content)
                
                return {
                    "content": content,
                    "provider": "mistral",
                    "usage": {
                        "prompt_tokens": result["usage"]["prompt_tokens"],
                        "completion_tokens": result["usage"]["completion_tokens"]
                    }
                }
            except Exception as e2:
                logger.error(f"Fallback model failed: {str(e2)}")
                raise LLMError(f"Both primary and fallback models failed: {str(e)} | {str(e2)}")

    async def _call_mistral(
        self,
        prompt: str,
        system_message: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Mistral API"""
        headers = {
            "Authorization": f"Bearer {self.api_keys[LLMProvider.MISTRAL]}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"]
        }
        
        async with self.session.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=config["timeout"]
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise LLMError(f"Mistral API error: {response.status} - {error_text}")
            return await response.json()

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 