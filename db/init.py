"""
Database initialization script.
Run this once to create the database tables.
"""
import os
from dotenv import load_dotenv
import sqlite3
import logging

# load env variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database config
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///discord_summarizer.db')

def create_tables():
    """Create tables using raw SQL"""
    
    # Extract filename from DATABASE_URL
    db_file = DATABASE_URL.replace('sqlite:///', '')
    
    logger.info(f"Creating database: {db_file}")
    
    # Connect to SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Create monitored_channels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                setup_by_user_id INTEGER NOT NULL,
                setup_by_username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                UNIQUE(guild_id, channel_id)
            )
        ''')
        
        # Create stored_messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stored_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER UNIQUE NOT NULL,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT,
                timestamp TIMESTAMP NOT NULL,
                has_attachments BOOLEAN DEFAULT 0,
                reply_to INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance :D
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monitored_guild_channel ON monitored_channels(guild_id, channel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_guild_channel ON stored_messages(guild_id, channel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON stored_messages(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_id ON stored_messages(message_id)')
        
        # Commit changes
        conn.commit()
        logger.info("Database tables created successfully!")
        
        # Show table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Created tables: {[table[0] for table in tables]}")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
    print("Database initialization complete!")
    print("You can now run the bot with: python bot.py")