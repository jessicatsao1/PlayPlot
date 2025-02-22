"""
Test file demonstrating the usage of StoryDatabase.
"""

import os
import json
import pytest
import asyncio
from datetime import datetime

from models.story_database import StoryDatabase

@pytest.fixture
async def db():
    """Create a test database instance."""
    db_path = "test_story_agents.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = StoryDatabase(db_path)
    yield db
    await db.close()
    os.remove(db_path)

@pytest.mark.asyncio
async def test_user_operations(db):
    """Test user creation and management."""
    # Create a test user
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "profile_data": {"bio": "Test user bio"},
        "preferences": {"theme": "dark"}
    }
    
    user_id = await db.create_user(**user_data)
    assert user_id is not None

    # Fetch user
    user = await db.get_user(user_id)
    assert user["username"] == user_data["username"]
    assert user["email"] == user_data["email"]

@pytest.mark.asyncio
async def test_character_operations(db):
    """Test character creation and management."""
    # Create test user first
    user_id = await db.create_user(
        username="character_test_user",
        email="character@test.com",
        password_hash="test_hash"
    )

    # Create character
    character_data = {
        "user_id": user_id,
        "character_profile": {
            "name": "Neo-9",
            "bio": "A rogue android detective",
            "traits": ["analytical", "mysterious"],
            "background": "Created in 2150"
        }
    }
    
    character_id = await db.create_character(**character_data)
    assert character_id is not None

    # Fetch character
    character = await db.get_character(character_id)
    assert character["character_profile"]["name"] == "Neo-9"

@pytest.mark.asyncio
async def test_story_operations(db):
    """Test story creation and management."""
    # Create test user
    user_id = await db.create_user(
        username="story_test_user",
        email="story@test.com",
        password_hash="test_hash"
    )

    # Create story
    story_data = {
        "user_id": user_id,
        "title": "The Android's Dream",
        "scenes": json.dumps([{"scene_number": 1, "content": "Initial scene"}]),
        "characters": json.dumps(["Neo-9", "Detective Smith"]),
        "metadata": json.dumps({"genre": "sci-fi", "setting": "future"})
    }
    
    story_id = await db.create_story(**story_data)
    assert story_id is not None

    # Create scene
    scene_data = {
        "story_id": story_id,
        "scene_number": 1,
        "content": "It was a dark and stormy night in Neo Tokyo...",
        "visual_analysis": json.dumps({"mood": "dark", "setting": "urban"}),
        "audio_direction": json.dumps({"background": "rain", "music": "noir"}),
        "scene_analysis": json.dumps({"key_elements": ["rain", "city", "neon"]})
    }
    
    scene_id = await db.create_scene(**scene_data)
    assert scene_id is not None

@pytest.mark.asyncio
async def test_task_operations(db):
    """Test task creation and management."""
    # Create test user and story
    user_id = await db.create_user(
        username="task_test_user",
        email="task@test.com",
        password_hash="test_hash"
    )
    
    story_id = await db.create_story(
        user_id=user_id,
        title="Test Story"
    )

    scene_id = await db.create_scene(
        story_id=story_id,
        scene_number=1,
        content="Test scene"
    )

    # Create task
    task_data = {
        "user_id": user_id,
        "story_id": story_id,
        "scene_id": scene_id,
        "task_type": "scene_generation",
        "status": "pending",
        "content": json.dumps({"prompt": "Generate next scene"}),
        "metadata": json.dumps({"priority": "high"})
    }
    
    task_id = await db.create_task(**task_data)
    assert task_id is not None

    # Update task status
    success = await db.update_task_status(task_id, "completed")
    assert success

@pytest.mark.asyncio
async def test_compliance_guidelines(db):
    """Test compliance guidelines management."""
    # Create guideline
    guideline_data = {
        "guideline": "No explicit content",
        "category": "content_safety"
    }
    
    guideline_id = await db.create_compliance_guideline(**guideline_data)
    assert guideline_id > 0

    # Fetch guidelines
    guidelines = await db.get_compliance_guidelines()
    assert len(guidelines) > 0
    assert guidelines[0]["guideline"] == guideline_data["guideline"]

if __name__ == "__main__":
    pytest.main([__file__]) 