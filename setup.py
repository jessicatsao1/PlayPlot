from setuptools import setup, find_packages

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
) 