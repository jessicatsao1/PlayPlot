import pytest
import json
from unittest.mock import Mock, patch
from src.models.llm_client import (
    DialogueAnalysis,
    GroqLLMClient,
    MistralLLMClient,
    # OpenAILLMClient,  # Commented out
    BaseLLMClient,
    LLMClient  # Add this for backward compatibility tests
)

# Test data
TEST_SCENE = """
John looked at Mary with concern. "Are you sure about this?" he asked.
"Absolutely," Mary replied confidently. "We have to try."
"""

EXPECTED_DIALOGUE_ANALYSIS = [
    {
        "text": "Are you sure about this?",
        "speaker": "John",
        "emotion": "concerned",
        "context": "looked at Mary with concern",
        "tone": "normal",
        "intensity": 0.6
    },
    {
        "text": "Absolutely. We have to try.",
        "speaker": "Mary",
        "emotion": "confident",
        "context": "replied confidently",
        "tone": "normal",
        "intensity": 0.8
    }
]

EXPECTED_VOICE_RECOMMENDATIONS = {
    "John": {
        "stability": 0.7,
        "speaking_rate": 0.9,
        "similarity_boost": 0.75
    },
    "Mary": {
        "stability": 0.8,
        "speaking_rate": 1.1,
        "similarity_boost": 0.7
    }
}

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data

# class MockOpenAIResponse:  # Commented out
#     def __init__(self, content):
#         self.choices = [Mock(message=Mock(content=content))]

@pytest.fixture
def mock_requests():
    with patch('requests.post') as mock_post:
        mock_post.return_value = MockResponse({
            "choices": [{
                "message": {
                    "content": json.dumps(EXPECTED_DIALOGUE_ANALYSIS)
                }
            }]
        })
        yield mock_post

# @pytest.fixture  # Commented out
# def mock_openai_client():
#     with patch('openai.OpenAI') as mock_openai:
#         client = Mock()
#         client.chat.completions.create.return_value = MockOpenAIResponse(
#             json.dumps(EXPECTED_DIALOGUE_ANALYSIS)
#         )
#         mock_openai.return_value = client
#         yield mock_openai

def test_dialogue_analysis_model():
    """Test DialogueAnalysis Pydantic model"""
    data = EXPECTED_DIALOGUE_ANALYSIS[0]
    analysis = DialogueAnalysis(**data)
    
    assert analysis.text == data["text"]
    assert analysis.speaker == data["speaker"]
    assert analysis.emotion == data["emotion"]
    assert analysis.context == data["context"]
    assert analysis.tone == data["tone"]
    assert analysis.intensity == data["intensity"]

# Groq Tests
def test_groq_analyze_dialogue(mock_requests):
    """Test Groq dialogue analysis"""
    client = GroqLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    assert len(result) == 2
    assert isinstance(result[0], DialogueAnalysis)
    assert result[0].speaker == "John"
    assert result[1].speaker == "Mary"

def test_groq_generate_voice_recommendations(mock_requests):
    """Test Groq voice recommendations"""
    mock_requests.return_value = MockResponse({
        "choices": [{
            "message": {
                "content": json.dumps(EXPECTED_VOICE_RECOMMENDATIONS)
            }
        }]
    })
    
    client = GroqLLMClient(api_key="test_key")
    dialogue_analysis = [DialogueAnalysis(**data) for data in EXPECTED_DIALOGUE_ANALYSIS]
    result = client.generate_voice_recommendations(dialogue_analysis)
    
    assert "John" in result
    assert "Mary" in result
    assert result["John"]["speaking_rate"] == 0.9
    assert result["Mary"]["stability"] == 0.8

def test_groq_fallback_on_error(mock_requests):
    """Test Groq fallback mechanism on API error"""
    mock_requests.return_value = MockResponse({"error": "API Error"}, status_code=500)
    
    client = GroqLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    # Should fall back to rule-based analysis
    assert len(result) > 0
    assert isinstance(result[0], DialogueAnalysis)
    assert result[0].text == "Are you sure about this?"

# Mistral Tests
def test_mistral_analyze_dialogue(mock_requests):
    """Test Mistral dialogue analysis"""
    client = MistralLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    assert len(result) == 2
    assert isinstance(result[0], DialogueAnalysis)
    assert result[0].speaker == "John"
    assert result[1].speaker == "Mary"

def test_mistral_generate_voice_recommendations(mock_requests):
    """Test Mistral voice recommendations"""
    mock_requests.return_value = MockResponse({
        "choices": [{
            "message": {
                "content": json.dumps(EXPECTED_VOICE_RECOMMENDATIONS)
            }
        }]
    })
    
    client = MistralLLMClient(api_key="test_key")
    dialogue_analysis = [DialogueAnalysis(**data) for data in EXPECTED_DIALOGUE_ANALYSIS]
    result = client.generate_voice_recommendations(dialogue_analysis)
    
    assert "John" in result
    assert "Mary" in result
    assert result["John"]["speaking_rate"] == 0.9
    assert result["Mary"]["stability"] == 0.8

def test_mistral_fallback_on_error(mock_requests):
    """Test Mistral fallback mechanism on API error"""
    mock_requests.return_value = MockResponse({"error": "API Error"}, status_code=500)
    
    client = MistralLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    # Should fall back to rule-based analysis
    assert len(result) > 0
    assert isinstance(result[0], DialogueAnalysis)
    assert result[0].text == "Are you sure about this?"

# OpenAI Tests  # Commented out
# def test_openai_analyze_dialogue(mock_openai_client):
#     """Test OpenAI dialogue analysis"""
#     client = OpenAILLMClient(api_key="test_key")
#     result = client.analyze_dialogue(TEST_SCENE)
#     
#     assert len(result) == 2
#     assert isinstance(result[0], DialogueAnalysis)
#     assert result[0].speaker == "John"
#     assert result[1].speaker == "Mary"
# 
# def test_openai_generate_voice_recommendations(mock_openai_client):
#     """Test OpenAI voice recommendations"""
#     mock_openai_client.return_value.chat.completions.create.return_value = MockOpenAIResponse(
#         json.dumps(EXPECTED_VOICE_RECOMMENDATIONS)
#     )
#     
#     client = OpenAILLMClient(api_key="test_key")
#     dialogue_analysis = [DialogueAnalysis(**data) for data in EXPECTED_DIALOGUE_ANALYSIS]
#     result = client.generate_voice_recommendations(dialogue_analysis)
#     
#     assert "John" in result
#     assert "Mary" in result
#     assert result["John"]["speaking_rate"] == 0.9
#     assert result["Mary"]["stability"] == 0.8
# 
# def test_openai_fallback_on_error(mock_openai_client):
#     """Test OpenAI fallback mechanism on API error"""
#     mock_openai_client.return_value.chat.completions.create.side_effect = Exception("API Error")
#     
#     client = OpenAILLMClient(api_key="test_key")
#     result = client.analyze_dialogue(TEST_SCENE)
#     
#     # Should fall back to rule-based analysis
#     assert len(result) > 0
#     assert isinstance(result[0], DialogueAnalysis)
#     assert result[0].text == "Are you sure about this?"

# Fallback Tests
def test_fallback_dialogue_extraction():
    """Test the fallback dialogue extraction directly"""
    client = GroqLLMClient(api_key="test_key")  # Using Groq client for base functionality
    result = client._extract_dialogue_fallback(TEST_SCENE)
    
    assert len(result) == 2
    assert result[0].text == "Are you sure about this?"
    assert result[0].speaker == "John"
    assert result[1].text == "Absolutely. We have to try."
    assert result[1].speaker == "Mary"

def test_fallback_voice_recommendations():
    """Test the fallback voice recommendations directly"""
    client = GroqLLMClient(api_key="test_key")
    dialogue_analysis = [DialogueAnalysis(**data) for data in EXPECTED_DIALOGUE_ANALYSIS]
    result = client._get_voice_recommendations_fallback(dialogue_analysis)
    
    assert "John" in result
    assert "Mary" in result
    assert 0.0 <= result["John"]["stability"] <= 1.0
    assert 0.5 <= result["John"]["speaking_rate"] <= 2.0

def test_invalid_json_response(mock_requests):
    """Test handling of invalid JSON response"""
    mock_requests.return_value = MockResponse({
        "choices": [{
            "message": {
                "content": "Invalid JSON response"
            }
        }]
    })
    
    client = GroqLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    # Should fall back to rule-based analysis
    assert len(result) > 0
    assert isinstance(result[0], DialogueAnalysis)

def test_quota_exceeded_handling(mock_requests):
    """Test handling of quota exceeded error"""
    mock_requests.return_value = MockResponse(
        {"error": "insufficient_quota"},
        status_code=429
    )
    
    client = GroqLLMClient(api_key="test_key")
    result = client.analyze_dialogue(TEST_SCENE)
    
    # Should fall back to rule-based analysis
    assert len(result) > 0
    assert isinstance(result[0], DialogueAnalysis)

# Test backward compatibility
def test_default_llm_client():
    """Test that default LLMClient is now GroqLLMClient"""
    client = LLMClient(api_key="test_key")
    assert isinstance(client, GroqLLMClient) 