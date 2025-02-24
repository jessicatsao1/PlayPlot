import json
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import os
from dotenv import load_dotenv
from custom_llm_base import BaseLLM
from llm_factory import LLMFactory
from config import LLMProvider, AgentType, LLM_CONFIG
import aiohttp
import logging
# Load environment variables
load_dotenv()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Validate required environment variables
if not os.getenv("GROQ_API_KEY"):
    raise EnvironmentError("GROQ_API_KEY not found in environment variables. Please ensure it is set in your .env file.")

@dataclass
class StoryOutput:
    story_scene: str        # Generated story scene
    options: List[str]      # List of 3 options for next steps
    task_id: str           # Task identifier
    timestamp: str         # ISO format timestamp

class StoryValidationError(Exception):
    """Custom exception for story validation errors"""
    pass

class StoryAgent:
    def __init__(self, llm_factory: LLMFactory, db=None):
        self.llm_factory = llm_factory
        self.db = db
        # Use create_llm with story agent config
        config = LLM_CONFIG[AgentType.STORY]["primary"]
        # Add API key to config
        config["api_key"] = os.getenv("GROQ_API_KEY")
        self.llm: BaseLLM = self.llm_factory.create_llm(
            provider=config["provider"],
            config=config
        )
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.llm, 'close'):
            await self.llm.close()
        
    def validate_manager_output(self, manager_output: Dict) -> bool:
        """Validate the manager agent output structure"""
        try:
            # Check basic structure
            if not isinstance(manager_output, dict):
                raise StoryValidationError("Manager output must be a dictionary")

            # Check status
            if manager_output.get("status") != "success":
                raise StoryValidationError(f"Invalid manager output status: {manager_output.get('status')}")

            # Get story task
            story_task = next(
                (task for task in manager_output.get("tasks", []) 
                if task.get("task_type") == "story"),
                None
            )
            if not story_task:
                raise StoryValidationError("No story task found in manager output")

            # Validate story task structure
            content = story_task.get("content", {})
            
            # Validate content fields with both type and value checks
            if not isinstance(content.get("task_type"), str) or content.get("task_type") != "story":
                raise StoryValidationError("Invalid task_type in content")
                
            if not isinstance(content.get("content_type"), str) or content.get("content_type") != "scene":
                raise StoryValidationError("Invalid content_type in content")
                
            if not isinstance(content.get("user_request"), str):
                raise StoryValidationError("Invalid user_request in content")
                
            if not isinstance(content.get("context"), dict):
                raise StoryValidationError("Invalid context in content")

            # Validate context structure
            context = content["context"]
            required_context_fields = {
                "story_id": str,
                "characters": dict,
                "scene_number": int,
                "story_context": str
            }
            
            for field, expected_type in required_context_fields.items():
                if field not in context:
                    raise StoryValidationError(f"Missing required field in context: {field}")
                if not isinstance(context[field], expected_type):
                    raise StoryValidationError(f"Invalid type for field {field} in context")

            # Validate task analysis
            analysis = story_task.get("task_analysis", {})
            required_analysis_fields = {
                "flow_type": str,
                "recommendations": str,
                "reasoning": str,
                "context": dict
            }
            
            for field, expected_type in required_analysis_fields.items():
                if field not in analysis:
                    raise StoryValidationError(f"Missing required field in task analysis: {field}")
                if not isinstance(analysis[field], expected_type):
                    raise StoryValidationError(f"Invalid type for field {field} in task analysis")

            # Validate flow_type value
            if analysis["flow_type"] not in ["story_media", "video"]:
                raise StoryValidationError(f"Invalid flow_type value: {analysis['flow_type']}")

            return True

        except Exception as e:
            raise StoryValidationError(f"Error validating manager output: {str(e)}")

    def extract_story_elements(self, task: Dict) -> Dict:
        """Extract relevant story elements from the task"""
        return {
            "user_input": task["content"].get("user_input", ""),
            "story_elements": task["content"].get("story_elements", ""),
            "recommendations": task["task_analysis"].get("recommendations", ""),
            "reasoning": task["task_analysis"].get("reasoning", "")
        }

    async def generate_story_and_options(self, story_elements: Dict, context: Dict) -> Dict:
        """Generate story scene and options in a single LLM call"""
        system_message = """You are a master storyteller that ALWAYS responds in valid JSON format.
        Your responses must STRICTLY follow the specified JSON schema without ANY additional text.
        Do not include any explanations, notes, or text outside the JSON structure.
        
        When writing dialogue and character interactions:
        1. Stay true to each character's personality and background
        2. Use their established speaking style
        3. Consider their relationships with other characters
        4. Maintain emotional consistency
        5. Advance character development naturally"""
        
        prompt = f"""
        IMPORTANT: You MUST respond with ONLY a JSON object. No other text is allowed.
        
        Based on the following elements, generate a story scene and options.
        
        USER REQUEST:
        {story_elements['user_input']}

        SCENE ELEMENTS:
        {story_elements['story_elements']}

        CHARACTER PROFILES:
        {json.dumps(story_elements.get('characters', {}), indent=2)}

        CONVERSATION HISTORY:
        {context.get('conversation_history', 'No conversation history provided')}

        STORYTELLING GUIDELINES:
        {story_elements['recommendations']}

        REQUIREMENTS:
        1. Story Scene:
           - Maximum 200 words
           - Focus on natural dialogue that matches each character's speaking style
           - Include character emotions and reactions based on their personalities
           - Create vivid atmosphere
           - Follow story recommendations
           - Advance character relationships naturally

        2. Options:
           - Provide exactly 3 distinct options
           - Make each option actionable
           - Maintain story continuity
           - Keep consistent with character profiles
           - Consider character relationships and development

        RESPONSE FORMAT:
        You must ONLY return a JSON object in this exact format:
        {{
            "story_scene": string,
            "options": [string, string, string],
            "character_emotions": {{
                "character_name": {{
                    "emotion": string,
                    "intensity": float (0.0 to 1.0),
                    "reason": string
                }}
            }}
        }}

        No other text, formatting, or explanation should be included.
        The response must be valid JSON that can be parsed by json.loads().
        """
        
        try:
            # Generate with system message enforcing JSON
            response = await self.llm.generate(
                prompt,
                system_message=system_message,
                response_format={"type": "json_object"}  # If supported by the LLM
            )
            
            # Try to parse the JSON response
            content = response["content"].strip()
            
            # Log the raw response for debugging
            print("\nDEBUG - Raw LLM Response:")
            print(content)
            print("\n")
            
            # Remove any potential non-JSON text
            if "{" in content:
                content = content[content.find("{"):content.rfind("}") + 1]
            
            # Parse and validate JSON
            result = json.loads(content)
            
            # Validate the response structure
            if not isinstance(result, dict):
                raise StoryValidationError("LLM response is not a dictionary")
            if "story_scene" not in result or "options" not in result:
                raise StoryValidationError("LLM response missing required fields")
            if not isinstance(result["options"], list) or len(result["options"]) != 3:
                raise StoryValidationError("LLM response options must be a list of exactly 3 items")
            if "character_emotions" not in result:
                raise StoryValidationError("LLM response missing character emotions")
            
            return result
        except json.JSONDecodeError as e:
            print(f"\nDEBUG - JSON Parse Error: {str(e)}")
            print(f"DEBUG - Attempted to parse: {content}")
            raise StoryValidationError(f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response['content']}")
        except Exception as e:
            raise StoryValidationError(f"Error processing LLM response: {str(e)}")

    async def process_manager_output(self, manager_output: Dict) -> Dict[str, Any]:
        """Process the manager agent output to generate story content"""
        try:
            # Extract story ID and scene number
            story_id = manager_output["story_id"]
            scene_number = manager_output["scene_number"]
            logger.info(f"Processing scene {scene_number} for story {story_id}")
            
            # Get task data
            story_task = None
            for task in manager_output["tasks"]:
                if task["task_type"] == "story":
                    story_task = task
                    break
                    
            if not story_task:
                raise ValueError("No story task found in manager output")
            
            # Get context from task
            context = story_task["content"]["context"]
            
            # Generate story content
            result = await self._generate_story_content(
                story_task["content"]["user_input"],
                context,
                story_task["task_analysis"]
            )
            
            # Update scene with story output
            scene_data = {
                "story_id": story_id,
                "scene_number": scene_number,
                "story_scene": result["story_scene"],
                "options": json.dumps(result["options"])
            }
            
            # Save to database
            await self.db.save_scene(scene_data)
            logger.info(f"Saved story output for scene {scene_number}")
            
            return {
                "status": "success",
                "story_id": story_id,
                "scene_number": scene_number,
                "content": result["story_scene"],
                "metadata": {
                    "options": result["options"],
                    "character_emotions": result.get("character_emotions", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing story: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _generate_story_content(
        self,
        user_input: str,
        context: Dict[str, Any],
        task_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate story content with context"""
        try:
            # Prepare prompt with complete context
            prompt = f"""Generate a story scene and options based on the following:

User Input: {user_input}

Story Context:
Scene Number: {context['scene_number']}
Previous Scenes: {json.dumps(context.get('previous_scenes', []), indent=2)}

Characters: {json.dumps(context['characters'], indent=2)}

Analysis:
{json.dumps(task_analysis, indent=2)}

Requirements:
1. Story Scene:
   - Create engaging narrative
   - Use natural dialogue
   - Show character emotions
   - Follow story recommendations
   - Maximum 300 words

2. Options:
   - Provide 3 distinct choices
   - Make them actionable
   - Keep consistent with story

Response Format:
{{
    "story_scene": "the story text",
    "options": ["option 1", "option 2", "option 3"],
    "character_emotions": {{
        "character_name": {{
            "emotion": "current emotion",
            "intensity": 0.0 to 1.0
        }}
    }}
}}"""

            # Get story from LLM
            result = await self.llm.generate(
                prompt,
                system_message="You are a master storyteller creating engaging interactive narratives.",
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = result["content"]
            if isinstance(content, str):
                content = json.loads(content)
                
            # Validate response structure
            required_fields = ["story_scene", "options", "character_emotions"]
            for field in required_fields:
                if field not in content:
                    raise ValueError(f"Missing required field: {field}")
                    
            if not isinstance(content["options"], list) or len(content["options"]) != 3:
                raise ValueError("Options must be a list of exactly 3 items")
                
            return content
            
        except Exception as e:
            logger.error(f"Error generating story content: {str(e)}")
            raise

if __name__ == "__main__":
    import asyncio
    
    # Example manager output
    example_manager_output = {
        "status": "success",
        "task_id": "test-task-123",
        "tasks": [
            {
                "task_id": "story-task-123",
                "task_type": "story",
                "content": {
                    "user_input": """
                    Create a scene where Sarah and Mike discuss a mysterious package in a coffee shop.
                    Make it suspenseful but family-friendly.
                    """,
                    "story_elements": """
                    Setting: Modern coffee shop, afternoon
                    Characters: Sarah (nervous but determined), Mike (skeptical and cautious)
                    Key elements: Mysterious package, tense atmosphere, public setting
                    Genre: Mystery/Suspense (family-friendly)
                    """
                },
                "task_analysis": {
                    "recommendations": """
                    1. Focus on subtle tension between characters
                    2. Use coffee shop ambiance for atmosphere
                    3. Keep dialogue natural but meaningful
                    4. Build suspense through reactions
                    5. Maintain mystery about package contents
                    """
                }
            }
        ]
    }

    # Example context with character profiles and history
    example_context = {
        "character_profiles": {
            "Sarah": {
                "personality": "Curious and determined",
                "background": "Former investigative journalist",
                "speaking_style": "Direct but thoughtful"
            },
            "Mike": {
                "personality": "Cautious and analytical",
                "background": "Security consultant",
                "speaking_style": "Measured and precise"
            }
        },
        "conversation_history": [
            "Sarah received a mysterious package this morning.",
            "Mike suggested meeting at the coffee shop to discuss it.",
            "Both agreed to keep the matter private."
        ]
    }

    async def main():
        try:
            # Initialize and use the story agent with context manager
            async with StoryAgent(LLMFactory()) as agent:
                # Process the manager output with context
                result = await agent.process_manager_output(
                    example_manager_output
                )
                
                # Print the results in a formatted way
                print("\n=== Generated Story Scene ===")
                print(result["content"])
                
                print("\n=== Story Generation Details ===")
                print(f"Task ID: {result['task_id']}")
                print(f"Generated at: {result['timestamp']}")
            
        except Exception as e:
            print(f"Error occurred: {str(e)}")

    # Run the async main function
    asyncio.run(main()) 