import asyncio
from dotenv import load_dotenv
from os import getenv

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.contrib.middlewares.logging import LoggingMiddleware

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


class TelegramApiBot:
    
    def __init__(self):
        load_dotenv()
        self._token = getenv("TELEGRAM_API_KEY")
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

    @dp.message()
    async def echo_handler(message: types.Message) -> None:
        """
        Handler will forward receive a message back to the sender

        By default, message handler will handle all message types (like a text, photo, sticker etc.)
        """
        try:
            # Send a copy of the received message
            await message.send_copy(chat_id=message.chat.id)
        except TypeError:
            # But not all the types is supported to be copied so need to handle it
            await message.answer("Nice try!")

    async def _run(self):
        self._bot = Bot(self._token, parse_mode=ParseMode.HTML)
        await dp.start_polling(self._bot)

    def get_keyboard(user_id):
        """Get inline keyboard"""
        return None
