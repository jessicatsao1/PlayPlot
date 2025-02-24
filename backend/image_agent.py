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
from llm_factory import LLMFactory, LLMManager
from config import LLM_CONFIG, AgentType

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
    1. Processing manager agent output and story scene
    2. Generating prompts and style selection
    3. Handling Fal.ai API integration
    4. Managing image generation and storage
    """
    
    def __init__(self, llm_factory: LLMFactory):
        """Initialize image agent with LLM factory"""
        self.llm_factory = llm_factory
        # Get config from LLM_CONFIG
        config = LLM_CONFIG[AgentType.IMAGE]["primary"]
        # Add API key to config
        config["api_key"] = os.getenv("GROQ_API_KEY")
        # Create LLM manager for fallback support
        self.llm_manager = LLMManager(config)
        self.logger = logging.getLogger(__name__)
        
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
        
    async def process_task(
        self,
        task_data: Dict[str, Any],
        story_scene: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process image generation task"""
        try:
            # Log input data types
            logger.info("=== Image Agent Input Data ===")
            logger.info(f"Task Data Type: {type(task_data)}")
            logger.info(f"Story Scene Type: {type(story_scene)}")
            logger.info(f"Context Type: {type(context)}")

            # Validate inputs
            if not isinstance(task_data, dict):
                raise ImageGenerationError("task_data must be a dictionary")
            if not isinstance(story_scene, str):
                raise ImageGenerationError("story_scene must be a string")
            if not isinstance(context, dict):
                raise ImageGenerationError("context must be a dictionary")

            # Log validated data structure
            logger.info(f"Task Data Keys: {list(task_data.keys())}")
            logger.info(f"Story Scene Length: {len(story_scene)}")
            logger.info(f"Context Keys: {list(context.keys())}")

            # Prepare reasoning prompt
            prompt = self._prepare_reasoning_prompt(story_scene, task_data, context)
            
            # Get structured output from LLM
            llm_response = await self.llm_manager.execute_with_fallback(
                prompt,
                system_message="You are an expert at converting story scenes into detailed image generation prompts.",
                response_type="image_generation"
            )
            
            # Parse LLM response
            parsed_response = self._parse_llm_response(llm_response)
            
            # Generate image using parsed response
            image_result = await self._generate_image(parsed_response, context)
            
            # Save image locally if URL is present
            if image_result and "image_url" in image_result:
                try:
                    saved_path = await self._save_image(
                        image_url=image_result["image_url"],
                        task_id=task_data.get("task_id", "unknown"),
                        scene_id=context.get("scene_id", "unknown")
                    )
                    image_result["local_path"] = saved_path
                    logger.info(f"Image saved locally at: {saved_path}")
                except Exception as e:
                    logger.error(f"Failed to save image locally: {str(e)}")
            
            return image_result
            
        except Exception as e:
            logger.error(f"Error processing image task: {str(e)}")
            raise ImageGenerationError(f"Failed to process image task: {str(e)}")
            
    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Get content from response
            content = llm_response.get("content", {})
            
            # If content is a string, clean and parse it
            if isinstance(content, str):
                # Remove markdown code blocks if present
                content = content.strip()
                if content.startswith("```") and content.endswith("```"):
                    # Extract content between code blocks
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]  # Remove 'json' language specifier
                content = content.strip()
                
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse content as JSON: {str(e)}")
                    logger.error(f"Raw content after cleaning: {content}")
                    raise ImageGenerationError("Invalid JSON in LLM response content")
            elif not isinstance(content, dict):
                logger.error(f"Unexpected content type: {type(content)}")
                raise ImageGenerationError(f"Expected string or dict content, got {type(content)}")
                
            # Validate required fields
            required_fields = ["positive_prompt", "negative_prompt", "lora_choice"]
            missing_fields = [field for field in required_fields if field not in content]
            if missing_fields:
                logger.error(f"Missing required fields: {missing_fields}")
                logger.error(f"Available fields: {list(content.keys())}")
                raise ImageGenerationError(f"Missing required fields in LLM response: {', '.join(missing_fields)}")
            
            # Validate field types
            if not isinstance(content["positive_prompt"], str):
                raise ImageGenerationError("positive_prompt must be a string")
            if not isinstance(content["negative_prompt"], str):
                raise ImageGenerationError("negative_prompt must be a string")
            if not isinstance(content["lora_choice"], str):
                raise ImageGenerationError("lora_choice must be a string")
            
            # Validate lora_choice value
            if content["lora_choice"].lower() not in ["cartoon", "anime"]:
                logger.warning(f"Invalid lora_choice: {content['lora_choice']}, defaulting to cartoon")
                content["lora_choice"] = "cartoon"
                    
            return content
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            logger.error(f"Full LLM response: {json.dumps(llm_response, indent=2)}")
            raise ImageGenerationError(f"Failed to parse LLM response: {str(e)}")
            
    def _prepare_reasoning_prompt(
        self,
        story_scene: str,
        task_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Prepare prompt for LLM reasoning"""
        return f"""Given this story scene, create a detailed image generation prompt.

Scene: {story_scene}

Task requirements: {task_data.get('reasoning', '')} You are an expert Flux Model Visual Director specializing in dynamic scene composition and adaptive image generation. Craft a coherent, high-impact prompt that integrates: • Relevant character descriptions (up to 2 main characters if the scene has more)
• Precisely chosen art style and mood
• Balanced environment and technical details

PROMPT STRUCTURE:

Scene Composition (25% of tokens):

Primary focus elements and how they interact or relate
Dynamic positioning of characters (e.g., wide angle, full body)
Character-environment integration (how they occupy the scene, any physical contact or shared action)
Visual Style Definition (15% of tokens):

Art direction (e.g., painterly, cinematic, anime)
Mood and atmosphere (e.g., bright, tense, whimsical)
Quality enhancement parameters (e.g., “masterpiece,” “high_detail,” or relevant style tags)
Environmental Context (20% of tokens):

Setting elements (e.g., architecture, nature, futuristic city)
Lighting (e.g., soft sunlight, neon glow, dramatic shadows)
Atmospheric conditions (e.g., fog, warm glow, rainy backdrop)
Technical Tags (60% of tokens):

Must begin with “rating_SFW”
Use 'break' to separate major components
Include character counts (e.g., “2 characters,” or “1 girl, 2 men”) and specify their actions/poses
Detail interactions or positions (e.g., “positioned center-left,” “sparring boldly”)
FORMAT (example):
rating_SFW, rating_suggestive, break,
count of characters, angle of shot theme of the scene focus, break,
[each character description with features, actions], break,
[environment: static or dynamic], break,
[quality tags like ‘cinematic, 8k, volumetric lighting, dramatic shadows’]

Character Description Format:
"[Character ID], [Physical Attributes], [Dynamic Elements], [Spatial Position], [Interaction Details]"

Example: "rating_SFW, cinematic, high_detail, break,
2 characters, dynamic wide shot, emotional focus, break,
Character_A, tall figure, flowing red dress, expressing joy, positioned center-left, reaching outward, break,
Character_B, athletic build, casual attire, responding with warmth, positioned right, moving forward, break,
grand hall interior, golden hour lighting, marble columns, break,
hyperrealistic, volumetric lighting, dramatic shadows, depth of field, 8k resolution"


IMPORTANT: You must respond with ONLY a JSON object. No markdown formatting, no code blocks, no additional text.
The response must be a valid JSON object with exactly these fields:
{{
    "positive_prompt": "detailed description of what to include in the image",
    "negative_prompt": "what to avoid in the image generation",
    "lora_choice": "either 'cartoon' or 'anime'"
}}

Example valid response:
{{"positive_prompt": "A serene garden scene with blooming flowers","negative_prompt": "No people or animals","lora_choice": "cartoon"}}

Remember:
1. ONLY return the JSON object
2. NO markdown formatting (```) or code blocks
3. NO explanations or additional text
4. Fields must be exactly as shown
5. lora_choice must be either 'cartoon' or 'anime'
"""

    async def _generate_image(self, parsed_response: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image using Fal.ai flux-lora endpoint"""
        try:
            # Get LoRA configuration based on recommended style
            lora_choice = parsed_response["lora_choice"]
            lora_config = self.lora_models.get(lora_choice.lower())
            if not lora_config:
                self.logger.warning(f"Style {lora_choice} not found, defaulting to cartoon")
                lora_config = self.lora_models["cartoon"]
            
            # Prepare API call arguments for FLUX.1 endpoint
            api_args = {
                "prompt": parsed_response["positive_prompt"],
                "negative_prompt": parsed_response["negative_prompt"],
                "image_size": {
                    "width": 1080,
                    "height": 1920
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
            
            # Submit request to Fal.ai flux-lora endpoint
            self.logger.info("\n=== Submitting Request to FLUX.1 ===")
            handler = await fal_client.submit_async(
                "fal-ai/flux-lora",
                arguments=api_args
            )
            
            # Process events with focused logging
            self.logger.info("\n=== Generation Progress ===")
            last_progress = 0
            
            async for event in handler.iter_events(with_logs=True):
                if hasattr(event, 'progress'):
                    current_progress = int(event.progress * 100)
                    if current_progress - last_progress >= 25:
                        self.logger.info(f"Progress: {current_progress}%")
                        last_progress = current_progress
            
            # Get final result
            result = await handler.get()
            
            if not result.get('images') or not result['images'][0].get('url'):
                raise ImageGenerationError("No image URL in API response")
            
            return {
                "image_url": result['images'][0]['url'],
                "models_used": {
                    "endpoint": "fal-ai/flux-lora",
                    "lora": lora_config,
                    "style": lora_choice,
                    "dimensions": f"{api_args['image_size']['width']}x{api_args['image_size']['height']}"
                },
                "scene_id": context.get("scene_id")
            }
            
        except Exception as e:
            self.logger.error(f"Error generating image: {str(e)}")
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
                        self.logger.info(f"Image saved to: {save_path}")
                    else:
                        raise ImageGenerationError(f"Failed to download image: {response.status}")
                        
            return save_path
            
        except Exception as e:
            self.logger.error(f"Error saving image: {str(e)}")
            raise ImageGenerationError(f"Failed to save image: {str(e)}") 