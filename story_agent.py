import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import os
from dotenv import load_dotenv
from custom_llm_base import BaseLLM
from llm_factory import LLMFactory
from config import LLMProvider, AgentType, LLM_CONFIG
import aiohttp

# Load environment variables
load_dotenv()

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
    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
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
        required_fields = ["status", "task_id", "tasks"]
        
        if not all(field in manager_output for field in required_fields):
            raise StoryValidationError("Missing required fields in manager output")
            
        if manager_output["status"] != "success":
            raise StoryValidationError(f"Invalid manager output status: {manager_output['status']}")
            
        story_tasks = [task for task in manager_output["tasks"] if task["task_type"] == "story"]
        if not story_tasks:
            raise StoryValidationError("No story task found in manager output")
            
        story_task = story_tasks[0]
        required_task_fields = ["task_id", "content", "task_analysis"]
        if not all(field in story_task for field in required_task_fields):
            raise StoryValidationError("Missing required fields in story task")
            
        return True

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
        Do not include any explanations, notes, or text outside the JSON structure."""
        
        prompt = f"""
        IMPORTANT: You MUST respond with ONLY a JSON object. No other text is allowed.
        
        Based on the following elements, generate a story scene and options.
        
        USER REQUEST:
        {story_elements['user_input']}

        SCENE ELEMENTS:
        {story_elements['story_elements']}

        CHARACTER PROFILES:
        {context.get('character_profiles', 'No character profiles provided')}

        CONVERSATION HISTORY:
        {context.get('conversation_history', 'No conversation history provided')}

        STORYTELLING GUIDELINES:
        {story_elements['recommendations']}

        REQUIREMENTS:
        1. Story Scene:
           - Maximum 200 words
           - Focus on natural dialogue
           - Include character emotions and reactions
           - Create vivid atmosphere
           - Follow story recommendations

        2. Options:
           - Provide exactly 3 distinct options
           - Make each option actionable
           - Maintain story continuity
           - Keep consistent with character profiles

        RESPONSE FORMAT:
        You must ONLY return a JSON object in this exact format:
        {{"story_scene": string, "options": [string, string, string]}}

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
            
            return result
        except json.JSONDecodeError as e:
            print(f"\nDEBUG - JSON Parse Error: {str(e)}")
            print(f"DEBUG - Attempted to parse: {content}")
            raise StoryValidationError(f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response['content']}")
        except Exception as e:
            raise StoryValidationError(f"Error processing LLM response: {str(e)}")

    async def process_manager_output(self, manager_output: Dict, context: Dict = None) -> StoryOutput:
        """Process manager output and generate story response"""
        try:
            # Validate manager output
            self.validate_manager_output(manager_output)
            
            # Get story task
            story_task = next(task for task in manager_output["tasks"] 
                            if task["task_type"] == "story")
            
            # Extract story elements
            story_elements = self.extract_story_elements(story_task)
            
            # Generate story and options in single call
            result = await self.generate_story_and_options(
                story_elements,
                context or {}  # Use empty dict if no context provided
            )
            
            return StoryOutput(
                story_scene=result["story_scene"],
                options=result["options"],
                task_id=story_task["task_id"],
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            raise StoryValidationError(f"Error processing manager output: {str(e)}")

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
                    example_manager_output,
                    example_context
                )
                
                # Print the results in a formatted way
                print("\n=== Generated Story Scene ===")
                print(result.story_scene)
                
                print("\n=== Options ===")
                for i, option in enumerate(result.options, 1):
                    print(f"Option {i}: {option}")
                
                print("\n=== Story Generation Details ===")
                print(f"Task ID: {result.task_id}")
                print(f"Generated at: {result.timestamp}")
            
        except Exception as e:
            print(f"Error occurred: {str(e)}")

    # Run the async main function
    asyncio.run(main()) 