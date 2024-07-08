import asyncio
import os

from kvira_space_bot_src.spreadsheets.api import Lang
from redis import Redis
from pydantic import BaseModel
from asyncio import Lock

ALL_USERS_KEY_LIST = 'all_users_redis_key_list'
ADMIN_CHATS_KEY = 'admin_chats_redis_key'

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
redos_service_db = Redis(host=redis_host, port=redis_port, db=SERVICE_DATA_DB)

class UserPass(BaseModel):
    pass
class TelegramUser(BaseModel):
    user_id: str
    username: str
    lang: Lang
    user_pass: UserPass | None = None


def init_redis() -> None:
    """this function checks if global variables are redis objects is working properly
    if not, it will try to reconnect to the redis server
    """
    global redis_user_db
    global redos_service_db
    try:
        redis_user_db.ping()
        redos_service_db.ping()
    except:
        redis_user_db = Redis(host=redis_host, port=redis_port, db=USER_DATA_DB)
        redos_service_db = Redis(host=redis_host, port=redis_port, db=SERVICE_DATA_DB)
        redis_user_db.ping()
        redos_service_db.ping()

def add_chat_to_redis_list(chat_id: str, key: str) -> None:
    """Adds this chat_id to the Redis database list of admin chats.
    """
    redis = redos_service_db
    redis.sadd(key, chat_id)
    
def read_chats_from_redis_list(key: str) -> list[str]:
    """Reads the list of admin chats from the Redis database.
    Decode each chat_id from bytes to string.
    """
    redis = redos_service_db
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
    return TelegramUser.parse_raw(redis.get(userid))


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
