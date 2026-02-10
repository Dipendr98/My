"""
Database module for CC Killer Bot
MySQL for Railway, with SQLite fallback for local development
"""
import os
import asyncio
from datetime import datetime
import hashlib
import random
import string

# Try to import aiomysql for MySQL, fallback to sqlite3
try:
    import aiomysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    print("[WARNING] aiomysql not installed, using SQLite fallback")

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

# ============ MySQL Functions ============
async def init_mysql():
    """Initialize MySQL connection pool and create tables."""
    global db_pool
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set!")
        return False
    
    try:
        # Parse DATABASE_URL manually if needed or let aiomysql handle it
        # aiomysql doesn't support the full URI string in create_pool directly like asyncpg sometimes does
        # But we can try to parse it or pass it if the driver supports it. 
        # Actually, aiomysql.create_pool doesn't take a DSN string directly in the same way.
        # It's safer to parse the URL or expect standard params.
        # However, many frameworks use a parser. Let's try a simple parse or pass as kwargs if expected.
        # For simplicity/compatibility with Railway's mysql://... user:pass@host:port/db
        
        # We'll use a helper to parse the DSN if possible, or just expect the user to have valid vars.
        # A simple URI parser:
        from urllib.parse import urlparse
        result = urlparse(DATABASE_URL)
        
        username = result.username
        password = result.password
        host = result.hostname
        port = result.port or 3306
        db_name = result.path.lstrip('/')
        
        db_pool = await aiomysql.create_pool(
            host=host, 
            port=port,
            user=username, 
            password=password, 
            db=db_name,
            autocommit=True,
            minsize=2, 
            maxsize=10
        )
        
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Create users table
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        credits INTEGER DEFAULT 10,
                        plan VARCHAR(50) DEFAULT 'FREE',
                        is_vip BOOLEAN DEFAULT FALSE,
                        is_registered BOOLEAN DEFAULT FALSE,
                        referral_code VARCHAR(50) UNIQUE,
                        referred_by BIGINT,
                        referral_count INTEGER DEFAULT 0,
                        expiry DATETIME,
                        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create referrals tracking table
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS referrals (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        referrer_id BIGINT NOT NULL,
                        referred_id BIGINT NOT NULL UNIQUE,
                        credited BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                        FOREIGN KEY (referred_id) REFERENCES users(user_id)
                    )
                ''')
            
        print("[OK] MySQL initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ MySQL Error: {e}")
        return False

async def mysql_get_user(user_id: int) -> dict:
    """Get user from MySQL."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            row = await cur.fetchone()
            if row:
                # Normalize datetime objects if needed
                return dict(row)
            return None

async def mysql_create_user(user_id: int, username: str = None, first_name: str = None, referred_by_code: str = None) -> dict:
    """Create new user in MySQL."""
    referral_code = generate_referral_code(user_id)
    referred_by = None
    
    # Check if referred by code exists
    if referred_by_code:
        async with db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute('SELECT user_id FROM users WHERE referral_code = %s', (referred_by_code.upper(),))
                referrer = await cur.fetchone()
                if referrer and referrer['user_id'] != user_id:
                    referred_by = referrer['user_id']
    
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            # MySQL UPSERT (INSERT ... ON DUPLICATE KEY UPDATE)
            await cur.execute('''
                INSERT INTO users (user_id, username, first_name, referral_code, referred_by, credits, is_registered)
                VALUES (%s, %s, %s, %s, %s, 10, TRUE)
                ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    is_registered = TRUE,
                    last_active = NOW()
            ''', (user_id, username, first_name, referral_code, referred_by))
            
            # If referred, add referral tracking and give credits to referrer
            if referred_by:
                try:
                    # Insert referral record
                    await cur.execute('''
                        INSERT IGNORE INTO referrals (referrer_id, referred_id, credited)
                        VALUES (%s, %s, FALSE)
                    ''', (referred_by, user_id))
                    
                    # Check if actually inserted (or already existed) - tricky with IGNORE, let's select
                    await cur.execute(
                        'SELECT credited FROM referrals WHERE referrer_id = %s AND referred_id = %s',
                        (referred_by, user_id)
                    )
                    ref_row = await cur.fetchone() # returns tuple in standard cursor
                    
                    # ref_row[0] is 'credited' check
                    if ref_row and not ref_row[0]:
                        # Give 10 credits to referrer
                        await cur.execute(
                            'UPDATE users SET credits = credits + 10, referral_count = referral_count + 1 WHERE user_id = %s',
                            (referred_by,)
                        )
                        # Mark as credited
                        await cur.execute(
                            'UPDATE referrals SET credited = TRUE WHERE referrer_id = %s AND referred_id = %s',
                            (referred_by, user_id)
                        )
                        print(f"✅ Referral Credit: +10 to user {referred_by} from {user_id}")
                except Exception as e:
                    print(f"Referral error: {e}")
    
    return await mysql_get_user(user_id)

async def mysql_update_user(user_id: int, **kwargs) -> bool:
    """Update user fields in MySQL."""
    if not kwargs:
        return False
    
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)
    
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(set_clauses)}, last_active = NOW() WHERE user_id = %s"
    
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, tuple(values))
    return True

async def mysql_update_credits(user_id: int, amount: int) -> bool:
    """Update user credits (add or subtract)."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if amount < 0:
                # Check if enough credits
                await cur.execute('SELECT credits, is_vip FROM users WHERE user_id = %s', (user_id,))
                row = await cur.fetchone()
                if row:
                    if row['is_vip']:
                        return True  # VIP has unlimited
                    if row['credits'] + amount < 0:
                        return False  # Not enough credits
            
            await cur.execute(
                'UPDATE users SET credits = credits + %s, last_active = NOW() WHERE user_id = %s',
                (amount, user_id)
            )
            return True

async def mysql_get_all_users(limit: int = 50, offset: int = 0) -> list:
    """Get all registered users."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                'SELECT * FROM users WHERE is_registered = TRUE ORDER BY joined_at DESC LIMIT %s OFFSET %s',
                (limit, offset)
            )
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

async def mysql_get_user_count() -> int:
    """Get total registered users count."""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT COUNT(*) FROM users WHERE is_registered = TRUE')
            row = await cur.fetchone()
            return row[0] if row else 0

async def mysql_get_referral_stats(user_id: int) -> dict:
    """Get referral statistics for a user."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                'SELECT referral_code, referral_count, referred_by FROM users WHERE user_id = %s',
                (user_id,)
            )
            row = await cur.fetchone()
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
    """Unified database interface - uses MySQL if available, SQLite otherwise."""
    
    def __init__(self):
        self.use_mysql = False
        self.initialized = False
    
    async def init(self):
        """Initialize database connection."""
        if DATABASE_URL and HAS_MYSQL:
            self.use_mysql = await init_mysql()
        
        if not self.use_mysql:
            init_sqlite()
        
        self.initialized = True
        return True

    async def _query(self, query: str, *args):
        """Raw query execution helper (Compatibility)."""
        try:
            if self.use_mysql:
                async with db_pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        # Handle args if nested tuple
                        q_args = args[0] if len(args) == 1 and isinstance(args[0], tuple) else args
                        await cur.execute(query, q_args)
                        if query.strip().upper().startswith("SELECT"):
                             rows = await cur.fetchall()
                             return [dict(row) for row in rows]
                        return True
            else:
                 # SQLite fallback
                 conn = sqlite3.connect(SQLITE_DB)
                 # Map %s to ?
                 q_sqlite = query.replace("%s", "?")
                 conn.row_factory = sqlite3.Row
                 cursor = conn.cursor()
                 q_args = args[0] if len(args) == 1 and isinstance(args[0], tuple) else args
                 cursor.execute(q_sqlite, q_args)
                 if query.strip().upper().startswith("SELECT"):
                     rows = cursor.fetchall()
                     conn.close()
                     return [dict(row) for row in rows]
                 conn.commit()
                 conn.close()
                 return True
        except Exception as e:
            print(f"[_query] Error: {e}")
            return None
    
    async def get_user(self, user_id: int) -> dict:
        """Get user by ID."""
        if self.use_mysql:
            return await mysql_get_user(user_id)
        return sqlite_get_user(user_id)
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, referral_code: str = None) -> dict:
        """Create or update user."""
        if self.use_mysql:
            return await mysql_create_user(user_id, username, first_name, referral_code)
        return sqlite_create_user(user_id, username, first_name, referral_code)
    
    async def update_credits(self, user_id: int, amount: int) -> bool:
        """Update user credits."""
        if self.use_mysql:
            return await mysql_update_credits(user_id, amount)
        return sqlite_update_credits(user_id, amount)
    
    async def get_all_users(self, limit: int = 50, offset: int = 0) -> list:
        """Get all registered users."""
        if self.use_mysql:
            return await mysql_get_all_users(limit, offset)
        return sqlite_get_all_users(limit, offset)
    
    async def get_user_count(self) -> int:
        """Get total user count."""
        if self.use_mysql:
            return await mysql_get_user_count()
        return sqlite_get_user_count()
    
    async def get_referral_stats(self, user_id: int) -> dict:
        """Get referral stats for user."""
        if self.use_mysql:
            return await mysql_get_referral_stats(user_id)
        
        # SQLite Fallback for this method logic
        # (It was missing in the original fallback, so we use the generic getter)
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
