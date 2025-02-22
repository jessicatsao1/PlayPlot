"""
Database schema for the story agents system.
"""

SCHEMA_DEFINITIONS = [
    """
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
    """,
    
    """
    CREATE TABLE IF NOT EXISTS characters (
        character_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        character_profile JSON NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """,
    
    """
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
    """,
    
    """
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
    """,
    
    """
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        story_id TEXT,
        scene_id TEXT,
        task_type TEXT NOT NULL,
        status TEXT NOT NULL,
        content JSON NOT NULL,
        compliance_result JSON,
        task_analysis JSON,
        parent_task_id TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metadata JSON,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (story_id) REFERENCES stories(story_id),
        FOREIGN KEY (scene_id) REFERENCES scenes(scene_id)
    )
    """,
    
    """
    CREATE TABLE IF NOT EXISTS compliance_guidelines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guideline TEXT NOT NULL,
        category TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_characters_user_id ON characters(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_story_id ON tasks(story_id)",
    "CREATE INDEX IF NOT EXISTS idx_scenes_story_id ON scenes(story_id)"
] 