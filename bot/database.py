import sqlite3
import asyncio
from datetime import datetime
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_path: str = "drink_check_bot.db"):
        self.db_path = db_path
        self.connection = None
        
    async def initialize(self):
        """Create tables if they don't exist"""
        await self._create_tables()
        
    async def _create_tables(self):
        """Create the necessary database tables"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        # Create drink_checks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drink_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                author_id TEXT NOT NULL,
                author_name TEXT,
                content TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                response_count INTEGER DEFAULT 0
            )
        ''')
        
        # Create responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drink_check_id INTEGER NOT NULL,
                message_id TEXT UNIQUE NOT NULL,
                author_id TEXT NOT NULL,
                author_name TEXT,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (drink_check_id) REFERENCES drink_checks (id)
            )
        ''')
        
        # Create users table for caching
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                drink_check_count INTEGER DEFAULT 0,
                response_count INTEGER DEFAULT 0,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    async def _get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
        
    async def save_drink_check(self, message_id: str, author_id: str, author_name: str,
                              content: str, channel_id: str) -> int:
        """Insert drink check, return ID"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO drink_checks (message_id, author_id, author_name, content, channel_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (message_id, author_id, author_name, content, channel_id))
            
            drink_check_id = cursor.lastrowid
            
            # Update user stats
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, drink_check_count, last_seen)
                VALUES (?, ?, 
                    COALESCE((SELECT drink_check_count FROM users WHERE user_id = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            ''', (author_id, author_name, author_id))
            
            conn.commit()
            return drink_check_id
            
        except sqlite3.IntegrityError:
            # Message already exists
            conn.rollback()
            return -1
        finally:
            conn.close()
        
    async def save_response(self, drink_check_id: int, message_id: str,
                           author_id: str, author_name: str, content: str) -> int:
        """Insert response"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO responses (drink_check_id, message_id, author_id, author_name, content)
                VALUES (?, ?, ?, ?, ?)
            ''', (drink_check_id, message_id, author_id, author_name, content))
            
            response_id = cursor.lastrowid
            
            # Update drink check response count
            cursor.execute('''
                UPDATE drink_checks 
                SET response_count = response_count + 1
                WHERE id = ?
            ''', (drink_check_id,))
            
            # Update user stats
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, response_count, last_seen)
                VALUES (?, ?, 
                    COALESCE((SELECT response_count FROM users WHERE user_id = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            ''', (author_id, author_name, author_id))
            
            conn.commit()
            return response_id
            
        except sqlite3.IntegrityError:
            # Message already exists
            conn.rollback()
            return -1
        finally:
            conn.close()
        
    async def get_user_stats(self, user_id: str) -> dict:
        """Query user statistics"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        # Get user's stats
        cursor.execute('''
            SELECT drink_check_count, response_count, username
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            drink_checks, responses, username = result
        else:
            drink_checks, responses, username = 0, 0, "Unknown"
            
        # Get total stats
        cursor.execute('SELECT COUNT(*) FROM drink_checks')
        total_drink_checks = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM responses')
        total_responses = cursor.fetchone()[0]
        
        # Get user's rank
        cursor.execute('''
            SELECT COUNT(*) + 1 FROM users 
            WHERE drink_check_count > (SELECT drink_check_count FROM users WHERE user_id = ?)
        ''', (user_id,))
        
        rank_result = cursor.fetchone()
        rank = rank_result[0] if rank_result else 0
        
        conn.close()
        
        return {
            "drink_checks": drink_checks,
            "responses": responses,
            "total_drink_checks": total_drink_checks,
            "total_responses": total_responses,
            "user_rank": rank,
            "username": username
        }
        
    async def get_leaderboard(self, stat_type: str) -> list:
        """Query leaderboard data"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        if stat_type == "drink_checks":
            cursor.execute('''
                SELECT user_id, username, drink_check_count 
                FROM users 
                ORDER BY drink_check_count DESC 
                LIMIT 10
            ''')
        elif stat_type == "responses":
            cursor.execute('''
                SELECT user_id, username, response_count 
                FROM users 
                ORDER BY response_count DESC 
                LIMIT 10
            ''')
        else:
            conn.close()
            return []
            
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    async def get_drink_check_by_message_id(self, message_id: str) -> Optional[int]:
        """Get drink check ID by Discord message ID"""
        conn = await self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM drink_checks WHERE message_id = ?', (message_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None