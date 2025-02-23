# Database Schema and Manager Agent Interactions

## Core Tables Schema

### 1. Tasks Table (In-Memory Only)
```sql
-- Note: This is a representation of the in-memory structure, not a database table
{
    task_id: UUID,
    user_id: TEXT,
    story_id: TEXT NULL,
    scene_id: TEXT NULL,
    task_type: ENUM('story', 'image', 'speech', 'video'),
    status: ENUM('pending', 'processing', 'completed', 'failed'),
    content: JSON,
    compliance_result: JSON,
    task_analysis: JSON,
    parent_task_id: UUID NULL,
    metadata: JSON
}
```

### 2. Stories Table
```sql
CREATE TABLE stories (
    story_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    current_scene INTEGER DEFAULT 1,
    characters JSON,                -- Flat array of character objects
    metadata JSON,                  -- Story settings and preferences
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

### 3. Scenes Table
```sql
CREATE TABLE scenes (
    scene_id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    scene_number INTEGER NOT NULL,
    content TEXT,                   -- Raw scene content
    media_metadata JSON,            -- URLs and metadata for generated media
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(story_id)
)
```

### 4. Compliance Guidelines Table
```sql
CREATE TABLE compliance_guidelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guideline TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

## Database Interactions

### Read Operations

1. **Compliance Check**
```python
# Get guidelines for content validation
async def get_compliance_guidelines(self) -> List[str]:
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT guideline FROM compliance_guidelines") as cursor:
            rows = await cursor.fetchall()
            return [row["guideline"] for row in rows]
```

2. **Story Context Loading**
```python
# Get story with minimal required fields
async def get_story(self, story_id: str) -> Optional[Story]:
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT story_id, user_id, title, current_scene, characters, metadata FROM stories WHERE story_id = ?",
            (story_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Story(
                story_id=row["story_id"],
                user_id=row["user_id"],
                title=row["title"],
                current_scene=row["current_scene"],
                characters=json.loads(row["characters"]),
                metadata=json.loads(row["metadata"])
            )
```

3. **Scene Loading**
```python
# Get scene with minimal required fields
async def get_scene(self, scene_id: str) -> Optional[Scene]:
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT scene_id, story_id, scene_number, content, media_metadata FROM scenes WHERE scene_id = ?",
            (scene_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Scene(
                scene_id=row["scene_id"],
                story_id=row["story_id"],
                scene_number=row["scene_number"],
                content=row["content"],
                media_metadata=json.loads(row["media_metadata"])
            )
```

## JSON Schema Definitions

### 1. Task Content Schema
```json
{
    "type": "object",
    "properties": {
        "user_input": {"type": "string"},
        "story_elements": {"type": "string", "optional": true},
        "visual_elements": {"type": "string", "optional": true},
        "audio_elements": {"type": "string", "optional": true},
        "context": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "optional": true},
                "tone": {"type": "string", "optional": true}
            }
        }
    },
    "required": ["user_input"]
}
```

### 2. Compliance Result Schema
```json
{
    "type": "object",
    "properties": {
        "is_safe": {"type": "boolean"},
        "reasoning": {"type": "string"},
        "concerns": {
            "type": "array",
            "items": {"type": "string"}
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["is_safe", "reasoning"]
}
```

### 3. Task Analysis Schema
```json
{
    "type": "object",
    "properties": {
        "flow_type": {
            "type": "string",
            "enum": ["story_media", "video"]
        },
        "context": {"type": "object"},
        "recommendations": {"type": "string"},
        "reasoning": {"type": "string"}
    },
    "required": ["flow_type", "recommendations", "reasoning"]
}
```

### 4. Media Metadata Schema
```json
{
    "type": "object",
    "properties": {
        "images": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "type": {"type": "string"},
                    "timestamp": {"type": "string"}
                }
            }
        },
        "audio": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "duration": {"type": "number"},
                    "timestamp": {"type": "string"}
                }
            }
        },
        "video": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "thumbnail": {"type": "string"},
                    "duration": {"type": "number"},
                    "timestamp": {"type": "string"}
                }
            }
        }
    }
}
```

## Database Indexes
```sql
-- Primary lookups
CREATE INDEX idx_stories_user_id ON stories(user_id);
CREATE INDEX idx_scenes_story_id ON scenes(story_id);

-- Scene ordering
CREATE INDEX idx_scenes_story_number ON scenes(story_id, scene_number);

-- Compliance guidelines
CREATE INDEX idx_guidelines_category ON compliance_guidelines(category);
```

## Important Notes

1. **Task Persistence**
   - Tasks are managed in-memory during processing
   - No direct database table for tasks
   - Results are stored in scene's media_metadata

2. **Simplified Schema**
   - Removed nested JSON structures where possible
   - Flattened character and media metadata
   - Minimized redundant data storage

3. **Performance Considerations**
   - Indexes on frequently queried fields
   - Minimal JSON parsing/serialization
   - Efficient scene retrieval for context 