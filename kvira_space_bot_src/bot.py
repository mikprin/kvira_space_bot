import asyncio
from dotenv import load_dotenv
from os import getenv

# Initialize logger:
import logging
import json
logging.basicConfig(level=logging.INFO)


from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter
from aiogram.filters import Command

from kvira_space_bot_src.spreadsheets.api import (
    get_days_left,
    get_message_for_user,
    Lang
)
from kvira_space_bot_src.redis_tools import (
    init_redis,
    get_user_from_redis,
    add_user_to_redis,
    TelegramUser
)


dp = Dispatcher()  # TODO: put inside the class?
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


class TelegramApiBot:
    
    def __init__(self):
        
        self._token = getenv("TELEGRAM_API_KEY")
        
        logging.info(f"Inited bot with token!")
        self.admin_ids_users = admin_ids_users
        logging.info(f"Admins: {self.admin_ids_users}")
        
        self._redis = init_redis()
    def run(self):
        asyncio.run(self._run())

    @dp.message(CommandStart())
    async def command_start_handler(self, message: Message) -> None:
        """This handler receives messages with `/start` command
        """

        user = get_user_from_redis(self._redis, message.from_user.id)

        if user is None:

            add_user_to_redis(TelegramUser(
                message.from_user.id,
                message.from_user.username,
                Lang.Rus  # TODO: add language selection
            ))

            await message.answer(f"Username {message.from_user.username} added to the Reddis")

        else:  # user is not None

            hello_msg = get_message_for_user('hello_msg', user.lang)

            days_left = get_days_left(user.username) 

            if days_left > 0:
                hello_msg += "\n" \
                    + get_message_for_user('acc_days', user.lang) % days_left
            else:
                hello_msg += "\n" + get_message_for_user('no_pass', user.lang)

            await message.answer(hello_msg)

    # @dp.message()
    # async def echo_handler(message: types.Message) -> None:
    #     """
    #     Handler will forward receive a message back to the sender

    #     By default, message handler will handle all message types (like a text, photo, sticker etc.)
    #     """
    #     try:
    #         # Send a copy of the received message
    #         await message.send_copy(chat_id=message.chat.id)
    #     except TypeError:
    #         # But not all the types is supported to be copied so need to handle it
    #         await message.answer("Nice try!")

    async def _run(self):
        self._bot = Bot(self._token, parse_mode=ParseMode.HTML)
        await dp.start_polling(self._bot)

    def get_keyboard(user_id):
        """Get inline keyboard"""
        return None

    @dp.message(Command("check_if_admin"), IsAdmin(admin_ids_users))
    async def admin_command_handler(message: Message):
        await message.answer("You are an admin!")