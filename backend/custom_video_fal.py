import os
import time
from typing import Dict, Any, Optional
import fal_client
from config import VideoProvider, ERROR_MESSAGES

class VideoGenerationError(Exception):
    """Custom exception for video generation errors"""
    pass

class FalVideoClient:
    def __init__(self, config: Dict[str, Any]):
        """Initialize FAL video client with configuration"""
        self.api_key = config["api_key"]
        self.provider = config["provider"]
        self.endpoint = config["endpoint"]
        self.settings = config.get("settings", {})
        self.last_update_time = 0
        self.update_interval = 2.0  # Update every 2 seconds
        
        # Set API key in environment
        os.environ["FAL_KEY"] = self.api_key

    def _get_model_settings(self) -> Dict[str, Any]:
        """Get model-specific settings"""
        base_settings = {
            "guidance_scale": self.settings.get("guidance_scale", 6.0),
            "num_inference_steps": self.settings.get("num_inference_steps", 30),
            "aspect_ratio": self.settings.get("aspect_ratio", "9:16")  # Changed to 9:16
        }
        
        # Add model-specific settings based on provider
        if self.provider == VideoProvider.FAL_SKYREELS.value:
            base_settings.update({
                "seed": self.settings.get("seed", None),
                "negative_prompt": self.settings.get("negative_prompt", "")
            })
        elif self.provider == VideoProvider.FAL_PIXVERSE.value:
            base_settings.update({
                "resolution": self.settings.get("resolution", "720p"),
                "style": self.settings.get("style", None)
            })
        elif self.provider == VideoProvider.FAL_MINIMAX.value:
            base_settings.update({
                "duration": self.settings.get("duration", "5"),
                "style": self.settings.get("style", None)
            })
        elif self.provider == VideoProvider.FAL_LUMA.value:
            base_settings.update({
                "duration": self.settings.get("duration", "5"),
                "style": self.settings.get("style", None),
                "resolution": self.settings.get("resolution", "720p")
            })
        elif self.provider == VideoProvider.FAL_KLING.value:
            base_settings.update({
                "style": self.settings.get("style", None),
                "resolution": self.settings.get("resolution", "720p")
            })
            
        return base_settings

    def _handle_queue_update(self, update) -> None:
        """Handle queue status updates with rate limiting"""
        current_time = time.time()
        
        if isinstance(update, fal_client.InProgress):
            # Only update if enough time has passed
            if current_time - self.last_update_time >= self.update_interval:
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                for log in update.logs:
                    print(f"[{timestamp}] {log['message']}")
                self.last_update_time = current_time

    async def generate_video(self, prompt: str, image_url: str) -> Dict[str, Any]:
        """Generate video from image using FAL AI"""
        try:
            # Prepare arguments
            arguments = {
                "prompt": prompt,
                "image_url": image_url,
                **self._get_model_settings()
            }
            
            # Remove None values
            arguments = {k: v for k, v in arguments.items() if v is not None}
            
            # Log generation start
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n[{timestamp}] Starting video generation with {self.provider}")
            print(f"[{timestamp}] Settings: {self._get_model_settings()}")
            
            # Submit request using the specific endpoint
            result = fal_client.subscribe(
                self.endpoint,
                arguments=arguments,
                with_logs=True,
                on_queue_update=self._handle_queue_update
            )
            
            if not result or not result.get("video"):
                raise VideoGenerationError(
                    ERROR_MESSAGES["validation"].format(
                        details="No video in response"
                    )
                )
            
            # Log success
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n[{timestamp}] Video generation successful!")
            
            return {
                "video_url": result["video"]["url"],
                "seed": result.get("seed"),  # Only available for some models
                "metadata": {
                    "model": self.provider,
                    "endpoint": self.endpoint,
                    "settings": self._get_model_settings()
                }
            }
            
        except Exception as e:
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n[{timestamp}] Error: {str(e)}")
            raise VideoGenerationError(
                ERROR_MESSAGES["api_error"].format(
                    error=str(e)
                )
            )

    async def upload_image(self, image_path: str) -> str:
        """Upload image to FAL storage"""
        try:
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"\n[{timestamp}] Uploading image: {image_path}")
            url = fal_client.upload_file(image_path)
            print(f"[{timestamp}] Upload successful: {url}")
            return url
        except Exception as e:
            raise VideoGenerationError(
                ERROR_MESSAGES["api_error"].format(
                    error=f"Failed to upload image: {str(e)}"
                )
            ) 