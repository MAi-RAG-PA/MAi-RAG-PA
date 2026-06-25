# ~/MAi-RAG/app/memory/sqlite_memory.py
import sqlite3
import json
import logging
import uuid
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Optional

# =============================================================================
# Configuration: SQLite Database Path
# =============================================================================

DB_PATH = Path(__file__).parent / "memory_store.db"
logger = logging.getLogger(__name__)

# =============================================================================
# SQLiteMemoryManager Class
# =============================================================================

class SQLiteMemoryManager:
    """
    Unified manager for Short-Term Memory (SQLite).
    Handles: chat threads/messages, planner data (events/reminders/todos), 
    user profile, notes, and generic key-value storage.
    """
    
    SYSTEM_PROMPT_KEY = "system_prompt"
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize connection and ensure tables exist."""
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Enable foreign keys and WAL mode for better concurrency
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        
        self._create_tables()
        self._migrate_tables()
    
    @contextmanager
    def get_cursor(self):
        """Context manager for safe, transactional DB access."""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"SQLite transaction error: {e}", exc_info=True)
            raise
        finally:
            cursor.close()
    
    def _create_tables(self):
        """Create all necessary tables if they don't exist."""
        with self.get_cursor() as cur:
            # === Events table with recurrence support ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    location TEXT,
                    category TEXT DEFAULT 'general',
                    is_recurring INTEGER DEFAULT 0,
                    recurrence_type TEXT,
                    recurrence_days TEXT,
                    recurrence_end_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0
                )
            """)
            self._create_index_safe(cur, "events", "start_time")
            self._create_index_safe(cur, "events", "category")
            
            # === Generic Key-Value Store ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    confidence REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            self._create_index_safe(cur, "user_facts", "category")

            # === Notes ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === Chat Threads ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # === Chat Messages ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                )
            """)
            self._create_index_safe(cur, "chat_messages", "thread_id")
            self._create_index_safe(cur, "chat_messages", "timestamp")
            
            # === Reminders ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    due_time TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    completed BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._create_index_safe(cur, "reminders", "due_time")
            self._create_index_safe(cur, "reminders", "completed")
            
            # === To-Do Items ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT DEFAULT 'medium',
                    completed BOOLEAN DEFAULT FALSE,
                    due_date TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    order_index INTEGER DEFAULT 0
                )
            """)
            self._create_index_safe(cur, "todos", "due_date")
            self._create_index_safe(cur, "todos", "completed")
            
            # === User Profile ===
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _migrate_tables(self):
        """Add missing columns to existing tables (for upgrades)."""
        with self.get_cursor() as cur:
            # Check if events table has recurrence columns
            cur.execute("PRAGMA table_info(events)")
            columns = [row[1] for row in cur.fetchall()]

            # Add recurrence columns if missing
            if 'is_recurring' not in columns:
                logger.info("Migrating events table: adding recurrence columns")
                cur.execute("ALTER TABLE events ADD COLUMN is_recurring INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE events ADD COLUMN recurrence_type TEXT")
                cur.execute("ALTER TABLE events ADD COLUMN recurrence_days TEXT")
                cur.execute("ALTER TABLE events ADD COLUMN recurrence_end_date TEXT")
        
            # Always check for updated_at separately
            if 'updated_at' not in columns:
                logger.info("Migrating events table: adding updated_at column")
                cur.execute("ALTER TABLE events ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    def _create_index_safe(self, cur, table_name: str, column_name: str):
        """Safely create an index only if the column exists."""
        try:
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cur.fetchall()]
            if column_name in columns:
                index_name = f"idx_{table_name}_{column_name}"
                cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
        except Exception as e:
            logger.warning(f"Could not create index on {table_name}.{column_name}: {e}")
    
    # =============================================================================
    # Generic Key-Value Store Methods
    # =============================================================================
    
    def set(self, key: str, value: str) -> bool:
        """Set a key-value pair in short-term memory with robust error handling."""
        try:
            value_str = value if isinstance(value, str) else json.dumps(value)
            
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT OR REPLACE INTO short_term_memory (key, value, timestamp)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value_str))
            logger.debug(f"Set key '{key}' in short_term_memory")
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"SQLite OperationalError setting key '{key}': {e}")
            logger.error(f"DB path: {self.db_path}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting key '{key}': {e}", exc_info=True)
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get a value by key from short-term memory."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT value FROM short_term_memory WHERE key = ?", (key,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from short-term memory."""
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM short_term_memory WHERE key = ?", (key,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete key '{key}': {e}")
            return False
    
    # =============================================================================
    # System Prompt Methods
    # =============================================================================
    
    def get_system_prompt(self) -> str:
        """Get the system prompt, with fallback default."""
        prompt = self.get(self.SYSTEM_PROMPT_KEY)
        if prompt is None:
            prompt = "You are a personal assistant who grows with your user."
        return prompt
    
    def set_system_prompt(self, prompt_text: str) -> bool:
        """Save the system prompt."""
        return self.set(self.SYSTEM_PROMPT_KEY, prompt_text)
    
    # =============================================================================
    # Notes Methods
    # =============================================================================
    
    def set_note(self, note_id: str, title: str, content: str) -> bool:
        """Create or update a note."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1 FROM notes WHERE id = ?", (note_id,))
                if cur.fetchone():
                    cur.execute("""
                        UPDATE notes 
                        SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (title, content, note_id))
                else:
                    cur.execute("""
                        INSERT INTO notes (id, title, content) 
                        VALUES (?, ?, ?)
                    """, (note_id, title, content))
            return True
        except Exception as e:
            logger.error(f"Failed to save note '{note_id}': {e}")
            return False
    
    def get_note(self, note_id: str) -> Optional[dict]:
        """Get a note by ID."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT id, title, content, created_at, updated_at 
                FROM notes WHERE id = ?
            """, (note_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_notes_list(self, limit: int = 50) -> list[dict]:
        """List notes, ordered by last updated."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT id, title, created_at, updated_at 
                FROM notes 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    
    def delete_note(self, note_id: str) -> bool:
        """Delete a note by ID."""
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete note '{note_id}': {e}")
            return False
    
    # =============================================================================
    # Chat Auto-Save Methods
    # =============================================================================
    
    def save_chat_thread(self, thread_id: str, title: Optional[str] = None) -> str:
        """Save or update a chat thread metadata."""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO chat_threads (id, title, created_at, last_message_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (thread_id, title))
        return thread_id
    
    def save_chat_message(
        self, 
        thread_id: str, 
        role: str, 
        content: str, 
        message_id: Optional[str] = None
    ) -> str:
        """Save a chat message and update thread's last_message_at."""
        message_id = message_id or str(uuid.uuid4())
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1 FROM chat_threads WHERE id = ?", (thread_id,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO chat_threads (id, title, created_at, last_message_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (thread_id, f"Chat {thread_id[:8]}"))
            
                cur.execute("""
                    INSERT INTO chat_messages (id, thread_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (message_id, thread_id, role, content))
                cur.execute("""
                    UPDATE chat_threads 
                    SET last_message_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (thread_id,))
            return message_id
        except Exception as e:
            logger.error(f"Failed to save chat message: {e}", exc_info=True)
            raise
    
    def get_chat_messages(self, thread_id: str, limit: int = 50) -> list[dict]:
        """Get recent messages for a thread."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT id, role, content, timestamp 
                FROM chat_messages 
                WHERE thread_id = ? 
                ORDER BY timestamp ASC 
                LIMIT ?
            """, (thread_id, limit))
            return [dict(row) for row in cur.fetchall()]
    
    def get_chat_threads(self, limit: int = 20) -> list[dict]:
        """List chat threads, ordered by last activity."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT id, title, created_at, last_message_at 
                FROM chat_threads 
                ORDER BY last_message_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    
    # =============================================================================
    # Planner Auto-Save Methods
    # =============================================================================
    
    def save_event(self, event: dict) -> str:
        """Save or update an event."""
        event_id = event.get("id") or str(uuid.uuid4())
    
        logger.info(f"Saving event: {event.get('title')}")
        logger.info(f"is_recurring: {event.get('is_recurring')}")
        logger.info(f"recurrence_type: {event.get('recurrence_type')}")
        logger.info(f"recurrence_days: {event.get('recurrence_days')}")
        logger.info(f"recurrence_end_date: {event.get('recurrence_end_date')}")
    
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO events 
                (id, title, description, start_time, end_time, location, category,
                 is_recurring, recurrence_type, recurrence_days, recurrence_end_date,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                event_id,
                event["title"],
                event.get("description"),
                event["start_time"],
                event.get("end_time"),
                event.get("location"),
                event.get("category", "general"),
                1 if event.get("is_recurring") else 0,
                event.get("recurrence_type"),
                json.dumps(event.get("recurrence_days")) if event.get("recurrence_days") else None,
                event.get("recurrence_end_date")
            ))
        
        # If recurring, generate instances
        if event.get("is_recurring"):
            self._generate_recurring_events(event_id, event)
        
        return event_id

    def _generate_recurring_events(self, base_event_id: str, event: dict):
        """Generate recurring event instances."""
        from datetime import datetime, timedelta

        recurrence_type = event.get("recurrence_type")
        recurrence_days = event.get("recurrence_days", [])
        recurrence_end_date = event.get("recurrence_end_date")

        if not recurrence_type or not recurrence_end_date:
            logger.info(f"No recurrence type or end date for event {base_event_id}")
            return

        # Parse dates - handle different formats safely
        try:
            start_time_str = event["start_time"]
            if start_time_str.endswith('Z'):
                start_time_str = start_time_str[:-1]
            start_time = datetime.fromisoformat(start_time_str)

            end_date_str = recurrence_end_date
            if end_date_str.endswith('Z'):
                end_date_str = end_date_str[:-1]
            end_date = datetime.fromisoformat(end_date_str)
            
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                end_date = end_date.replace(hour=23, minute=59, second=59)

            logger.info(f"Generating recurring events from {start_time} to {end_date}")
        except Exception as e:
            logger.error(f"Failed to parse dates for recurring event: {e}")
            logger.error(f"Start time: {event.get('start_time')}")
            logger.error(f"End date: {recurrence_end_date}")
            return

        current = start_time
        event_count = 0
        max_events = 365

        while current <= end_date and event_count < max_events:
            should_create = False

            if recurrence_type == "daily":
                should_create = True
            elif recurrence_type == "weekly":
                day_name = current.strftime("%A").lower()
                if day_name in [d.lower() for d in recurrence_days]:
                    should_create = True
            elif recurrence_type == "monthly":
                should_create = current.day == start_time.day
            elif recurrence_type == "yearly":
                should_create = (current.month == start_time.month and 
                               current.day == start_time.day)

            if should_create:
                current_date = current.strftime('%Y-%m-%d')
                start_date = start_time.strftime('%Y-%m-%d')
                
                if current_date == start_date:
                    logger.debug(f"Skipping instance for start date {current_date}")
                    current += timedelta(days=1)
                    continue
                
                instance_id = f"{base_event_id}_{current.strftime('%Y%m%d')}"
                instance = event.copy()
                instance["id"] = instance_id
                instance["start_time"] = current.isoformat()
                instance["is_recurring"] = False

                if event.get("end_time"):
                    try:
                        original_end_str = event["end_time"]
                        if original_end_str.endswith('Z'):
                            original_end_str = original_end_str[:-1]
                        original_end = datetime.fromisoformat(original_end_str)
                        
                        duration = original_end - start_time
                        instance_end = current + duration
                        instance["end_time"] = instance_end.isoformat()
                    except Exception as e:
                        logger.error(f"Failed to calculate end time: {e}")
                        instance["end_time"] = None

                try:
                    with self.get_cursor() as cur:
                        cur.execute("""
                            INSERT OR REPLACE INTO events 
                            (id, title, description, start_time, end_time, location, category,
                             is_recurring, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            instance_id,
                            instance["title"],
                            instance.get("description"),
                            instance["start_time"],
                            instance.get("end_time"),
                            instance.get("location"),
                            instance.get("category", "general")
                        ))
                    event_count += 1
                    logger.info(f"Created recurring event instance: {instance_id} at {instance['start_time']}")
                except Exception as e:
                    logger.error(f"Failed to create recurring event instance: {e}")

            current += timedelta(days=1)

        logger.info(f"Generated {event_count} recurring event instances for {base_event_id}")

    def delete_event(self, event_id: str) -> bool:
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False
    
    def get_upcoming_events(self, limit: int = 10) -> list[dict]:
        """Get upcoming events, ordered by start time."""
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT id, title, description, start_time, end_time, location, category, 
                           is_recurring, recurrence_type, recurrence_days, recurrence_end_date, order_index
                    FROM events 
                    WHERE start_time >= datetime('now') 
                    ORDER BY start_time ASC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []

    def get_all_events(self, limit: int = 1000) -> list[dict]:
        """Get ALL events including past recurring instances."""
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT id, title, description, start_time, end_time, location, category, 
                           is_recurring, recurrence_type, recurrence_days, recurrence_end_date, order_index
                    FROM events 
                    ORDER BY start_time ASC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get all events: {e}")
            return []
    
    def save_reminder(self, reminder: dict) -> str:
        """Save or update a reminder."""
        reminder_id = reminder.get("id") or str(uuid.uuid4())
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO reminders 
                (id, text, due_time, priority, completed, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                reminder_id,
                reminder["text"],
                reminder["due_time"],
                reminder.get("priority", "medium"),
                reminder.get("completed", False)
            ))
        return reminder_id
    
    def delete_reminder(self, reminder_id: str) -> bool:
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete reminder: {e}")
            return False

    def get_pending_reminders(self, limit: int = 20) -> list[dict]:
        """Get reminders that are not yet completed."""
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT id, text, due_time, priority, completed 
                    FROM reminders 
                    WHERE completed = FALSE 
                    ORDER BY due_time ASC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get pending reminders: {e}")
            return []

    def save_todo(self, todo: dict) -> str:
        """Save or update a to-do item."""
        todo_id = todo.get("id") or str(uuid.uuid4())
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO todos 
                (id, title, description, priority, completed, due_date, created_at, order_index)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                todo_id,
                todo["title"],
                todo.get("description"),
                todo.get("priority", "medium"),
                todo.get("completed", False),
                todo.get("due_date"),
                todo.get("order_index", 0)
            ))
        return todo_id
    
    def get_pending_todos(self, limit: int = 20) -> list[dict]:
        """Get to-dos that are not yet completed, ordered by order_index."""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT id, title, description, priority, completed, due_date, order_index
                FROM todos 
                WHERE completed = FALSE 
                ORDER BY 
                    order_index ASC,
                    CASE WHEN due_date IS NOT NULL THEN 0 ELSE 1 END,
                    due_date ASC,
                    created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    def delete_todo(self, todo_id: str) -> bool:
        """Delete a todo by ID."""
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete todo: {e}")
            return False

    # =============================================================================
    # User Profile / Preferences Methods
    # =============================================================================
    
    def save_user_profile(self, key: str, value: Any) -> bool:
        """Save a user preference or profile field."""
        try:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT OR REPLACE INTO user_profile (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value_str))
            return True
        except Exception as e:
            logger.error(f"Failed to save user profile '{key}': {e}")
            return False
    
    def get_user_preference(self, key: str) -> Any:
        """Get a user preference by key."""
        with self.get_cursor() as cur:
            cur.execute("SELECT value FROM user_profile WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
        return None
    
    def get_user_profile(self) -> dict:
        """Get all user profile data as a dictionary."""
        with self.get_cursor() as cur:
            cur.execute("SELECT key, value FROM user_profile")
            rows = cur.fetchall()
            profile = {}
            for row in rows:
                try:
                    profile[row[0]] = json.loads(row[1])
                except json.JSONDecodeError:
                    profile[row[0]] = row[1]
            return profile
    
    # =============================================================================
    # Manual Ingestion Helper
    # =============================================================================
    
    def ingest_documents(self, table_name: str, documents: list[dict]) -> int:
        """Bulk insert documents into a specific table."""
        valid_tables = ['chat_threads', 'chat_messages', 'events', 'reminders', 'todos', 'user_profile', 'notes', 'short_term_memory']
        if table_name not in valid_tables:
            raise ValueError(f"Invalid table: {table_name}. Must be one of {valid_tables}")
        
        count = 0
        with self.get_cursor() as cur:
            for doc in documents:
                try:
                    columns = ", ".join(doc.keys())
                    placeholders = ", ".join(["?"] * len(doc))
                    values = list(doc.values())
                    cur.execute(f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})", values)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to ingest document into {table_name}: {e}")
                    continue
        return count
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False