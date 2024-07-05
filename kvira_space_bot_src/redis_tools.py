from kvira_space_bot_src.spreadsheets.api import Lang
from redis import Redis

def init_redis():
    """Initialize the Redis database.
    """
    redis = Redis(host='localhost', port=6379, db=0)
    return redis

def get_user_lang(redis: Redis, user_id: str) -> Lang:
    """Get user language from the Redis database.
    Check
    """
    return Lang(int(redis.get(f"{user_id}_lang")))

def set_user_lang(redis: Redis, user_id: str, lang: Lang):
    """Set user language in the Redis database.
    """
    redis.set(f"{user_id}_lang", lang.value)
    
def get_all_users(redis: Redis) -> list:
    """Get all user ids from the Redis database.
    """
    pass