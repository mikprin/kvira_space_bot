import asyncio
from dotenv import load_dotenv
from os import getenv
import pandas as pd
# Initialize logger:
import logging
import json
logging.basicConfig(level=logging.INFO)
from redis import Redis
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter
from aiogram.filters import Command
from aiogram.types.keyboard_button import KeyboardButton
from aiogram import F, exceptions

from kvira_space_bot_src.spreadsheets.api import (
    get_days_left,
    get_message_for_user,
    Lang,
    find_working_membership,
    get_days_left_from_membership,
    get_user_data_pandas,
    punch_user_day,
    process_punches_from_string
)
from kvira_space_bot_src.redis_tools import (
    init_redis,
    get_user_from_redis,
    add_user_to_redis,
    TelegramUser,
    add_admin_chat_to_redis,
    read_admin_chats_from_redis
)


buttons = {
    Lang.Rus.value: {
        "check_membership": "Проверить абонемент",
        "check_in": "Отметить посещение",
        "lang": "🌐"
    },
    Lang.Eng.value: {
        "check_membership": "Check membership",
        "check_in": "Register visit",
        "lang": "🌐",
    },
}

# Redis databases
USER_DATA_DB = 0
SERVICE_DATA_DB = 1

dp = Dispatcher()  # TODO: put inside the class?
token = getenv("TELEGRAM_API_KEY")
bot = Bot(token, parse_mode=ParseMode.HTML)
load_dotenv()
admin_ids_users = getenv("ADMIN_CHATS")

if admin_ids_users:
    if "," in admin_ids_users:
        admin_ids_users = admin_ids_users.split(",")
    else:
        admin_ids_users = [admin_ids_users]
class IsAdmin(BaseFilter):
    """Check if the user is an admin. Works with user ids and usernames.
    """
    def __init__(self, admin_ids_users) -> None:
        self.admin_ids_users = admin_ids_users

    async def __call__(self, message: Message) -> bool:
        logging.info(f"Checking if {message.from_user.username} is an admin...")
        is_admin = message.from_user.id in self.admin_ids_users or message.from_user.username in self.admin_ids_users
        if not is_admin:
            await message.answer("You are not privileged to use this command.")
        return is_admin

def get_keyboard(user_id, redis: Redis | None=None):
    """Get inline keyboard"""
    
    if redis is None:
        redis = init_redis(db=USER_DATA_DB)
    
    user = get_user_from_redis(redis, user_id)
    
    if user is not None:
        lang = user.lang
    else:
        lang = Lang.Rus
    
    keyboard_buttons = [
        [
            KeyboardButton(text=buttons[lang.value]["check_membership"]),
            KeyboardButton(text=buttons[lang.value]["check_in"]),
            KeyboardButton(text=buttons[lang.value]["lang"]),
            ]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="ТЫК"
    )
    return keyboard

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

def send_message_to_admins(text: str, bot: Bot):
    redis = init_redis(db=SERVICE_DATA_DB)
    for admin_chat_id in read_admin_chats_from_redis(redis): 
        send_message_to_user(int(admin_chat_id), text, bot)


class TelegramApiBot:

    def __init__(self):
        
        logging.info(f"Inited bot with token!")
        self.admin_ids_users = admin_ids_users
        logging.info(f"Admins: {self.admin_ids_users}")
    
    def run(self):
        asyncio.run(self._run())




    # User handler zone

    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        """This handler receives messages with `/start` command
        """
        redis = init_redis(db=USER_DATA_DB)
        user = get_user_from_redis(redis, message.from_user.id)

        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(redis=redis, user=user)

            logging.info(f"Username {message.from_user.username} added to the Reddis")

        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        # TODO: Process table errors on this step
        hello_msg = get_message_for_user('hello_msg', user.lang)
        
        if membership.row_id is None:
            hello_msg += f"\n{get_message_for_user('no_pass', user.lang)}"
        else:
            days_left = get_days_left_from_membership(membership)
            hello_msg += f"\n{get_message_for_user('days_left', user.lang).format(days_left)}"
        
        await message.answer(hello_msg, reply_markup=get_keyboard(user.user_id))

    # Process the user's choice. Language change is handled here.
    @dp.message(F.text == buttons[Lang.Rus.value]["lang"] or F.text == buttons[Lang.Eng.value]["lang"])
    async def lang_change_handler(message: Message):
        redis = init_redis(db=USER_DATA_DB)
        user = get_user_from_redis(redis, message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(redis=redis, user=user)
            logging.info(f"Username {message.from_user.username} added to the Reddis")
        
        if user.lang == Lang.Rus:
            user.lang = Lang.Eng
        else:
            user.lang = Lang.Rus
    
        add_user_to_redis(redis, user) 
        await message.answer(get_message_for_user('lang_changed', user.lang), reply_markup=get_keyboard(user.user_id, redis))


    @dp.message((F.text == buttons[Lang.Rus.value]["check_membership"]) or (F.text == buttons[Lang.Eng.value]["check_membership"]) or F.text == "Check membership")
    async def check_membership_handler(message: Message):
        redis = init_redis(db=USER_DATA_DB)
        user = get_user_from_redis(redis, message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(redis=redis, user=user)
            logging.info(f"Username {message.from_user.username} added to the Reddis")
        
        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        if membership.row_id is None:
            await message.answer(get_message_for_user('no_pass', user.lang), reply_markup=get_keyboard(user.user_id))
        else:
            days_left = get_days_left_from_membership(membership)
            await message.answer(get_message_for_user('days_left', user.lang).format(days_left), reply_markup=get_keyboard(user.user_id))


    @dp.message(F.text == buttons[Lang.Rus.value]["check_in"] or F.text == buttons[Lang.Eng.value]["check_in"])
    async def check_in_handler(message: Message):
        redis = init_redis(db=USER_DATA_DB)
        user = get_user_from_redis(redis, message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(redis=redis, user=user)
            logging.info(f"Username {message.from_user.username} added to the Reddis")
        
        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        if membership.row_id is None:
            await message.answer(get_message_for_user('no_pass', user.lang), reply_markup=get_keyboard(user.user_id))
        else:
            # If last punch was today, do nothing
            last_punch = process_punches_from_string(membership.membership_data['punches'])[-1]
            if last_punch == datetime.now().strftime('%d.%m.%Y'):
                await message.answer(get_message_for_user('already_punched', user.lang), reply_markup=get_keyboard(user.user_id))
            ret_code = punch_user_day(membership.row_id)
        if ret_code:
            send_message_to_admins(f"User {user.username} punched the pass", bot=bot)
            logging.info(f"User {user.username} punched the pass")
            await message.answer(get_message_for_user('pass_punched', user.lang), reply_markup=get_keyboard(user.user_id))
        else:
            logging.error(f"Error while punching the pass for user {user.username}")
            await message.answer(get_message_for_user('error_punching', user.lang), reply_markup=get_keyboard(user.user_id))

    async def _run(self):
        self._bot = bot
        await dp.start_polling(self._bot)

    @dp.message(Command("admin"), IsAdmin(admin_ids_users))
    async def admin_command_handler(message: Message):
        redis = init_redis(db=SERVICE_DATA_DB)
        admin_chats = read_admin_chats_from_redis(redis)
        if message.chat.id not in admin_chats:
            add_admin_chat_to_redis(redis, message.chat.id)
            admin_chats.append(message.chat.id)
            await message.answer(f"Chat {message.chat.id} added to the admin list!")
        else:
            await message.answer("You are already in admin list!")