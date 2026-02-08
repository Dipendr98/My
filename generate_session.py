"""
Session String Generator for CC Killer Bot
Run this ONCE locally to generate a session string, then add it to Railway env vars.
"""

from pyrogram import Client
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

print("=" * 50)
print("SESSION STRING GENERATOR")
print("=" * 50)
print("\nThis will generate a session string for your bot.")
print("After generation, add it to Railway as SESSION_STRING env var.\n")

# Create a temporary client to get session
with Client("temp_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN) as app:
    session_string = app.export_session_string()
    
    print("\n" + "=" * 50)
    print("YOUR SESSION STRING (Copy this):")
    print("=" * 50)
    print(session_string)
    print("=" * 50)
    print("\n  Add this to Railway as: SESSION_STRING")
    print("  Keep this SECRET - it gives full bot access!")
