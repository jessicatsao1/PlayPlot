import asyncio
import os
import aiohttp
import random
from dotenv import load_dotenv
from config import APIConfig
from video_agent import VideoAgent

# Load environment variables from .env file
load_dotenv()

async def download_video(url: str, save_path: str):
    """Download video from URL and save to specified path"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                # Save the video
                with open(save_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                return True
            return False

async def test_video_generation():
    try:
        # Initialize config and video agent
        config = APIConfig.load_from_env()
        video_agent = VideoAgent(config)
        
        # Use the image from root folder
        image_path = os.path.join(os.getcwd(), "playplot_demo.jpg")
        
        # Verify image exists
        if not os.path.exists(image_path):
            print(f"Error: Image not found at {image_path}")
            print("Please ensure 'playplot_demo.jpg' is in the root folder.")
            return
        
        # Detailed prompt - exactly as shown in screenshot
        prompt = """She stands behind the café counter, her emerald-green eyes locking onto yours with a knowing smile. The warm morning light filters through the windows, casting a soft glow on her long, pink hair as it gently sways with the motion of the air. A neatly tied green apron rests over her crisp white shirt, the embroidered emblem just barely catching the light. One hand rests on an open order book, fingers idly tracing the edge of the page, while the other gently presses against the counter, steady but relaxed. The faint aroma of freshly brewed coffee lingers in the air, blending with the sweet scent of pastries stacked neatly on display. Her head tilts slightly, a hint of amusement playing on her lips—waiting, expecting, as if she already knows what you're about to order."""
        
        print("Starting video generation test...")
        print(f"Using image: {image_path}")
        print(f"Using prompt: {prompt}")
        print(f"Using FAL API key: {os.getenv('FAL_API_KEY')[:8]}...")  # Only show first 8 chars for security
        
        # Generate a random seed
        seed = random.randint(1, 2147483647)  # Using a random integer seed
        print(f"Using seed: {seed}")
        
        # Try generating video - matching the UI settings exactly
        result = await video_agent.generate_video(
            prompt=prompt,
            image_path=image_path,
            guidance_scale=6.0,  # As shown in screenshot
            num_inference_steps=30,  # As shown in screenshot
            aspect_ratio="9:16",  # Portrait mode as shown
            negative_prompt="blurry, low quality, pixelated, poor quality, poor lighting, poor composition",
            seed=seed  # Using integer seed
        )
        
        print("\nVideo generation successful!")
        print(f"Video URL: {result['video_url']}")
        print("\nMetadata:")
        for key, value in result['metadata'].items():
            print(f"{key}: {value}")
            
        # Download the generated video
        video_url = result['video_url']
        timestamp = asyncio.get_event_loop().time()
        video_filename = f"generated_video_{int(timestamp)}.mp4"
        save_path = os.path.join(os.getcwd(), "generated_videos", video_filename)
        
        print(f"\nDownloading video to: {save_path}")
        if await download_video(video_url, save_path):
            print("Video downloaded successfully!")
        else:
            print("Failed to download video")
            
    except Exception as e:
        print(f"\nError during video generation: {str(e)}")
        raise

if __name__ == "__main__":
    # Make sure FAL API key is available
    if not os.getenv("FAL_API_KEY"):
        print("Error: FAL_API_KEY not found in environment variables or .env file!")
        print("Please make sure you have FAL_API_KEY set in your .env file.")
        exit(1)
        
    # Run the test
    asyncio.run(test_video_generation()) 