# Story Agent Development Guide

## Overview
The Story Agent is a Layer 2 component in the agent system that processes manager agent output to generate story scenes and next-step recommendations. It operates as part of a larger pipeline where it receives structured data from the manager agent and produces story content that can be further processed by image and speech agents.

## System Position (from flowchart)
1. **Input Flow**:
   - Receives processed output from Manager Agent (Layer 1)
   - Accesses character profiles and conversation history from DB
   - Uses knowledge base for story context

2. **Output Flow**:
   - Generates story scene text
   - Provides next-step recommendations
   - Feeds into image and speech generation pipelines

## Dependencies

### Required Components
```python
from llm_factory import LLMFactory, BaseLLM
from config import LLMProvider, AgentType, LLM_CONFIG
from db_manager import DBManager  # For accessing character/story data
```

### Environment Variables
```env
GROQ_API_KEY=your_key_here
```

### Database Schema Requirements
```python
class Character:
    id: str
    name: str
    personality: str
    background: str
    speaking_style: str

class Story:
    id: str
    scenes: List[Scene]
    characters: List[Character]
    conversation_history: List[str]
```

## Input/Output Schema

### Input from Manager Agent
```python
manager_output = {
    "status": "success",
    "task_id": str,
    "tasks": [{
        "task_id": str,
        "task_type": "story",
        "content": {
            "user_input": str,
            "story_elements": str
        },
        "task_analysis": {
            "recommendations": str,
            "reasoning": str
        }
    }]
}
```

### Context from Database
```python
context = {
    "character_profiles": {
        "character_name": {
            "personality": str,
            "background": str,
            "speaking_style": str
        }
    },
    "conversation_history": List[str]
}
```

### Output Structure
```python
story_output = {
    "story_scene": str,      # Generated scene text (max 200 words)
    "options": List[str],    # 3 next-step recommendations
    "task_id": str,         # For tracking
    "timestamp": str        # ISO format timestamp
}
```

## Integration Guide

### 1. Basic Integration
```python
from story_agent import StoryAgent
from llm_factory import LLMFactory
from db_manager import DBManager

async def process_story(manager_output: Dict, db: DBManager):
    # Initialize story agent
    async with StoryAgent(LLMFactory()) as agent:
        # Get context from database
        context = await db.get_story_context(
            story_id=manager_output["story_id"]
        )
        
        # Process story
        result = await agent.process_manager_output(
            manager_output,
            context
        )
        
        return result
```

### 2. Pipeline Integration
```python
class StoryPipeline:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.llm_factory = LLMFactory()
    
    async def process_manager_output(self, manager_output: Dict):
        async with StoryAgent(self.llm_factory) as story_agent:
            # Get context
            context = await self.db.get_story_context(
                story_id=manager_output["story_id"]
            )
            
            # Generate story content
            story_result = await story_agent.process_manager_output(
                manager_output,
                context
            )
            
            # Store result
            await self.db.save_story_scene(story_result)
            
            return story_result
```

## Error Handling

1. **Input Validation**:
   - Manager output structure validation
   - Context data validation
   - API key verification

2. **Processing Errors**:
   - LLM API errors
   - JSON parsing errors
   - Context missing errors

3. **Resource Management**:
   - Async context manager for cleanup
   - Connection pooling
   - Rate limiting

## Testing Strategy

1. **Unit Tests**:
   - Input validation
   - Output structure
   - Error handling

2. **Integration Tests**:
   - Database integration
   - LLM API integration
   - Pipeline flow

3. **End-to-End Tests**:
   - Full pipeline testing
   - Error recovery
   - Performance testing

## Best Practices

1. **Performance**:
   - Use async/await for I/O operations
   - Implement connection pooling
   - Cache frequently used data

2. **Reliability**:
   - Implement retry mechanisms
   - Handle API rate limits
   - Log all operations

3. **Maintainability**:
   - Follow clean code principles
   - Document all public methods
   - Use type hints

## Monitoring and Logging

1. **Metrics to Track**:
   - Story generation time
   - API response times
   - Error rates
   - Character usage statistics

2. **Log Events**:
   - Input validation failures
   - API errors
   - Story generation events
   - Context loading issues

## Development Workflow

1. **Local Development**:
   ```bash
   # Set up environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Run tests
   pytest test_story_agent.py -v
   
   # Run example
   python story_agent.py
   ```

2. **Integration Testing**:
   ```bash
   # Test with database
   python -m pytest tests/integration/
   
   # Test full pipeline
   python -m pytest tests/e2e/
   ```

## Future Improvements

1. **Enhanced Context**:
   - Add scene memory
   - Implement character relationships
   - Add world-building elements

2. **Performance Optimization**:
   - Implement caching
   - Add batch processing
   - Optimize prompt length

3. **Quality Improvements**:
   - Add style consistency checks
   - Implement content filters
   - Add tone analysis 