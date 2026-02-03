import os
import json
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
UPI_ID = os.getenv("UPI_ID", "your-upi@id")
PAYMENT_QR_URL = os.getenv("PAYMENT_QR_URL", "")
WELCOME_PHOTO_URL = os.getenv("WELCOME_PHOTO_URL", "") # URL or local path in assets/
DEVELOPER_NAME = os.getenv("DEVELOPER_NAME", "Antigravity")
PROJECT_NAME = os.getenv("PROJECT_NAME", "CC KILLER")
PROJECT_TAG = os.getenv("PROJECT_TAG", "#KillerProject")
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
SITES_FILE = "sites.json"

def load_sites():
    if os.path.exists(SITES_FILE):
        try:
            with open(SITES_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_site(url):
    sites = load_sites()
    if url not in sites:
        sites.append(url)
        with open(SITES_FILE, "w") as f:
            json.dump(sites, f)
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
USERS_FILE = "users.json"
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
            "credits": 50, 
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
    
    if data["is_vip"] or data["plan"] == "VIP":
        return True
    
    if data["credits"] + amount < 0:
        return False
    
    users = load_users() # reload after get_user_data might have saved
    users[user_id_str]["credits"] += amount
    save_users(users)
    return True

def set_user_plan(user_id, plan_name):
    users = load_users()
    user_id_str = str(user_id)
    get_user_data(user_id) # ensure exists
    
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

# PROXY CONFIG
PROXY_URL = os.getenv("PROXY_URL", "") 

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
SHOPIFY_AUTH_API = os.getenv("SHOPIFY_AUTH_API", "https://babachecker.com/api/autog.php")
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
