import aiosqlite
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import os
import logging
import uuid

from models import Story, Scene, Character

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "test.db"):
        self.db_path = db_path
        
    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create characters table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    character_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description_physical TEXT,
                    voice_id TEXT,
                    voice_description TEXT
                )
            """)
            
            # Create scenes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    story_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL,
                    user_request TEXT,
                    manager_task_analysis TEXT,
                    image_task_analysis TEXT,
                    speech_task_analysis TEXT,
                    video_task_analysis TEXT,
                    story_scene TEXT,
                    options TEXT,
                    image_positive_prompt TEXT,
                    image_negative_prompt TEXT,
                    image_lora_choice TEXT,
                    speech_api_call TEXT,
                    video_prompt TEXT,
                    image_url TEXT,
                    speech_url TEXT,
                    video_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (story_id, scene_number)
                )
            """)
            
            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_scenes_story_id ON scenes(story_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_characters_story_id ON characters(user_id)")
            
            await db.commit()
            
    async def cleanup(self):
        """Clean up test database"""
        logger.info(f"Cleaning up database at {self.db_path}")
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info("Database file removed")

    async def get_last_scenes(self, story_id: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Get the last N scenes for a story"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT *
                FROM scenes
                WHERE story_id = ?
                ORDER BY scene_number DESC
                LIMIT ?
            """
            async with db.execute(query, (story_id, limit)) as cursor:
                rows = await cursor.fetchall()
                scenes = []
                for row in rows:
                    scene = dict(row)
                    # Parse JSON fields
                    for field in ['manager_task_analysis', 'image_task_analysis', 
                                'speech_task_analysis', 'video_task_analysis', 'options']:
                        if scene[field]:
                            try:
                                scene[field] = json.loads(scene[field])
                            except:
                                scene[field] = None
                    scenes.append(scene)
                return scenes

    async def get_next_scene_number(self, story_id: str) -> int:
        """Get the next scene number for a story"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT MAX(scene_number) FROM scenes WHERE story_id = ?",
                (story_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return (result[0] or 0) + 1

    async def save_scene(self, scene_data: Dict[str, Any]) -> bool:
        """Save or update a scene"""
        try:
            # Convert any dict fields to JSON strings
            for key, value in scene_data.items():
                if isinstance(value, (dict, list)):
                    scene_data[key] = json.dumps(value)

            async with aiosqlite.connect(self.db_path) as db:
                # Check if scene exists
                async with db.execute(
                    "SELECT 1 FROM scenes WHERE story_id = ? AND scene_number = ?",
                    (scene_data['story_id'], scene_data['scene_number'])
                ) as cursor:
                    exists = await cursor.fetchone() is not None

                if exists:
                    # Update existing scene
                    fields = [k for k in scene_data.keys() if k not in ['story_id', 'scene_number']]
                    query = f"""
                        UPDATE scenes 
                        SET {', '.join(f'{field} = ?' for field in fields)}
                        WHERE story_id = ? AND scene_number = ?
                    """
                    values = [scene_data[field] for field in fields]
                    values.extend([scene_data['story_id'], scene_data['scene_number']])
                    await db.execute(query, values)
                else:
                    # Insert new scene
                    fields = list(scene_data.keys())
                    query = f"""
                        INSERT INTO scenes ({', '.join(fields)})
                        VALUES ({', '.join('?' * len(fields))})
                    """
                    await db.execute(query, [scene_data[field] for field in fields])

                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving scene: {str(e)}")
            return False

    async def get_characters(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all characters for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT character_id, user_id, name, description_physical,
                           voice_id, voice_description
                    FROM characters 
                    WHERE user_id = ?
                    """,
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    characters = []
                    for row in rows:
                        character = {
                            "character_id": row["character_id"],
                            "user_id": row["user_id"],
                            "name": row["name"],
                            "description_physical": row["description_physical"],
                            "voice_id": row["voice_id"],
                            "voice_description": row["voice_description"]
                        }
                        characters.append(character)
                        logger.info(f"Found character {character['name']} with voice {character['voice_id']}")
                    return characters
        except Exception as e:
            logger.error(f"Error fetching characters for user {user_id}: {str(e)}")
            return []

    async def save_character(self, character_data: Dict[str, Any]) -> str:
        """Save or update a character"""
        try:
            character_id = character_data.get('character_id', str(uuid.uuid4()))
            async with aiosqlite.connect(self.db_path) as db:
                # Check if character exists
                async with db.execute(
                    "SELECT 1 FROM characters WHERE character_id = ?",
                    (character_id,)
                ) as cursor:
                    exists = await cursor.fetchone() is not None

                if exists:
                    # Update existing character (only description fields)
                    await db.execute("""
                        UPDATE characters 
                        SET description_physical = ?,
                            voice_description = ?
                        WHERE character_id = ?
                    """, (
                        character_data.get('description_physical'),
                        character_data.get('voice_description'),
                        character_id
                    ))
                else:
                    # Insert new character
                    await db.execute("""
                        INSERT INTO characters (
                            character_id, user_id, name,
                            description_physical, voice_id, voice_description
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        character_id,
                        character_data['user_id'],
                        character_data['name'],
                        character_data.get('description_physical'),
                        character_data.get('voice_id'),
                        character_data.get('voice_description')
                    ))

                await db.commit()
                return character_id
        except Exception as e:
            logger.error(f"Error saving character: {str(e)}")
            raise

    async def get_story(self, story_id: str) -> Dict[str, Any]:
        """Get story from database"""
        logger.debug(f"Fetching story {story_id}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM stories WHERE story_id = ?",
                    (story_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        logger.debug(f"Found story {story_id}")
                        # Convert row to dict and parse JSON fields
                        story_dict = dict(row)
                        try:
                            story_dict["conversation_history"] = json.loads(story_dict["conversation_history"])
                        except:
                            story_dict["conversation_history"] = []
                            
                        try:
                            story_dict["metadata"] = json.loads(story_dict["metadata"])
                        except:
                            story_dict["metadata"] = {}
                            
                        return story_dict
                    
            logger.debug(f"Story {story_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching story {story_id}: {str(e)}")
            raise
        
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
                        manager_output=json.loads(row["manager_output"]),
                        story_output=json.loads(row["story_output"]),
                        image_output=json.loads(row["image_output"]),
                        speech_output=json.loads(row["speech_output"]),
                        character_profiles=json.loads(row["character_profiles"]),
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
                        manager_output=json.loads(row["manager_output"]),
                        story_output=json.loads(row["story_output"]),
                        image_output=json.loads(row["image_output"]),
                        speech_output=json.loads(row["speech_output"]),
                        character_profiles=json.loads(row["character_profiles"]),
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
                
    async def save_story(self, story: Union[Dict[str, Any], Story]) -> str:
        """Save story to database"""
        try:
            # Convert dict to Story model if needed
            if isinstance(story, dict):
                story_data = {
                    "story_id": story.get("story_id", str(uuid.uuid4())),
                    "user_id": story["user_id"],
                    "title": story.get("title", "New Story"),
                    "current_scene": story.get("current_scene", 1),
                    "conversation_history": json.dumps(story.get("conversation_history", [])),
                    "metadata": json.dumps(story.get("metadata", {}))
                }
            else:
                story_data = {
                    "story_id": story.story_id,
                    "user_id": story.user_id,
                    "title": story.title,
                    "current_scene": story.current_scene,
                    "conversation_history": json.dumps(story.conversation_history),
                    "metadata": json.dumps(story.metadata)
                }

            logger.debug(f"Saving story with data: {json.dumps(story_data, indent=2)}")
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO stories (
                        story_id, user_id, title, current_scene,
                        conversation_history, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    story_data["story_id"],
                    story_data["user_id"],
                    story_data["title"],
                    story_data["current_scene"],
                    story_data["conversation_history"],
                    story_data["metadata"]
                ))
                await db.commit()
                logger.debug(f"Successfully saved story {story_data['story_id']}")
                return story_data["story_id"]
        except Exception as e:
            logger.error(f"Error saving story: {str(e)}")
            raise

    async def get_character(self, character_id: str) -> Optional[Dict[str, str]]:
        """Get character from database"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT character_name, character_description FROM characters WHERE character_id = ?",
                (character_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "name": row["character_name"],
                        "description": row["character_description"]
                    }
        return None

    async def get_story_characters(self, story_id: str) -> Dict[str, Dict[str, str]]:
        """Get all characters for a story with only necessary fields (name, description, voice_id)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT character_name as name, character_description as description,
                           voice_id
                    FROM characters 
                    WHERE story_id = ?
                    """,
                    (story_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    characters = {}
                    for row in rows:
                        characters[row["name"]] = {
                            "description": row["description"],
                            "voice_id": row["voice_id"]
                        }
                        logger.info(f"Found character {row['name']} with voice {row['voice_id']}")
                    return characters
        except Exception as e:
            logger.error(f"Error fetching characters for story {story_id}: {str(e)}")
            return {}

    async def get_story_context(self, story_id: str) -> Dict[str, Any]:
        """Get complete story context including characters and conversation history"""
        try:
            # Get story data
            story = await self.get_story(story_id)
            if not story:
                logger.warning(f"Story {story_id} not found")
                return {}

            # Get characters
            characters = await self.get_story_characters(story_id)

            # Format context - simplified to avoid dependency on scenes table
            context = {
                "story_id": story_id,
                "title": story.get("title", ""),
                "current_scene": story.get("current_scene", 1),
                "characters": characters,
                "conversation_history": story.get("conversation_history", [])[-5:],  # Last 5 conversations
                "previous_scenes": story.get("scenes", [])[-3:],  # Last 3 scenes from story data
                "metadata": story.get("metadata", {})
            }

            logger.debug(f"Retrieved context for story {story_id}")
            return context

        except Exception as e:
            logger.error(f"Error getting story context for {story_id}: {str(e)}")
            return {} 