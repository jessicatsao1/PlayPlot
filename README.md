# Story Agents Database System

A comprehensive SQLite database system for managing multi-layer storytelling agents, with support for workflow management, compliance checking, and artifact versioning.

## Features

- Asynchronous database operations
- Connection pooling
- Encrypted storage for sensitive data
- Full workflow management system
- Compliance policy enforcement
- Artifact versioning with lineage tracking
- Comprehensive test suite

## Requirements

- Python 3.8+
- SQLite 3.35.0+
- Dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd story-agents-db
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create necessary directories:
```bash
mkdir -p db/backups artifacts
```

## Database Schema

The system includes the following core tables:

- `characters`: Story character management
- `stories`: Story content and metadata
- `users`: User profiles and preferences
- `story_knowledge`: Knowledge base facts
- `compliance_policies`: Safety and ethics rules
- `agents`: AI agent definitions
- `workflows`: Task workflow tracking
- `tasks`: Individual task management
- `artifacts`: Content version control

## Usage Example

```python
import asyncio
from src.models.story_database import StoryDatabase

async def main():
    # Initialize database
    db = StoryDatabase('story_agents.db')
    
    # Create a character
    character_id = await db.create_character(
        name="Neo-9",
        bio="A rogue android detective",
        traits={
            'alignment': 'chaotic_good',
            'skills': ['hacking', 'deduction']
        }
    )
    
    # Start a workflow
    workflow_id = await db.initiate_workflow(
        user_id=1,
        prompt="A cyberpunk detective story"
    )
    
    # Get pending tasks
    tasks = await db.get_pending_tasks('story_generator')
    
    # Clean up old data
    await db.cleanup_old_workflows(days=7)
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing

Run the test suite:

```bash
pytest src/tests/
```

## Security Features

- All database operations use parameterized queries
- Sensitive data is encrypted using Fernet encryption
- Database backups are encrypted using SQLCipher
- Row-level security through view filters
- Content hash verification for artifacts

## Maintenance

The system includes built-in maintenance features:

- Automatic index rebuilding
- Old workflow cleanup
- Connection pool management
- Transaction management with rollback support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
