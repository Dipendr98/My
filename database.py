"""
Database module for CC Killer Bot
MySQL (aiomysql) for Railway, with SQLite fallback for local development
"""
import os
import asyncio
from datetime import datetime
import hashlib
import random
import string
import json

# Try to import aiomysql for MySQL, fallback to sqlite3
try:
    import aiomysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    print("⚠️ aiomysql not installed, using SQLite fallback")

import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Global connection pool
db_pool = None



# ============ MySQL Functions ============
async def init_mysql():
    """Initialize MySQL connection pool and create tables."""
    global db_pool
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set!")
        return False
    
    try:
        # Parse DATABASE_URL (mysql://user:pass@host:port/db)
        from urllib.parse import urlparse
        url = urlparse(DATABASE_URL)
        
        db_name = url.path[1:]
        
        # 1. Connect without DB to create it if missing
        initial_config = {
            'host': url.hostname,
            'port': url.port or 3306,
            'user': url.username,
            'password': url.password,
            'autocommit': True
        }
        
        try:
            conn = await aiomysql.connect(**initial_config)
            async with conn.cursor() as cur:
                await cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                print(f"✅ Database '{db_name}' checked/created.")
            conn.close()
        except Exception as e:
            print(f"⚠️ Could not create DB (might exist or perm issue): {e}")

        # 2. Connect to the specific DB
        db_config = initial_config.copy()
        db_config['db'] = db_name

        db_pool = await aiomysql.create_pool(**db_config, minsize=2, maxsize=10)
        
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Create users table
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        credits INTEGER DEFAULT 10,
                        plan VARCHAR(255) DEFAULT 'FREE',
                        is_vip BOOLEAN DEFAULT FALSE,
                        is_registered BOOLEAN DEFAULT FALSE,
                        expiry TIMESTAMP NULL,
                        features JSON,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                ''')
                


                # Create proxies table
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS proxies (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        proxy TEXT NOT NULL,
                        status VARCHAR(50) DEFAULT 'live',
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create sites table
                await cur.execute('''
                    CREATE TABLE IF NOT EXISTS sites (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        url TEXT NOT NULL,
                        status VARCHAR(50) DEFAULT 'active',
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
        print("✅ MySQL initialized successfully!")
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
                # Parse JSON features if string (depends on driver/version)
                if isinstance(row.get('features'), str):
                     try:
                         row['features'] = json.loads(row['features'])
                     except:
                         row['features'] = []
                # Ensure features is a list
                if row.get('features') is None:
                    row['features'] = []
                return row
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
            # Upsert User
            await cur.execute('''
                INSERT INTO users (user_id, username, first_name, referral_code, referred_by, credits, is_registered, features)
                VALUES (%s, %s, %s, %s, %s, 10, TRUE, '[]')
                ON DUPLICATE KEY UPDATE 
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    is_registered = TRUE,
                    last_active = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, referral_code, referred_by))
            
            # If referred, add referral tracking and give credits to referrer
            if referred_by:
                try:
                    # Insert referral record
                    await cur.execute('''
                        INSERT IGNORE INTO referrals (referrer_id, referred_id, credited)
                        VALUES (%s, %s, FALSE)
                    ''', (referred_by, user_id))
                    
                    # Check if credited
                    await cur.execute(
                        'SELECT credited FROM referrals WHERE referrer_id = %s AND referred_id = %s',
                        (referred_by, user_id)
                    )
                    ref_row = await cur.fetchone()
                    
                    if ref_row and not ref_row[0]: # 0 is 'credited' col index
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
        # Handle list/dict for JSON column
        if key == 'features' and isinstance(value, (list, dict)):
             values.append(json.dumps(value))
        else:
             values.append(value)
    
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(set_clauses)}, last_active = CURRENT_TIMESTAMP WHERE user_id = %s"
    
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
                'UPDATE users SET credits = credits + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s',
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
            # Clean features
            for row in rows:
                if isinstance(row.get('features'), str):
                     try: row['features'] = json.loads(row['features'])
                     except: row['features'] = []
                if row.get('features') is None: row['features'] = []
            return rows

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

            return None

async def mysql_add_proxy(proxy: str):
    """Add a proxy to MySQL."""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('INSERT INTO proxies (proxy) VALUES (%s)', (proxy,))
    return True

async def mysql_get_proxies():
    """Get all live proxies from MySQL."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT proxy FROM proxies WHERE status = 'live'")
            rows = await cur.fetchall()
            return [row['proxy'] for row in rows]

async def mysql_clear_proxies():
    """Clear all proxies."""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('TRUNCATE TABLE proxies')
    return True

async def mysql_add_site(url: str):
    """Add a site to MySQL."""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('INSERT INTO sites (url) VALUES (%s)', (url,))
    return True

async def mysql_get_sites():
    """Get all active sites from MySQL."""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT url FROM sites WHERE status = 'active'")
            rows = await cur.fetchall()
            return [row['url'] for row in rows]

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
            features TEXT DEFAULT '[]',
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy TEXT NOT NULL,
            status TEXT DEFAULT 'live',
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ SQLite initialized")
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
        d = dict(row)
        # Handle features JSON
        if isinstance(d.get('features'), str):
             try: d['features'] = json.loads(d['features'])
             except: d['features'] = []
        if d.get('features') is None: d['features'] = []
        return d
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
        INSERT OR REPLACE INTO users (user_id, username, first_name, referral_code, referred_by, credits, is_registered, features)
        VALUES (?, ?, ?, ?, ?, 10, 1, '[]')
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

def sqlite_update_user(user_id: int, **kwargs) -> bool:
     # ... (Implementation similar to postgres but usage is rare in prod)
     conn = sqlite3.connect(SQLITE_DB)
     cursor = conn.cursor()
     set_clauses = []
     values = []
     for key, value in kwargs.items():
         set_clauses.append(f"{key} = ?")
         if key == 'features' and isinstance(value, (list, dict)):
             values.append(json.dumps(value))
         else:
             values.append(value)
     values.append(user_id)
     cursor.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?", tuple(values))
     conn.commit()
     conn.close()
     return True

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
    res = []
    for row in rows:
        d = dict(row)
        if isinstance(d.get('features'), str):
             try: d['features'] = json.loads(d['features'])
             except: d['features'] = []
        if d.get('features') is None: d['features'] = []
        res.append(d)
    return res

def sqlite_get_user_count() -> int:
    """Get user count from SQLite."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_registered = 1')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def sqlite_add_proxy(proxy: str):
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO proxies (proxy) VALUES (?)', (proxy,))
    conn.commit()
    conn.close()
    return True

def sqlite_get_proxies():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT proxy FROM proxies WHERE status = 'live'")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def sqlite_clear_proxies():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM proxies') # SQLite doesn't support TRUNCATE
    conn.commit()
    conn.close()
    return True

def sqlite_add_site(url: str):
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sites (url) VALUES (?)', (url,))
    conn.commit()
    conn.close()
    return True

def sqlite_get_sites():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM sites WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

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
    
    async def update_user(self, user_id: int, **kwargs) -> bool:
         """Update user fields."""
         if self.use_mysql:
             return await mysql_update_user(user_id, **kwargs)
         return sqlite_update_user(user_id, **kwargs)

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
        user = await self.get_user(user_id)
        if user:
            return {
                "referral_code": user.get('referral_code'),
                "referral_count": user.get('referral_count', 0),
                "referred_by": user.get('referred_by')
            }
        return None

    async def add_proxy(self, proxy: str):
        if self.use_mysql:
            return await mysql_add_proxy(proxy)
        return sqlite_add_proxy(proxy)

    async def get_proxies(self):
        if self.use_mysql:
            return await mysql_get_proxies()
        return sqlite_get_proxies()

    async def clear_proxies(self):
        if self.use_mysql:
            return await mysql_clear_proxies()
        return sqlite_clear_proxies()

    async def add_site(self, url: str):
        if self.use_mysql:
            return await mysql_add_site(url)
        return sqlite_add_site(url)

    async def get_sites(self):
        if self.use_mysql:
            return await mysql_get_sites()
        return sqlite_get_sites()

# Global database instance
db = Database()

print("✅ Database module loaded (MySQL/SQLite)")
