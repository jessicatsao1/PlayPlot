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
    TaskAnalysis
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
        story_id: Optional[str] = None,
        scene_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process incoming request and orchestrate task execution
        """
        task = None
        try:
            # Create task record in memory
            task = self._create_task(user_id, content, flow_type, story_id, scene_id)
            logger.info(f"Created task: {task.task_id}")
            
            # Run compliance and knowledge base reasoning in parallel
            guidelines = await self.db.get_compliance_guidelines()
            if not guidelines:
                logger.error("No compliance guidelines found")
                return await self._handle_error(task, "No compliance guidelines available")
            logger.info(f"Retrieved {len(guidelines)} compliance guidelines")
            
            story = await self.db.get_story(story_id) if story_id else None
            scene = await self.db.get_scene(scene_id) if scene_id else None
            prev_scenes = await self.db.get_previous_scenes(story_id, 3) if story_id else []
            
            # Execute parallel tasks
            logger.info("Executing parallel compliance check and knowledge base analysis")
            results = await asyncio.gather(
                self._check_compliance(content, guidelines),
                self._analyze_knowledge_base(content, story, scene, prev_scenes),
                return_exceptions=True
            )
            
            # Process results
            compliance_result, kb_result = await self._process_parallel_results(results)
            logger.info(f"Processed parallel results - Compliance safe: {compliance_result['is_safe']}")
            
            # Update task with results
            try:
                task.compliance_result = ComplianceResult(**compliance_result)
                task.status = TaskStatus.PROCESSING
                logger.info(f"Updated task {task.task_id} with compliance result")
            except Exception as e:
                logger.error(f"Failed to update task with compliance result: {str(e)}")
                return await self._handle_error(task, f"Failed to update compliance result: {str(e)}")
            
            # Check compliance
            if not compliance_result["is_safe"]:
                logger.warning(f"Content failed compliance check: {compliance_result['reasoning']}")
                return await self._handle_compliance_failure(task, compliance_result)
            
            # Process based on flow type
            if flow_type == TaskFlow.STORY_MEDIA:
                logger.info("Processing story media flow")
                return await self._handle_story_media_flow(
                    task,
                    content,
                    kb_result
                )
            else:  # VIDEO flow
                logger.info("Processing video flow")
                return await self._handle_video_flow(
                    task,
                    content,
                    kb_result
                )
                
        except Exception as e:
            logger.error(f"Error in process_request: {str(e)}")
            if task is None:
                return {
                    "status": "error",
                    "error": str(e)
                }
            return await self._handle_error(task, str(e))
            
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
                    "reasoning": response_dict.get("explanation", "No explanation provided"),
                    "concerns": response_dict.get("concerns", []),
                    "suggestions": response_dict.get("suggestions", [])
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
        story: Story,
        scene: Scene,
        prev_scenes: List[Scene]
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
                    "id": story.story_id if story else None,
                    "title": story.title if story else None,
                    "current_scene": story.current_scene if story else None,
                    "characters": story.characters if story else None
                },
                "scene": {
                    "id": scene.scene_id if scene else None,
                    "number": scene.scene_number if scene else None,
                    "content": scene.content if scene else None
                },
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
                system_message="You are a story analysis expert. Provide detailed analysis following the exact format specified.",
                response_type="story_analysis"
            )

            if not result or not result.get("content"):
                logger.error("Empty LLM response for knowledge base analysis")
                raise LLMError("Empty response from LLM")

            # Log API usage
            logger.info(f"API Call: provider={result.get('provider', 'unknown')} | in_tokens={result.get('usage', {}).get('prompt_tokens', 0)} | out_tokens={result.get('usage', {}).get('completion_tokens', 0)}")
            
            # Parse response
            content = result.get("content", {})
            if not content:
                raise ValueError("Empty content in LLM response")

            # Create agent-specific analysis with simplified structure
            return {
                "agent_analysis": {
                    "story_agent": {
                        "recommendations": content.get("story_agent", {}).get("recommendations", ""),
                        "reasoning": content.get("story_agent", {}).get("reasoning", "")
                    },
                    "image_agent": {
                        "recommendations": content.get("image_agent", {}).get("recommendations", ""),
                        "reasoning": content.get("image_agent", {}).get("reasoning", "")
                    },
                    "speech_agent": {
                        "recommendations": content.get("speech_agent", {}).get("recommendations", ""),
                        "reasoning": content.get("speech_agent", {}).get("reasoning", "")
                    }
                }
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
            if isinstance(compliance_result, dict) and all(key in compliance_result for key in ["is_safe", "reasoning", "concerns", "suggestions"]):
                logger.debug("Compliance result already in correct format")
                return compliance_result, kb_result
            
            # Extract content from result
            content = compliance_result.get("content")
            logger.debug(f"Extracted content from compliance result: {json.dumps(content, indent=2)}")
            
            if not content:
                logger.warning("Empty compliance result content")
                return {
                    "is_safe": True,
                    "reasoning": "Default safe response - no content provided",
                    "concerns": [],
                    "suggestions": []
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
                    "reasoning": response_dict.get("explanation", "No explanation provided"),
                    "concerns": response_dict.get("concerns", []),
                    "suggestions": response_dict.get("suggestions", [])
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
                    "reasoning": str(content),
                    "concerns": [],
                    "suggestions": []
                }
                
                logger.debug(f"Fallback compliance result: {json.dumps(fallback_result, indent=2)}")
                return fallback_result, kb_result
                
        except Exception as e:
            logger.error(f"Failed to process compliance result: {str(e)}")
            logger.error(f"Raw compliance result: {compliance_result}")
            return {
                "is_safe": True,
                "reasoning": f"Failed to process compliance result: {str(e)}",
                "concerns": [],
                "suggestions": []
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
            "reason": compliance_result["reasoning"],
            "suggestions": compliance_result.get("suggestions", []),
            "task_id": task.task_id
        }
        
    async def _handle_story_media_flow(
        self,
        task: Task,
        content: Dict[str, Any],
        kb_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle story media flow"""
        try:
            # Create tasks in memory
            tasks = []
            
            # Create story task
            story_task = await self._create_story_task(task, content, kb_result)
            tasks.append(story_task)
            
            # Create image task if visual elements present
            if kb_result["agent_analysis"].get("image_agent"):
                image_task = Task(
                    user_id=task.user_id,
                    story_id=task.story_id,
                    scene_id=task.scene_id,
                    task_type=TaskType.IMAGE,
                    content={
                        "visual_elements": kb_result["agent_analysis"]["image_agent"]["recommendations"],
                        "context": content.get("context", {})
                    },
                    task_analysis=TaskAnalysis(
                        flow_type=TaskFlow.STORY_MEDIA,
                        context=content.get("context", {}),
                        recommendations=kb_result["agent_analysis"]["image_agent"]["recommendations"],
                        reasoning=kb_result["agent_analysis"]["image_agent"]["reasoning"]
                    ),
                    status=TaskStatus.PENDING
                )
                tasks.append(image_task)
            
            # Create speech task if audio elements present
            if kb_result["agent_analysis"].get("speech_agent"):
                speech_task = Task(
                    user_id=task.user_id,
                    story_id=task.story_id,
                    scene_id=task.scene_id,
                    task_type=TaskType.SPEECH,
                    content={
                        "audio_elements": kb_result["agent_analysis"]["speech_agent"]["recommendations"],
                        "context": content.get("context", {})
                    },
                    task_analysis=TaskAnalysis(
                        flow_type=TaskFlow.STORY_MEDIA,
                        context=content.get("context", {}),
                        recommendations=kb_result["agent_analysis"]["speech_agent"]["recommendations"],
                        reasoning=kb_result["agent_analysis"]["speech_agent"]["reasoning"]
                    ),
                    status=TaskStatus.PENDING
                )
                tasks.append(speech_task)
            
            # Update original task
            task.status = TaskStatus.COMPLETED
            task.metadata["child_tasks"] = [t.task_id for t in tasks]
            
            # Return flattened task list
            return {
                "status": "success",
                "task_id": task.task_id,
                "tasks": [t.dict() for t in tasks]
            }
            
        except Exception as e:
            return await self._handle_error(task, str(e))
            
    async def _handle_video_flow(
        self,
        task: Task,
        content: Dict[str, Any],
        kb_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle video flow"""
        try:
            # Create video task in memory
            video_task = await self._create_video_task(task, content, kb_result)
            
            # Update original task
            task.status = TaskStatus.COMPLETED
            task.metadata["child_tasks"] = [video_task.task_id]
            return {
                "status": "success",
                "task_id": task.task_id,
                "video_task": video_task.dict()
            }
            
        except Exception as e:
            return await self._handle_error(task, str(e))
            
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
        kb_result: Dict[str, Any]
    ) -> Task:
        """Create story task with detailed analysis"""
        try:
            # Ensure we have story agent analysis
            story_analysis = kb_result["agent_analysis"]["story_agent"]
            if not story_analysis.get("recommendations"):
                raise ValueError("Missing story recommendations in knowledge base result")
                
            task_analysis = TaskAnalysis(
                flow_type=TaskFlow.STORY_MEDIA,
                context=content.get("context", {}),
                recommendations=story_analysis["recommendations"],
                reasoning=story_analysis["reasoning"]
            )
            
            return Task(
                user_id=parent_task.user_id,
                story_id=parent_task.story_id,
                scene_id=parent_task.scene_id,
                task_type=TaskType.STORY,
                content={
                    **content,
                    "story_elements": story_analysis["recommendations"]
                },
                task_analysis=task_analysis,
                status=TaskStatus.PENDING
            )
            
        except Exception as e:
            logger.error(f"Failed to create story task: {str(e)}")
            raise
        
    async def _create_video_task(
        self,
        parent_task: Task,
        content: Dict[str, Any],
        kb_result: Dict[str, Any]
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
                "audio_elements": kb_result["agent_analysis"]["speech_agent"]["recommendations"]
            },
            task_analysis=task_analysis,
            parent_task_id=parent_task.task_id,
            status=TaskStatus.PENDING
        ) 