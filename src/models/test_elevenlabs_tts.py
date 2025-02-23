import pytest
from io import BytesIO
import os
from unittest.mock import Mock, patch
from elevenlabs_tts import ElevenLabsTTS, ElevenLabsError
import unittest
from elevenlabs_tts import generate_couple_argument

@pytest.fixture
def tts_client():
    config = {
        "model_id": "test_model",
        "voice_id": "test_voice",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
    return ElevenLabsTTS(config)

@pytest.fixture
def mock_response():
    mock = Mock()
    mock.status_code = 200
    mock.content = b"mock_audio_data"
    return mock

# def test_init_without_api_key():
    # """Test initialization without API key should raise error"""
    # with patch.dict(os.environ, clear=True):  # Clear environment variables
    #     with pytest.raises(ElevenLabsError) as exc_info:
    #         ElevenLabsTTS({})  # Empty config, no environment variable
    #     assert "API key not found" in str(exc_info.value)

def test_init_with_config_api_key():
    """Test initialization with API key in config"""
    config = {
        "api_key": "sk_4a337e583ca66d032b4dce28896c9fb6ca643ac6f2bda752",
        "model_id": "test_model",
        "voice_id": "test_voice",
        "stability": 0.5,
        "similarity_boost": 0.75
    }
    client = ElevenLabsTTS(config)
    assert client.api_key == "sk_4a337e583ca66d032b4dce28896c9fb6ca643ac6f2bda752"

def test_init_with_env_api_key():
    """Test initialization with API key from environment"""
    with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "sk_4a337e583ca66d032b4dce28896c9fb6ca643ac6f2bda752"}):
        client = ElevenLabsTTS({})
        assert client.api_key == "sk_4a337e583ca66d032b4dce28896c9fb6ca643ac6f2bda752"

def test_init_with_config(tts_client):
    """Test initialization with valid config"""
    assert tts_client.model_id == "test_model"
    assert tts_client.voice_id == "test_voice"
    assert tts_client.stability == 0.5
    assert tts_client.similarity_boost == 0.75

def test_get_headers(tts_client):
    """Test header generation"""
    headers = tts_client.get_headers()
    assert "xi-api-key" in headers
    assert headers["Content-Type"] == "application/json"

def test_format_request(tts_client):
    """Test request formatting"""
    text = "Test text"
    request = tts_client.format_request(text)
    
    assert request["text"] == text
    assert request["model_id"] == "test_model"
    assert "voice_settings" in request
    assert request["voice_settings"]["stability"] == 0.5
    assert request["voice_settings"]["similarity_boost"] == 0.75

@patch('requests.post')
def test_text_to_speech_success(mock_post, tts_client, mock_response):
    """Test successful text-to-speech conversion"""
    mock_post.return_value = mock_response
    
    # Test without output path
    result = tts_client.text_to_speech("Test text")
    assert isinstance(result, BytesIO)
    assert result.getvalue() == b"mock_audio_data"
    
    # Test with output path
    with patch('builtins.open', create=True) as mock_open:
        result = tts_client.text_to_speech("Test text", output_path="test.mp3")
        assert result is None
        mock_open.assert_called_once_with("test.mp3", "wb")

@patch('requests.post')
def test_text_to_speech_api_error(mock_post, tts_client):
    """Test API error handling"""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response
    
    with pytest.raises(ElevenLabsError) as exc_info:
        tts_client.text_to_speech("Test text")
    assert "API request failed" in str(exc_info.value)

@patch('requests.post')
def test_text_to_speech_with_custom_params(mock_post, tts_client, mock_response):
    """Test text-to-speech with custom parameters"""
    mock_post.return_value = mock_response
    
    custom_params = {
        "voice_id": "custom_voice",
        "stability": 0.8,
        "similarity_boost": 0.9
    }
    
    tts_client.text_to_speech("Test text", **custom_params)
    
    # Verify the custom parameters were used
    called_args = mock_post.call_args
    assert "custom_voice" in called_args[0][0]  # URL contains custom voice ID
    assert called_args[1]["json"]["voice_settings"]["stability"] == 0.8
    assert called_args[1]["json"]["voice_settings"]["similarity_boost"] == 0.9

@patch('requests.get')
def test_get_available_voices_success(mock_get, tts_client):
    """Test successful retrieval of available voices"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"voices": ["voice1", "voice2"]}
    mock_get.return_value = mock_response
    
    result = tts_client.get_available_voices()
    assert "voices" in result
    assert result["voices"] == ["voice1", "voice2"]

@patch('requests.get')
def test_get_available_voices_error(mock_get, tts_client):
    """Test error handling in get_available_voices"""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_get.return_value = mock_response
    
    with pytest.raises(ElevenLabsError) as exc_info:
        tts_client.get_available_voices()
    assert "Failed to get voices" in str(exc_info.value)

class TestElevenLabsTTS(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "model_id": "eleven_multilingual_v2",
            "stability": 0.5,
            "similarity_boost": 0.75
        }
        self.tts_client = ElevenLabsTTS(self.config)
        self.test_output_dir = "test_outputs"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.test_output_dir):
            os.makedirs(self.test_output_dir)

    def test_generate_couple_argument(self):
        """Test generating a couple's argument audio"""
        output_path = os.path.join(self.test_output_dir, "test_couple_argument.mp3")
        
        try:
            # Generate the argument audio
            generate_couple_argument(self.tts_client, output_path)
            
            # Check if file was created
            self.assertTrue(os.path.exists(output_path))
            
            # Check if file has content
            self.assertGreater(os.path.getsize(output_path), 0)
            
            print(f"\nArgument audio generated successfully at: {output_path}")
            
        except Exception as e:
            self.fail(f"Failed to generate couple argument: {str(e)}")

    def test_individual_voice_generation(self):
        """Test generating individual voice lines"""
        test_lines = [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Josh
                "text": "This is a test for the male voice.",
                "output": "male_test.mp3"
            },
            {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Rachel
                "text": "This is a test for the female voice.",
                "output": "female_test.mp3"
            }
        ]

        for line in test_lines:
            output_path = os.path.join(self.test_output_dir, line["output"])
            
            try:
                # Generate speech for each test line
                audio_data = self.tts_client.text_to_speech(
                    text=line["text"],
                    voice_id=line["voice_id"]
                )
                
                # Save the audio
                with open(output_path, 'wb') as f:
                    f.write(audio_data.getvalue())
                
                # Verify file creation
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
                
                print(f"\nTest audio generated successfully at: {output_path}")
                
            except Exception as e:
                self.fail(f"Failed to generate test audio for {line['output']}: {str(e)}")

if __name__ == '__main__':
    unittest.main() 