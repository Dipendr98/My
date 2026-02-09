"""
Database module for CC Killer Bot
PostgreSQL for Railway, with SQLite fallback for local development
"""
import os
import asyncio
from datetime import datetime
import hashlib
import random
import string

# Try to import asyncpg for PostgreSQL, fallback to sqlite3
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    print("[WARNING] asyncpg not installed, using SQLite fallback")


import sqlite3
import json

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Global connection pool
db_pool = None

def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code for user."""
    base = f"{user_id}{datetime.now().timestamp()}"
    hash_obj = hashlib.md5(base.encode())
    return hash_obj.hexdigest()[:8].upper()

# ============ PostgreSQL Functions ============
async def init_postgres():
    """Initialize PostgreSQL connection pool and create tables."""
    global db_pool
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set!")
        return False
    
    try:
        # Railway uses postgres:// but asyncpg needs postgresql://
        db_url = DATABASE_URL.replace("postgres://", "postgresql://")
        db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        
        async with db_pool.acquire() as conn:
            # Create users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    credits INTEGER DEFAULT 10,
                    plan TEXT DEFAULT 'FREE',
                    is_vip BOOLEAN DEFAULT FALSE,
                    is_registered BOOLEAN DEFAULT FALSE,
                    referral_code TEXT UNIQUE,
                    referred_by BIGINT,
                    referral_count INTEGER DEFAULT 0,
                    expiry TIMESTAMP,
                    joined_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # Create referrals tracking table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL UNIQUE,
                    credited BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )
            ''')
            
        print("[OK] PostgreSQL initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False

async def pg_get_user(user_id: int) -> dict:
    """Get user from PostgreSQL."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
        if row:
            return dict(row)
        return None

async def pg_create_user(user_id: int, username: str = None, first_name: str = None, referred_by_code: str = None) -> dict:
    """Create new user in PostgreSQL."""
    referral_code = generate_referral_code(user_id)
    referred_by = None
    
    # Check if referred by code exists
    if referred_by_code:
        async with db_pool.acquire() as conn:
            referrer = await conn.fetchrow('SELECT user_id FROM users WHERE referral_code = $1', referred_by_code.upper())
            if referrer and referrer['user_id'] != user_id:
                referred_by = referrer['user_id']
    
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, username, first_name, referral_code, referred_by, credits, is_registered)
            VALUES ($1, $2, $3, $4, $5, 10, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                is_registered = TRUE,
                last_active = NOW()
        ''', user_id, username, first_name, referral_code, referred_by)
        
        # If referred, add referral tracking and give credits to referrer
        if referred_by:
            try:
                await conn.execute('''
                    INSERT INTO referrals (referrer_id, referred_id, credited)
                    VALUES ($1, $2, FALSE)
                    ON CONFLICT (referred_id) DO NOTHING
                ''', referred_by, user_id)
                
                # Check if already credited
                ref_row = await conn.fetchrow(
                    'SELECT credited FROM referrals WHERE referrer_id = $1 AND referred_id = $2',
                    referred_by, user_id
                )
                
                if ref_row and not ref_row['credited']:
                    # Give 10 credits to referrer
                    await conn.execute(
                        'UPDATE users SET credits = credits + 10, referral_count = referral_count + 1 WHERE user_id = $1',
                        referred_by
                    )
                    # Mark as credited
                    await conn.execute(
                        'UPDATE referrals SET credited = TRUE WHERE referrer_id = $1 AND referred_id = $2',
                        referred_by, user_id
                    )
                    print(f"✅ Referral Credit: +10 to user {referred_by} from {user_id}")
            except Exception as e:
                print(f"Referral error: {e}")
    
    return await pg_get_user(user_id)

async def pg_update_user(user_id: int, **kwargs) -> bool:
    """Update user fields in PostgreSQL."""
    if not kwargs:
        return False
    
    set_clauses = []
    values = []
    for i, (key, value) in enumerate(kwargs.items(), 1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value)
    
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(set_clauses)}, last_active = NOW() WHERE user_id = ${len(values)}"
    
    async with db_pool.acquire() as conn:
        await conn.execute(query, *values)
    return True

async def pg_update_credits(user_id: int, amount: int) -> bool:
    """Update user credits (add or subtract)."""
    async with db_pool.acquire() as conn:
        if amount < 0:
            # Check if enough credits
            row = await conn.fetchrow('SELECT credits, is_vip FROM users WHERE user_id = $1', user_id)
            if row:
                if row['is_vip']:
                    return True  # VIP has unlimited
                if row['credits'] + amount < 0:
                    return False  # Not enough credits
        
        await conn.execute(
            'UPDATE users SET credits = credits + $1, last_active = NOW() WHERE user_id = $2',
            amount, user_id
        )
        return True

async def pg_get_all_users(limit: int = 50, offset: int = 0) -> list:
    """Get all registered users."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            'SELECT * FROM users WHERE is_registered = TRUE ORDER BY joined_at DESC LIMIT $1 OFFSET $2',
            limit, offset
        )
        return [dict(row) for row in rows]

async def pg_get_user_count() -> int:
    """Get total registered users count."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow('SELECT COUNT(*) FROM users WHERE is_registered = TRUE')
        return row['count'] if row else 0

async def pg_get_referral_stats(user_id: int) -> dict:
    """Get referral statistics for a user."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT referral_code, referral_count, referred_by FROM users WHERE user_id = $1',
            user_id
        )
        if row:
            return {
                "referral_code": row['referral_code'],
                "referral_count": row['referral_count'],
                "referred_by": row['referred_by']
            }
        return None

# ============ SQLite Fallback Functions ============
SQLITE_DB = os.path.join(os.path.dirname(__file__), "bot_database.db")

def init_sqlite():
    """Initialize SQLite database for local development."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            credits INTEGER DEFAULT 10,
            plan TEXT DEFAULT 'FREE',
            is_vip INTEGER DEFAULT 0,
            is_registered INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            expiry TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            credited INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[OK] SQLite initialized")
    return True

def sqlite_get_user(user_id: int) -> dict:
    """Get user from SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def sqlite_create_user(user_id: int, username: str = None, first_name: str = None, referred_by_code: str = None) -> dict:
    """Create new user in SQLite."""
    referral_code = generate_referral_code(user_id)
    referred_by = None
    
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check referrer
    if referred_by_code:
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referred_by_code.upper(),))
        referrer = cursor.fetchone()
        if referrer and referrer['user_id'] != user_id:
            referred_by = referrer['user_id']
    
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, referral_code, referred_by, credits, is_registered)
        VALUES (?, ?, ?, ?, ?, 10, 1)
    ''', (user_id, username, first_name, referral_code, referred_by))
    
    # Handle referral
    if referred_by:
        cursor.execute('SELECT credited FROM referrals WHERE referrer_id = ? AND referred_id = ?', (referred_by, user_id))
        ref_row = cursor.fetchone()
        
        if not ref_row:
            cursor.execute('INSERT INTO referrals (referrer_id, referred_id, credited) VALUES (?, ?, 0)', (referred_by, user_id))
            cursor.execute('UPDATE users SET credits = credits + 10, referral_count = referral_count + 1 WHERE user_id = ?', (referred_by,))
            cursor.execute('UPDATE referrals SET credited = 1 WHERE referrer_id = ? AND referred_id = ?', (referred_by, user_id))
    
    conn.commit()
    conn.close()
    
    return sqlite_get_user(user_id)

def sqlite_update_credits(user_id: int, amount: int) -> bool:
    """Update credits in SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute('SELECT credits, is_vip FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        if row[1]:  # is_vip
            conn.close()
            return True
        if row[0] + amount < 0:
            conn.close()
            return False
    
    cursor.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    return True

def sqlite_get_all_users(limit: int = 50, offset: int = 0) -> list:
    """Get all users from SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE is_registered = 1 ORDER BY joined_at DESC LIMIT ? OFFSET ?', (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def sqlite_get_user_count() -> int:
    """Get user count from SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_registered = 1')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ============ Unified Interface ============
class Database:
    """Unified database interface - uses PostgreSQL if available, SQLite otherwise."""
    
    def __init__(self):
        self.use_postgres = False
        self.initialized = False
    
    async def init(self):
        """Initialize database connection."""
        if DATABASE_URL and HAS_ASYNCPG:
            self.use_postgres = await init_postgres()
        
        if not self.use_postgres:
            init_sqlite()
        
        self.initialized = True
        return True
    
    async def get_user(self, user_id: int) -> dict:
        """Get user by ID."""
        if self.use_postgres:
            return await pg_get_user(user_id)
        return sqlite_get_user(user_id)
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, referral_code: str = None) -> dict:
        """Create or update user."""
        if self.use_postgres:
            return await pg_create_user(user_id, username, first_name, referral_code)
        return sqlite_create_user(user_id, username, first_name, referral_code)
    
    async def update_credits(self, user_id: int, amount: int) -> bool:
        """Update user credits."""
        if self.use_postgres:
            return await pg_update_credits(user_id, amount)
        return sqlite_update_credits(user_id, amount)
    
    async def get_all_users(self, limit: int = 50, offset: int = 0) -> list:
        """Get all registered users."""
        if self.use_postgres:
            return await pg_get_all_users(limit, offset)
        return sqlite_get_all_users(limit, offset)
    
    async def get_user_count(self) -> int:
        """Get total user count."""
        if self.use_postgres:
            return await pg_get_user_count()
        return sqlite_get_user_count()
    
    async def get_referral_stats(self, user_id: int) -> dict:
        """Get referral stats for user."""
        user = await self.get_user(user_id)
        if user:
            return {
                "referral_code": user.get('referral_code'),
                "referral_count": user.get('referral_count', 0),
                "referred_by": user.get('referred_by')
            }
        return None

# Global database instance
db = Database()

print("[OK] Database module loaded")
