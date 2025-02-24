from typing import Dict, Any, Optional, List, Type
import logging
import aiohttp
from config import LLMProvider, LLM_CONFIG, AgentType, PROMPT_TEMPLATES, API_ENDPOINTS
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
    def validate_model_selection(content: str) -> Dict[str, Any]:
        """Validate and parse model selection response"""
        try:
            # Remove any markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            
            # Required fields
            required_fields = ["checkpoint", "lora"]
            
            # Validate required fields
            for field in required_fields:
                if field not in result:
                    raise LLMValidationError(f"Missing required field: {field}")
                    
                # Validate field is a non-empty string
                if not isinstance(result[field], str):
                    raise LLMValidationError(f"Field '{field}' must be a string")
                if not result[field].strip():
                    raise LLMValidationError(f"Field '{field}' cannot be empty")
                    
            # Validate checkpoint type
            if result["checkpoint"] not in ["realistic", "anime"]:
                raise LLMValidationError("Checkpoint must be either 'realistic' or 'anime'")
                
            # Validate lora type
            if result["lora"] not in ["realistic", "anime"]:
                raise LLMValidationError("LoRA must be either 'realistic' or 'anime'")
                
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse model selection JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(f"Invalid JSON format in model selection response: {str(e)}")
        except Exception as e:
            logger.error(f"Model selection validation failed: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(str(e))

    @staticmethod
    def validate_compliance_check(content: str) -> Dict[str, Any]:
        """Validate and parse compliance check response"""
        try:
            # Remove any markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            
            # Required fields
            required_fields = ["is_safe", "explanation"]
            
            # Validate required fields
            for field in required_fields:
                if field not in result:
                    raise LLMValidationError(f"Missing required field: {field}")
                    
            # Validate field types
            if not isinstance(result["is_safe"], str):
                raise LLMValidationError("Field 'is_safe' must be a string")
            if not isinstance(result["explanation"], str):
                raise LLMValidationError("Field 'explanation' must be a string")
                
            # Convert is_safe to boolean
            is_safe = str(result["is_safe"]).lower() in ["yes", "true"]
            
            # Validate content length
            if len(result["explanation"].strip()) < 50:
                raise LLMValidationError("Field 'explanation' must contain a detailed explanation (at least 50 characters)")
                
            return {
                "is_safe": is_safe,
                "explanation": result["explanation"]
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse compliance check JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(f"Invalid JSON format in compliance check response: {str(e)}")
        except Exception as e:
            logger.error(f"Compliance check validation failed: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(str(e))

    @staticmethod
    def validate_image_prompt(content: str) -> Dict[str, Any]:
        """Validate and parse image prompt response"""
        try:
            # Remove any markdown formatting
            content = re.sub(r'```json\s*|\s*```', '', content)
            result = json.loads(content)
            
            # Required fields
            required_fields = ["prompt", "negative_prompt"]
            
            # Validate required fields
            for field in required_fields:
                if field not in result:
                    raise LLMValidationError(f"Missing required field: {field}")
                    
            # Validate field types
            if not isinstance(result["prompt"], str):
                raise LLMValidationError("Field 'prompt' must be a string")
            if not isinstance(result["negative_prompt"], str):
                raise LLMValidationError("Field 'negative_prompt' must be a string")
                
            # Validate content length
            if len(result["prompt"].strip()) < 50:
                raise LLMValidationError("Field 'prompt' must contain a detailed description (at least 50 characters)")
                
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse image prompt JSON: {str(e)}")
            logger.error(f"Raw content: {content}")
            raise LLMValidationError(f"Invalid JSON format in image prompt response: {str(e)}")
        except Exception as e:
            logger.error(f"Image prompt validation failed: {str(e)}")
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
        
        # Try primary model
        try:
            if config["primary"]["provider"] == LLMProvider.GROQ:
                result = await self._call_groq(prompt, system_message, config["primary"])
            elif config["primary"]["provider"] == LLMProvider.PERPLEXITY:
                result = await self._call_perplexity(prompt, system_message, config["primary"])
            elif config["primary"]["provider"] == LLMProvider.MISTRAL:
                result = await self._call_mistral(prompt, system_message, config["primary"])
            else:
                raise LLMError(f"Unsupported primary provider: {config['primary']['provider']}")
            
            content = result["choices"][0]["message"]["content"]
            logger.debug(f"Raw LLM response:\n{content}")
            
            # Validate response based on type
            if response_type == "story_analysis":
                content = self.validator.validate_story_analysis(content)
            elif response_type == "compliance_check":
                content = self.validator.validate_compliance_check(content)
            elif response_type == "image_prompt":
                content = self.validator.validate_image_prompt(content)
            elif response_type == "model_selection":
                content = self.validator.validate_model_selection(content)
            
            return {
                "content": content,
                "provider": config["primary"]["provider"].value,
                "usage": result.get("usage", {})
            }
            
        except Exception as primary_error:
            logger.error(f"Primary model failed: {str(primary_error)}")
            
            # Try fallback model
            try:
                if config["fallback"]["provider"] == LLMProvider.GROQ:
                    result = await self._call_groq(prompt, system_message, config["fallback"])
                elif config["fallback"]["provider"] == LLMProvider.PERPLEXITY:
                    result = await self._call_perplexity(prompt, system_message, config["fallback"])
                elif config["fallback"]["provider"] == LLMProvider.MISTRAL:
                    result = await self._call_mistral(prompt, system_message, config["fallback"])
                else:
                    raise LLMError(f"Unsupported fallback provider: {config['fallback']['provider']}")
                
                content = result["choices"][0]["message"]["content"]
                logger.debug(f"Raw LLM fallback response:\n{content}")
                
                # Validate response based on type
                if response_type == "story_analysis":
                    content = self.validator.validate_story_analysis(content)
                elif response_type == "compliance_check":
                    content = self.validator.validate_compliance_check(content)
                elif response_type == "image_prompt":
                    content = self.validator.validate_image_prompt(content)
                elif response_type == "model_selection":
                    content = self.validator.validate_model_selection(content)
                
                return {
                    "content": content,
                    "provider": config["fallback"]["provider"].value,
                    "usage": result.get("usage", {})
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback model failed: {str(fallback_error)}")
                raise LLMError(f"Both primary and fallback models failed. Primary: {str(primary_error)}. Fallback: {str(fallback_error)}")

    async def _call_groq(
        self,
        prompt: str,
        system_message: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Groq API"""
        chat_completion = self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            model=config["model"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"]
        )
        return {
            "choices": [{"message": {"content": chat_completion.choices[0].message.content}}],
            "usage": {
                "prompt_tokens": chat_completion.usage.prompt_tokens,
                "completion_tokens": chat_completion.usage.completion_tokens
            }
        }

    async def _call_perplexity(
        self,
        prompt: str,
        system_message: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Perplexity API"""
        headers = {
            "Authorization": f"Bearer {self.api_keys[LLMProvider.PERPLEXITY]}",
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
            API_ENDPOINTS["perplexity"],
            headers=headers,
            json=data,
            timeout=config["timeout"]
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise LLMError(f"Perplexity API error: {response.status} - {error_text}")
            return await response.json()

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
            API_ENDPOINTS["mistral"],
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