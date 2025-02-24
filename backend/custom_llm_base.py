from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import aiohttp
from config import ERROR_MESSAGES, DEFAULT_PARAMS

class LLMError(Exception):
    """Base exception for LLM related errors"""
    pass

class LLMAPIError(LLMError):
    """Exception raised for API related errors"""
    pass

class LLMTimeoutError(LLMError):
    """Exception raised for timeout errors"""
    pass

class LLMValidationError(LLMError):
    """Exception raised for validation errors"""
    pass

class BaseLLM(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config["model"]
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", DEFAULT_PARAMS["timeout"])
        self.retry_count = config.get("retry_count", DEFAULT_PARAMS["max_retries"])
        self._session = None

    async def ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def format_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Format prompt according to provider's requirements"""
        pass

    @abstractmethod
    async def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse provider's response into standardized format"""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response from LLM"""
        try:
            await self.ensure_session()
            formatted_prompt = await self.format_prompt(prompt, **kwargs)
            
            async with self._session.post(
                self.api_endpoint,
                json=formatted_prompt,
                headers=self.get_headers(),
                timeout=self.timeout
            ) as response:
                if response.status != 200:
                    error_body = await response.text()
                    raise LLMAPIError(
                        ERROR_MESSAGES["api_error"].format(
                            error=f"{response.status}: {error_body}"
                        )
                    )
                    
                result = await response.json()
                return await self.parse_response(result)
                
        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                ERROR_MESSAGES["timeout"].format(timeout=self.timeout)
            )
        except Exception as e:
            if isinstance(e, (LLMAPIError, LLMTimeoutError)):
                raise
            raise LLMAPIError(ERROR_MESSAGES["api_error"].format(error=str(e)))

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API request"""
        pass

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 