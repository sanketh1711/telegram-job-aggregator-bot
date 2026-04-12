import sqlite3
import os
from datetime import datetime

DATABASE_FILE = 'users.db'

def init_database():
    """Initialize the SQLite database with users table"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_until TEXT DEFAULT NULL,
            searches_today INTEGER DEFAULT 0,
            viewed_today INTEGER DEFAULT 0,
            last_search TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

def add_user(user_id, username=None, first_name=None):
    """Add a new user to the database"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """Get user data from database"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    
    conn.close()
    return user

def is_premium(user_id):
    """Check if user is premium"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('SELECT is_premium, premium_until FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        is_prem, premium_until = result
        if is_prem and premium_until:
            if datetime.fromisoformat(premium_until) > datetime.now():
                return True
        return False
    return False

def add_premium(user_id, days=30):
    """Add premium status to user for X days"""
    from datetime import timedelta
    
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    premium_until = (datetime.now() + timedelta(days=days)).isoformat()
    
    c.execute('''
        UPDATE users 
        SET is_premium = 1, premium_until = ?
        WHERE user_id = ?
    ''', (premium_until, user_id))
    
    conn.commit()
    conn.close()

def remove_premium(user_id):
    """Remove premium status from user"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET is_premium = 0, premium_until = NULL
        WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()

def increment_searches(user_id):
    """Increment search count for today"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET searches_today = searches_today + 1, last_search = ?
        WHERE user_id = ?
    ''', (datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()

def increment_viewed(user_id, count=1):
    """Increment viewed jobs count for today"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET viewed_today = viewed_today + ?
        WHERE user_id = ?
    ''', (count, user_id))
    
    conn.commit()
    conn.close()

def reset_daily_counts():
    """Reset daily search and view counts (run daily)"""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    
    c.execute('''
        UPDATE users 
        SET searches_today = 0, viewed_today = 0
    ''')
    
    conn.commit()
    conn.close()