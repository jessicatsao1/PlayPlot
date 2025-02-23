import aiosqlite
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import logging

from models import Story, Scene

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "test.db"):
        self.db_path = db_path
        
    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    profile_data JSON,
                    preferences JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create stories table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    story_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    current_scene INTEGER DEFAULT 1,
                    scenes JSON,
                    characters JSON,
                    conversation_history JSON,
                    metadata JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Create scenes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL,
                    content TEXT,
                    visual_analysis JSON,
                    audio_direction JSON,
                    scene_analysis JSON,
                    media JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(story_id)
                )
            """)
            
            # Create compliance guidelines table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS compliance_guidelines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guideline TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_scenes_story_id ON scenes(story_id)")
            
            # Add default compliance guidelines if none exist
            async with db.execute("SELECT COUNT(*) FROM compliance_guidelines") as cursor:
                count = await cursor.fetchone()
                if count[0] == 0:
                    logger.info("Adding default compliance guidelines")
                    default_guidelines = [
                        ("Keep content family-friendly and appropriate for all ages", "content"),
                        ("Avoid explicit violence or graphic descriptions", "violence"),
                        ("Use inclusive and respectful language", "language"),
                        ("Maintain positive themes and messages", "themes"),
                        ("Ensure cultural sensitivity and respect", "culture"),
                        ("Avoid controversial political or religious topics", "topics"),
                        ("Promote educational and constructive values", "values")
                    ]
                    await db.executemany(
                        "INSERT INTO compliance_guidelines (guideline, category) VALUES (?, ?)",
                        default_guidelines
                    )
                    logger.info(f"Added {len(default_guidelines)} default compliance guidelines")
            
            await db.commit()
        
    async def get_story(self, story_id: str) -> Optional[Story]:
        """Get story from database"""
        logger.debug(f"Fetching story {story_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM stories WHERE story_id = ?",
                (story_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    logger.debug(f"Found story {story_id}")
                    return Story(
                        story_id=row["story_id"],
                        user_id=row["user_id"],
                        title=row["title"],
                        current_scene=row["current_scene"],
                        scenes=json.loads(row["scenes"]),
                        characters=json.loads(row["characters"]),
                        conversation_history=json.loads(row["conversation_history"]),
                        metadata=json.loads(row["metadata"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"])
                    )
        logger.debug(f"Story {story_id} not found")
        return None
        
    async def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get scene from database"""
        logger.debug(f"Fetching scene {scene_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM scenes WHERE scene_id = ?",
                (scene_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    logger.debug(f"Found scene {scene_id}")
                    return Scene(
                        scene_id=row["scene_id"],
                        story_id=row["story_id"],
                        scene_number=row["scene_number"],
                        content=row["content"],
                        visual_analysis=json.loads(row["visual_analysis"]),
                        audio_direction=json.loads(row["audio_direction"]),
                        scene_analysis=json.loads(row["scene_analysis"]),
                        media=json.loads(row["media"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"])
                    )
        logger.debug(f"Scene {scene_id} not found")
        return None
        
    async def get_previous_scenes(
        self,
        story_id: str,
        limit: int = 3
    ) -> List[Scene]:
        """Get previous scenes from database"""
        logger.debug(f"Fetching previous {limit} scenes for story {story_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM scenes 
                WHERE story_id = ? 
                ORDER BY scene_number DESC 
                LIMIT ?
                """,
                (story_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                scenes = [
                    Scene(
                        scene_id=row["scene_id"],
                        story_id=row["story_id"],
                        scene_number=row["scene_number"],
                        content=row["content"],
                        visual_analysis=json.loads(row["visual_analysis"]),
                        audio_direction=json.loads(row["audio_direction"]),
                        scene_analysis=json.loads(row["scene_analysis"]),
                        media=json.loads(row["media"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"])
                    )
                    for row in rows
                ]
                logger.debug(f"Found {len(scenes)} previous scenes")
                return scenes
                
    async def get_compliance_guidelines(self) -> List[str]:
        """Get compliance guidelines from database"""
        logger.debug("Fetching compliance guidelines")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT guideline FROM compliance_guidelines"
            ) as cursor:
                rows = await cursor.fetchall()
                guidelines = [row["guideline"] for row in rows]
                logger.debug(f"Found {len(guidelines)} compliance guidelines")
                return guidelines
                
    async def cleanup(self):
        """Clean up test database"""
        logger.info(f"Cleaning up database at {self.db_path}")
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info("Database file removed")

    async def save_story(self, story: Story) -> Story:
        """Save story to database"""
        logger.debug(f"Saving story {story.story_id}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO stories (
                        story_id, user_id, title, current_scene,
                        scenes, characters, conversation_history, metadata,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    story.story_id,
                    story.user_id,
                    story.title,
                    story.current_scene,
                    json.dumps(story.scenes),
                    json.dumps(story.characters),
                    json.dumps(story.conversation_history),
                    json.dumps(story.metadata),
                    story.created_at.isoformat(),
                    story.updated_at.isoformat()
                ))
                await db.commit()
                logger.debug(f"Successfully saved story {story.story_id}")
        except Exception as e:
            logger.error(f"Error saving story {story.story_id}: {str(e)}")
            raise
        return story

    async def save_scene(self, scene: Scene) -> Scene:
        """Save scene to database"""
        logger.debug(f"Saving scene {scene.scene_id}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO scenes (
                        scene_id, story_id, scene_number, content,
                        visual_analysis, audio_direction, scene_analysis,
                        media, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scene.scene_id,
                    scene.story_id,
                    scene.scene_number,
                    scene.content,
                    json.dumps(scene.visual_analysis),
                    json.dumps(scene.audio_direction),
                    json.dumps(scene.scene_analysis),
                    json.dumps(scene.media),
                    scene.created_at.isoformat(),
                    scene.updated_at.isoformat()
                ))
                await db.commit()
                logger.debug(f"Successfully saved scene {scene.scene_id}")
        except Exception as e:
            logger.error(f"Error saving scene {scene.scene_id}: {str(e)}")
            raise
        return scene 