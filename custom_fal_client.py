import aiohttp
import asyncio
import json
from typing import Dict, Any, AsyncGenerator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FalHandler:
    """Handler for Fal.ai API responses"""
    def __init__(self, response_data: Dict[str, Any]):
        self.response_data = response_data
        self._events = []
        self._current_event = 0
        
    async def iter_events(self, with_logs: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """Simulate event stream for the API call"""
        events = [
            {"status": "starting", "progress": 0.0},
            {"status": "processing", "progress": 0.5},
            {"status": "completed", "progress": 1.0, "output": self.response_data}
        ]
        
        for event in events:
            if with_logs:
                logger.info(f"Event: {event}")
            yield event
            await asyncio.sleep(0.5)  # Simulate processing time
            
    async def get(self) -> Dict[str, Any]:
        """Get the final result"""
        return self.response_data

async def submit_async(
    endpoint_id: str,
    arguments: Dict[str, Any],
    api_key: str = None,
    base_url: str = "https://fal.run"
) -> FalHandler:
    """
    Submit a request to Fal.ai API
    
    Args:
        endpoint_id: The ID of the endpoint (e.g., "comfy/PeterL-1111/test")
        arguments: The arguments for the API call
        api_key: The Fal.ai API key
        base_url: The base URL for the API
        
    Returns:
        FalHandler: A handler for the API response
    """
    if not api_key:
        raise ValueError("API key is required")
        
    url = f"{base_url}/{endpoint_id}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=arguments,
                timeout=60
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error: {response.status} - {error_text}")
                    
                result = await response.json()
                logger.info(f"API Response: {result}")
                
                return FalHandler(result)
                
    except Exception as e:
        logger.error(f"Error submitting to Fal.ai API: {str(e)}")
        raise

# Example usage
async def test_api():
    try:
        handler = await submit_async(
            "comfy/PeterL-1111/test",
            arguments={
                "prompt": "a girl",
                "negative_prompt": "lowres, bad anatomy, bad hands...",
                "checkpoint_url": "https://huggingface.co/...",
                "lora_url": "https://huggingface.co/..."
            },
            api_key="your-api-key-here"
        )
        
        async for event in handler.iter_events(with_logs=True):
            print(f"Event received: {event}")
            
        result = await handler.get()
        print(f"Final result: {result}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_api()) 