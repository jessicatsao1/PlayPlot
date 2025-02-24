import os
from typing import Dict, Any, Optional
from custom_video_fal import FalVideoClient, VideoGenerationError
from config import APIConfig, VideoProvider

class VideoAgent:
    def __init__(self, config: APIConfig):
        """Initialize video agent with configuration"""
        self.config = config
        self.video_client = None

    def _init_client(self, use_fallback: bool = False) -> None:
        """Initialize video client with appropriate configuration"""
        video_config = self.config.get_video_config(use_fallback=use_fallback)
        self.video_client = FalVideoClient(video_config)

    async def generate_video(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate video from image using primary or fallback provider"""
        try:
            # Initialize client if not already done
            if not self.video_client:
                self._init_client()

            # Handle image input
            if image_path and not image_url:
                image_url = await self.video_client.upload_image(image_path)
            elif not image_url:
                raise VideoGenerationError("Either image_path or image_url must be provided")

            # Update settings from kwargs
            if kwargs:
                self.video_client.settings.update(kwargs)

            # Try primary provider
            try:
                return await self.video_client.generate_video(prompt, image_url)
            except VideoGenerationError as e:
                print(f"Primary provider failed: {str(e)}")
                print("Trying fallback provider...")
                
                # Try fallback provider
                self._init_client(use_fallback=True)
                return await self.video_client.generate_video(prompt, image_url)

        except Exception as e:
            raise VideoGenerationError(f"Video generation failed: {str(e)}")

    async def process_scene(
        self,
        scene_content: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Process a scene to generate video with appropriate settings"""
        try:
            # Extract video generation settings from scene content
            # This could be enhanced with LLM analysis if needed
            settings = {
                "guidance_scale": kwargs.get("guidance_scale", 6.0),
                "num_inference_steps": kwargs.get("num_inference_steps", 30),
                "aspect_ratio": kwargs.get("aspect_ratio", "16:9"),
                "negative_prompt": kwargs.get("negative_prompt", "blurry, low quality")
            }

            # Generate video
            result = await self.generate_video(
                prompt=scene_content,
                image_path=image_path,
                image_url=image_url,
                **settings
            )

            return {
                "video_url": result["video_url"],
                "metadata": {
                    **result["metadata"],
                    "scene_content": scene_content
                }
            }

        except Exception as e:
            raise VideoGenerationError(f"Scene processing failed: {str(e)}")

    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """Get list of available video models"""
        return {name: model.value for name, model in VideoProvider.__members__.items()} 