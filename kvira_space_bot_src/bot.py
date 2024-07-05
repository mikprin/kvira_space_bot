import asyncio
from dotenv import load_dotenv
from os import getenv

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from kvira_space_bot_src.spreadsheets.api import get_days_left, get_message_for_user

dp = Dispatcher()  # TODO: put inside the class?


class TelegramApiBot:
    
    def __init__(self):
        load_dotenv()
        self._token = getenv("TELEGRAM_API_KEY")
    
    def run(self):
        asyncio.run(self._run())

    @dp.message(CommandStart())
    async def command_start_handler(message: Message) -> None:
        """
        This handler receives messages with `/start` command
        """
        # Most event objects have aliases for API methods that can be called in events' context
        # For example if you want to answer to incoming message you can use `message.answer(...)` alias
        # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
        # method automatically or call API method directly via
        # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
        await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")

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
