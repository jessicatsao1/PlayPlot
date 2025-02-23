# Agent Architecture and Setup Guide

## Overview
The system implements a two-layer agent architecture:
- Layer 1 (Manager Agent): Handles triage, compliance, knowledge integration, and task orchestration
- Layer 2 (Worker Agents): Specialized agents for content generation (Story, Image, Speech, Video)

The system uses Llama 3.3 on Groq as primary and Mistral as fallback for content generation, while the manager agent uses Perplexity with Mistral fallback.

## Architectural Layers

### Layer 1: Manager Agent
```python
class ManagerAgent:
    """
    Central controller handling:
    1. Policy compliance
    2. Knowledge base integration (RAG)
    3. Task definition and routing
    4. Multi-step orchestration
    """
    role: "Task Management and Orchestration"
    primary_model: "perplexity/pplx-70b-online"
    fallback_model: "mistral/mistral-7b"
    temperature: 0.7
    
    # Unified task schema for consistent data flow between layers
    task_schema = {
        "story": {
            "input": {
                "required_fields": {
                    "task_id": "UUID for task tracking",
                    "task_type": "story",
                    "content_type": "Literal['scene', 'dialogue', 'description']",
                    "user_request": "Original user input",
                    "reasoning": "Manager's analysis and reasoning",
                    "context": {
                        "story_id": "UUID",
                        "characters": "List[Dict]",
                        "previous_scenes": "List[Dict]",
                        "scene_number": "int",
                        "story_context": "str"
                    }
                },
                "optional_fields": {
                    "style_preferences": "Dict[str, Any]",
                    "tone": "str",
                    "genre": "str",
                    "next_actions": "List[str]"
                }
            },
            "output": {
                "required_fields": {
                    "task_id": "UUID",
                    "content": "str",
                    "scene_type": "str",
                    "characters": "List[Dict]",
                    "metadata": {
                        "scene_number": "int",
                        "word_count": "int",
                        "tone": "str"
                    }
                },
                "optional_fields": {
                    "visual_description": "str",
                    "dialogue_sections": "List[Dict]",
                    "suggested_next_scenes": "List[str]"
                }
            }
        },
        "image": {
            "input": {
                "required_fields": {
                    "task_id": "UUID",
                    "task_type": "image",
                    "scene_description": "str",
                    "style": "str",
                    "reasoning": "Manager's analysis for visual elements",
                    "context": {
                        "story_id": "UUID",
                        "scene_id": "UUID",
                        "characters": "List[Dict]"
                    }
                },
                "optional_fields": {
                    "lora_model": "str",
                    "negative_prompt": "str",
                    "reference_images": "List[str]"
                }
            },
            "output": {
                "required_fields": {
                    "task_id": "UUID",
                    "image_url": "str",
                    "prompt_used": "str",
                    "metadata": {
                        "model": "str",
                        "size": "str",
                        "seed": "int"
                    }
                }
            }
        },
        "speech": {
            "input": {
                "required_fields": {
                    "task_id": "UUID",
                    "task_type": "speech",
                    "text": "str",
                    "voice_id": "str",
                    "emotion": "str",
                    "reasoning": "Manager's analysis for voice modulation",
                    "context": {
                        "character_id": "UUID",
                        "scene_id": "UUID"
                    }
                },
                "optional_fields": {
                    "speed": "float",
                    "pitch": "float",
                    "background_music": "str"
                }
            },
            "output": {
                "required_fields": {
                    "task_id": "UUID",
                    "audio_url": "str",
                    "duration": "float",
                    "metadata": {
                        "voice_id": "str",
                        "emotion": "str"
                    }
                }
            }
        },
        "video": {
            "input": {
                "required_fields": {
                    "task_id": "UUID",
                    "task_type": "video",
                    "scene_description": "str",
                    "duration": "int",
                    "style": "str",
                    "reasoning": "Manager's analysis for video generation",
                    "context": {
                        "story_id": "UUID",
                        "scene_id": "UUID",
                        "characters": "List[Dict]",
                        "source_image": "Optional[str]",  # For image-to-video
                        "source_text": "Optional[str]"    # For text-to-video
                    }
                },
                "optional_fields": {
                    "fps": "int",
                    "resolution": "str",
                    "transitions": "List[str]",
                    "background_music": "str",
                    "special_effects": "List[Dict]"
                }
            },
            "output": {
                "required_fields": {
                    "task_id": "UUID",
                    "video_url": "str",
                    "thumbnail_url": "str",
                    "duration": "float",
                    "metadata": {
                        "model": "str",
                        "resolution": "str",
                        "fps": "int",
                        "file_size": "int"
                    }
                },
                "optional_fields": {
                    "preview_gif": "str",
                    "chapters": "List[Dict]",
                    "generated_captions": "List[str]"
                }
            }
        }
    }
    
    async def process_request(self, request: Dict) -> Dict:
        try:
            # 1. Policy Check with detailed reasoning
            compliance_check = await self.check_compliance_with_reasoning(request)
            if not compliance_check["is_compliant"]:
                return {
                    "status": "rejected",
                    "reason": compliance_check["reasoning"],
                    "suggestion": compliance_check["alternative_suggestion"]
                }
            
            # 2. Knowledge Integration with structured retrieval
            kb_results = await self.query_knowledge_base(
                category=request["task_type"],
                context=request["context"],
                structured_output=True
            )
            
            # 3. Task Analysis and Planning with Reasoning
            task_plan = await self.analyze_and_plan_tasks(
                user_request=request["user_input"],
                kb_results=kb_results,
                context=request["context"]
            )
            
            # 4. Task Definition with Schema Validation
            tasks = await self.define_tasks_with_schema(
                task_plan=task_plan,
                user_request=request["user_input"],
                kb_results=kb_results
            )
            
            # 5. Orchestration with Enhanced Error Handling
            results = []
            for task in tasks:
                try:
                    # Validate task against schema
                    self.validate_task_schema(task)
                    
                    # Add reasoning and context enrichment
                    enriched_task = await self.enrich_task_with_reasoning(task)
                    
                    # Execute task with retry logic
                    result = await self.execute_task_with_retry(enriched_task)
                    
                    # Validate result against output schema
                    self.validate_task_output(result, task["task_type"])
                    
                    results.append(result)
                    
                    # Handle dependent tasks with context passing
                    if task["type"] == "story" and task.get("requires_media"):
                        media_tasks = await self.create_media_tasks_with_context(
                            story_result=result,
                            original_task=enriched_task
                        )
                        for media_task in media_tasks:
                            media_result = await self.execute_task_with_retry(media_task)
                            results.append(media_result)
                            
                except TaskValidationError as e:
                    logger.error(f"Task validation failed: {str(e)}")
                    return self.create_error_response("task_validation_error", str(e))
                except TaskExecutionError as e:
                    logger.error(f"Task execution failed: {str(e)}")
                    return self.create_error_response("task_execution_error", str(e))
            
            return self.format_response(results)
``` 