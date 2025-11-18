
from aiogram import exceptions
import logging
import asyncio
from aiogram import Bot
from kvira_space_bot_src.redis_tools import (
    read_chats_from_redis_list,
    ADMIN_CHATS_KEY,
    read_json_from_redis,
    TEXT_SAVED_KEY,
    TelegramUser,
)
from kvira_space_bot_src.spreadsheets.api import (
    Lang,
    WorkingMembership,
    get_days_left_from_membership,
)
from datetime import datetime, timedelta


def join_messages(messages: list[str]) -> str:
    """Join the messages in the list into one string.
    """
    return '\n'.join(messages)

def check_membership(user: TelegramUser, membership: WorkingMembership) -> list[str]:
    """Check the membership of the user and return list of messages to send.
    """
    messages = list()
    if membership.row_id is None:
        messages.append(get_message_for_user('no_pass', user.lang))
        # await message.answer(get_message_for_user('no_pass', user.lang), reply_markup=get_keyboard(user.user_id))
    else:
        if membership.activated is False:
            messages.append(get_message_for_user('not_activated_pass', user.lang))
        # If 30 day pass. Then just get expiration date. And also sent month_pass msg.
        elif membership.membership_data['pass_type'] == '30day':
            messages.append(get_message_for_user('month_pass', user.lang))
        else:
            days_left = get_days_left_from_membership(membership)
            messages.append(get_message_for_user('days_left', user.lang).format(days_left))
        if membership.activated:
            # Expiration date is activation date + 30 days
            # TODO Remove this ugly hack
            activation_date_str = membership.membership_data['date_activated']
            activation_date = datetime.strptime(activation_date_str, '%d.%m.%Y')
            expiration_date = activation_date + timedelta(days=30)
            expiration_date_str = expiration_date.strftime('%d.%m.%Y')
            messages.append(get_message_for_user('exp_date', user.lang).format(expiration_date_str))
    logging.info(f"Messages for user {user.username}: {messages}")
    return messages

async def send_message_to_user(user_id: int, text: str, bot: Bot, disable_notification: bool = False) -> bool:
    try:
        await bot.send_message(user_id, text, disable_notification=disable_notification)
    except exceptions.BotBlocked:
        logging.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        logging.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logging.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_message_to_user(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        logging.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return True
    return False

    # Admin handler zone
    # Admin chats are defined in the .env file and messages are sent to them when

async def send_message_to_admins(text: str, bot: Bot):
    for admin_chat_id in read_chats_from_redis_list(ADMIN_CHATS_KEY): 
        await send_message_to_user(int(admin_chat_id), text, bot)

        
def get_message_for_user(str_id: str, lang: Lang) -> str:
    """This is used to get cached messages from the Redis database.
    """
    text_dict = read_json_from_redis(TEXT_SAVED_KEY)
    try:
        text = text_dict[str_id][lang.value]
    except KeyError:
        logging.error(f"Message with id {str_id} not found in the Redis database.")
        return "Message not found. Please contact the administrator with a bugreport."
    return text