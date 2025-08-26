"""Persistent memory for long-term storage and learning."""

import asyncio
import sqlite3
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from .base import BaseMemory, MemoryEntry, MemoryType, MemoryStats


class PersistentMemory(BaseMemory):
    """SQLite-based persistent memory storage."""
    
    def __init__(self, db_path: Optional[Path] = None, max_entries: int = 10000):
        super().__init__(max_entries)
        self.db_path = db_path or Path.home() / ".ai_coding_agent" / "memory.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the database."""
        async with self._lock:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            
            # Create tables
            await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create database tables."""
        cursor = self._connection.cursor()
        
        # Main memory entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME NOT NULL,
                importance REAL NOT NULL,
                tags TEXT,
                embeddings BLOB,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accessed_count INTEGER DEFAULT 0,
                last_accessed DATETIME
            )
        ''')
        
        # Index for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON memory_entries(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires ON memory_entries(expires_at)')
        
        # Learning patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self._connection.commit()
    
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry persistently."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            # Serialize complex data
            metadata_json = json.dumps(entry.metadata) if entry.metadata else None
            tags_json = json.dumps(entry.tags) if entry.tags else None
            embeddings_blob = pickle.dumps(entry.embeddings) if entry.embeddings else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO memory_entries 
                (id, type, content, metadata, timestamp, importance, tags, embeddings, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id,
                entry.type.value,
                entry.content,
                metadata_json,
                entry.timestamp,
                entry.importance,
                tags_json,
                embeddings_blob,
                entry.expires_at
            ))
            
            self._connection.commit()
            
            # Clean up if we exceed max entries
            await self._cleanup_if_needed()
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Retrieve memory entries based on query."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            # Build query conditions
            conditions = ["(content LIKE ? OR metadata LIKE ?)"]
            params = [f"%{query}%", f"%{query}%"]
            
            if memory_type:
                conditions.append("type = ?")
                params.append(memory_type.value)
            
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
                conditions.append(f"({' OR '.join(tag_conditions)})")
            
            # Execute query
            sql = f'''
                SELECT * FROM memory_entries 
                WHERE {' AND '.join(conditions)}
                ORDER BY importance DESC, timestamp DESC 
                LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            entries = []
            for row in rows:
                entry = await self._row_to_entry(row)
                entries.append(entry)
                
                # Update access count
                await self._update_access_count(entry.id)
            
            return entries
    
    async def get_recent(
        self, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryEntry]:
        """Get recent memory entries."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            conditions = []
            params = []
            
            if memory_type:
                conditions.append("type = ?")
                params.append(memory_type.value)
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            sql = f'''
                SELECT * FROM memory_entries 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            entries = []
            for row in rows:
                entry = await self._row_to_entry(row)
                entries.append(entry)
            
            return entries
    
    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            # Check if entry exists
            cursor.execute("SELECT id FROM memory_entries WHERE id = ?", (entry_id,))
            if not cursor.fetchone():
                return False
            
            # Build update query
            update_fields = []
            params = []
            
            if 'content' in updates:
                update_fields.append("content = ?")
                params.append(updates['content'])
            
            if 'metadata' in updates:
                update_fields.append("metadata = ?")
                params.append(json.dumps(updates['metadata']))
            
            if 'importance' in updates:
                update_fields.append("importance = ?")
                params.append(max(0.0, min(1.0, updates['importance'])))
            
            if 'tags' in updates:
                update_fields.append("tags = ?")
                params.append(json.dumps(updates['tags']))
            
            if not update_fields:
                return False
            
            params.append(entry_id)
            
            sql = f"UPDATE memory_entries SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, params)
            self._connection.commit()
            
            return cursor.rowcount > 0
    
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            cursor.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            self._connection.commit()
            
            return cursor.rowcount > 0
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """Clear memory entries."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            if memory_type is None:
                cursor.execute("DELETE FROM memory_entries")
            else:
                cursor.execute("DELETE FROM memory_entries WHERE type = ?", (memory_type.value,))
            
            self._connection.commit()
    
    async def count(self) -> int:
        """Get total number of memory entries."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            return cursor.fetchone()[0]
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            now = datetime.now()
            
            cursor.execute(
                "DELETE FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,)
            )
            self._connection.commit()
            
            return cursor.rowcount
    
    async def _cleanup_if_needed(self) -> None:
        """Clean up old entries if max_entries is exceeded."""
        current_count = await self.count()
        
        if current_count <= self.max_entries:
            return
        
        # Remove entries to get back to 90% of max_entries
        target_count = int(self.max_entries * 0.9)
        entries_to_remove = current_count - target_count
        
        cursor = self._connection.cursor()
        cursor.execute('''
            DELETE FROM memory_entries 
            WHERE id IN (
                SELECT id FROM memory_entries 
                ORDER BY importance ASC, timestamp ASC 
                LIMIT ?
            )
        ''', (entries_to_remove,))
        self._connection.commit()
    
    async def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert database row to MemoryEntry."""
        # Deserialize complex data
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        tags = json.loads(row['tags']) if row['tags'] else []
        embeddings = pickle.loads(row['embeddings']) if row['embeddings'] else None
        
        return MemoryEntry(
            id=row['id'],
            type=MemoryType(row['type']),
            content=row['content'],
            metadata=metadata,
            timestamp=datetime.fromisoformat(row['timestamp']),
            importance=row['importance'],
            tags=tags,
            embeddings=embeddings,
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
        )
    
    async def _update_access_count(self, entry_id: str) -> None:
        """Update access count and last accessed time."""
        cursor = self._connection.cursor()
        cursor.execute('''
            UPDATE memory_entries 
            SET accessed_count = accessed_count + 1, last_accessed = ?
            WHERE id = ?
        ''', (datetime.now(), entry_id))
        self._connection.commit()
    
    async def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            total_entries = cursor.fetchone()[0]
            
            if total_entries == 0:
                return MemoryStats()
            
            # Entries by type
            cursor.execute('''
                SELECT type, COUNT(*) FROM memory_entries 
                GROUP BY type
            ''')
            entries_by_type = {MemoryType(row[0]): row[1] for row in cursor.fetchall()}
            
            # Timestamp stats
            cursor.execute('''
                SELECT MIN(timestamp), MAX(timestamp), AVG(importance)
                FROM memory_entries
            ''')
            min_ts, max_ts, avg_importance = cursor.fetchone()
            
            return MemoryStats(
                total_entries=total_entries,
                entries_by_type=entries_by_type,
                memory_usage_mb=self._estimate_db_size(),
                oldest_entry=datetime.fromisoformat(min_ts) if min_ts else None,
                newest_entry=datetime.fromisoformat(max_ts) if max_ts else None,
                avg_importance=avg_importance or 0.0
            )
    
    def _estimate_db_size(self) -> float:
        """Estimate database size in MB."""
        try:
            return self.db_path.stat().st_size / (1024 * 1024)
        except FileNotFoundError:
            return 0.0
    
    async def store_learning_pattern(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Store a learning pattern."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            pattern_json = json.dumps(pattern_data)
            
            # Check if pattern exists
            cursor.execute('''
                SELECT id, success_count, failure_count FROM learning_patterns 
                WHERE pattern_type = ? AND pattern_data = ?
            ''', (pattern_type, pattern_json))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                pattern_id, success_count, failure_count = existing
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                
                total_attempts = success_count + failure_count
                confidence = success_count / total_attempts if total_attempts > 0 else 0.5
                
                cursor.execute('''
                    UPDATE learning_patterns 
                    SET success_count = ?, failure_count = ?, confidence = ?, updated_at = ?
                    WHERE id = ?
                ''', (success_count, failure_count, confidence, datetime.now(), pattern_id))
            else:
                # Create new pattern
                success_count = 1 if success else 0
                failure_count = 0 if success else 1
                confidence = 1.0 if success else 0.0
                
                cursor.execute('''
                    INSERT INTO learning_patterns 
                    (pattern_type, pattern_data, success_count, failure_count, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern_type, pattern_json, success_count, failure_count, confidence))
            
            self._connection.commit()
    
    async def get_learning_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.6,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get learning patterns."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            conditions = ["confidence >= ?"]
            params = [min_confidence]
            
            if pattern_type:
                conditions.append("pattern_type = ?")
                params.append(pattern_type)
            
            sql = f'''
                SELECT * FROM learning_patterns 
                WHERE {' AND '.join(conditions)}
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            patterns = []
            for row in rows:
                patterns.append({
                    'id': row['id'],
                    'pattern_type': row['pattern_type'],
                    'pattern_data': json.loads(row['pattern_data']),
                    'success_count': row['success_count'],
                    'failure_count': row['failure_count'],
                    'confidence': row['confidence'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return patterns
    
    async def store_user_preference(self, key: str, value: Any, category: str = "general") -> None:
        """Store a user preference."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            value_json = json.dumps(value)
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_preferences (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (key, value_json, category, datetime.now()))
            
            self._connection.commit()
    
    async def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['value'])
            return default
    
    async def get_user_preferences(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get all user preferences."""
        async with self._lock:
            if not self._connection:
                await self.initialize()
            
            cursor = self._connection.cursor()
            
            if category:
                cursor.execute(
                    "SELECT key, value FROM user_preferences WHERE category = ?",
                    (category,)
                )
            else:
                cursor.execute("SELECT key, value FROM user_preferences")
            
            rows = cursor.fetchall()
            
            preferences = {}
            for row in rows:
                preferences[row['key']] = json.loads(row['value'])
            
            return preferences
    
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None