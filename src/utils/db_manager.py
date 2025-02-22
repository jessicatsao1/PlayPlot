"""
Database connection manager with connection pooling and encryption support.
"""

import os
import asyncio
import aiosqlite
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet

class DatabaseManager:
    def __init__(self, db_path: str, encryption_key: Optional[str] = None):
        self.db_path = db_path
        self.encryption_key = encryption_key or os.environ.get('DB_ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        self._pool = []
        self._pool_lock = asyncio.Lock()
        self.max_connections = 5

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection."""
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        return conn

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a connection from the pool or create a new one."""
        async with self._pool_lock:
            if self._pool:
                return self._pool.pop()
            return await self._create_connection()

    async def _return_connection(self, conn: aiosqlite.Connection):
        """Return a connection to the pool."""
        async with self._pool_lock:
            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:
                await conn.close()

    @asynccontextmanager
    async def connection(self):
        """Context manager for database connections."""
        conn = await self._get_connection()
        try:
            yield conn
        finally:
            await self._return_connection(conn)

    async def execute(self, query: str, parameters: tuple = ()) -> Any:
        """Execute a query and return the result."""
        async with self.connection() as conn:
            async with conn.execute(query, parameters) as cursor:
                await conn.commit()
                return cursor.lastrowid

    async def execute_many(self, query: str, parameters_list: list):
        """Execute multiple queries in a transaction."""
        async with self.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, parameters_list)
                await conn.commit()

    async def fetch_one(self, query: str, parameters: tuple = ()) -> Optional[tuple]:
        """Fetch a single row."""
        async with self.connection() as conn:
            async with conn.execute(query, parameters) as cursor:
                return await cursor.fetchone()

    async def fetch_all(self, query: str, parameters: tuple = ()) -> List[tuple]:
        """Fetch all rows."""
        async with self.connection() as conn:
            async with conn.execute(query, parameters) as cursor:
                return await cursor.fetchall()

    # User Management Methods
    async def create_user(self, username: str, email: str, password_hash: str,
                         profile_data: Optional[Dict] = None,
                         preferences: Optional[Dict] = None) -> str:
        """Create a new user."""
        query = """
            INSERT INTO users (user_id, username, email, password_hash, profile_data, preferences)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        user_id = os.urandom(16).hex()
        params = (
            user_id,
            username,
            email,
            password_hash,
            json.dumps(profile_data or {}),
            json.dumps(preferences or {"theme": "light"})
        )
        await self.execute(query, params)
        return user_id

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE user_id = ?"
        result = await self.fetch_one(query, (user_id,))
        if result:
            return {
                "user_id": result[0],
                "username": result[1],
                "email": result[2],
                "profile_data": json.loads(result[4] or "{}"),
                "preferences": json.loads(result[5] or "{}")
            }
        return None

    # Character Management Methods
    async def create_character(self, user_id: str, character_profile: Dict) -> str:
        """Create a new character."""
        query = """
            INSERT INTO characters (character_id, user_id, character_profile)
            VALUES (?, ?, ?)
        """
        character_id = os.urandom(16).hex()
        params = (character_id, user_id, json.dumps(character_profile))
        await self.execute(query, params)
        return character_id

    # Story Management Methods
    async def create_story(self, user_id: str, title: str, scenes: Optional[List] = None,
                          characters: Optional[List] = None, metadata: Optional[Dict] = None) -> str:
        """Create a new story."""
        query = """
            INSERT INTO stories (story_id, user_id, title, scenes, characters, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        story_id = os.urandom(16).hex()
        params = (
            story_id,
            user_id,
            title,
            json.dumps(scenes or []),
            json.dumps(characters or []),
            json.dumps(metadata or {})
        )
        await self.execute(query, params)
        return story_id

    # Scene Management Methods
    async def create_scene(self, story_id: str, scene_number: int, content: str,
                          visual_analysis: Optional[Dict] = None,
                          audio_direction: Optional[Dict] = None,
                          scene_analysis: Optional[Dict] = None,
                          media: Optional[Dict] = None) -> str:
        """Create a new scene."""
        query = """
            INSERT INTO scenes (scene_id, story_id, scene_number, content,
                              visual_analysis, audio_direction, scene_analysis, media)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        scene_id = os.urandom(16).hex()
        params = (
            scene_id,
            story_id,
            scene_number,
            content,
            json.dumps(visual_analysis or {}),
            json.dumps(audio_direction or {}),
            json.dumps(scene_analysis or {}),
            json.dumps(media or {})
        )
        await self.execute(query, params)
        return scene_id

    # Task Management Methods
    async def create_task(self, user_id: str, task_type: str, content: Dict,
                         story_id: Optional[str] = None, scene_id: Optional[str] = None,
                         metadata: Optional[Dict] = None) -> str:
        """Create a new task."""
        query = """
            INSERT INTO tasks (task_id, user_id, story_id, scene_id, task_type,
                             status, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        task_id = os.urandom(16).hex()
        params = (
            task_id,
            user_id,
            story_id,
            scene_id,
            task_type,
            'pending',
            json.dumps(content),
            json.dumps(metadata or {})
        )
        await self.execute(query, params)
        return task_id

    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        query = """
            UPDATE tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        result = await self.execute(query, (status, task_id))
        return result is not None

    # Compliance Guidelines Methods
    async def create_compliance_guideline(self, guideline: str, category: str) -> int:
        """Create a new compliance guideline."""
        query = """
            INSERT INTO compliance_guidelines (guideline, category)
            VALUES (?, ?)
        """
        return await self.execute(query, (guideline, category))

    async def get_compliance_guidelines(self) -> List[Dict]:
        """Get all compliance guidelines."""
        query = "SELECT * FROM compliance_guidelines"
        results = await self.fetch_all(query)
        return [
            {
                "id": row[0],
                "guideline": row[1],
                "category": row[2],
                "created_at": row[3]
            }
            for row in results
        ]

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt binary data."""
        return self.fernet.encrypt(data)

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt binary data."""
        return self.fernet.decrypt(encrypted_data)

    async def backup_database(self, backup_path: str):
        """Create an encrypted backup of the database."""
        async with self.connection() as conn:
            await conn.execute(f"VACUUM INTO '{backup_path}'")

    async def close_all(self):
        """Close all connections in the pool."""
        async with self._pool_lock:
            while self._pool:
                conn = self._pool.pop()
                await conn.close() 