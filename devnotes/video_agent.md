# Video Agent Development Requirements

## Overview
The Video Agent (Layer 2) transforms story scenes into dynamic videos by utilizing scene content, image context, and Layer 1 agent recommendations. It leverages the Fal.ai API for video generation and handles both primary and fallback video generation paths.

## Input/Output Flow and Reasoning

### Input Sources
1. **From Story Database**
   ```python
   # Story Scene (Natural Language)
   story_scene = """
   A young barista stands behind the counter of a cozy café. Her most striking feature 
   is her long pink hair that catches the morning light streaming through the windows. 
   She's wearing a white shirt with a green apron, holding a menu book in her hands. 
   The café has a warm, inviting atmosphere with the scent of coffee and pastries in the air.
   """
   ```

2. **From Image Generation**
   ```python
   # SDXL-Style Image Prompt (Used for initial image generation)
   image_prompt = """
   young anime girl barista, long flowing pink hair, emerald green eyes, wearing white shirt 
   and green apron with embroidered logo, standing behind cafe counter, holding menu book, 
   morning sunlight streaming through windows, warm cafe atmosphere, pastries on display, 
   photorealistic, detailed lighting, cinematic composition, soft morning glow, 8k uhd, 
   hyperrealistic, professional photography
   Negative prompt: blurry, distorted, low quality, bad anatomy, extra limbs, poorly drawn 
   hands, deformed, amateur, unprofessional
   """
   ```

3. **From Layer 1 Agent Analysis**
   ```python
   # Layer 1 Agent Recommendations (INPUT to Video Agent)
   layer1_recommendations = """
   Scene Analysis:
   - Key focus on the barista's gentle movements and expressions
   - Emphasis on the warm, inviting café atmosphere
   - Important details: pink hair movement, light interactions, menu book

   Video Generation Guidelines:
   - Subtle camera movement: slow push-in shot
   - Emphasize morning light dynamics and reflections
   - Maintain high detail on character features
   - Smooth motion for hair and fabric physics
   - Keep pastries and café elements in frame
   """
   ```

4. **Combined Context**
   ```python
   # Aggregated Input Context
   story_context = {
       "scene_content": story_scene,
       "scene_number": 5,
       "image_prompt": image_prompt,
       "image_url": "https://storage.example.com/scene5_cafe_barista.jpg",
       "layer1_analysis": layer1_recommendations
   }
   ```

### Video Agent Reasoning Process
1. **Scene Analysis**
   ```python
   # Internal reasoning steps the agent should perform
   reasoning_steps = {
       "motion_analysis": {
           "scene_type": "character_focused",
           "movement_requirements": ["subtle", "atmospheric"],
           "key_elements": ["character", "environment", "props"],
           "timing_considerations": "slow_paced"
       },
       "technical_requirements": {
           "quality_needs": "high_detail_preservation",
           "focus_areas": ["face", "hair", "menu_book"],
           "lighting_dynamics": "morning_light_interaction"
       },
       "generation_strategy": {
           "primary_approach": "push_in_with_subtle_movement",
           "fallback_options": "pan_with_focus_points",
           "quality_thresholds": {
               "min_resolution": "1024x576",
               "min_fps": 24,
               "min_duration": 6.0
           }
       }
   }
   ```

### Expected Output
1. **Video Generation Parameters**
   ```python
   # Parameters derived from agent reasoning
   video_params = {
       "scene": {
           "content": "A young barista with flowing pink hair in a sunlit café, creating a warm and inviting atmosphere",
           "number": 5,
           "image_url": "https://storage.example.com/scene5_cafe_barista.jpg"
       },
       "generation": {
           "guidance_scale": 7.0,  # Increased for better detail retention
           "num_inference_steps": 35,  # More steps for complex scene
           "aspect_ratio": "16:9",
           "negative_prompt": "blurry, distorted, low quality, bad anatomy, deformed",
           "motion_scale": 0.8,  # Subtle motion for natural feel
           "motion_type": "push_in"  # Slow camera push-in
       },
       "motion": {
           "type": "push_in",
           "speed": "slow",
           "duration": 6.0,  # Longer duration for atmospheric scene
           "focus_points": ["face", "hair", "menu_book"]  # Key elements to track
       }
   }
   ```

2. **Final Output Structure**
   ```python
   {
       "video_url": "https://storage.example.com/videos/scene5_cafe_barista.mp4",
       "metadata": {
           "duration": 6.0,
           "resolution": "1024x576",
           "fps": 24,
           "scene_content": story_scene,
           "generation_params": {
               "guidance_scale": 7.0,
               "num_inference_steps": 35,
               "motion_type": "push_in",
               "motion_scale": 0.8
           },
           "scene_elements": {
               "primary_focus": "barista",
               "key_details": ["pink_hair", "green_apron", "menu_book"],
               "atmosphere": "warm_morning_light"
           }
       }
   }
   ```

### Important Notes for Engineers
1. **Layer 1 to Layer 2 Flow**
   - Layer 1 agent provides initial scene analysis and recommendations
   - Video Agent (Layer 2) uses these recommendations but performs its own technical analysis
   - Final parameters should consider both Layer 1 insights and technical constraints

2. **Reasoning Requirements**
   - Must implement explicit reasoning about motion choices
   - Should validate recommendations against technical capabilities
   - Need to handle conflicts between creative and technical requirements

3. **Quality Assurance**
   - Verify that Layer 1 recommendations are properly interpreted
   - Ensure generation parameters match scene requirements
   - Validate output against both technical specs and creative intent

## Processing Steps

1. **Context Analysis (Using Manager Agent Output)**
   ```python
   # Input: Story context and manager recommendations
   # Output: Structured video generation parameters
   video_params = {
       "scene": {
           "content": story_context["scene_content"],
           "number": story_context["scene_number"],
           "image_url": story_context["image_url"]
       },
       "generation": {
           "guidance_scale": 6.0,
           "num_inference_steps": 30,
           "aspect_ratio": "16:9",
           "negative_prompt": "blurry, low quality"
       },
       "motion": {
           "type": "pan",
           "direction": "left-to-right",
           "duration": 4.0
       }
   }
   ```

2. **Video Generation Settings**
   ```python
   # Combine scene context with manager recommendations
   generation_settings = {
       "primary": {
           "model": "fal-ai-video-gen-1",
           "settings": {
               "guidance_scale": 6.0,
               "num_inference_steps": 30,
               "aspect_ratio": "16:9",
               "fps": 24
           }
       },
       "fallback": {
           "model": "fal-ai-video-gen-2",
           "settings": {
               "guidance_scale": 5.0,
               "num_inference_steps": 25,
               "aspect_ratio": "16:9",
               "fps": 24
           }
       }
   }
   ```

3. **Video Generation Sequence**
   ```python
   async def generate_scene_video(video_params):
       try:
           # Initialize video client
           video_client = FalVideoClient(config)
           
           # Upload image if local path provided
           if video_params["scene"].get("image_path"):
               image_url = await video_client.upload_image(
                   video_params["scene"]["image_path"]
               )
           else:
               image_url = video_params["scene"]["image_url"]
           
           # Generate video
           result = await video_client.generate_video(
               prompt=video_params["scene"]["content"],
               image_url=image_url,
               **video_params["generation"]
           )
           
           return {
               "video_url": result["video_url"],
               "metadata": {
                   **result["metadata"],
                   "scene_content": video_params["scene"]["content"]
               }
           }
       except VideoGenerationError:
           # Try fallback provider
           return await generate_fallback_video(video_params)
   ```

## Video Requirements

1. **Quality Guidelines**
   - Resolution: 1024x576 (minimum)
   - Frame rate: 24 fps
   - Duration: 4-10 seconds
   - Format: MP4 with H.264 encoding

2. **Generation Requirements**
   - High fidelity to source image
   - Smooth motion transitions
   - Consistent lighting and colors
   - Appropriate motion based on scene context

3. **Technical Specifications**
   - Codec: H.264
   - Container: MP4
   - Bitrate: 2-5 Mbps
   - Audio: None (handled separately by Speech Agent)

## Fal.ai Integration
```python
async def generate_video_segment(params):
    video_client = FalVideoClient(config)
    
    generation_request = {
        "prompt": params["scene"]["content"],
        "image_url": params["scene"]["image_url"],
        "guidance_scale": params["generation"]["guidance_scale"],
        "num_inference_steps": params["generation"]["num_inference_steps"],
        "aspect_ratio": params["generation"]["aspect_ratio"]
    }
    
    return await video_client.generate_video(**generation_request)
```

## Testing Focus Areas

1. **Scene Context Testing**
   ```python
   test_context = {
       "scene_content": "A busy city street at night",
       "image_url": "https://example.com/city.jpg"
   }
   # Verify:
   # - Context properly processed
   # - Image URL validated
   # - Generation parameters appropriate
   ```

2. **Video Quality Testing**
   ```python
   test_generation = {
       "prompt": "City street at night",
       "image_url": "https://example.com/city.jpg"
   }
   # Verify:
   # - Resolution meets requirements
   # - Motion is smooth
   # - Fidelity to source image
   # - No artifacts or glitches
   ```

## Error Handling

1. **Critical Errors (Stop Processing)**
   - Failed image upload
   - Primary and fallback generation failure
   - Invalid image URL or format
   - Insufficient GPU resources

2. **Non-Critical Errors (Use Fallback)**
   - Primary provider timeout
   - Quality threshold not met
   - Temporary API issues

## Development Guidelines

### Code Structure
```
video_agent/
├── __init__.py
├── agent.py           # Main agent logic
├── fal_client.py     # API integration
├── processors/       
│   ├── context.py    # Context processing
│   └── video.py      # Video processing
└── utils/
    ├── validation.py
    └── storage.py
```

### Processing Rules
1. **Context Processing**
   - Validate image URLs/paths
   - Parse motion requirements
   - Extract style preferences

2. **Video Generation**
   - Apply appropriate motion type
   - Maintain image fidelity
   - Handle fallback gracefully

3. **Performance Optimization**
   - Cache frequently used images
   - Implement request queuing
   - Monitor GPU usage

## Testing Requirements
1. **Unit Tests**
   - Context processing functions
   - Parameter validation
   - Error handling

2. **Integration Tests**
   - Fal.ai API integration
   - Fallback provider testing
   - End-to-end flow

## Monitoring
- Track API response times
- Monitor generation success rate
- Log GPU usage
- Record video quality metrics

## Dependencies
```requirements.txt
aiohttp>=3.8.0
fal.ai>=0.4.0
pydantic>=2.0.0
```

## Implementation Notes for Engineers

1. **Video Processing Team**
   - Implement robust error handling for API failures
   - Develop quality assessment metrics
   - Create efficient video processing pipeline
   - Handle different aspect ratios and resolutions

2. **Integration Team**
   - Coordinate with Speech Agent for timing
   - Implement storage solution for generated videos
   - Create API endpoints for video status and retrieval
   - Handle concurrent generation requests

3. **Quality Assurance Team**
   - Develop automated quality checks
   - Create test suites for different scene types
   - Implement performance monitoring
   - Validate fallback mechanisms

4. **Frontend Team**
   - Create video preview component
   - Implement progress indicators
   - Handle video playback controls
   - Manage caching of generated videos

## Storage and Delivery

1. **Local Storage**
   ```
   /generated_video/
   ├── scene_1/
   │   ├── video.mp4
   │   └── metadata.json
   ├── scene_2/
   │   ├── video.mp4
   │   └── metadata.json
   └── temp/
   ```

2. **Cloud Storage (Future Implementation)**
   - AWS S3 or similar for scalability
   - CDN integration for delivery
   - Automatic cleanup of temporary files
   - Version control for regenerated videos 