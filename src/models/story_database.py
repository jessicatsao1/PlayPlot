"""
Main StoryDatabase class implementing all required database operations.
"""

import json
import hashlib
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from utils.db_manager import DatabaseManager
from models.schema import SCHEMA_DEFINITIONS, INDEXES

class StoryDatabase:
    def __init__(self, db_path: str, encryption_key: Optional[str] = None):
        """Initialize the story database."""
        self.db = DatabaseManager(db_path, encryption_key)
        self._initialize_database()

    async def _initialize_database(self):
        """Initialize the database schema."""
        for definition in SCHEMA_DEFINITIONS:
            await self.db.execute(definition)
        for index in INDEXES:
            await self.db.execute(index)

    # Core CRUD Operations
    async def create_character(self, name: str, bio: str, traits: dict, story_id: Optional[int] = None) -> int:
        """Create a new character."""
        query = """
        INSERT INTO characters (name, bio, traits, story_id)
        VALUES (?, ?, ?, ?)
        """
        return await self.db.execute(query, (name, bio, json.dumps(traits), story_id))

    async def update_story(self, story_id: int, new_content: str) -> bool:
        """Update story content."""
        query = """
        UPDATE stories 
        SET content = ?, status = 'draft'
        WHERE story_id = ?
        """
        result = await self.db.execute(query, (new_content, story_id))
        return bool(result)

    async def get_user_preferences(self, user_id: int) -> dict:
        """Get user preferences."""
        query = "SELECT preferences FROM users WHERE user_id = ?"
        result = await self.db.fetch_one(query, (user_id,))
        return json.loads(result[0]) if result else {}

    # Workflow Management
    async def initiate_workflow(self, user_id: int, prompt: str, story_id: Optional[int] = None) -> int:
        """Start a new workflow.
        
        Args:
            user_id: The ID of the user initiating the workflow
            prompt: The initial prompt or request
            story_id: Optional ID of an existing story. If None, a new story will be created.
        
        Returns:
            The ID of the created workflow
        """
        async with self.db.connection() as conn:
            if story_id is None:
                # Create a new story
                story_result = await conn.execute("""
                    INSERT INTO stories (title, content, genre, status)
                    VALUES (?, ?, 'sci-fi', 'draft')
                """, (prompt[:50] + "...", ""))
                story_id = story_result.lastrowid

            # Create workflow
            workflow_result = await conn.execute("""
                INSERT INTO workflows (user_id, story_id, current_stage)
                VALUES (?, ?, 'compliance_check')
            """, (user_id, story_id))
            workflow_id = workflow_result.lastrowid

            # Create initial compliance task
            await conn.execute("""
                INSERT INTO tasks (workflow_id, agent_id, input_data)
                SELECT ?, agent_id, ?
                FROM agents 
                WHERE agent_type = 'compliance'
                LIMIT 1
            """, (workflow_id, prompt))

            await conn.commit()
            return workflow_id

    async def get_workflow_story(self, workflow_id: int) -> Dict:
        """Get the story associated with a workflow."""
        query = """
        SELECT s.story_id, s.title, s.content, s.genre, s.status
        FROM stories s
        JOIN workflows w ON w.story_id = s.story_id
        WHERE w.workflow_id = ?
        """
        result = await self.db.fetch_one(query, (workflow_id,))
        if result:
            return {
                'story_id': result[0],
                'title': result[1],
                'content': result[2],
                'genre': result[3],
                'status': result[4]
            }
        return None

    async def get_pending_tasks(self, agent_type: str) -> List[dict]:
        """Get pending tasks for an agent type."""
        query = """
        SELECT t.task_id, t.input_data, t.workflow_id, w.priority
        FROM tasks t
        JOIN workflows w ON t.workflow_id = w.workflow_id
        JOIN agents a ON t.agent_id = a.agent_id
        WHERE a.agent_type = ? AND t.status = 'pending'
        ORDER BY w.priority DESC, t.created_at ASC
        """
        rows = await self.db.fetch_all(query, (agent_type,))
        return [
            {
                'task_id': row[0],
                'input_data': row[1],
                'workflow_id': row[2],
                'priority': row[3]
            }
            for row in rows
        ]

    async def complete_task(self, task_id: int, output: str) -> bool:
        """Complete a task and update workflow stage."""
        async with self.db.connection() as conn:
            # Update task
            await conn.execute("""
                UPDATE tasks 
                SET status = 'completed', 
                    output_data = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (output, task_id))

            # Get workflow info
            workflow = await conn.execute("""
                SELECT workflow_id, current_stage 
                FROM workflows w
                JOIN tasks t ON w.workflow_id = t.workflow_id
                WHERE t.task_id = ?
            """, (task_id,))
            workflow_data = await workflow.fetchone()

            if workflow_data:
                workflow_id, current_stage = workflow_data
                next_stage = {
                    'compliance_check': 'story_generation',
                    'story_generation': 'media_creation',
                    'media_creation': 'review',
                    'review': 'completed'
                }.get(current_stage)

                if next_stage:
                    await conn.execute("""
                        UPDATE workflows
                        SET current_stage = ?
                        WHERE workflow_id = ?
                    """, (next_stage, workflow_id))

            await conn.commit()
            return True

    # Artifact Handling
    async def create_artifact_version(self, parent_id: int, content: bytes) -> int:
        """Create a new version of an artifact."""
        # Get parent artifact info
        parent = await self.db.fetch_one("""
            SELECT artifact_type, workflow_id, version
            FROM artifacts WHERE artifact_id = ?
        """, (parent_id,))

        if not parent:
            raise ValueError("Parent artifact not found")

        content_hash = hashlib.sha256(content).hexdigest()
        storage_path = f"artifacts/{content_hash[:8]}/{parent[0]}"

        encrypted_content = self.db.encrypt_data(content)
        with open(storage_path, 'wb') as f:
            f.write(encrypted_content)

        query = """
        INSERT INTO artifacts (
            artifact_type, content_hash, storage_path,
            parent_artifact, workflow_id, version
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        return await self.db.execute(query, (
            parent[0], content_hash, storage_path,
            parent_id, parent[1], parent[2] + 1
        ))

    async def get_artifact_lineage(self, artifact_id: int) -> List[dict]:
        """Get the version history of an artifact."""
        query = """
        WITH RECURSIVE lineage AS (
            SELECT * FROM artifacts WHERE artifact_id = ?
            UNION ALL
            SELECT a.* 
            FROM artifacts a
            JOIN lineage l ON a.artifact_id = l.parent_artifact
        )
        SELECT artifact_id, version, created_at, metadata
        FROM lineage
        ORDER BY version DESC
        """
        rows = await self.db.fetch_all(query, (artifact_id,))
        return [
            {
                'artifact_id': row[0],
                'version': row[1],
                'created_at': row[2],
                'metadata': json.loads(row[3]) if row[3] else {}
            }
            for row in rows
        ]

    # Compliance Checks
    async def validate_compliance(self, workflow_id: int) -> bool:
        """Validate workflow compliance."""
        query = """
        SELECT cp.rule, cp.severity
        FROM compliance_policies cp
        JOIN tasks t ON t.workflow_id = ?
        WHERE cp.active = 1
        AND t.status = 'completed'
        AND t.output_data LIKE '%' || cp.rule || '%'
        """
        violations = await self.db.fetch_all(query, (workflow_id,))
        return len(violations) == 0

    async def log_policy_violation(self, workflow_id: int, policy_id: int) -> None:
        """Log a policy violation."""
        query = """
        INSERT INTO tasks (
            workflow_id,
            agent_id,
            input_data,
            status,
            output_data
        )
        SELECT
            ?,
            (SELECT agent_id FROM agents WHERE agent_type = 'compliance' LIMIT 1),
            (SELECT rule FROM compliance_policies WHERE policy_id = ?),
            'failed',
            'Policy violation detected'
        """
        await self.db.execute(query, (workflow_id, policy_id))

    # Maintenance
    async def cleanup_old_workflows(self, days: int = 7) -> int:
        """Clean up old workflows and their associated data."""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = """
        DELETE FROM workflows
        WHERE created_at < ? AND current_stage = 'completed'
        """
        result = await self.db.execute(query, (cutoff_date.isoformat(),))
        return result

    async def rebuild_indexes(self) -> None:
        """Rebuild database indexes."""
        async with self.db.connection() as conn:
            await conn.execute("PRAGMA optimize")
            for index in INDEXES:
                # Drop existing index
                index_name = index.split()[3]
                await conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                # Recreate index
                await conn.execute(index)
            await conn.commit()

    async def close(self):
        """Close database connections."""
        await self.db.close_all() 