from setuptools import setup, find_packages, Command
from setuptools.command.install import install
import subprocess
import sys

class CustomInstallCommand(install):
    """Custom installation command that checks for ffmpeg."""
    def run(self):
        # Run the standard installation
        install.run(self)
        
        # Import and run ffmpeg check
        try:
            from src.utils.setup_utils import check_ffmpeg
            if not check_ffmpeg():
                print("Warning: ffmpeg installation failed. Please install it manually.")
                print("The package will still work, but audio processing features will be limited.")
        except Exception as e:
            print(f"Warning: Could not verify ffmpeg installation: {str(e)}")
            print("Please ensure ffmpeg is installed manually if you plan to use audio features.")

setup(
    name="playplot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-json-logger>=2.0.7",
        "asyncio>=3.4.3",
        "cryptography>=41.0.1",
        "alembic>=1.12.0",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.1",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pydub>=0.25.1",
        "aiohttp>=3.8.0",
        "elevenlabs>=0.1.0",
        "pydantic>=2.0.0",
        "openai>=1.0.0",
        "typing-extensions>=4.5.0"
    ],
    python_requires=">=3.8",
    cmdclass={
        'install': CustomInstallCommand,
    },
) 