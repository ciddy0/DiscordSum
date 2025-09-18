"""
Database operations using SQLite
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Extract database file from URL
DB_FILE = DATABASE_URL.replace('sqlite:///', '')

@contextmanager
def get_db():
    """Get a database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def is_channel_monitored(guild_id: int, channel_id: int) -> bool:
    """Check if a channel is being monitored (active only)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM monitored_channels 
            WHERE guild_id = ? AND channel_id = ? AND active = 1
        ''', (guild_id, channel_id))
        return cursor.fetchone() is not None

def channel_exists_in_db(guild_id: int, channel_id: int) -> bool:
    """Check if a channel exists in database (active or inactive)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM monitored_channels 
            WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        return cursor.fetchone() is not None

def add_monitored_channel(guild_id: int, channel_id: int, channel_name: str, 
                         user_id: int, username: str) -> bool:
    """Add a channel to monitoring or reactivate existing one"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # First, check if channel already exists (active or inactive)
            cursor.execute('''
                SELECT id, active FROM monitored_channels 
                WHERE guild_id = ? AND channel_id = ?
            ''', (guild_id, channel_id))
            existing = cursor.fetchone()
            
            if existing:
                # reactivate it and update info
                cursor.execute('''
                    UPDATE monitored_channels 
                    SET active = 1, 
                        channel_name = ?, 
                        setup_by_user_id = ?, 
                        setup_by_username = ?,
                        created_at = CURRENT_TIMESTAMP
                    WHERE guild_id = ? AND channel_id = ?
                ''', (channel_name, user_id, username, guild_id, channel_id))
                logger.info(f"Reactivated channel {channel_name} ({channel_id}) for monitoring")
            else:
                # Channel doesn't exist, create new entry
                cursor.execute('''
                    INSERT INTO monitored_channels 
                    (guild_id, channel_id, channel_name, setup_by_user_id, setup_by_username)
                    VALUES (?, ?, ?, ?, ?)
                ''', (guild_id, channel_id, channel_name, user_id, username))
                logger.info(f"Added new channel {channel_name} ({channel_id}) to monitoring")
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to add monitored channel: {e}")
        return False

def remove_monitored_channel(guild_id: int, channel_id: int) -> bool:
    """Stop monitoring a channel (set active = 0)"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE monitored_channels 
                SET active = 0 
                WHERE guild_id = ? AND channel_id = ?
            ''', (guild_id, channel_id))
            conn.commit()
            logger.info(f"Removed channel {channel_id} from monitoring")
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to remove monitored channel: {e}")
        return False

def get_channel_info(guild_id: int, channel_id: int, active_only: bool = True) -> dict:
    """Get information about a monitored channel"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT * FROM monitored_channels 
                WHERE guild_id = ? AND channel_id = ? AND active = 1
            ''', (guild_id, channel_id))
        else:
            cursor.execute('''
                SELECT * FROM monitored_channels 
                WHERE guild_id = ? AND channel_id = ?
            ''', (guild_id, channel_id))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def store_message(guild_id: int, channel_id: int, message_id: int, 
                 author_id: int, author_name: str, content: str, 
                 timestamp: datetime, has_attachments: bool = False, 
                 reply_to: int = None) -> bool:
    """Store a message in the database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO stored_messages 
                (guild_id, channel_id, message_id, author_id, author_name, 
                 content, timestamp, has_attachments, reply_to)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (guild_id, channel_id, message_id, author_id, author_name, 
                  content, timestamp, has_attachments, reply_to))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to store message {message_id}: {e}")
        return False

def get_message_count(guild_id: int, channel_id: int) -> int:
    """Get the number of stored messages for a channel"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM stored_messages 
            WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        return cursor.fetchone()[0]

def get_messages(guild_id: int, channel_id: int, limit: int = 100, 
                offset: int = 0) -> list:
    """Get stored messages for a channel"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM stored_messages 
            WHERE guild_id = ? AND channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (guild_id, channel_id, limit, offset))
        return [dict(row) for row in cursor.fetchall()]

def get_messages_by_timeframe(guild_id: int, channel_id: int, hours: int, limit: int = 1000) -> list:
    """Get stored messages for a channel within the specified timeframe"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM stored_messages 
            WHERE guild_id = ? AND channel_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (guild_id, channel_id, cutoff_time.isoformat(), limit))
        return [dict(row) for row in cursor.fetchall()]

def get_message_stats(guild_id: int, channel_id: int, hours: int = None) -> dict:
    """Get message statistics for a channel, optionally within timeframe"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        if hours:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT author_id) as unique_authors,
                    MIN(timestamp) as oldest_message,
                    MAX(timestamp) as newest_message
                FROM stored_messages 
                WHERE guild_id = ? AND channel_id = ? AND timestamp >= ?
            ''', (guild_id, channel_id, cutoff_time.isoformat()))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT author_id) as unique_authors,
                    MIN(timestamp) as oldest_message,
                    MAX(timestamp) as newest_message
                FROM stored_messages 
                WHERE guild_id = ? AND channel_id = ?
            ''', (guild_id, channel_id))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            'total_messages': 0,
            'unique_authors': 0, 
            'oldest_message': None,
            'newest_message': None
        }