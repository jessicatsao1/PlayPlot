import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import fal_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific log levels for different loggers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set higher log level for noisy libraries
logging.getLogger('fal_client').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

class ImageGenerationError(Exception):
    """Custom exception for image generation errors"""
    pass

class ImagePromptError(Exception):
    """Custom exception for prompt generation errors"""
    pass

class ImageValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class Character(BaseModel):
    """Character model for validation"""
    id: str
    name: str
    description: str
    traits: Optional[List[str]] = Field(default_factory=list)

class SceneContext(BaseModel):
    """Scene context model for validation"""
    scene_id: str
    scene_number: int
    content: str
    characters: List[Character]
    setting: Optional[str] = None
    tone: Optional[str] = None

class ImageTask(BaseModel):
    """Image task model for validation"""
    task_id: str
    task_type: str = "image"
    scene_description: str
    style: str
    context: Dict[str, Any]
    reasoning: Dict[str, Any]

class ImageAgent:
    """
    Image Agent responsible for:
    1. Processing manager agent output
    2. Generating prompts and style selection
    3. Handling Fal.ai API integration
    4. Managing image generation and storage
    """
    
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager
        self.fal_api_key = os.getenv("FAL_API_KEY")
        if not self.fal_api_key:
            raise ImageValidationError("FAL_API_KEY not found in environment variables")
            
        # Set FAL_KEY environment variable
        os.environ["FAL_KEY"] = self.fal_api_key
            
        # Initialize available LoRA models
        self.lora_models = {
            "cartoon": {
                "path": "https://civitai.com/api/download/models/838667?type=Model&format=SafeTensor",
                "scale": 0.75,
                "keywords": ["cartoon", "stylized", "animated", "colorful", "exaggerated"]
            },
            "anime": {
                "path": "https://civitai.com/api/download/models/747534?type=Model&format=SafeTensor",
                "scale": 0.65,
                "keywords": ["anime", "manga", "japanese", "illustration", "2d"]
            }
        }
        
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process image generation task from manager agent"""
        try:
            # Validate task data
            task = ImageTask(**task_data)
            logger.info(f"Processing image task: {task.task_id}")
            
            # Extract scene context
            scene_context = self._extract_scene_context(task.context)
            logger.info(f"Extracted scene context for scene {scene_context.scene_id}")
            
            # Generate image prompt and get style recommendation
            prompt_result = await self._generate_image_prompt(
                task.scene_description,
                scene_context,
                task.reasoning
            )
            logger.info("Generated image prompt and style recommendation")
            
            # Generate image with flux-lora endpoint
            image_result = await self._generate_image(
                prompt_result["prompt"],
                scene_context,
                prompt_result["recommended_style"]  # Use LLM recommended style
            )
            logger.info("Generated image")
            
            # Save image locally
            local_path = await self._save_image(
                image_result["image_url"],
                task.task_id,
                scene_context.scene_id
            )
            logger.info(f"Saved image to {local_path}")
            
            return {
                "status": "success",
                "task_id": task.task_id,
                "image_url": image_result["image_url"],
                "local_path": local_path,
                "metadata": {
                    "prompt": prompt_result["prompt"],
                    "recommended_style": prompt_result["recommended_style"],
                    "style_reasoning": prompt_result["style_reasoning"],
                    "models": image_result["models_used"],
                    "scene_id": scene_context.scene_id,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing image task: {str(e)}")
            raise ImageGenerationError(f"Failed to process image task: {str(e)}")
            
    def _extract_scene_context(self, context_data: Dict) -> SceneContext:
        """Extract and validate scene context"""
        try:
            # Convert characters to proper format
            characters = [
                Character(**char) if isinstance(char, dict) else char
                for char in context_data.get("characters", [])
            ]
            
            return SceneContext(
                scene_id=context_data["scene_id"],
                scene_number=context_data.get("scene_number", 1),
                content=context_data.get("content", ""),
                characters=characters,
                setting=context_data.get("setting"),
                tone=context_data.get("tone")
            )
        except Exception as e:
            raise ImageValidationError(f"Invalid scene context: {str(e)}")
            
    async def _generate_image_prompt(
        self,
        scene_description: str,
        scene_context: SceneContext,
        reasoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate image prompt and recommend style based on context"""
        try:
            # Use LLM to generate detailed prompt and style recommendation
            prompt_template = """
            Analyze the following scene and generate an image prompt with style recommendation:
            
            Scene Description:
            {scene_description}
            
            Scene Context:
            {scene_context}
            
            Reasoning:
            {reasoning}
            
            Available Styles:
            1. Cartoon: Stylized, animated, colorful, exaggerated features
            2. Anime: Japanese animation style, clean lines, distinctive eyes
            
            Generate a JSON response with:
            1. A detailed prompt that captures the scene
            2. Recommended style (either "cartoon" or "anime")
            3. Reasoning for the style choice
            
            Format:
            {{
                "prompt": "detailed prompt",
                "recommended_style": "cartoon or anime",
                "style_reasoning": "explanation for style choice"
            }}
            """
            
            prompt = prompt_template.format(
                scene_description=scene_description,
                scene_context=json.dumps(scene_context.dict()),
                reasoning=json.dumps(reasoning)
            )
            
            # Get prompt and style recommendation from LLM
            result = await self.llm_manager.execute_with_fallback(
                prompt,
                system_message="You are an expert at writing image generation prompts and analyzing visual style requirements.",
                response_type="image_prompt"
            )
            
            return result["content"]
            
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            raise ImagePromptError(f"Failed to generate image prompt: {str(e)}")
            
    async def _generate_image(
        self,
        prompt: str,
        scene_context: SceneContext,
        recommended_style: str
    ) -> Dict[str, Any]:
        """Generate image using Fal.ai flux-lora endpoint"""
        try:
            # Get LoRA configuration based on recommended style
            lora_config = self.lora_models.get(recommended_style.lower())
            if not lora_config:
                logger.warning(f"Style {recommended_style} not found, defaulting to cartoon")
                lora_config = self.lora_models["cartoon"]
            
            # Define image dimensions
            width = 1080
            height = 1920
            logger.info(f"Setting image dimensions: {width}x{height}")
            
            # Prepare API call arguments
            api_args = {
                "prompt": prompt,
                "image_size": {
                    "width": width,
                    "height": height
                },
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": True,
                "output_format": "jpeg",
                "loras": [{
                    "path": lora_config["path"],
                    "scale": lora_config["scale"]
                }]
            }
            
            # Log API call details
            logger.info("\n=== API Call Configuration ===")
            logger.info("Endpoint: fal-ai/flux-lora")
            logger.info("Arguments:")
            logger.info(json.dumps({
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "image_size": {
                    "width": width,
                    "height": height
                },
                "num_inference_steps": api_args["num_inference_steps"],
                "guidance_scale": api_args["guidance_scale"],
                "lora": {
                    "path": lora_config["path"],
                    "scale": lora_config["scale"]
                }
            }, indent=2))
            
            # Submit request to Fal.ai flux-lora endpoint
            logger.info("\n=== Submitting Request ===")
            handler = await fal_client.submit_async(
                "fal-ai/flux-lora",
                arguments=api_args
            )
            
            # Process events with focused logging
            logger.info("\n=== Generation Progress ===")
            last_progress = 0
            event_logs = []
            
            async for event in handler.iter_events(with_logs=True):
                # Collect event logs for error analysis
                if hasattr(event, 'logs') and event.logs:
                    event_logs.append(event.logs)
                    
                # Log status changes
                if hasattr(event, 'status') and event.status != "processing":
                    logger.info(f"Status: {event.status}")
                    
                # Log progress at 25% intervals
                if hasattr(event, 'progress'):
                    current_progress = int(event.progress * 100)
                    if current_progress - last_progress >= 25:
                        logger.info(f"Progress: {current_progress}%")
                        last_progress = current_progress
            
            # Analyze event logs for errors
            for log in event_logs:
                if isinstance(log, str) and "error" in log.lower():
                    logger.error(f"Generation error detected: {log}")
                elif isinstance(log, dict) and log.get('level', '').lower() == 'error':
                    logger.error(f"Generation error detected: {log.get('message', '')}")
            
            # Get final result
            logger.info("\n=== Getting Final Result ===")
            result = await handler.get()
            
            # Extract and validate image URL
            if not result.get('images') or not result['images'][0].get('url'):
                raise ImageGenerationError("No image URL in API response")
            
            image_url = result['images'][0]['url']
            logger.info(f"\nGenerated Image URL: {image_url}")
            
            return {
                "image_url": image_url,
                "models_used": {
                    "endpoint": "fal-ai/flux-lora",
                    "lora": lora_config,
                    "style": recommended_style,
                    "dimensions": f"{width}x{height}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            logger.error(f"Error details:", exc_info=True)
            raise ImageGenerationError(f"Failed to generate image: {str(e)}")
            
    async def _save_image(
        self,
        image_url: str,
        task_id: str,
        scene_id: str
    ) -> str:
        """Download and save image locally"""
        try:
            # Create output directory
            output_dir = os.path.join("output", "images")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{scene_id}_{task_id}_{timestamp}.png"
            save_path = os.path.join(output_dir, filename)
            
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        with open(save_path, 'wb') as f:
                            f.write(await response.read())
                        logger.info(f"Image saved to: {save_path}")
                    else:
                        raise ImageGenerationError(f"Failed to download image: {response.status}")
                        
            return save_path
            
        except Exception as e:
            logger.error(f"Error saving image: {str(e)}")
            raise ImageGenerationError(f"Failed to save image: {str(e)}") 