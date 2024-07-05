from typing import List

from kvira_space_bot_src.spreadsheets.api import Lang
from redis import Redis
from pydantic import BaseModel


class TelegramUser(BaseModel):
    user_id: str
    username: str
    lang: Lang


def init_redis(host='kvira_redis', db=0):
    """Initialize the Redis database.
    """
    redis = Redis(host=host, port=6379, db=db)
    return redis


def add_user_to_redis(redis: Redis, user: TelegramUser) -> None:
    """Add a user to the Redis database.
    """
    redis.set(user.user_id, user.json())


def get_user_from_redis(redis: Redis, userid: str) -> TelegramUser:
    """Get a user from the Redis database.
    """
    # Check if the user exists in the database
    if not redis.exists(userid):
        return None
    return TelegramUser.parse_raw(redis.get(userid))


def update_user_lang_in_redis(redis: Redis, userid: str, lang: Lang) -> None:
    """Update the user's language in the Redis database.
    """
    user = get_user_from_redis(redis, userid)
    user.lang = lang
    add_user_to_redis(redis, user)


def get_all_users(redis: Redis) -> List[TelegramUser]:
    """Get all users from the Redis database.
    """
    keys = redis.keys('*')
    return [
        get_user_from_redis(redis, key.decode('utf-8'))
        for key in keys
    ]
