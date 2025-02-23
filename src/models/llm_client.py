from typing import Dict, List, Any, Optional
import json
import os
from abc import ABC, abstractmethod
import requests
from pydantic import BaseModel, Field

class DialogueAnalysis(BaseModel):
    text: str
    speaker: str
    emotion: str
    context: str
    tone: Optional[str] = None
    intensity: Optional[float] = None
    start_time: float = 0.0  # Start time in seconds
    duration: float = 0.0    # Duration in seconds

class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    MAX_TOTAL_DURATION = 5.0  # Maximum total duration in seconds
    
    def _estimate_duration(self, text: str, speaking_rate: float = 1.0) -> float:
        """Estimate duration of spoken text in seconds.
        Based on average speaking rate of 150 words per minute.
        """
        words = len(text.split())
        # 150 words/minute = 2.5 words/second at rate 1.0
        return (words / 2.5) / speaking_rate

    def _extract_dialogue_fallback(self, scene_content: str) -> List[DialogueAnalysis]:
        """Simple rule-based dialogue extraction as fallback"""
        dialogue_segments = []
        current_time = 0.0
        lines = scene_content.split('\n')
        
        for line in lines:
            if '"' not in line or current_time >= self.MAX_TOTAL_DURATION:
                continue
                
            # Extract quoted text
            quote_start = line.find('"')
            quote_end = line.find('"', quote_start + 1)
            if quote_end == -1:
                continue
                
            text = line[quote_start + 1:quote_end]
            
            # Estimate duration and skip if it would exceed limit
            estimated_duration = self._estimate_duration(text)
            if current_time + estimated_duration > self.MAX_TOTAL_DURATION:
                continue
            
            # Split line into before and after quote parts
            before_quote = line[:quote_start].lower()
            after_quote = line[quote_end + 1:].lower()
            
            # Simple speaker detection
            speaker = "Narrator"
            context = ""
            
            # Check for speaker before the quote
            if before_quote:
                words = before_quote.split()
                if words:
                    speaker = words[0].title()
                    context = before_quote
            
            # Check for speaker after the quote if not found before
            if speaker == "Narrator" and after_quote:
                for word in after_quote.split():
                    if word.endswith("said") or word.endswith("asked"):
                        prev_words = after_quote.split()[:after_quote.split().index(word)]
                        if prev_words:
                            speaker = prev_words[-1].title()
                            break
                context = after_quote
            
            # Simple emotion detection
            emotion = "neutral"
            tone = "normal"
            intensity = 0.5
            
            full_context = f"{context} {after_quote}".lower()
            
            if any(word in full_context for word in ["angrily", "furiously", "rage"]):
                emotion = "angry"
                intensity = 0.8
            elif any(word in full_context for word in ["happily", "cheerfully", "joy"]):
                emotion = "happy"
                intensity = 0.6
            elif any(word in full_context for word in ["sadly", "glumly"]):
                emotion = "sad"
                intensity = 0.4
            elif any(word in full_context for word in ["whispered", "softly"]):
                tone = "whisper"
                intensity = 0.3
            elif any(word in full_context for word in ["shouted", "yelled"]):
                tone = "shout"
                intensity = 0.9
            elif "concerned" in full_context:
                emotion = "concerned"
                intensity = 0.6
            elif "confident" in full_context:
                emotion = "confident"
                intensity = 0.8
            
            # Add segment with timing information
            dialogue_segments.append(DialogueAnalysis(
                text=text,
                speaker=speaker,
                emotion=emotion,
                context=full_context.strip(),
                tone=tone,
                intensity=intensity,
                start_time=current_time,
                duration=estimated_duration
            ))
            
            current_time += estimated_duration
        
        return dialogue_segments

    def _get_voice_recommendations_fallback(self, dialogue_analysis: List[DialogueAnalysis]) -> Dict[str, Any]:
        """Generate fallback voice recommendations based on emotions"""
        recommendations = {}
        
        for dialogue in dialogue_analysis:
            if dialogue.speaker not in recommendations:
                settings = {
                    "stability": 0.7,
                    "speaking_rate": 1.0,
                    "similarity_boost": 0.75
                }
                
                # Adjust settings based on emotion and intensity
                if dialogue.emotion == "angry":
                    settings["stability"] = 0.5
                    settings["speaking_rate"] = 1.3
                elif dialogue.emotion == "sad":
                    settings["stability"] = 0.8
                    settings["speaking_rate"] = 0.8
                elif dialogue.emotion == "happy":
                    settings["stability"] = 0.6
                    settings["speaking_rate"] = 1.1
                
                if dialogue.tone == "whisper":
                    settings["speaking_rate"] = 0.7
                    settings["stability"] = 0.9
                elif dialogue.tone == "shout":
                    settings["speaking_rate"] = 1.2
                    settings["stability"] = 0.5
                
                # Ensure speaking rate is optimized for 5-second limit
                text_length = len(dialogue.text.split())
                if text_length > 8:  # If text is longer, increase rate
                    settings["speaking_rate"] = min(settings["speaking_rate"] * 1.2, 2.0)
                
                recommendations[dialogue.speaker] = settings
        
        return recommendations

    def _get_analysis_prompt(self, scene_content: str) -> str:
        """Get the prompt for dialogue analysis"""
        return f"""Analyze the following scene and extract dialogue segments that can fit within a 5-second total duration.
Choose the most important/impactful dialogues if not all can fit.

For each dialogue segment:
1. Identify the speaker
2. Extract the exact dialogue text
3. Determine the emotion and tone
4. Note any relevant context
5. Rate the emotional intensity (0.0-1.0)

The total duration of all segments must not exceed 5 seconds.
Assume average speaking rate of 2.5 words per second.

Format the response as a JSON array of objects with fields:
- text: The exact dialogue text
- speaker: The speaker's name
- emotion: Primary emotion (e.g., happy, sad, angry, concerned)
- tone: Speaking tone (e.g., whisper, shout, normal)
- context: Relevant contextual information
- intensity: Emotional intensity as float (0.0-1.0)

Scene:
{scene_content}
"""

    def _get_recommendations_prompt(self, dialogue_analysis: List[DialogueAnalysis]) -> str:
        """Get the prompt for voice recommendations"""
        segments_text = "\n".join([
            f"Speaker: {d.speaker}\nText: {d.text}\nEmotion: {d.emotion}\nIntensity: {d.intensity}\n"
            for d in dialogue_analysis
        ])
        
        return f"""Based on the following dialogue segments, recommend voice settings for each speaker.
Each segment must be deliverable within 5 seconds, so adjust speaking rates accordingly.

Consider emotion, intensity, and context to suggest:
1. Stability (0.0-1.0): Lower for more variation, higher for consistency
2. Speaking rate (0.5-2.0): Adjust based on emotion and text length
3. Similarity boost (0.0-1.0): How closely to match the base voice

For longer segments (>8 words), increase the speaking rate while maintaining clarity.
For emotional segments, balance speaking rate with emotional expression.

Dialogue segments:
{segments_text}

Format response as JSON with speaker names as keys and settings as values.
"""

    @abstractmethod
    def analyze_dialogue(self, scene_content: str) -> List[DialogueAnalysis]:
        """Analyze dialogue using LLM"""
        pass

    @abstractmethod
    def generate_voice_recommendations(self, dialogue_analysis: List[DialogueAnalysis]) -> Dict[str, Any]:
        """Generate voice recommendations"""
        pass

class GroqLLMClient(BaseLLMClient):
    """Groq-based LLM client"""
    
    def __init__(self, api_key: str, model: str = "mixtral-8x7b-32768"):
        self.api_key = api_key
        self.model = model
        self.api_base = "https://api.groq.com/openai/v1"  # Updated to use OpenAI-compatible endpoint

    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Call Groq API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]

    def analyze_dialogue(self, scene_content: str) -> List[DialogueAnalysis]:
        try:
            response_text = self._call_api([
                {"role": "system", "content": "You are a dialogue analysis expert. Extract and analyze dialogue from scenes."},
                {"role": "user", "content": self._get_analysis_prompt(scene_content)}
            ], temperature=0.2)

            try:
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
                
                analysis_data = json.loads(response_text)
                return [DialogueAnalysis(**item) for item in analysis_data]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse Groq response, falling back to rule-based analysis: {str(e)}")
                return self._extract_dialogue_fallback(scene_content)

        except Exception as e:
            print(f"Warning: Groq API error, falling back to rule-based analysis: {str(e)}")
            return self._extract_dialogue_fallback(scene_content)

    def generate_voice_recommendations(self, dialogue_analysis: List[DialogueAnalysis]) -> Dict[str, Any]:
        try:
            response_text = self._call_api([
                {"role": "system", "content": "You are a voice synthesis expert. Recommend optimal voice settings for dialogue."},
                {"role": "user", "content": self._get_recommendations_prompt(dialogue_analysis)}
            ], temperature=0.3)

            try:
                recommendations = json.loads(response_text)
                return recommendations
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse Groq recommendations, using fallback: {str(e)}")
                return self._get_voice_recommendations_fallback(dialogue_analysis)

        except Exception as e:
            print(f"Warning: Groq API error, using fallback voice recommendations: {str(e)}")
            return self._get_voice_recommendations_fallback(dialogue_analysis)

class MistralLLMClient(BaseLLMClient):
    """Mistral-based LLM client"""
    
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        self.api_key = api_key
        self.model = model
        self.api_base = "https://api.mistral.ai/v1"

    def _call_api(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Call Mistral API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(
            f"{self.api_base}/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Mistral API error: {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]

    def analyze_dialogue(self, scene_content: str) -> List[DialogueAnalysis]:
        try:
            response_text = self._call_api([
                {"role": "system", "content": "You are a dialogue analysis expert. Extract and analyze dialogue from scenes."},
                {"role": "user", "content": self._get_analysis_prompt(scene_content)}
            ], temperature=0.2)

            try:
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
                
                analysis_data = json.loads(response_text)
                return [DialogueAnalysis(**item) for item in analysis_data]
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse Mistral response, falling back to rule-based analysis: {str(e)}")
                return self._extract_dialogue_fallback(scene_content)

        except Exception as e:
            print(f"Warning: Mistral API error, falling back to rule-based analysis: {str(e)}")
            return self._extract_dialogue_fallback(scene_content)

    def generate_voice_recommendations(self, dialogue_analysis: List[DialogueAnalysis]) -> Dict[str, Any]:
        try:
            response_text = self._call_api([
                {"role": "system", "content": "You are a voice synthesis expert. Recommend optimal voice settings for dialogue."},
                {"role": "user", "content": self._get_recommendations_prompt(dialogue_analysis)}
            ], temperature=0.3)

            try:
                recommendations = json.loads(response_text)
                return recommendations
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse Mistral recommendations, using fallback: {str(e)}")
                return self._get_voice_recommendations_fallback(dialogue_analysis)

        except Exception as e:
            print(f"Warning: Mistral API error, using fallback voice recommendations: {str(e)}")
            return self._get_voice_recommendations_fallback(dialogue_analysis)

# For backward compatibility
LLMClient = GroqLLMClient  # Using Groq as default 