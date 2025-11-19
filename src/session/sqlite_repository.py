"""
SQLite implementation of SessionRepository
"""
import sqlite3
import json
import asyncio
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path
from session.repository import SessionRepository
from utils.logger import get_logger

logger = get_logger()


class SQLiteSessionRepository(SessionRepository):
    """SQLite-based session storage"""
    
    def __init__(self, db_path: str = "data/sessions.db"):
        self.db_path = db_path
        self._conn = None
        self._ensure_db_directory()
        self._init_db()
        logger.info(f"SQLite session repository initialized: {db_path}")
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        if self.db_path != ":memory:":
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_db(self):
        """Initialize database schema"""
        # For :memory: databases, keep a persistent connection
        if self.db_path == ":memory:":
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        
        cursor = conn.cursor()
        
        # Check if sessions table exists and has expires_at column
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sessions'
        """)
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check if expires_at column exists
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if "expires_at" not in columns:
                # Add expires_at column with default value (7 days from now)
                logger.info("Migrating sessions table: adding expires_at column")
                
                # First add column without default
                cursor.execute("""
                    ALTER TABLE sessions 
                    ADD COLUMN expires_at TEXT
                """)
                
                # Then update existing rows with expires_at = last_accessed + 7 days
                cursor.execute("""
                    UPDATE sessions 
                    SET expires_at = datetime(last_accessed, '+7 days')
                    WHERE expires_at IS NULL
                """)
                
                conn.commit()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        
        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id 
            ON messages(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed 
            ON sessions(last_accessed)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at 
            ON sessions(expires_at)
        """)
        
        conn.commit()
        if self.db_path != ":memory:":
            conn.close()
        logger.debug("Database schema initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        # For :memory: databases, reuse the persistent connection
        if self.db_path == ":memory:" and self._conn:
            return self._conn
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _close_connection(self, conn: sqlite3.Connection):
        """Close connection if not using :memory:"""
        if self.db_path != ":memory:":
            conn.close()
    
    async def save_session(
        self, 
        session_id: str, 
        created_at: datetime, 
        last_accessed: datetime,
        expires_at: datetime
    ) -> bool:
        """Save or update session metadata"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sessions (session_id, created_at, last_accessed, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_accessed = excluded.last_accessed,
                    expires_at = excluded.expires_at
            """, (
                session_id,
                created_at.isoformat(),
                last_accessed.isoformat(),
                expires_at.isoformat()
            ))
            
            conn.commit()
            self._close_connection(conn)
            return True
            
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session metadata"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, created_at, last_accessed, expires_at
                FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            self._close_connection(conn)
            
            if row:
                return {
                    "session_id": row["session_id"],
                    "created_at": datetime.fromisoformat(row["created_at"]),
                    "last_accessed": datetime.fromisoformat(row["last_accessed"]),
                    "expires_at": datetime.fromisoformat(row["expires_at"])
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all its messages"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Foreign key cascade will delete messages automatically
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            self._close_connection(conn)
            
            if deleted:
                logger.info(f"Deleted session: {session_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, created_at, last_accessed, expires_at
                FROM sessions
                ORDER BY last_accessed DESC
            """)
            
            rows = cursor.fetchall()
            self._close_connection(conn)
            
            return [
                {
                    "session_id": row["session_id"],
                    "created_at": datetime.fromisoformat(row["created_at"]),
                    "last_accessed": datetime.fromisoformat(row["last_accessed"]),
                    "expires_at": datetime.fromisoformat(row["expires_at"])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return []
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: datetime,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save a message to session"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO messages (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                role,
                content,
                timestamp.isoformat(),
                metadata_json
            ))
            
            conn.commit()
            self._close_connection(conn)
            return True
            
        except Exception as e:
            logger.error(f"Error saving message for session {session_id}: {e}")
            return False
    
    async def get_messages(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get messages for a session"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                # Get last N messages
                query = f"""
                    SELECT role, content, timestamp, metadata
                    FROM (
                        SELECT role, content, timestamp, metadata
                        FROM messages
                        WHERE session_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                    ORDER BY timestamp ASC
                """
                cursor.execute(query, (session_id, limit))
            else:
                cursor.execute(query, (session_id,))
            
            rows = cursor.fetchall()
            self._close_connection(conn)
            
            return [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    async def delete_messages(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            
            conn.commit()
            self._close_connection(conn)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting messages for session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self, expiry_time: datetime) -> int:
        """Delete sessions that have expired (expires_at < now)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM sessions
                WHERE expires_at < ?
            """, (expiry_time.isoformat(),))
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            self._close_connection(conn)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_session_count(self) -> int:
        """Get total number of active sessions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            row = cursor.fetchone()
            self._close_connection(conn)
            
            return row["count"] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting session count: {e}")
            return 0
    
    async def get_total_message_count(self) -> int:
        """Get total number of messages across all sessions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            row = cursor.fetchone()
            self._close_connection(conn)
            
            return row["count"] if row else 0
            
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
