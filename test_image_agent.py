import os
import json
import pytest
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import aiohttp
from image_agent import ImageAgent, ImageTask, SceneContext, Character
from llm_factory import LLMManager

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO to reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add specific loggers for API and HTTP
api_logger = logging.getLogger('api.fal')
api_logger.setLevel(logging.INFO)

# Disable noisy HTTP connection logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Test data fixtures
@pytest.fixture
def complex_scene_data():
    return {
        "task_id": "test-flow-analysis",
        "task_type": "image",
        "scene_description": "A tense meeting in a high-tech boardroom",
        "style": "realistic",
        "context": {
            "scene_id": "scene-flow-001",
            "scene_number": 5,
            "characters": [
                {
                    "id": "char-exec",
                    "name": "Victoria Chen",
                    "description": "A sharp CEO in her 50s, wearing a designer suit",
                    "traits": ["authoritative", "strategic", "composed"]
                },
                {
                    "id": "char-rival",
                    "name": "Marcus Thompson",
                    "description": "A competing executive, mid-40s, in a modern suit",
                    "traits": ["ambitious", "calculating", "confident"]
                }
            ],
            "setting": "Ultra-modern corporate boardroom with glass walls",
            "tone": "Tense and professional",
            "content": "Victoria stands at the head of the table, her posture commanding as she faces Marcus across the polished surface. The city skyline visible through the glass walls adds to the scene's gravity."
        },
        "reasoning": {
            "reasoning": "Scene requires high-end corporate atmosphere with focus on power dynamics",
            "recommendations": "Emphasize professional setting, character positioning, and environmental details"
        }
    }

class MockLLMManager:
    """Mock LLM Manager for testing"""
    async def execute_with_fallback(self, prompt: str, system_message: str, response_type: str) -> Dict[str, Any]:
        return {
            "content": {
                "prompt": "A high-tech corporate boardroom with glass walls offering a breathtaking view of the city skyline. Victoria Chen, a sharp and authoritative CEO in her 50s, stands at the head of a polished wooden table, wearing a sleek designer suit. Her posture exudes confidence and control as she faces Marcus Thompson. The atmosphere is tense and professional, with ultra-modern furniture and state-of-the-art technology.",
                "recommended_style": "cartoon",
                "style_reasoning": "The scene's emphasis on professional environment and character expressions would benefit from the cartoon style's ability to emphasize facial expressions and environmental details while maintaining a clean, professional look."
            }
        }

class DataFlowLogger:
    """Helper class to track data flow through the agent"""
    def __init__(self):
        self.flow_log = []
        
    def log_step(self, step_name: str, input_data: Any, output_data: Any):
        # Clean and format the data for better readability
        cleaned_input = self._clean_data(input_data)
        cleaned_output = self._clean_data(output_data)
        
        self.flow_log.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "input": cleaned_input,
            "output": cleaned_output
        })
    
    def _clean_data(self, data: Any) -> Any:
        """Clean and format data for logging"""
        if isinstance(data, dict):
            # Remove or mask sensitive data
            cleaned = data.copy()
            if 'api_key' in cleaned:
                cleaned['api_key'] = '***'
            return cleaned
        return data
        
    def print_flow_summary(self):
        print("\n=== Data Flow Summary ===")
        for entry in self.flow_log:
            print(f"\nStep: {entry['step']}")
            print(f"Time: {entry['timestamp']}")
            
            # Format API calls specially
            if entry['step'] == 'image_generation':
                print("\nAPI Request to Fal.ai:")
                if isinstance(entry['input'], dict):
                    print("Prompt:", entry['input'].get('prompt', 'N/A'))
                    print("Style:", entry['input'].get('recommended_style', 'N/A'))
                    print("Dimensions:", entry['input'].get('expected_dimensions', 'N/A'))
                print("\nAPI Response:")
                if isinstance(entry['output'], dict):
                    print("Image URL:", entry['output'].get('image_url', 'N/A'))
                    print("Model Configuration:")
                    models = entry['output'].get('models_used', {})
                    print(json.dumps(models, indent=2))
            else:
                print("Input:")
                print(json.dumps(entry['input'], indent=2))
                print("Output:")
                print(json.dumps(entry['output'], indent=2))

@pytest.mark.asyncio
async def test_image_agent_flow(complex_scene_data):
    """Test the complete flow of data through the ImageAgent with detailed logging"""
    
    # Initialize components
    session = aiohttp.ClientSession()
    llm_manager = MockLLMManager()  # Use mock LLM manager
    agent = ImageAgent(llm_manager=llm_manager)
    flow_logger = DataFlowLogger()
    
    try:
        # 1. Task Validation
        logger.info("Step 1: Task Validation")
        task = ImageTask(**complex_scene_data)
        flow_logger.log_step(
            "task_validation",
            complex_scene_data,
            task.dict()
        )
        
        # 2. Scene Context Extraction
        logger.info("Step 2: Scene Context Extraction")
        scene_context = agent._extract_scene_context(task.context)
        flow_logger.log_step(
            "scene_context_extraction",
            task.context,
            scene_context.dict()
        )
        
        # 3. Prompt Generation with Style Recommendation
        logger.info("Step 3: Prompt Generation and Style Analysis")
        prompt_result = await agent._generate_image_prompt(
            task.scene_description,
            scene_context,
            task.reasoning
        )
        flow_logger.log_step(
            "prompt_generation",
            {
                "scene_description": task.scene_description,
                "scene_context": scene_context.dict(),
                "reasoning": task.reasoning
            },
            prompt_result
        )
        
        # 4. Model Selection
        logger.info("Step 4: Model Selection")
        recommended_style = prompt_result["recommended_style"].lower()
        lora_config = agent.lora_models.get(recommended_style, agent.lora_models["cartoon"])
        flow_logger.log_step(
            "model_selection",
            {
                "recommended_style": recommended_style,
                "scene_context": scene_context.dict()
            },
            {
                "lora_config": lora_config
            }
        )
        
        # 5. Image Generation
        logger.info("\n=== Starting Image Generation ===")
        logger.info("Preparing API call to Fal.ai flux-lora endpoint...")
        image_result = await agent._generate_image(
            prompt_result["prompt"],
            scene_context,
            recommended_style
        )
        
        # Log the actual API request and response
        logger.info("\nAPI Request Details:")
        logger.info(f"Endpoint: fal-ai/flux-lora")
        logger.info(f"Prompt: {prompt_result['prompt']}")
        logger.info(f"Style: {recommended_style}")
        logger.info(f"Dimensions: 1080x1920")
        
        logger.info("\nAPI Response Details:")
        logger.info(f"Image URL: {image_result['image_url']}")
        logger.info("Model Configuration:")
        logger.info(json.dumps(image_result['models_used'], indent=2))
        
        flow_logger.log_step(
            "image_generation",
            {
                "prompt": prompt_result["prompt"],
                "recommended_style": recommended_style,
                "expected_dimensions": "1080x1920"
            },
            image_result
        )
        
        # Verify image dimensions in result
        assert "dimensions" in image_result["models_used"], "Image dimensions not found in result"
        assert image_result["models_used"]["dimensions"] == "1080x1920", "Incorrect image dimensions"
        
        # 6. Image Saving
        logger.info("Step 6: Image Saving")
        local_path = await agent._save_image(
            image_result["image_url"],
            task.task_id,
            scene_context.scene_id
        )
        flow_logger.log_step(
            "image_saving",
            {"image_url": image_result["image_url"]},
            {"local_path": local_path}
        )
        
        # Print detailed flow summary
        flow_logger.print_flow_summary()
        
        # Print key metrics and choices
        print("\n=== Style Analysis ===")
        print(f"Recommended Style: {recommended_style}")
        print(f"Style Reasoning: {prompt_result['style_reasoning']}")
        print(f"Selected LoRA: {lora_config}")
        
        print("\n=== Prompt Analysis ===")
        print("Generated Prompt:")
        print(prompt_result["prompt"])
        
        print("\n=== Performance Metrics ===")
        print(f"Total Steps: {len(flow_logger.flow_log)}")
        print(f"Image URL: {image_result['image_url']}")
        print(f"Local Save Path: {local_path}")
        
    finally:
        await session.close()

def run_flow_test():
    """Run the flow analysis test"""
    pytest.main(["-v", __file__])

if __name__ == "__main__":
    run_flow_test() 