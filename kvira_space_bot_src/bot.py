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
    add_chat_to_redis_list,
    read_chats_from_redis_list,
    ADMIN_CHATS_KEY
)

from asyncio import Lock

table_push_lock = Lock()

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

    user = get_user_from_redis(user_id)
    
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
    for admin_chat_id in read_chats_from_redis_list(ADMIN_CHATS_KEY): 
        send_message_to_user(int(admin_chat_id), text, bot)


async def redis_loop():
    '''This loop is needed to execute the Redis commands pereopdically.'''
    init_redis()
    while True:
        await asyncio.sleep(1200)

class TelegramApiBot:

    def __init__(self):
        
        logging.info(f"Inited bot with token!")
        self.admin_ids_users = admin_ids_users
        logging.info(f"Admins: {self.admin_ids_users}")

    async def run_tasks(self):
        database_loop = asyncio.create_task(redis_loop())
        bot_loop = asyncio.create_task(self._run())
        await asyncio.gather(database_loop, bot_loop)


    def run(self):
        asyncio.run(self.run_tasks())

    # User handler zone
    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        """This handler receives messages with `/start` command
        """
        redis = init_redis()
        user = get_user_from_redis(message.from_user.id)

        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(user=user)

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
        user = get_user_from_redis(message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(user=user)
            logging.info(f"Username {message.from_user.username} added to the Reddis")
        
        if user.lang == Lang.Rus:
            user.lang = Lang.Eng
        else:
            user.lang = Lang.Rus
    
        add_user_to_redis(user) 
        await message.answer(get_message_for_user('lang_changed', user.lang), reply_markup=get_keyboard(user.user_id))


    @dp.message((F.text == buttons[Lang.Rus.value]["check_membership"]) or (F.text == buttons[Lang.Eng.value]["check_membership"]) or F.text == "Check membership")
    async def check_membership_handler(message: Message):
        user = get_user_from_redis(message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(user=user)
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
        user = get_user_from_redis(message.from_user.id)
        if user is None:
            user=TelegramUser(
                user_id=str(message.from_user.id),
                username=str(message.from_user.username),
                lang=Lang.Rus
            )
            add_user_to_redis(user=user)
            logging.info(f"Username {message.from_user.username} added to the Reddis")
        await table_push_lock.acquire()
        try:
            msg = None
            users_memberships: pd.DataFrame = get_user_data_pandas()
            membership = find_working_membership(user.username, users_memberships)
            if membership.row_id is None:
                msg = 'no_pass'
            else:
                # If last punch was today, do nothing
                last_punch = process_punches_from_string(membership.membership_data['punches'])[-1]
                today = datetime.now().strftime('%d.%m.%Y')
                # logging.info(f"Last punch: {last_punch}, today: {today}, {last_punch == today}")
                if last_punch == today:
                    msg = 'already_punched'
                else:
                    ret_code = punch_user_day(membership.row_id)
                    if ret_code:
                        send_message_to_admins(f"User {user.username} punched the pass", bot=bot)
                        logging.info(f"User {user.username} punched the pass")
                        msg = 'pass_punched'
                    else:
                        logging.error(f"Error while punching the pass for user {user.username}")
                        msg = "error_punching"
        finally:
            table_push_lock.release()
        await message.answer(get_message_for_user(msg, user.lang), reply_markup=get_keyboard(user.user_id))
    async def _run(self):
        self._bot = bot
        await dp.start_polling(self._bot)

    @dp.message(Command("admin"), IsAdmin(admin_ids_users))
    async def admin_command_handler(message: Message):
        admin_chats = read_chats_from_redis_list(ADMIN_CHATS_KEY)
        if message.chat.id not in admin_chats:
            add_chat_to_redis_list(message.chat.id, ADMIN_CHATS_KEY)
            admin_chats.append(message.chat.id)
            await message.answer(f"Chat {message.chat.id} added to the admin list!")
        else:
            await message.answer("You are already in admin list!")