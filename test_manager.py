import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from database import Database
from manager_agent import ManagerAgent
from config import TaskFlow
from models import Story, Scene
import logging
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set aiosqlite logging to WARNING level to reduce debug output
logging.getLogger('aiosqlite').setLevel(logging.WARNING)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            logger.debug(f"Attempting to serialize object of type: {type(obj)}")
            if isinstance(obj, datetime):
                logger.debug("Converting datetime to ISO format")
                return obj.isoformat()
            if isinstance(obj, TaskFlow):
                logger.debug(f"Converting TaskFlow enum to value: {obj.value}")
                return obj.value
            if hasattr(obj, 'dict'):
                logger.debug("Converting Pydantic model to dict")
                return obj.dict()
            if hasattr(obj, 'value'):
                logger.debug("Converting enum to value")
                return obj.value
            logger.warning(f"Falling back to string representation for type {type(obj)}")
            return str(obj)
        except Exception as e:
            logger.error(f"Serialization error for object {type(obj)}: {str(e)}")
            return f"<Unserializable {type(obj).__name__}>"

async def main():
    # Load environment variables
    load_dotenv()
    
    # Verify API keys are loaded
    required_keys = ["PERPLEXITY_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]
    for key in required_keys:
        if not os.getenv(key):
            logger.error(f"Missing required environment variable: {key}")
            raise ValueError(f"Missing required environment variable: {key}")
        logger.info(f"Found API key: {key}")
    
    # Initialize database
    db = Database("test.db")
    await db.init_db()
    logger.info("Database initialized")
    
    # Verify compliance guidelines
    guidelines = await db.get_compliance_guidelines()
    logger.info(f"Retrieved {len(guidelines)} compliance guidelines: {guidelines}")
    
    try:
        # Create a test story
        story = Story(
            user_id="test_user",
            title="Test Story",
            characters={
                "char1": "John - A brave adventurer"
            }
        )
        await db.save_story(story)
        logger.info(f"Created test story with ID: {story.story_id}")
        
        # Create a test scene
        scene = Scene(
            story_id=story.story_id,
            scene_number=1,
            content="This is the first scene",
            visual_analysis={},
            audio_direction={},
            scene_analysis={},
            media={}
        )
        await db.save_scene(scene)
        logger.info(f"Created test scene with ID: {scene.scene_id}")
        
        # Initialize manager agent
        async with ManagerAgent(db) as manager:
            logger.info("Initialized manager agent")
            
            # Test story media flow
            content = {
                "user_input": """
                Create a scene where John discovers an ancient map in a dusty library.
                The map leads to a hidden temple in the jungle.
                Make it exciting but keep it family-friendly.
                """
            }
            
            logger.info("Testing story media flow...")
            logger.debug(f"Content for story media flow: {content}")
            
            try:
                result = await manager.process_request(
                    user_id="test_user",
                    content=content,
                    flow_type=TaskFlow.STORY_MEDIA,
                    story_id=story.story_id,
                    scene_id=scene.scene_id
                )
                logger.info("Story media flow completed successfully")
                logger.debug("Raw result structure:")
                for key, value in result.items():
                    logger.debug(f"Key: {key}, Type: {type(value)}")
                    if isinstance(value, dict):
                        logger.debug(f"Dict contents for {key}:")
                        for k, v in value.items():
                            logger.debug(f"  Subkey: {k}, Type: {type(v)}")
            except Exception as e:
                logger.error(f"Story media flow failed: {str(e)}")
                logger.exception("Full traceback:")
                result = {"status": "error", "error": str(e)}
            
            print("\nStory Media Flow Result:")
            try:
                # First try to serialize individual components
                logger.debug("Attempting to serialize result components:")
                for key, value in result.items():
                    try:
                        json.dumps(value, cls=CustomJSONEncoder)
                        logger.debug(f"Successfully serialized key: {key}")
                    except Exception as e:
                        logger.error(f"Failed to serialize key {key}: {str(e)}")
                        logger.error(f"Value type: {type(value)}")
                        if isinstance(value, dict):
                            logger.error(f"Dict contents: {value}")
                
                # Then try to serialize the whole thing
                serialized = json.dumps(result, indent=2, cls=CustomJSONEncoder)
                print(serialized)
            except Exception as e:
                logger.error(f"Failed to serialize story result: {str(e)}")
                logger.error(f"Result type: {type(result)}")
                logger.error(f"Result content: {result}")
            
            # Test video flow
            video_content = {
                "user_input": """
                Create a short video showing the jungle temple from different angles.
                Include some mystical elements and soft ambient sounds.
                Keep it mysterious but not scary.
                """
            }
            
            logger.info("Testing video flow...")
            logger.debug(f"Content for video flow: {video_content}")
            
            try:
                video_result = await manager.process_request(
                    user_id="test_user",
                    content=video_content,
                    flow_type=TaskFlow.VIDEO,
                    story_id=story.story_id,
                    scene_id=scene.scene_id
                )
                logger.info("Video flow completed successfully")
                logger.debug("Raw video result structure:")
                for key, value in video_result.items():
                    logger.debug(f"Key: {key}, Type: {type(value)}")
                    if isinstance(value, dict):
                        logger.debug(f"Dict contents for {key}:")
                        for k, v in value.items():
                            logger.debug(f"  Subkey: {k}, Type: {type(v)}")
            except Exception as e:
                logger.error(f"Video flow failed: {str(e)}")
                logger.exception("Full traceback:")
                video_result = {"status": "error", "error": str(e)}
            
            print("\nVideo Flow Result:")
            try:
                # First try to serialize individual components
                logger.debug("Attempting to serialize video result components:")
                for key, value in video_result.items():
                    try:
                        json.dumps(value, cls=CustomJSONEncoder)
                        logger.debug(f"Successfully serialized key: {key}")
                    except Exception as e:
                        logger.error(f"Failed to serialize key {key}: {str(e)}")
                        logger.error(f"Value type: {type(value)}")
                        if isinstance(value, dict):
                            logger.error(f"Dict contents: {value}")
                
                # Then try to serialize the whole thing
                serialized = json.dumps(video_result, indent=2, cls=CustomJSONEncoder)
                print(serialized)
            except Exception as e:
                logger.error(f"Failed to serialize video result: {str(e)}")
                logger.error(f"Video result type: {type(video_result)}")
                logger.error(f"Video result content: {video_result}")
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        logger.exception("Full traceback:")
        raise
    finally:
        # Clean up test database
        await db.cleanup()
        logger.info("Cleaned up test database")

@pytest.mark.asyncio
async def test_compliance_check():
    """Test compliance check functionality"""
    load_dotenv()
    
    # Initialize database
    db = Database("test.db")
    await db.init_db()
    
    try:
        async with ManagerAgent(db) as manager:
            # Test safe content
            safe_content = {
                "user_input": "Create a happy story about a puppy making friends in the park."
            }
            
            guidelines = await db.get_compliance_guidelines()
            result = await manager._check_compliance(safe_content, guidelines)
            
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "is_safe" in result, "Result should have is_safe field"
            assert "reasoning" in result, "Result should have reasoning field"
            assert "concerns" in result, "Result should have concerns field"
            assert "suggestions" in result, "Result should have suggestions field"
            assert result["is_safe"] is True, "Safe content should be marked as safe"
            
            # Test unsafe content
            unsafe_content = {
                "user_input": "Create a violent and inappropriate story with explicit content."
            }
            
            result = await manager._check_compliance(unsafe_content, guidelines)
            assert result["is_safe"] is False, "Unsafe content should be marked as unsafe"
            assert len(result["concerns"]) > 0, "Unsafe content should have concerns listed"
            
    finally:
        await db.cleanup()

if __name__ == "__main__":
    # Set debug logging for this module
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    asyncio.run(main()) 