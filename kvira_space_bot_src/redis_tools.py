import asyncio
import os

import logging
import json
from kvira_space_bot_src.spreadsheets.data import Lang
from redis import Redis
from pydantic import BaseModel
from asyncio import Lock
from pydantic import ValidationError

ALL_USERS_KEY_LIST = 'all_users_redis_key_list'
ADMIN_CHATS_KEY = 'admin_chats_redis_key'
TEXT_SAVED_KEY = 'text_saved_redis_key'

redis_user_db_lock = Lock()

# if REDIS_HOST is not set, use the default value
redis_host = os.environ.get('REDIS_HOST', 'kvira_redis')
redis_port = os.environ.get('REDIS_PORT', 6379)

print(f"REDIS_HOST: {redis_host}")

# Redis databases
USER_DATA_DB = 0
SERVICE_DATA_DB = 1

os.environ.get('AWS_MAX_POOL_CONNECTIONS', 1)
redis_user_db = Redis(host=redis_host, port=redis_port, db=USER_DATA_DB)
redis_service_db = Redis(host=redis_host, port=redis_port, db=SERVICE_DATA_DB)

class UserPass(BaseModel):
    pass
class TelegramUser(BaseModel):
    user_id: str
    username: str
    lang: Lang
    user_pass: UserPass | None = None


def get_redis_user_db() -> Redis:
    """For using in notebooks and tests."""
    return redis_user_db

def get_redis_service_db() -> Redis:
    """For using in notebooks and tests."""
    return redis_service_db

def init_redis() -> None:
    """this function checks if global variables are redis objects is working properly
    if not, it will try to reconnect to the redis server
    """
    global redis_user_db
    global redis_service_db
    try:
        redis_user_db.ping()
        redis_service_db.ping()
    except:
        redis_user_db = Redis(host=redis_host, port=redis_port, db=USER_DATA_DB)
        redis_service_db = Redis(host=redis_host, port=redis_port, db=SERVICE_DATA_DB)
        redis_user_db.ping()
        redis_service_db.ping()

def add_chat_to_redis_list(chat_id: str, key: str) -> None:
    """Adds this chat_id to the Redis database list of admin chats.
    """
    redis = redis_service_db
    redis.sadd(key, chat_id)
    
def read_chats_from_redis_list(key: str) -> list[str]:
    """Reads the list of admin chats from the Redis database.
    Decode each chat_id from bytes to string.
    """
    redis = redis_service_db
    return [chat_id.decode('utf-8') for chat_id in redis.smembers(key)]

def add_user_to_redis(user: TelegramUser) -> None:
    """Add a user to the Redis database.
    """
    redis = redis_user_db
    redis.set(user.user_id, user.json())
    redis.sadd(ALL_USERS_KEY_LIST, user.user_id)


def get_user_from_redis(userid: str) -> TelegramUser:
    """Get a user from the Redis database.
    """
    redis = redis_user_db
    # Check if the user exists in the database
    if not redis.exists(userid):
        return None
    user = redis.get(userid)
    try:
        user = TelegramUser.parse_raw(user)
    except ValidationError:
        logging.error(f"User with id {userid} is not in the correct format.")
        return None
    return user


def update_user_lang_in_redis(userid: str, lang: Lang) -> None:
    """Update the user's language in the Redis database.
    """
    redis = redis_user_db
    user = get_user_from_redis(userid)
    user.lang = lang
    add_user_to_redis(redis, user)


def get_all_users() -> list[TelegramUser]:
    """Get all users from the Redis database.
    """
    redis = redis_user_db
    keys = redis.keys('*')
    return [
        get_user_from_redis(key.decode('utf-8'))
        for key in keys
    ]
    
def save_json_to_redis(data: dict, key: str) -> None:
    """Save a JSON object to the Redis database.
    """
    json_data = json.dumps(data)
    redis = redis_service_db
    redis.set(key, json_data)
    
def read_json_from_redis(key: str) -> dict:
    """Read a JSON object from the Redis database.
    """
    redis = redis_service_db
    json_data = redis.get(key)
    return json.loads(json_data)
