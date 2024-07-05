from typing import List

from kvira_space_bot_src.spreadsheets.api import Lang
from redis import Redis
from pydantic import BaseModel


class TelegramUser(BaseModel):
    user_id: int
    username: str
    lang: Lang


def init_redis(db=0):
    """Initialize the Redis database.
    """
    redis = Redis(host='localhost', port=6379, db=db)
    return redis


def add_user_to_redis(redis: Redis, user: TelegramUser) -> None:
    """Add a user to the Redis database.
    """
    redis.set(user.user_id, user.json())


def get_user_from_redis(redis: Redis, userid: int) -> TelegramUser:
    """Get a user from the Redis database.
    """
    return TelegramUser.parse_raw(redis.get(userid))


def update_user_lang_in_redis(redis: Redis, userid: int, lang: Lang) -> None:
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
