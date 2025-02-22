import pytest
from unittest.mock import Mock, patch
from src.models.elevenlabs_tts import ElevenLabsTTS
from test_dog_sounds import find_voice_by_description

@pytest.fixture
def tts_client():
    return ElevenLabsTTS({
        "model_id": "eleven_multilingual_v2"
    })

@pytest.fixture
def mock_successful_response():
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "voice_id": "test_voice_id",
        "name": "Generated Voice",
        "settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    return mock

@pytest.fixture
def mock_failed_response():
    mock = Mock()
    mock.status_code = 404
    return mock

def test_find_voice_by_description_success(tts_client, mock_successful_response):
    """Test successful voice generation from description"""
    with patch('requests.post', return_value=mock_successful_response):
        description = "A deep, gruff male voice that sounds like a large dog"
        result = find_voice_by_description(tts_client, description)
        
        assert result is not None
        assert result["voice_id"] == "test_voice_id"
        assert result["name"] == "Generated Voice"
        assert "settings" in result

def test_find_voice_by_description_failure(tts_client, mock_failed_response):
    """Test failed voice generation"""
    with patch('requests.post', return_value=mock_failed_response):
        description = "Invalid description"
        result = find_voice_by_description(tts_client, description)
        
        assert result is None

def test_find_voice_by_description_exception(tts_client):
    """Test exception handling"""
    with patch('requests.post', side_effect=Exception("API Error")):
        description = "Test description"
        result = find_voice_by_description(tts_client, description)
        
        assert result is None

def test_find_voice_by_description_request_params(tts_client, mock_successful_response):
    """Test that correct parameters are sent to the API"""
    with patch('requests.post', return_value=mock_successful_response) as mock_post:
        description = "Test voice description"
        find_voice_by_description(tts_client, description)
        
        # Verify the API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        # Check URL
        assert args[0] == f"{tts_client.base_url}/voice-lab/generate"
        
        # Check headers
        assert kwargs["headers"] == tts_client.get_headers()
        
        # Check request body
        assert kwargs["json"] == {
            "description": description,
            "name": "Generated Voice"
        }

def test_find_voice_by_description_empty_description(tts_client, mock_successful_response):
    """Test with empty description"""
    with patch('requests.post', return_value=mock_successful_response):
        result = find_voice_by_description(tts_client, "")
        assert result is not None  # API might still return a default voice

def test_find_voice_by_description_long_description(tts_client, mock_successful_response):
    """Test with a very long description"""
    long_description = "A " + "very " * 100 + "long description"
    with patch('requests.post', return_value=mock_successful_response):
        result = find_voice_by_description(tts_client, long_description)
        assert result is not None 