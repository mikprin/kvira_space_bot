from kvira_space_bot_src.spreadsheets.api import Lang
from redis import Redis
from pydantic import BaseModel



class TelegramUser(BaseModel):
    user_id: str
    username: str
    lang: Lang

def init_redis():
    """Initialize the Redis database.
    """
    redis = Redis(host='localhost', port=6379, db=0)
    return redis

def add_user_to_redis(redis: Redis, user: TelegramUser) -> None:
    """Add a user to the Redis database.
    """
    pass

def get_user_from_redis(redis: Redis, userid: str) -> TelegramUser:
    """Get a user from the Redis database.
    """
    pass

def update_user_lang_in_redis(redis: Redis, userid: str, lang: Lang) -> None:
    """Update the user's language in the Redis database.
    """
    pass
    
def get_all_users(redis: Redis) -> list:
    """Get all user ids from the Redis database.
    """
    pass