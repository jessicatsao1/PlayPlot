import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, create_autospec, patch
from story_agent import StoryAgent, StoryOutput, StoryValidationError
from llm_factory import LLMFactory, BaseLLM

# Test class to group related tests
class TestStoryAgent:
    @pytest.fixture
    def mock_llm_factory(self):
        # Create a mock LLM instance
        mock_llm = Mock(spec=BaseLLM)
        mock_llm.generate = AsyncMock()
        
        # Create a mock factory with create_llm method
        mock_factory = Mock(spec=LLMFactory)
        mock_factory.create_llm = Mock(return_value=mock_llm)
        mock_factory.get_llm = Mock(return_value=mock_llm)
        
        return mock_factory

    @pytest.fixture
    def story_agent(self, mock_llm_factory):
        return StoryAgent(mock_llm_factory)

    @pytest.fixture
    def valid_manager_output(self):
        return {
            "status": "success",
            "task_id": "test-task-123",
            "tasks": [
                {
                    "task_id": "story-task-123",
                    "task_type": "story",
                    "content": {
                        "user_input": "Create a scene with John and Mary discussing a secret.",
                        "story_elements": "Setting: Library, Characters: John (nervous), Mary (curious)"
                    },
                    "task_analysis": {
                        "recommendations": "Focus on tension and dialogue",
                        "reasoning": "Build suspense through character interaction"
                    }
                }
            ]
        }

    @pytest.fixture
    def example_context(self):
        return {
            "character_profiles": {
                "John": {
                    "personality": "Reserved and cautious",
                    "background": "Librarian",
                    "speaking_style": "Formal and precise"
                },
                "Mary": {
                    "personality": "Curious and direct",
                    "background": "Journalist",
                    "speaking_style": "Engaging and inquisitive"
                }
            },
            "conversation_history": [
                "John found an unusual manuscript.",
                "Mary noticed his strange behavior."
            ]
        }

    @pytest.fixture
    def valid_llm_response(self):
        return {
            "content": json.dumps({
                "story_scene": "John nervously adjusted his glasses as Mary approached...",
                "options": [
                    "Mary discovers the manuscript's hidden message",
                    "John reveals why he's been acting strange",
                    "An unexpected visitor interrupts their conversation"
                ]
            })
        }

    # Test Initialization and Configuration
    def test_initialization(self, story_agent, mock_llm_factory):
        """Test proper agent initialization with config"""
        assert story_agent.llm_factory == mock_llm_factory
        assert isinstance(story_agent.llm, Mock)
        assert story_agent.llm.generate.called is False

    @pytest.mark.asyncio
    async def test_context_manager(self, story_agent):
        """Test async context manager functionality"""
        async with story_agent as agent:
            assert agent == story_agent
        # Verify cleanup
        if hasattr(story_agent.llm, 'close'):
            assert story_agent.llm.close.called

    # Test Input Validation
    @pytest.mark.parametrize("invalid_output", [
        {"status": "success"},  # Missing fields
        {"status": "error", "task_id": "123", "tasks": []},  # Wrong status
        {"status": "success", "task_id": "123", "tasks": [{"task_type": "image"}]},  # No story task
        {"status": "success", "task_id": "123", "tasks": [{"task_type": "story", "task_id": "123"}]},  # Missing content
    ])
    def test_validate_manager_output_failures(self, story_agent, invalid_output):
        """Test various invalid manager output scenarios"""
        with pytest.raises(StoryValidationError):
            story_agent.validate_manager_output(invalid_output)

    def test_extract_story_elements_complete(self, story_agent, valid_manager_output):
        """Test extraction of all story elements"""
        elements = story_agent.extract_story_elements(valid_manager_output["tasks"][0])
        assert all(key in elements for key in ["user_input", "story_elements", "recommendations", "reasoning"])
        assert all(elements.values())  # All values should be non-empty

    def test_extract_story_elements_missing_fields(self, story_agent):
        """Test extraction with missing fields"""
        task = {
            "content": {"user_input": "test"},
            "task_analysis": {}
        }
        elements = story_agent.extract_story_elements(task)
        assert elements["user_input"] == "test"
        assert elements["story_elements"] == ""
        assert elements["recommendations"] == ""
        assert elements["reasoning"] == ""

    # Test LLM Integration
    @pytest.mark.asyncio
    async def test_generate_story_and_options_success(self, story_agent, example_context, valid_llm_response):
        """Test successful story generation"""
        story_elements = {
            "user_input": "Test scene",
            "story_elements": "Test elements",
            "recommendations": "Test recommendations",
            "reasoning": "Test reasoning"
        }
        
        story_agent.llm.generate.return_value = valid_llm_response
        result = await story_agent.generate_story_and_options(story_elements, example_context)
        
        assert isinstance(result, dict)
        assert "story_scene" in result
        assert "options" in result
        assert len(result["options"]) == 3
        assert story_agent.llm.generate.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_response", [
        {"content": "not json"},
        {"content": json.dumps({"story_scene": "test"})},  # Missing options
        {"content": json.dumps({"options": []})},  # Missing story_scene
        {"content": json.dumps({"story_scene": "test", "options": ["one", "two"]})},  # Wrong number of options
    ])
    async def test_generate_story_and_options_invalid_responses(self, story_agent, example_context, invalid_response):
        """Test handling of various invalid LLM responses"""
        story_elements = {
            "user_input": "Test scene",
            "story_elements": "Test elements",
            "recommendations": "Test recommendations",
            "reasoning": "Test reasoning"
        }
        
        story_agent.llm.generate.return_value = invalid_response
        with pytest.raises(StoryValidationError):
            await story_agent.generate_story_and_options(story_elements, example_context)

    # Test End-to-End Processing
    @pytest.mark.asyncio
    async def test_process_manager_output_success(self, story_agent, valid_manager_output, example_context, valid_llm_response):
        """Test successful end-to-end processing"""
        story_agent.llm.generate.return_value = valid_llm_response
        result = await story_agent.process_manager_output(valid_manager_output, example_context)
        
        assert isinstance(result, StoryOutput)
        assert result.story_scene
        assert len(result.options) == 3
        assert result.task_id == "story-task-123"
        assert isinstance(result.timestamp, str)

    @pytest.mark.asyncio
    async def test_process_manager_output_with_empty_context(self, story_agent, valid_manager_output, valid_llm_response):
        """Test processing with empty context"""
        story_agent.llm.generate.return_value = valid_llm_response
        result = await story_agent.process_manager_output(valid_manager_output)
        assert isinstance(result, StoryOutput)

    # Test Error Handling
    @pytest.mark.asyncio
    async def test_llm_error_handling(self, story_agent, valid_manager_output, example_context):
        """Test handling of LLM errors"""
        story_agent.llm.generate.side_effect = Exception("LLM API Error")
        with pytest.raises(StoryValidationError) as exc_info:
            await story_agent.process_manager_output(valid_manager_output, example_context)
        assert "LLM API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_json_parsing_error_handling(self, story_agent, valid_manager_output, example_context):
        """Test handling of JSON parsing errors"""
        story_agent.llm.generate.return_value = {"content": "Invalid JSON {"}
        with pytest.raises(StoryValidationError) as exc_info:
            await story_agent.process_manager_output(valid_manager_output, example_context)
        assert "Failed to parse LLM response as JSON" in str(exc_info.value)

    # Test Resource Management
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, story_agent):
        """Test proper resource cleanup"""
        async with story_agent as agent:
            pass
        if hasattr(story_agent.llm, 'close'):
            story_agent.llm.close.assert_called_once()

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__]) 