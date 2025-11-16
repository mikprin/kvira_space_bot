import asyncio
import logging
from asyncio import Lock
from datetime import datetime

import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types.keyboard_button import KeyboardButton

from kvira_space_bot_src.messaging import (
    send_message_to_admins,
    send_message_to_user,
    get_message_for_user,
    check_membership,
)
from kvira_space_bot_src.redis_tools import (
    init_redis,
    get_user_from_redis,
    add_user_to_redis,
    TelegramUser,
    add_chat_to_redis_list,
    read_chats_from_redis_list,
    ADMIN_CHATS_KEY,
    save_json_to_redis,
    TEXT_SAVED_KEY
)
from kvira_space_bot_src.spreadsheets.api import (
    Lang,
    find_working_membership,
    get_user_data_pandas,
    punch_user_day,
    process_punches_from_string,
    get_all_text_json,
    activate_membership,
)

table_push_lock = Lock()

BUTTONS = {
  "check_membership": {
    Lang.Rus: "Проверить абонемент",
    Lang.Eng: "Check membership",
  },
  "check_in": {
    Lang.Rus: "Отметить посещение",
    Lang.Eng: "Register visit",
  },
  "calendar": {
    Lang.Rus: "Календарь",
    Lang.Eng: "Calendar",
  },
  "lang": {
    Lang.Rus: "🌐 Eng/Ru",
    Lang.Eng: "🌐 Eng/Ru",
  },
}
ADMIN_LOG_MSG_TXT = "Kvira bot admin update:"
# (0 = Monday, 1 = Tuesday, ..., 2 = Wednesday, ..., 6 = Sunday)
COMMUNITY_DAY = 2


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


def get_keyboard(user_id):
    """Get inline keyboard"""

    user = get_user_from_redis(user_id)

    lang = Lang.Rus
    if user is not None:
        lang = user.lang

    keyboard_buttons = [
        [
            KeyboardButton(text=BUTTONS["check_membership"][lang]),
            KeyboardButton(text=BUTTONS["check_in"][lang]),
            KeyboardButton(text=BUTTONS["calendar"][lang]),
            KeyboardButton(text=BUTTONS["lang"][lang]),
        ]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="ТЫК"
    )
    return keyboard


def get_user(user_id, username):
    user = get_user_from_redis(user_id)
    if user is None:
        user = TelegramUser(
            user_id=str(user_id),
            username=str(username),
            lang=Lang.Rus
        )
        add_user_to_redis(user=user)
        logging.info(f"Username {username} added to the Reddis")
    return user


async def _redis_loop():
    """This loop is needed to execute the Redis commands periodically."""
    init_redis()
    while True:
        await asyncio.sleep(1200)


class TelegramApiBot:

    def __init__(self, admin_list: list[str], token: str):
        self._admin_list = admin_list
        logging.info(f"Admin whitelist: {self._admin_list}")

        self._bot = Bot(token, parse_mode=ParseMode.HTML)
        self._dp = Dispatcher()
        self.register_handlers()
        logging.info(f"Initiated bot with token")

        # Here I cache all the messages from the Google Sheet
        # To redis database
        all_msgs = get_all_text_json()
        save_json_to_redis(all_msgs, TEXT_SAVED_KEY)
        logging.info("Messages saved to the Redis database")

    async def _run_tasks(self):
        database_loop = asyncio.create_task(_redis_loop())
        bot_loop = asyncio.create_task(self._dp.start_polling(self._bot))
        await asyncio.gather(database_loop, bot_loop)

    def register_handlers(self):
        """
        Register all dispatcher handlers.
        """
        self._dp.message.register(self.handle_start, CommandStart())
        self._dp.message.register(self.handle_admin_register, Command("admin"), IsAdmin(self._admin_list))
        self._dp.message.register(self.handle_lang_change, F.text.in_(BUTTONS["lang"].values()))
        self._dp.message.register(self.handle_check_membership, F.text.in_(BUTTONS["check_membership"].values()))
        self._dp.message.register(self.handle_calendar, F.text.in_(BUTTONS["calendar"].values()))
        self._dp.message.register(self.handle_check_in, F.text.in_(BUTTONS["check_in"].values()))

    def run(self):
        asyncio.run(self._run_tasks())

    async def handle_start(self, message: Message) -> None:
        """
        This handler receives messages with `/start` command
        """
        init_redis()
        user = get_user(message.from_user.id, message.from_user.username)

        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        # Process error messages
        if len(membership.errors) > 0:
            for error in membership.errors:
                await send_message_to_admins(f"{ADMIN_LOG_MSG_TXT} Error in validation for user {user.username}: {error}", bot=self._bot)
        hello_msg = get_message_for_user('hello_msg', user.lang)
        messages = [hello_msg]
        messages.extend(check_membership(user, membership))
        # Also if it is a community day
        current_date = datetime.now()
        if current_date.weekday() == COMMUNITY_DAY:
            messages.append(get_message_for_user('community_day', user.lang))
        logging.info(f"Messages for user {user.username}: {messages}")
        await message.answer("\n".join(messages), reply_markup=get_keyboard(user.user_id))

    # Process the user's choice. Language change is handled here.
    async def handle_lang_change(self, message: Message):
        user = get_user(message.from_user.id, message.from_user.username)
        
        if user.lang == Lang.Rus:
            user.lang = Lang.Eng
        else:
            user.lang = Lang.Rus
    
        add_user_to_redis(user) 
        await message.answer(get_message_for_user('lang_changed', user.lang), reply_markup=get_keyboard(user.user_id))

    async def handle_check_membership(self, message: Message):
        user = get_user(message.from_user.id, message.from_user.username)
        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        messages = check_membership(user, membership)
        await message.answer("\n".join(messages), reply_markup=get_keyboard(user.user_id))

    async def handle_calendar(self, message: Message):
        user = get_user(message.from_user.id, message.from_user.username)
        await message.answer(get_message_for_user('calendar', user.lang), reply_markup=get_keyboard(user.user_id))

    async def handle_check_in(self, message: Message):
        # Get the current date
        current_date = datetime.now()
        
        user = get_user(message.from_user.id, message.from_user.username)
        msg = None
        users_memberships: pd.DataFrame = get_user_data_pandas()
        membership = find_working_membership(user.username, users_memberships)
        if current_date.weekday() != COMMUNITY_DAY:
            # Activate the pass if it is not activated if it is NOT a community day
            if membership.activated is False:
                activate_membership(membership)
                membership.activated = True
                user_id = message.from_user.id
                text = get_message_for_user('pass_activated', user.lang)
                await send_message_to_user(user_id, text, bot=self._bot)
                # Notify admins
                await send_message_to_admins(f"{ADMIN_LOG_MSG_TXT} User {user.username} activated the pass", bot=self._bot)
        if current_date.weekday() == COMMUNITY_DAY:
            msg = 'community_day'
        elif membership.row_id is None:
            msg = 'no_pass'
        else:
            await table_push_lock.acquire()
            try:
                # If last punch was today, do nothing
                if len(membership.membership_data['punches']) > 0:
                    last_punch = process_punches_from_string(membership.membership_data['punches'])[-1]
                else:
                    last_punch = None
                today = current_date.strftime('%d.%m.%Y')
                # logging.info(f"Last punch: {last_punch}, today: {today}, {last_punch == today}")
                if last_punch is not None and last_punch == today:
                    msg = 'already_punched'
                else:
                    ret_code = punch_user_day(membership.row_id)
                    if ret_code:
                        await send_message_to_admins(f"{ADMIN_LOG_MSG_TXT} User {user.username} punched the pass", bot=self._bot)
                        logging.info(f"User {user.username} punched the pass")
                        msg = 'pass_punched'
                    else:
                        logging.error(f"Error while punching the pass for user {user.username}")
                        msg = "error_punching"
            finally:
                table_push_lock.release()
        await message.answer(get_message_for_user(msg, user.lang), reply_markup=get_keyboard(user.user_id))

    async def handle_admin_register(self, message: Message):
        admin_chats = read_chats_from_redis_list(ADMIN_CHATS_KEY)
        if message.chat.id not in admin_chats:
            add_chat_to_redis_list(message.chat.id, ADMIN_CHATS_KEY)
            admin_chats.append(message.chat.id)
            await message.answer(f"Chat {message.chat.id} added to the admin list!")
        else:
            await message.answer("You are already in admin list!")