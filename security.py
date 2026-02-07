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
    current_time = time.time()
    if user_id in user_flood:
        last_time = user_flood[user_id]
        if current_time - last_time < wait_time:
            return True, int(wait_time - (current_time - last_time))
            
    user_flood[user_id] = current_time
    return False, 0
