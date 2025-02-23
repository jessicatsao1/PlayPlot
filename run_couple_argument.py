#!/usr/bin/env python3
"""
Run the couple argument scene example.
This script will use the Groq LLM client if GROQ_API_KEY is available,
falling back to Mistral if only MISTRAL_API_KEY is available.
"""
from src.examples.couple_argument_scene import main

if __name__ == "__main__":
    main() 