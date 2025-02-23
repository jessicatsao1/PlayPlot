# Layer 2 Agent Development Guide

## Overview

This document outlines the development specifications for Layer 2 (Worker) agents in our system. Layer 2 agents are specialized content generation agents that receive tasks from the Layer 1 Manager Agent.

## Agent Types

1. Story Agent
2. Image Agent
3. Speech Agent
4. Video Agent

## Input Schema from Layer 1 Manager

### Base Task Schema
```typescript
interface BaseTask {
  task_id: string;
  task_type: "story" | "image" | "speech" | "video";
  reasoning: {
    analysis: string;
    key_points: string[];
    suggestions: string[];
  };
  context: {
    story_id?: string;
    scene_id?: string;
    user_request: string;
    characters?: Character[];
    previous_scenes?: Scene[];
  };
  requirements: {
    guidelines: string[];
    style: StylePreferences;
    constraints: string[];
  };
}
```

### Story Task Schema
```typescript
interface StoryTask extends BaseTask {
  task_type: "story";
  content_type: "scene" | "dialogue" | "description";
  context: {
    story_id: string;
    characters: Character[];
    previous_scenes: Scene[];
    scene_number: number;
    story_context: string;
  };
  parameters: {
    tone?: string;
    genre?: string;
    style_preferences?: StylePreferences;
    next_actions?: string[];
  };
}
```

### Image Task Schema
```typescript
interface ImageTask extends BaseTask {
  task_type: "image";
  scene_description: string;
  style: string;
  context: {
    story_id: string;
    scene_id: string;
    characters: Character[];
  };
  parameters: {
    lora_model?: string;
    negative_prompt?: string;
    reference_images?: string[];
  };
}
```

### Speech Task Schema
```typescript
interface SpeechTask extends BaseTask {
  task_type: "speech";
  text: string;
  voice_id: string;
  emotion: string;
  context: {
    character_id: string;
    scene_id: string;
  };
  parameters: {
    speed?: number;
    pitch?: number;
    background_music?: string;
  };
}
```

### Video Task Schema
```typescript
interface VideoTask extends BaseTask {
  task_type: "video";
  scene_description: string;
  duration: number;
  style: string;
  context: {
    story_id: string;
    scene_id: string;
    characters: Character[];
    source_image?: string;  // For image-to-video
    source_text?: string;   // For text-to-video
  };
  parameters: {
    fps?: number;
    resolution?: string;
    transitions?: string[];
    background_music?: string;
    special_effects?: SpecialEffect[];
  };
}
```

## Layer 2 Agent Implementation Requirements

### Base Worker Agent
```python
class WorkerAgent:
    """Base class for all Layer 2 agents"""
    
    async def execute_task(self, task_definition: Dict) -> Dict:
        """
        Main execution method all agents must implement
        """
        try:
            # 1. Validate input schema
            self.validate_input_schema(task_definition)
            
            # 2. Process task with reasoning
            content = await self.generate_content_with_reasoning(
                task_definition["reasoning"],
                task_definition["context"],
                task_definition["parameters"]
            )
            
            # 3. Validate output
            result = self.format_result(content, task_definition)
            self.validate_output_schema(result)
            
            return result
            
        except Exception as e:
            return self.create_error_response(e, task_definition)
```

### Story Agent Requirements

1. **Responsibilities**:
   - Generate coherent story content based on context
   - Maintain character consistency
   - Follow style and tone guidelines
   - Generate visual descriptions for image generation
   - Structure dialogue for speech synthesis

2. **Implementation Focus**:
   ```python
   class StoryAgent(WorkerAgent):
       primary_model = "groq/llama-3.3-70b"
       fallback_model = "mistral/mistral-7b"
       
       async def generate_content_with_reasoning(
           self,
           reasoning: Dict,
           context: Dict,
           parameters: Dict
       ) -> Dict:
           # Implement story generation logic
           pass
   ```

### Image Agent Requirements

1. **Responsibilities**:
   - Generate stable diffusion prompts
   - Handle LoRA model selection
   - Process visual style requirements
   - Generate consistent character appearances
   - Handle image variations

2. **Implementation Focus**:
   ```python
   class ImageAgent(WorkerAgent):
       primary_model = "groq/llama-3.3-70b"
       fallback_model = "mistral/mistral-7b"
       
       async def generate_content_with_reasoning(
           self,
           reasoning: Dict,
           context: Dict,
           parameters: Dict
       ) -> Dict:
           # Implement image generation logic
           pass
   ```

### Speech Agent Requirements

1. **Responsibilities**:
   - Process text for speech synthesis
   - Handle voice emotion mapping
   - Manage voice ID selection
   - Process speech parameters
   - Handle background music integration

2. **Implementation Focus**:
   ```python
   class SpeechAgent(WorkerAgent):
       primary_model = "groq/llama-3.3-70b"
       fallback_model = "mistral/mistral-7b"
       
       async def generate_content_with_reasoning(
           self,
           reasoning: Dict,
           context: Dict,
           parameters: Dict
       ) -> Dict:
           # Implement speech generation logic
           pass
   ```

### Video Agent Requirements

1. **Responsibilities**:
   - Handle both image-to-video and text-to-video
   - Process scene transitions
   - Manage video duration and FPS
   - Handle special effects
   - Generate preview thumbnails and GIFs

2. **Implementation Focus**:
   ```python
   class VideoAgent(WorkerAgent):
       provider = "fal.ai"
       
       async def generate_content_with_reasoning(
           self,
           reasoning: Dict,
           context: Dict,
           parameters: Dict
       ) -> Dict:
           # Implement video generation logic
           pass
   ```

## Output Schema Requirements

### Story Output
```typescript
interface StoryOutput {
  task_id: string;
  content: string;
  scene_type: string;
  characters: Character[];
  metadata: {
    scene_number: number;
    word_count: number;
    tone: string;
  };
  visual_description?: string;
  dialogue_sections?: DialogueSection[];
  suggested_next_scenes?: string[];
}
```

### Image Output
```typescript
interface ImageOutput {
  task_id: string;
  image_url: string;
  prompt_used: string;
  metadata: {
    model: string;
    size: string;
    seed: number;
  };
}
```

### Speech Output
```typescript
interface SpeechOutput {
  task_id: string;
  audio_url: string;
  duration: number;
  metadata: {
    voice_id: string;
    emotion: string;
  };
  waveform_data?: number[];
}
```

### Video Output
```typescript
interface VideoOutput {
  task_id: string;
  video_url: string;
  thumbnail_url: string;
  duration: number;
  metadata: {
    model: string;
    resolution: string;
    fps: number;
    file_size: number;
  };
  preview_gif?: string;
  chapters?: VideoChapter[];
}
```

## Inter-Agent Data Flow

### Story Agent Output for Downstream Agents
```typescript
interface EnhancedStoryOutput {
  task_id: string;
  content: string;
  scene_type: string;
  characters: Character[];
  metadata: {
    scene_number: number;
    word_count: number;
    tone: string;
    emotional_context: string;
    setting_description: string;
  };
  visual_elements: {
    scene_description: string;
    character_descriptions: CharacterVisual[];
    key_moments: VisualMoment[];
    style_guidelines: string[];
    lighting: string;
    camera_angle?: string;
  };
  dialogue_elements: {
    sections: DialogueSection[];
    background_ambience: string;
    tone: string;
    emotional_markers: EmotionMarker[];
    character_voices: CharacterVoice[];
  };
  suggested_next_scenes?: string[];
}

interface CharacterVisual {
  character_id: string;
  name: string;
  appearance: string;
  pose: string;
  expression: string;
  clothing: string;
  distinguishing_features: string[];
}

interface VisualMoment {
  timestamp: number;
  description: string;
  focal_point: string;
  characters_involved: string[];
  action: string;
  emotional_tone: string;
}

interface DialogueSection {
  speaker_id: string;
  speaker_name: string;
  text: string;
  emotion: string;
  intensity: number;
  timing: {
    pause_before?: number;
    speaking_rate: number;
    emphasis_words: string[];
  };
}

interface EmotionMarker {
  timestamp: number;
  emotion: string;
  intensity: number;
  character_id: string;
}

interface CharacterVoice {
  character_id: string;
  voice_id: string;
  base_pitch: number;
  base_speed: number;
  emotion_mapping: {
    [emotion: string]: {
      pitch_adjustment: number;
      speed_adjustment: number;
      intensity_factor: number;
    };
  };
}
```

### Layer 1 Manager Analysis Output
```typescript
interface ManagerAnalysis {
  story_context: {
    current_arc: string;
    emotional_trajectory: string;
    key_themes: string[];
    active_plotlines: PlotLine[];
  };
  scene_analysis: {
    purpose: string;
    emotional_goals: string[];
    character_development: CharacterArc[];
    pacing: string;
    tension_level: number;
  };
  visual_direction: {
    style_reference: string;
    mood_board: string[];
    color_palette: string[];
    visual_focus: string[];
  };
  audio_direction: {
    emotional_landscape: string;
    sound_design_notes: string[];
    music_suggestions: string[];
    voice_direction: string;
  };
}

interface PlotLine {
  id: string;
  description: string;
  status: "active" | "resolved" | "developing";
  involved_characters: string[];
  tension_points: string[];
}

interface CharacterArc {
  character_id: string;
  current_state: string;
  development_goal: string;
  emotional_state: string;
  relationship_dynamics: {
    [character_id: string]: string;
  };
}
```

### Processing Flow

1. **Layer 1 Manager to Story Agent**:
```typescript
interface StoryAgentInput extends BaseTask {
  manager_analysis: ManagerAnalysis;
  story_requirements: {
    word_count: number;
    pacing: string;
    focus_character?: string;
    required_plot_points: string[];
  };
}
```

2. **Story Agent to Image Agent**:
```typescript
interface ImageAgentInput extends BaseTask {
  story_output: EnhancedStoryOutput;
  visual_requirements: {
    target_resolution: string;
    style_reference: string;
    focus_elements: string[];
    required_characters: string[];
  };
}
```

3. **Story Agent to Speech Agent**:
```typescript
interface SpeechAgentInput extends BaseTask {
  story_output: EnhancedStoryOutput;
  audio_requirements: {
    target_duration: number;
    background_music: boolean;
    emotion_intensity: number;
    voice_requirements: VoiceRequirement[];
  };
}
```

### Implementation Example for Story Agent
```python
class StoryAgent(WorkerAgent):
    primary_model = "groq/llama-3.3-70b"
    fallback_model = "mistral/mistral-7b"
    
    async def generate_content_with_reasoning(
        self,
        reasoning: Dict,
        context: Dict,
        parameters: Dict
    ) -> EnhancedStoryOutput:
        try:
            # 1. Process manager analysis
            scene_requirements = self.process_manager_analysis(
                reasoning["manager_analysis"]
            )
            
            # 2. Generate core story content
            story_content = await self.generate_story_content(
                scene_requirements,
                context,
                parameters
            )
            
            # 3. Generate visual elements
            visual_elements = await self.generate_visual_elements(
                story_content,
                scene_requirements
            )
            
            # 4. Generate dialogue elements
            dialogue_elements = await self.generate_dialogue_elements(
                story_content,
                scene_requirements
            )
            
            # 5. Compile enhanced output
            return {
                "task_id": context["task_id"],
                "content": story_content["text"],
                "scene_type": story_content["type"],
                "characters": story_content["characters"],
                "metadata": self.generate_metadata(story_content),
                "visual_elements": visual_elements,
                "dialogue_elements": dialogue_elements,
                "suggested_next_scenes": story_content["next_scenes"]
            }
            
        except Exception as e:
            logger.error(f"Story generation failed: {str(e)}")
            raise StoryGenerationError(str(e))
    
    async def generate_visual_elements(
        self,
        story_content: Dict,
        requirements: Dict
    ) -> Dict:
        """
        Generate detailed visual elements for Image Agent
        """
        # Implementation here
        pass
    
    async def generate_dialogue_elements(
        self,
        story_content: Dict,
        requirements: Dict
    ) -> Dict:
        """
        Generate detailed dialogue elements for Speech Agent
        """
        # Implementation here
        pass
```

## Error Handling Requirements

Each agent must implement:
1. Input validation
2. Model fallback strategy
3. Retry logic for API calls
4. Standardized error responses

```python
def create_error_response(self, error: Exception, task: Dict) -> Dict:
    return {
        "status": "error",
        "task_id": task["task_id"],
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
            "timestamp": time.time()
        }
    }
```

## Testing Requirements

Each agent should have:
1. Unit tests for schema validation
2. Integration tests with APIs
3. Error handling tests
4. Performance benchmarks

## API Keys and Configuration

Required environment variables:
```env
GROQ_API_KEY=your_groq_key
MISTRAL_API_KEY=your_mistral_key
ELEVENLABS_API_KEY=your_elevenlabs_key
FAL_API_KEY=your_fal_key
```

## Development Steps

1. Implement base `WorkerAgent` class
2. Implement schema validation
3. Implement model fallback strategy
4. Develop agent-specific logic
5. Add error handling
6. Write tests
7. Document API endpoints

## Performance Guidelines

1. Maximum response times:
   - Story: 180 seconds
   - Image: 30 seconds
   - Speech: 60 seconds
   - Video: 300 seconds

2. Retry Configuration:
   - Max retries: 3
   - Backoff: Exponential
   - Timeout: Varies by agent

## Monitoring Requirements

Each agent should track:
1. Response times
2. Success/failure rates
3. Model fallback frequency
4. Resource usage
5. API quota usage 