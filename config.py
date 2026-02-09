import os
import json
import asyncio
import time
import aiohttp
import random
from dotenv import load_dotenv
from database import db

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
UPI_ID = os.getenv("UPI_ID", "your-upi@id")
PAYMENT_QR_URL = os.getenv("PAYMENT_QR_URL", "")
WELCOME_PHOTO_URL = os.getenv("WELCOME_PHOTO_URL", "") # URL or local path in assets/
DEVELOPER_NAME = os.getenv("DEVELOPER_NAME", "@Oracle0812")
PROJECT_NAME = os.getenv("PROJECT_NAME", "CC KILLER")
PROJECT_TAG = os.getenv("PROJECT_TAG", "CRACKED BY @Oracle0812")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

# Gateway API Keys (from env vars or defaults)
import re
temp_sk = os.getenv("STRIPE_SK", "")
# Remove STRIPE_SK= prefix (case insensitive), remove quotes, strip whitespace
STRIPE_SK = re.sub(r'(?i)^STRIPE_SK\s*=\s*', '', temp_sk).replace('"', '').replace("'", "").strip()
STRIPE_HITTER_API = os.getenv("STRIPE_HITTER_API", "https://stripe-hitter.onrender.com/stripe/checkout-based/url/{YOUR_CHECKOUT_URL}/pay/cc/{YOUR_CC}")
BT_MERCHANT_ID = os.getenv("BT_MERCHANT_ID", "")
BT_PUBLIC_KEY = os.getenv("BT_PUBLIC_KEY", "")
BT_PRIVATE_KEY = os.getenv("BT_PRIVATE_KEY", "")
RZP_KEY_ID = os.getenv("RZP_KEY_ID", os.getenv("RAZORPAY_KEY", ""))
RZP_KEY_SECRET = os.getenv("RZP_KEY_SECRET", os.getenv("RAZORPAY_SECRET", ""))
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY", "")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
PAYU_MERCHANT_KEY = os.getenv("PAYU_MERCHANT_KEY", "")
PAYU_MERCHANT_SALT = os.getenv("PAYU_MERCHANT_SALT", "")
PROXY_URL = os.getenv("PROXY_URL", "")
AMAZON_COOKIE = os.getenv("AMAZON_COOKIE", "")
HITTER_URL = os.getenv("HITTER_URL", "")
NMI_API = os.getenv("NMI_API", "")
PAYFLOW_API = os.getenv("PAYFLOW_API", "")
SHOPIFY_AUTH_API = os.getenv("SHOPIFY_AUTH_API", "")
VBV_API = os.getenv("VBV_API", "")
PAYPAL_API = os.getenv("PAYPAL_API", "")
WOOSTRIPE_API = os.getenv("WOOSTRIPE_API", "")
WOOSTRIPE_API_2 = os.getenv("WOOSTRIPE_API_2", "")
WOOSTRIPE_API_3 = os.getenv("WOOSTRIPE_API_3", "")
NONSK_API_1 = os.getenv("NONSK_API_1", "")
NONSK_API_2 = os.getenv("NONSK_API_2", "")
NONSK_API_3 = os.getenv("NONSK_API_3", "")
NONSK_API_4 = os.getenv("NONSK_API_4", "")
SAVVY_API = os.getenv("SAVVY_API", "")
INBUILT_CVV_API = os.getenv("INBUILT_CVV_API", "")
INBUILT_CCN_API = os.getenv("INBUILT_CCN_API", "")
BT_AUTH_API = os.getenv("BT_AUTH_API", "")
BT_AUTH2_API = os.getenv("BT_AUTH2_API", "")
BT_CHARGE_API = os.getenv("BT_CHARGE_API", "")
PAYPAL_KEYS = os.getenv("PAYPAL_KEYS", "")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

def get_asset_path(filename):
    if not filename: return None
    local_path = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(local_path):
        return local_path
    return filename # assume its a URL if not local

# List of authorized user IDs
authorized_raw = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS = [int(u.strip()) for u in authorized_raw.split(",") if u.strip().isdigit()]
if OWNER_ID and OWNER_ID not in AUTHORIZED_USERS:
    AUTHORIZED_USERS.append(OWNER_ID)

# SITES MANAGEMENT
SITES_FILE = os.path.join(os.path.dirname(__file__), "sites.json")

def load_sites():
    # Try file first
    if os.path.exists(SITES_FILE):
        try:
            with open(SITES_FILE, "r") as f:
                return json.load(f)
        except: pass
    
    # Fallback to ENV VAR (for Railway persistence)
    env_sites = os.getenv("SITES_LIST", "")
    if env_sites:
        return [s.strip() for s in env_sites.split(",") if s.strip()]
    return []

def save_site(url):
    sites = load_sites()
    if url not in sites:
        sites.append(url)
        with open(SITES_FILE, "w") as f:
            json.dump(sites, f)
        # Also print for Railway logs (user can add to env var)
        print(f"📌 SITE ADDED: {url} | Total: {len(sites)}")
        print(f"💡 To persist, add to Railway ENV: SITES_LIST={','.join(sites)}")
        return True
    return False

# SUBSCRIPTION PLANS
PLANS = {
    "BASIC": {"credits": 100, "price": 5, "validity": None},
    "STANDARD": {"credits": 500, "price": 20, "validity": None},
    "ULTIMATE": {"credits": 2000, "price": 50, "validity": None},
    "VIP": {"credits": 0, "price": 100, "validity": 30} # Credits 0 means logic check for VIP
}

# USERS MANAGEMENT (Credits & VIP)
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
from datetime import datetime, timedelta

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_user_data(user_id):
    users = load_users()
    user_id_str = str(user_id)
    now = datetime.now()
    
    if user_id_str not in users:
        # Initial gift for new users
        users[user_id_str] = {
            "credits": 10, 
            "plan": "FREE", 
            "is_vip": False, 
            "expiry": None,
            "joined_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users(users)
    
    data = users[user_id_str]
    
    # Check Expiry
    if data.get("expiry"):
        expiry_dt = datetime.strptime(data["expiry"], "%Y-%m-%d %H:%M:%S")
        if now > expiry_dt:
            # Plan Expired
            users[user_id_str]["plan"] = "FREE"
            users[user_id_str]["is_vip"] = False
            users[user_id_str]["expiry"] = None
            save_users(users)
            data = users[user_id_str]
            
    return data

def update_user_credits(user_id, amount):
    # Credits input should be POSITIVE for addition, NEGATIVE for deduction
    users = load_users()
    user_id_str = str(user_id)
    
    # OWNER / AUTHORIZED USERS = UNLIMITED
    if user_id in AUTHORIZED_USERS or user_id == OWNER_ID:
        return True
        
    data = get_user_data(user_id) # also handles expiry check
    
    # VIP / ULTIMATE USERS = UNLIMITED CREDITS
    if data.get("is_vip") or data.get("plan") in ["VIP", "ULTIMATE"]:
        return True
    
    if data["credits"] + amount < 0:
        return False
    
    users = load_users() # reload after get_user_data might have saved
    users[user_id_str]["credits"] += amount
    save_users(users)
    return True

def set_user_plan(user_id, plan_name):
    # Ensure user exists first
    get_user_data(user_id) 
    
    # Then load fresh data
    users = load_users()
    user_id_str = str(user_id)
    
    plan_info = PLANS.get(plan_name)
    if not plan_info:
        return False
        
    users[user_id_str]["plan"] = plan_name
    if plan_name == "VIP":
        users[user_id_str]["is_vip"] = True
    else:
        users[user_id_str]["is_vip"] = False
        users[user_id_str]["credits"] += plan_info["credits"]
        
    if plan_info["validity"]:
        expiry = datetime.now() + timedelta(days=plan_info["validity"])
        users[user_id_str]["expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    else:
        users[user_id_str]["expiry"] = None
        
    save_users(users)
    return True

def set_user_vip(user_id, status=True):
    return set_user_plan(user_id, "VIP") if status else False

def grant_feature(user_id, feature):
    """Grant a specific feature access (steam, b3, mass_razorpay)."""
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        get_user_data(user_id)
        users = load_users()
        
    if "features" not in users[user_id_str]:
        users[user_id_str]["features"] = []
        
    if feature not in users[user_id_str]["features"]:
        users[user_id_str]["features"].append(feature)
        save_users(users)
        return True
    return False

def revoke_feature(user_id, feature):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users and "features" in users[user_id_str]:
        if feature in users[user_id_str]["features"]:
            users[user_id_str]["features"].remove(feature)
            save_users(users)
            return True
    return False

def has_feature_access(user_id, feature):
    """Check if user has access to a feature."""
    if user_id in AUTHORIZED_USERS or user_id == OWNER_ID:
        return True
        
    data = get_user_data(user_id)
    
    # VIPs have access to EVERYTHING
    if data.get("is_vip"):
        return True
        
    features = data.get("features", [])
    
    if feature in features:
        return True
        
    return False

# PROXY & SITE MANAGEMENT (DB-Backed)

PROXY_CACHE = []
LAST_PROXY_REFRESH = 0
PROXY_REFRESH_INTERVAL = 300 # 5 minutes

async def refresh_proxy_cache():
    """Refresh proxy cache from DB."""
    global PROXY_CACHE, LAST_PROXY_REFRESH
    if time.time() - LAST_PROXY_REFRESH > PROXY_REFRESH_INTERVAL or not PROXY_CACHE:
        if not db.initialized:
            await db.init()
        PROXY_CACHE = await db.get_proxies()
        LAST_PROXY_REFRESH = time.time()
        # print(f"♻️ Proxy cache refreshed: {len(PROXY_CACHE)} proxies")

def get_proxy():
    """Returns a RANDOM proxy from the cache (sync wrapper)."""
    if not PROXY_CACHE:
        # Check env var as fallback
        env_proxy = os.getenv("PROXY_URL", "")
        if env_proxy: return env_proxy
        return ""
    return random.choice(PROXY_CACHE)

async def check_proxy_live(proxy: str) -> tuple[bool, int]:
    """
    Verify if a proxy is live.
    Returns: (is_live, latency_ms)
    """
    test_url = "http://www.google.com"
    start = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, proxy=proxy, timeout=5) as resp:
                if resp.status == 200:
                    latency = int((time.time() - start) * 1000)
                    return True, latency
    except:
        pass
    return False, 0

async def check_site_valid(url: str) -> bool:
    """Verify if a site URL is reachable."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return True
    except:
        pass
    return False

# AUTOHITTER URLs MANAGEMENT
HITTER_URLS_FILE = os.path.join(os.path.dirname(__file__), "hitter_urls.json")

def load_hitter_urls():
    """Load saved autohitter URLs."""
    if os.path.exists(HITTER_URLS_FILE):
        try:
            with open(HITTER_URLS_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"stripe": [], "braintree": []}

def save_hitter_urls(data):
    """Save autohitter URLs."""
    with open(HITTER_URLS_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return True

def add_hitter_url(gateway: str, url: str) -> bool:
    """Add a hitter URL for a specific gateway (stripe/braintree)."""
    data = load_hitter_urls()
    gateway = gateway.lower()
    if gateway not in data:
        data[gateway] = []
    if url not in data[gateway]:
        data[gateway].append(url)
        save_hitter_urls(data)
        print(f"📌 HITTER URL ADDED ({gateway}): {url}")
        return True
    return False

def remove_hitter_url(gateway: str, url: str) -> bool:
    """Remove a hitter URL for a specific gateway."""
    data = load_hitter_urls()
    gateway = gateway.lower()
    if gateway in data and url in data[gateway]:
        data[gateway].remove(url)
        save_hitter_urls(data)
        return True
    return False

def get_hitter_urls(gateway: str) -> list:
    """Get all hitter URLs for a specific gateway."""
    data = load_hitter_urls()
    return data.get(gateway.lower(), [])

# STRIPE
STRIPE_SK = os.getenv("STRIPE_SK", "")
STRIPE_PK = os.getenv("STRIPE_PK", "")

# BRAINTREE
BT_MERCHANT_ID = os.getenv("BT_MERCHANT_ID", "")
BT_PUBLIC_KEY = os.getenv("BT_PUBLIC_KEY", "")
BT_PRIVATE_KEY = os.getenv("BT_PRIVATE_KEY", "")

# RAZORPAY
RZP_KEY_ID = os.getenv("RZP_KEY_ID", "")
RZP_KEY_SECRET = os.getenv("RZP_KEY_SECRET", "")

# AMAZON (Cookies/Session)
AMAZON_COOKIE = os.getenv("AMAZON_COOKIE", "")



# TELEGRAM ANNOUNCEMENTS
TELEGRAM_ANNOUNCE_CHAT_ID = os.getenv("TELEGRAM_ANNOUNCE_CHAT_ID", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

# EXTERNAL API ENDPOINTS (Cyborx Ports)
HITTER_API = "http://206.206.78.217:1212"
NMI_API = "http://206.206.78.217:1611"
PAYFLOW_API = "http://206.206.78.217:1120"
SHOPIFY_AUTH_API = os.getenv("SHOPIFY_AUTH_API", "https://cyborxchecker.com/api/autog.php")
VBV_API = "http://206.206.78.217:1555"
PAYPAL_API = "http://206.206.78.217:1313"
WOOSTRIPE_API = "http://206.206.78.217:1011"
WOOSTRIPE_API_2 = "http://206.206.78.217:1012"
WOOSTRIPE_API_3 = "http://206.206.78.217:1013"
NONSK_API_1 = "http://51.79.209.54:8001"
NONSK_API_2 = "http://51.79.209.54:8002"
NONSK_API_3 = "http://51.79.209.54:8003"
NONSK_API_4 = "http://51.79.209.54:8004"
SAVVY_API = "https://api.savvyapi.dev"
INBUILT_CVV_API = "http://206.206.78.217:1080"
INBUILT_CCN_API = "http://206.206.78.217:1070"

# BRAINTREE (Cyborx Ports)
BT_AUTH_API = os.getenv("BT_AUTH_API", "http://206.206.78.217:1510")
BT_AUTH2_API = os.getenv("BT_AUTH2_API", "http://206.206.78.217:1516")
BT_CHARGE_API = os.getenv("BT_CHARGE_API", "http://206.206.78.217:1520")

# AMAZON (Cyborx Port)
AMAZON_COOKIE = os.getenv("AMAZON_COOKIE", "")
AMAZON_JP_TOKEN = os.getenv("AMAZON_JP_TOKEN", "")

# PAYPAL KEYS (Cyborx Ports)
PAYPAL_KEYS = [
    ('Ae6C8zeWXPspOcNbpI5wSYLuERP8w3f0leoiLHxUJGQwaOPbGs_FnacYvn4MasLzY0BGM03dXFJ06edy', 'EPDlsXsiBrEpZaFZ94juzDmU6fekEtRWFqQolBWt4hBGyByIht_IQ8K73xFxp8yzOUWu9dNTFlKEgdND'),
    ('ARih0Y4Xo3YTyNpvsMg6qW8n2D003BSW8x1NHpeh3kypoLx-h5dgWuwdEo_oRQdcylcwxxmfSfYdiFZl', 'ENxE4tytsNQo91XFqsykY1aHJgzjnE8VcokNTmaRsOa5UM44xsiF3En5iKkhoVnAeYmplRtu4FdOsDUL'),
    ('AdNF0GIIc3et7JhCIx2IWLOpt0NMztRicOofOS1ZpyOkqWrRTR_II2TrG07aU_TWwWI5ZAxIn87Mhlp2', 'ECsM0_k-FV9cKDuxBPkxEsfCv6vwz1cBehpB1h_6WuCxyJsBNMrtDMBMALDsMrUiXPQbV1u9mpS0VsVi'),
    ('AdyHHJKYbCWwzq0FOJ6qBLk23Pkd2ozQpauQ1YMzKEIBZC3yZcU7aWxSF9HxNInUGp1z0xikoA4kGGyl', 'EAqb1IePRGyv5uDk1yBZkny9KL4UHmhwTQ0b6VqgiDd4kwZB11qaEjQnu8nsWHQ6nXQwMqUIv7JhjcN7'),
    ('Afth8tuZq5oNpy5VCaQlmuelnB5egFAKHrNwg5aka_tlRC9YpUec9I6IoRc3CNNNd5GsYgyR0JGpF-X6', 'EKXHVM_WbMqw5sMj1hI4kEe94_w5Ff_-WGHqE3zm-a5I4Dga-2ga7vLZbaA-iI12lWLhBgtMr9XLRXwc'),
    ('AXY3kP9mZ8vL5mQ7xR2tY6uJ4hN1bV9cX8wZ3qL5tY7uI9oP0mN2k', 'A21AAFu2e1Yc9bL9k3v7pQ8mX6nR4tS2wZ0yH5jK8lP3qV7xB9cD1fG'),
    ('AZ9abcdef12345678ghijklMNOpqrsTUVwxyZ1', 'DEF456GHI789JKL012MNP345QRS678TUV'),
    ('BAAuiGljqpkpMumy2IqXx0eBTUUr2UDH_320ktNxRHxqscLdmCgLAkaTQG1JpOtQ3r81es-JsszG_OSGwY', 'EP2Jxnp2hIcO2agtzn6qiSG5TDQIvocPPe10AB7r36IK6E3v0SFiAeJWUuP1ZXlXTg6eYbSr8vNuEqX2')
]
