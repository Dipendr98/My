from pyrogram import filters
from config import AUTHORIZED_USERS
import time

# Dictionary to store last command time for users
user_flood = {}

def is_authorized(_, __, message):
    return message.from_user and message.from_user.id in AUTHORIZED_USERS

authorized_filter = filters.create(is_authorized)

def check_flood(user_id, wait_time=10):
    """
    Check if user is flooding. 
    Returns (True, remaining_time) if flooding, (False, 0) otherwise.
    """
    # Bypass for authorized users
    if user_id in AUTHORIZED_USERS:
        return False, 0
        
    # Check if user is VIP (needs DB or config lookup)
    # Ideally, we should pass the user data object to avoid DB hits,
    # but for now, let's rely on config.get_user_data which caches to disk/memory
    from config import get_user_data
    try:
        user_data = get_user_data(user_id)
        if user_data.get('is_vip'):
            return False, 0
    except: pass

    current_time = time.time()
    if user_id in user_flood:
        last_time = user_flood[user_id]
        if current_time - last_time < wait_time:
            return True, int(wait_time - (current_time - last_time))
            
    user_flood[user_id] = current_time
    return False, 0
