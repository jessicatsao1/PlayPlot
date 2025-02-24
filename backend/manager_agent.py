import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
import logging
import aiohttp
import re
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from config import (
    LLM_CONFIG,
    PROMPT_TEMPLATES,
    AgentType,
    TaskFlow,
    ERROR_MESSAGES,
    LLMProvider
)
from llm_factory import LLMManager
from models import (
    Task,
    Story,
    Scene,
    TaskStatus,
    TaskType,
    ComplianceResult,
    TaskAnalysis,
    Character
)
from custom_llm_base import LLMError

class ManagerAgent:
    """
    Manager Agent responsible for:
    1. Task orchestration
    2. Compliance checking
    3. Content analysis
    4. Task routing
    """
    
    def __init__(self, db):
        self.db = db
        self.session = None
        self.llm_manager = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.llm_manager = LLMManager(self.session)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def process_request(
        self,
        user_id: str,
        content: Dict[str, Any],
        flow_type: TaskFlow,
        story_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incoming request and orchestrate task execution"""
        try:
            logger.info("=== Starting Request Processing ===")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Story ID: {story_id}")
            logger.info(f"Flow Type: {flow_type}")
            
            # Get scene number and context
            scene_number = 1
            last_scenes = []
            if story_id:
                scene_number = await self.db.get_next_scene_number(story_id)
                logger.info(f"Continuing story with scene {scene_number}")
                
                # Get last 2 scenes for context
                last_scenes = await self.db.get_last_scenes(story_id, 2)
                logger.info(f"Retrieved {len(last_scenes)} previous scenes")
            else:
                # Generate new story ID
                story_id = str(uuid.uuid4())
                logger.info(f"Created new story with ID: {story_id}")
            
            # First, get existing characters
            existing_characters = await self.db.get_characters(user_id)
            logger.info(f"Retrieved {len(existing_characters)} existing characters")
            
            # Prepare context for analysis
            context = {
                "user_id": user_id,
                "story_id": story_id,
                "scene_number": scene_number,
                "characters": existing_characters,
                "previous_scenes": last_scenes,
                "user_input": content["user_input"]
            }
            
            # Generate manager analysis first
            logger.info("Generating manager analysis...")
            manager_analysis = await self._generate_manager_analysis(context)
            
            # Process character updates from analysis
            if "character_analysis" in manager_analysis:
                character_analysis = manager_analysis["character_analysis"]
                
                # Handle new characters
                for new_char in character_analysis.get("new_characters", []):
                    try:
                        # Add required fields
                        new_char["user_id"] = user_id
                        new_char["character_id"] = str(uuid.uuid4())
                        new_char["voice_id"] = await self._assign_voice_id(new_char)
                        
                        # Save new character
                        char_id = await self.db.save_character(new_char)
                        logger.info(f"Created new character: {new_char['name']} with ID: {char_id}")
                    except Exception as e:
                        logger.error(f"Error creating character {new_char.get('name')}: {str(e)}")
                
                # Handle character updates
                for char_update in character_analysis.get("character_updates", []):
                    try:
                        char_id = char_update.get("character_id")
                        updates = char_update.get("updates", {})
                        if char_id and updates:
                            # Add character_id to updates
                            updates["character_id"] = char_id
                            await self.db.save_character(updates)
                            logger.info(f"Updated character {char_id}")
                    except Exception as e:
                        logger.error(f"Error updating character {char_id}: {str(e)}")
            
            # Get updated characters list
            characters = await self.db.get_characters(user_id)
            logger.info(f"Retrieved {len(characters)} characters after updates")
            
            # Create initial scene data
            scene_data = {
                'story_id': story_id,
                'scene_number': scene_number,
                'user_request': content['user_input'],
                'manager_task_analysis': json.dumps(manager_analysis)
            }
            
            # Save scene
            await self.db.save_scene(scene_data)
            logger.info(f"Saved scene data")
            
            # Process based on flow type
            if flow_type == TaskFlow.STORY_MEDIA:
                logger.info("Processing story media flow")
                return await self._handle_story_media_flow(
                    user_id=user_id,
                    story_id=story_id,
                    scene_number=scene_number,
                    content=content,
                    characters=characters
                )
            else:  # VIDEO flow
                logger.info("Processing video flow")
                return await self._handle_video_flow(
                    user_id=user_id,
                    story_id=story_id,
                    scene_number=scene_number,
                    content=content,
                    characters=characters
                )
                
        except Exception as e:
            logger.error(f"Error in process_request: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _handle_story_media_flow(
        self,
        user_id: str,
        story_id: str,
        scene_number: int,
        content: Dict[str, Any],
        characters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle story media flow"""
        try:
            # Get last scenes for context
            last_scenes = await self.db.get_last_scenes(story_id, 2) if scene_number > 1 else []
            
            # Prepare context for analysis
            context = {
                "user_id": user_id,
                "story_id": story_id,
                "scene_number": scene_number,
                "characters": [
                    {
                        "name": char.get("name"),
                        "description_physical": char.get("description_physical"),
                        "voice_id": char.get("voice_id"),
                        "voice_description": char.get("voice_description")
                    }
                    for char in characters
                ],
                "previous_scenes": last_scenes,
                "user_input": content["user_input"]
            }
            
            # Generate manager analysis
            manager_analysis = await self._generate_manager_analysis(context)
            
            # Update scene with manager analysis
            scene_data = {
                'story_id': story_id,
                'scene_number': scene_number,
                'manager_task_analysis': json.dumps(manager_analysis)
            }
            await self.db.save_scene(scene_data)
            
            # Create tasks for other agents
            tasks = []
            
            # Story task
            story_task = {
                "task_id": str(uuid.uuid4()),
                "task_type": "story",
                "content": {
                    "story_id": story_id,
                    "scene_number": scene_number,
                    "user_input": content["user_input"],
                    "context": context
                },
                "task_analysis": manager_analysis.get("story_analysis", {})
            }
            tasks.append(story_task)
            
            # Image task
            if "image_analysis" in manager_analysis:
                image_task = {
                    "task_id": str(uuid.uuid4()),
                    "task_type": "image",
                    "content": {
                        "story_id": story_id,
                        "scene_number": scene_number,
                        "context": context
                    },
                    "task_analysis": manager_analysis["image_analysis"]
                }
                tasks.append(image_task)
            
            # Speech task
            if "speech_analysis" in manager_analysis:
                speech_task = {
                    "task_id": str(uuid.uuid4()),
                    "task_type": "speech",
                    "content": {
                        "story_id": story_id,
                        "scene_number": scene_number,
                        "context": context
                    },
                    "task_analysis": manager_analysis["speech_analysis"]
                }
                tasks.append(speech_task)
            
            return {
                "status": "success",
                "story_id": story_id,
                "scene_number": scene_number,
                "tasks": tasks
            }
            
        except Exception as e:
            logger.error(f"Error in story media flow: {str(e)}")
            return {
                    "status": "error",
                    "error": str(e)
                }

    async def _generate_manager_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate manager analysis for the scene"""
        try:
            # Prepare prompt with context
            prompt = f"""Analyze this scene and provide guidance for story, image, speech generation, and character management.

User Input: {context['user_input']}

Story Context:
Scene Number: {context['scene_number']}
Previous Scenes: {json.dumps(context.get('previous_scenes', []), indent=2)}

Existing Characters: {json.dumps(context['characters'], indent=2)}

Provide analysis in the following format:
{{
    "story_analysis": {{
        "recommendations": "story development guidelines",
        "character_focus": "which characters to focus on",
        "tone": "emotional tone for the scene"
    }},
    "image_analysis": {{
        "scene_description": "visual scene description",
        "style_recommendation": "art style guidelines",
        "key_elements": ["list of important visual elements"]
    }},
    "speech_analysis": {{
        "dialogue_focus": "speaking characters and their emotions",
        "voice_direction": "how the dialogue should be delivered",
        "background_audio": "any background sound recommendations"
    }},
    "character_analysis": {{
        "new_characters": [
            {{
                "name": "character name",
                "description_physical": "physical description",
                "voice_description": "voice characteristics",
                "personality": "personality traits",
                "background": "character background"
            }}
        ],
        "character_updates": [
            {{
                "character_id": "existing character id",
                "updates": {{
                    "description_physical": "updated physical description",
                    "voice_description": "updated voice description",
                    "personality": "updated personality traits"
                }}
            }}
        ]
    }}
}}"""

            # Get analysis from LLM
            logger.info("Requesting analysis from LLM")
            result = await self.llm_manager.execute_with_fallback(
                prompt,
                system_message="""You are a story director providing scene analysis and recommendations.
Your response must be a valid JSON object with exactly these fields:
{
    "story_analysis": {
        "recommendations": "story development guidelines",
        "character_focus": "which characters to focus on",
        "tone": "emotional tone for the scene"
    },
    "image_analysis": {
        "scene_description": "visual scene description",
        "style_recommendation": "art style guidelines",
        "key_elements": ["list of important visual elements"]
    },
    "speech_analysis": {
        "dialogue_focus": "speaking characters and their emotions",
        "voice_direction": "how the dialogue should be delivered",
        "background_audio": "any background sound recommendations"
    },
    "character_analysis": {
        "new_characters": [
            {
                "name": "character name",
                "description_physical": "physical description",
                "voice_description": "voice characteristics",
                "personality": "personality traits",
                "background": "character background"
            }
        ],
        "character_updates": [
            {
                "character_id": "existing character id",
                "updates": {
                    "description_physical": "updated physical description",
                    "voice_description": "updated voice description",
                    "personality": "updated personality traits"
                }
            }
        ]
    }
}"""
            )
            
            # Process character updates
            if content := result.get("content"):
                if isinstance(content, str):
                    content = json.loads(content)
                
                # Handle character analysis
                if character_analysis := content.get("character_analysis"):
                    # Create new characters
                    for new_char in character_analysis.get("new_characters", []):
                        # Add user_id and generate voice_id
                        new_char["user_id"] = context["user_id"]
                        new_char["voice_id"] = await self._assign_voice_id(new_char)
                        await self.db.save_character(new_char)
                        logger.info(f"Created new character: {new_char['name']}")
                    
                    # Update existing characters
                    for char_update in character_analysis.get("character_updates", []):
                        if char_id := char_update.get("character_id"):
                            updates = char_update.get("updates", {})
                            if updates:
                                await self.db.update_character(char_id, updates)
                                logger.info(f"Updated character {char_id}")
                
                return content
                
        except Exception as e:
            logger.error(f"Error generating manager analysis: {str(e)}")
            return self._get_default_analysis()

    async def _assign_voice_id(self, character: Dict[str, Any]) -> str:
        """Assign a voice ID based on character traits"""
        # Voice ID mapping with more options
        voice_map = {
            "male": {
                "default": "ErXwobaYiN019PkySvjV",  # Default male voice
                "young": "pNInz6obpgDQGcFmaJgB",    # Young male
                "old": "VR6AewLTigWG4xSOukaG",      # Older male
                "professional": "TxGEqnHWrfWFTfGW9XjX"  # Professional male
            },
            "female": {
                "default": "EXAVITQu4vr4xnSDxMaL",  # Default female voice
                "young": "21m00Tcm4TlvDq8ikWAM",    # Young female
                "old": "AZnzlk1XvdvUeBnXmlld",      # Older female
                "professional": "21m00Tcm4TlvDq8ikWAM"  # Professional female
            }
        }
        
        # Extract character traits
        description = character.get("description_physical", "").lower()
        name = character.get("name", "").lower()
        
        # Determine gender
        is_female = any(pronoun in description for pronoun in ["she", "her", "female", "woman", "girl"])
        gender = "female" if is_female else "male"
        
        # Determine age/style category
        if any(word in description for word in ["young", "youth", "teen", "child"]):
            category = "young"
        elif any(word in description for word in ["old", "elder", "aged", "senior"]):
            category = "old"
        elif any(word in description for word in ["professional", "business", "formal"]):
            category = "professional"
        else:
            category = "default"
        
        # Get voice ID
        voice_id = voice_map[gender][category]
        logger.info(f"Assigned voice ID {voice_id} to character {name} ({gender}, {category})")
        
        return voice_id

    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis structure"""
        return {
            "story_analysis": {
                "recommendations": "Create an engaging scene with natural dialogue",
                "character_focus": "Focus on all available characters",
                "tone": "Neutral and engaging"
            },
            "image_analysis": {
                "scene_description": "Create a clear visual representation",
                "style_recommendation": "Realistic and detailed",
                "key_elements": ["characters", "environment", "mood"]
            },
            "speech_analysis": {
                "dialogue_focus": "Natural conversation between characters",
                "voice_direction": "Clear and emotive delivery",
                "background_audio": "Ambient background sounds"
            },
            "character_analysis": {
                "new_characters": [],
                "character_updates": []
            }
        }

    async def _handle_video_flow(
        self,
        user_id: str,
        story_id: str,
        scene_number: int,
        content: Dict[str, Any],
        characters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Handle video flow"""
        try:
            # Similar to story media flow but for video
            context = {
                "story_id": story_id,
                "scene_number": scene_number,
                "characters": characters,
                "user_input": content["user_input"]
            }
            
            # Generate manager analysis
            manager_analysis = await self._generate_manager_analysis(context)
            
            # Update scene with manager analysis
            scene_data = {
                'story_id': story_id,
                'scene_number': scene_number,
                'manager_task_analysis': manager_analysis,
                'video_task_analysis': manager_analysis.get("video_analysis", {})
            }
            await self.db.save_scene(scene_data)
            
            # Create video task
            video_task = {
                "task_id": str(uuid.uuid4()),
                "task_type": "video",
                "content": {
                    "story_id": story_id,
                    "scene_number": scene_number,
                    "context": context
                },
                "task_analysis": manager_analysis
            }
            
            return {
                "status": "success",
                "story_id": story_id,
                "scene_number": scene_number,
                "tasks": [video_task]
            }
            
        except Exception as e:
            logger.error(f"Error in video flow: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _create_task(
        self,
        user_id: str,
        content: Dict[str, Any],
        flow_type: TaskFlow,
        story_id: Optional[str] = None,
        scene_id: Optional[str] = None
    ) -> Task:
        """Create task record in memory"""
        return Task(
            user_id=user_id,
            story_id=story_id,
            scene_id=scene_id,
            task_type=TaskType.STORY if flow_type == TaskFlow.STORY_MEDIA else TaskType.VIDEO,
            content=content,
            status=TaskStatus.PROCESSING
        )
        
    async def _check_compliance(self, content: Dict[str, Any], guidelines: str) -> Dict[str, Any]:
        """Check compliance against guidelines"""
        try:
            compliance_prompt = PROMPT_TEMPLATES["compliance_check"].format(
                content=content["user_input"],
                guidelines=guidelines
            )
            
            result = await self.llm_manager.execute_with_fallback(
                compliance_prompt,
                system_message="You are a content compliance checker.",
                response_type="compliance_check"  # Add response type for validation
            )

            logger.debug(f"Raw compliance check result from LLM: {json.dumps(result, indent=2)}")

            if not result:
                logger.error("Empty result from LLM")
                raise LLMError("Empty response from LLM")

            # Log API usage
            logger.info(f"API Call: provider={result.get('provider', 'unknown')} | in_tokens={result.get('usage', {}).get('prompt_tokens', 0)} | out_tokens={result.get('usage', {}).get('completion_tokens', 0)}")

            try:
                content = result.get("content")
                logger.debug(f"Extracted content from result: {json.dumps(content, indent=2)}")
                
                if not content:
                    logger.error("Empty content in result")
                    raise ValueError("Empty content in compliance result")

                # Try to parse as JSON
                if isinstance(content, str):
                    logger.debug("Content is string, attempting to parse as JSON")
                    response_dict = json.loads(content)
                else:
                    logger.debug("Content is already a dict")
                    response_dict = content
                
                logger.debug(f"Parsed response dict: {json.dumps(response_dict, indent=2)}")
                
                # Validate required fields
                if "is_safe" not in response_dict:
                    logger.error("Missing is_safe field in response")
                    raise ValueError("Missing required field 'is_safe' in compliance result")

                compliance_result = {
                    "is_safe": str(response_dict["is_safe"]).lower() in ["yes", "true"],
                    "explanation": response_dict.get("explanation", "No explanation provided")
                }
                
                logger.debug(f"Final compliance result: {json.dumps(compliance_result, indent=2)}")
                return compliance_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse compliance result: {str(e)}")
                logger.error(f"Raw content: {content}")
                raise ValueError(f"Invalid JSON in compliance result: {str(e)}")

        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            raise LLMError(f"Compliance check failed: {str(e)}")
        
    async def _analyze_knowledge_base(
        self,
        content: Dict[str, Any],
        story: Optional[Dict[str, Any]],
        scene: Optional[Scene],
        prev_scenes: List[Scene],
        characters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze knowledge base"""
        try:
            # Custom JSON encoder for datetime objects
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)

            # Prepare minimal context
            context = {
                "story": {
                    "id": story.get("story_id") if story else None,
                    "title": story.get("title") if story else None,
                    "current_scene": story.get("current_scene") if story else None,
                    "conversation_history": story.get("conversation_history", [])
                },
                "scene": {
                    "id": scene.scene_id if scene else None,
                    "number": scene.scene_number if scene else None,
                    "content": scene.content if scene else None
                },
                "characters": characters,
                "user_input": content["user_input"]
            }
            
            # Generate detailed analysis prompt
            kb_prompt = PROMPT_TEMPLATES["story_analysis"].format(
                content=content["user_input"],
                context=json.dumps(context, indent=2, cls=DateTimeEncoder)
            )
            
            # Get analysis from LLM
            result = await self.llm_manager.execute_with_fallback(
                kb_prompt,
                system_message="""You are a story analysis expert. Analyze the scene and characters to provide detailed recommendations for:
1. Story progression and character development
2. Visual elements and scene composition
3. Character dialogue and voice modulation
4. Emotional pacing and atmosphere

Format your response as a JSON object with the following structure:
{
    "story_agent": {
        "recommendations": "detailed story recommendations",
        "reasoning": "explanation of story choices",
        "characters": {
            "character_name": "description of what this character will do in the scene"
        }
    },
    "image_agent": {
        "recommendations": "detailed visual scene description and guidelines",
        "reasoning": "explanation of visual choices",
        "scene_elements": {
            "element_name": "description of how this element should be visualized"
        }
    },
    "speech_agent": {
        "recommendations": "dialogue and voice direction",
        "reasoning": "explanation of audio choices",
        "character_voices": {
            "character_name": "description of how this character should sound and speak"
        }
    }
}""")

            if not result or not result.get("content"):
                logger.error("Empty LLM response for knowledge base analysis")
                raise LLMError("Empty response from LLM")

            # Log API usage
            logger.info(f"API Call: provider={result.get('provider', 'unknown')} | in_tokens={result.get('usage', {}).get('prompt_tokens', 0)} | out_tokens={result.get('usage', {}).get('completion_tokens', 0)}")
            
            # Parse response
            content = result.get("content", {})
            if not content:
                raise ValueError("Empty content in LLM response")

            # If content is a string, try to parse it as JSON
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
                    logger.error(f"Raw content: {content}")
                    raise ValueError(f"Invalid JSON in LLM response: {str(e)}")

            # Validate required agent sections
            required_agents = ["story_agent", "image_agent", "speech_agent"]
            for agent in required_agents:
                if agent not in content:
                    logger.warning(f"Missing {agent} in LLM response")
                    content[agent] = {
                        "recommendations": "",
                        "reasoning": "",
                        "scene_elements" if agent == "image_agent" else "characters": {}
                    }

            # Return structured analysis
            return {
                "agent_analysis": content
            }

        except Exception as e:
            logger.error(f"Knowledge base analysis failed: {str(e)}")
            raise LLMError(f"Knowledge base analysis failed: {str(e)}")
        
    async def _process_parallel_results(
        self,
        results: List[Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Process results from parallel execution"""
        compliance_result, kb_result = results
        
        # Handle potential exceptions
        if isinstance(compliance_result, Exception):
            logger.error(f"Compliance check failed with error: {str(compliance_result)}")
            raise LLMError(f"Compliance check failed: {str(compliance_result)}")
        if isinstance(kb_result, Exception):
            logger.error(f"Knowledge base analysis failed with error: {str(kb_result)}")
            raise LLMError(f"Knowledge base analysis failed: {str(kb_result)}")
            
        # Parse compliance result
        try:
            logger.debug(f"Processing compliance result: {json.dumps(compliance_result, indent=2)}")
            
            # If result is already in the correct format, use it directly
            if isinstance(compliance_result, dict) and all(key in compliance_result for key in ["is_safe", "explanation"]):
                logger.debug("Compliance result already in correct format")
                return compliance_result, kb_result
            
            # Extract content from result
            content = compliance_result.get("content")
            logger.debug(f"Extracted content from compliance result: {json.dumps(content, indent=2)}")
            
            if not content:
                logger.warning("Empty compliance result content")
                return {
                    "is_safe": True,
                    "explanation": "Default safe response - no content provided"
                }, kb_result
            
            # Try to parse as JSON
            try:
                if isinstance(content, str):
                    logger.debug("Parsing content string as JSON")
                    response_dict = json.loads(content)
                else:
                    logger.debug("Content is already a dict")
                    response_dict = content
                
                logger.debug(f"Parsed response dict: {json.dumps(response_dict, indent=2)}")
                
                # Validate and extract fields
                if "is_safe" not in response_dict:
                    raise ValueError("Missing required field 'is_safe'")
                
                is_safe_str = str(response_dict["is_safe"]).lower()
                is_safe = is_safe_str in ["yes", "true"]
                
                processed_result = {
                    "is_safe": is_safe,
                    "explanation": response_dict.get("explanation", "No explanation provided")
                }
                
                logger.debug(f"Final processed compliance result: {json.dumps(processed_result, indent=2)}")
                return processed_result, kb_result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse as JSON: {str(e)}, attempting fallback parsing")
                # Fallback parsing for non-JSON responses
                content_str = str(content).lower()
                is_safe = not any(indicator in content_str for indicator in ["not safe", "unsafe", "inappropriate", "rejected", "failed"])
                
                fallback_result = {
                    "is_safe": is_safe,
                    "explanation": str(content)
                }
                
                logger.debug(f"Fallback compliance result: {json.dumps(fallback_result, indent=2)}")
                return fallback_result, kb_result
                
        except Exception as e:
            logger.error(f"Failed to process compliance result: {str(e)}")
            logger.error(f"Raw compliance result: {compliance_result}")
            return {
                "is_safe": True,
                "explanation": f"Failed to process compliance result: {str(e)}"
            }, kb_result
        
    async def _handle_compliance_failure(
        self,
        task: Task,
        compliance_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle failed compliance check"""
        task.status = TaskStatus.FAILED
        task.metadata["failure_reason"] = "compliance_check_failed"
        return {
            "status": "rejected",
            "reason": compliance_result["explanation"],
            "task_id": task.task_id
        }
            
    async def _handle_error(
        self,
        task: Task,
        error_message: str
    ) -> Dict[str, Any]:
        """Handle task error"""
        task.status = TaskStatus.FAILED
        task.metadata["error"] = error_message
        return {
            "status": "error",
            "task_id": task.task_id,
            "error": error_message
        }
        
    async def _create_story_task(
        self,
        parent_task: Task,
        content: Dict[str, Any],
        kb_result: Dict[str, Any],
        characters: Dict[str, Any]
    ) -> Task:
        """Create story task with optimized schema"""
        # Extract agent analysis
        story_analysis = kb_result["agent_analysis"]["story_agent"]
        
        # Create streamlined task content
        task_content = {
            "task_type": "story",
            "content_type": "scene",
            "user_request": content["user_input"],
            "context": {
                "story_id": parent_task.story_id,
                "characters": characters,
                "scene_number": content.get("scene_number", 1),
                "story_context": story_analysis["recommendations"]
            }
        }

        # Create focused task analysis
        task_analysis = {
            "flow_type": TaskFlow.STORY_MEDIA,
            "recommendations": story_analysis["recommendations"],
            "reasoning": story_analysis["reasoning"],
            "media_requirements": {
                "visual": kb_result["agent_analysis"].get("image_agent", {}).get("recommendations", ""),
                "audio": kb_result["agent_analysis"].get("speech_agent", {}).get("recommendations", "")
            }
        }

        return Task(
            task_id=str(uuid.uuid4()),
            user_id=parent_task.user_id,
            story_id=parent_task.story_id,
            task_type=TaskType.STORY,
            content=task_content,
            task_analysis=task_analysis,
            parent_task_id=parent_task.task_id,
            status=TaskStatus.PENDING
        )
        
    async def _create_video_task(
        self,
        parent_task: Task,
        content: Dict[str, Any],
        kb_result: Dict[str, Any],
        characters: Dict[str, Character]
    ) -> Task:
        """Create video task in memory"""
        task_analysis = TaskAnalysis(
            flow_type=TaskFlow.VIDEO,
            context=content.get("context", {}),
            recommendations=f"""Story Elements:
{kb_result["agent_analysis"]["story_agent"]["recommendations"]}

Visual Elements:
{kb_result["agent_analysis"]["image_agent"]["recommendations"]}

Audio Elements:
{kb_result["agent_analysis"]["speech_agent"]["recommendations"]}""",
            reasoning="Integrated story, visual and audio direction for video generation"
        )
        
        return Task(
            user_id=parent_task.user_id,
            story_id=parent_task.story_id,
            scene_id=parent_task.scene_id,
            task_type=TaskType.VIDEO,
            content={
                **content,
                "visual_elements": kb_result["agent_analysis"]["image_agent"]["recommendations"],
                "audio_elements": kb_result["agent_analysis"]["speech_agent"]["recommendations"],
                "characters": {
                    char_id: {
                        "name": char.name,
                        "personality": char.personality,
                        "background": char.background,
                        "speaking_style": char.speaking_style,
                        "traits": char.traits,
                        "relationships": char.relationships
                    }
                    for char_id, char in characters.items()
                }
            },
            task_analysis=task_analysis,
            parent_task_id=parent_task.task_id,
            status=TaskStatus.PENDING
        ) 