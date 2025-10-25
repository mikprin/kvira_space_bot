import asyncio
import logging
from asyncio import Lock
from datetime import datetime
from typing import Any, Dict, Callable, Awaitable

from aiogram import Bot, Dispatcher, BaseMiddleware, types, F
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, Update
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
from kvira_space_bot_src.spreadsheets.data import Lang, split_by_coma
from kvira_space_bot_src.spreadsheets.halloween import CRYPTIDS
from kvira_space_bot_src.spreadsheets.memberships import (
    find_working_membership,
    punch_user_day,
    activate_membership,
)
from kvira_space_bot_src.spreadsheets.messages import get_all_text_json

table_push_lock = Lock()

BUTTONS = {
  "quest_mode": {
    Lang.Rus: "Квест на Хэллоуин",
    Lang.Eng: "Halloween Quest",
  },
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
  "return": {
    Lang.Rus: "Назад",
    Lang.Eng: "Return",
  },
}
TOP_LEVEL_BUTTON_LAYOUT = ["check_membership", "check_in", "calendar", "quest_mode", "lang"]
QUEST_BUTTON_LAYOUT = ["return", "lang"]
ADMIN_LOG_MSG_TXT = "Kvira bot admin update:"
# (0 = Monday, 1 = Tuesday, ..., 2 = Wednesday, ..., 6 = Sunday)
COMMUNITY_DAY = 2

class UserStates(StatesGroup):
    main_menu = State()
    quest_mode = State()

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


class StateAutoSetMiddleware(BaseMiddleware):
    """
    Выполняется до проверки обработчиков. Нужно для тех пользователей,
    которые начали пользоваться ботом до того как был введен стейт.
    """

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get('state')
        if state is not None:
            current_fsm_state = await state.get_state()
            if current_fsm_state is None:
                await state.set_state(UserStates.main_menu)
        return await handler(event, data)


def get_keyboard(user_id, button_layout):
    """Get inline keyboard"""

    user = get_user_from_redis(user_id)
    lang = Lang.Rus if user is None else user.lang

    keyboard_buttons = [
        [KeyboardButton(text=BUTTONS[name][lang]) for name in button_layout]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="ТЫК"
    )
    return keyboard


def get_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user_from_redis(str(user_id))
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
        self._dp.update.outer_middleware.register(StateAutoSetMiddleware())
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
        self._dp.message.register(handle_admin_register, Command("admin"), IsAdmin(self._admin_list))
        self._dp.message.register(self.handle_lang_change, F.text.in_(BUTTONS["lang"].values()))
        self._dp.message.register(
            self.handle_check_membership,
            StateFilter(UserStates.main_menu),
            F.text.in_(BUTTONS["check_membership"].values())
        )
        self._dp.message.register(
            self.handle_calendar,
            StateFilter(UserStates.main_menu),
            F.text.in_(BUTTONS["calendar"].values())
        )
        self._dp.message.register(
            self.handle_check_in,
            StateFilter(UserStates.main_menu),
            F.text.in_(BUTTONS["check_in"].values())
        )
        self._dp.message.register(
            handle_quest_mode_on,
            StateFilter(UserStates.main_menu),
            F.text.in_(BUTTONS["quest_mode"].values())
        )
        self._dp.message.register(
            handle_quest_mode_off,
            StateFilter(UserStates.quest_mode),
            F.text.in_(BUTTONS["return"].values())
        )
        self._dp.message.register(
            handle_quest_clue,
            StateFilter(UserStates.quest_mode),
        )

    def run(self):
        asyncio.run(self._run_tasks())

    async def handle_start(self, message: Message, state: FSMContext) -> None:
        """
        This handler receives messages with `/start` command
        """
        init_redis()
        user = get_user(message)

        membership = find_working_membership(user.username)
        # Process error messages
        if len(membership.errors) > 0:
            for error in membership.errors:
                await send_message_to_admins(
                    f"{ADMIN_LOG_MSG_TXT} Error in validation for user {user.username}: {error}",
                    bot=self._bot
                )
        hello_msg = get_message_for_user('hello_msg', user.lang)
        messages = [hello_msg]
        messages.extend(check_membership(user, membership))
        # Also if it is a community day
        current_date = datetime.now()
        if current_date.weekday() == COMMUNITY_DAY:
            messages.append(get_message_for_user('community_day', user.lang))
        logging.info(f"Messages for user {user.username}: {messages}")
        await state.set_state(UserStates.main_menu)
        await message.answer("\n".join(messages), reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT))

    async def handle_lang_change(self, message: Message):
        user = get_user(message)
        
        if user.lang == Lang.Rus:
            user.lang = Lang.Eng
        else:
            user.lang = Lang.Rus
    
        add_user_to_redis(user) 
        await message.answer(
            get_message_for_user('lang_changed', user.lang),
            reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT),
        )

    async def handle_check_membership(self, message: Message):
        user = get_user(message)
        membership = find_working_membership(user.username)
        messages = check_membership(user, membership)
        await message.answer("\n".join(messages), reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT))

    async def handle_calendar(self, message: Message):
        user = get_user(message)
        await message.answer(
            get_message_for_user('calendar', user.lang),
            reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT)
        )

    async def handle_check_in(self, message: Message):
        # Get the current date
        current_date = datetime.now()
        
        user = get_user(message)
        membership = find_working_membership(user.username)
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
                    last_punch = split_by_coma(membership.membership_data['punches'])[-1]
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
        await message.answer(
            get_message_for_user(msg, user.lang),
            reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT)
        )


async def handle_admin_register(message: Message):
    admin_chats = read_chats_from_redis_list(ADMIN_CHATS_KEY)
    chat_id = str(message.chat.id)
    if chat_id not in admin_chats:
        add_chat_to_redis_list(chat_id, ADMIN_CHATS_KEY)
        admin_chats.append(chat_id)
        await message.answer(f"Chat {message.chat.id} added to the admin list!")
    else:
        await message.answer("You are already in admin list!")


async def handle_quest_mode_on(message: Message, state: FSMContext):
    user = get_user(message)
    await state.set_state(UserStates.quest_mode)
    await message.answer(
        "quest mode",
        reply_markup=get_keyboard(user.user_id, QUEST_BUTTON_LAYOUT),
    )


async def handle_quest_mode_off(message: Message, state: FSMContext):
    user = get_user(message)
    await state.set_state(UserStates.main_menu)
    await message.answer(
        "main mode",
        reply_markup=get_keyboard(user.user_id, TOP_LEVEL_BUTTON_LAYOUT),
    )


async def handle_quest_clue(message: Message):
    user = get_user(message)
    if not message.text:
        # redundant
        await message.answer(
            "empty clue",
            reply_markup=get_keyboard(user.user_id, QUEST_BUTTON_LAYOUT),
        )
    else:

        reply = "Nice clue" if message.text in CRYPTIDS else "Not a clue"
        await message.answer(
            reply,
            reply_markup=get_keyboard(user.user_id, QUEST_BUTTON_LAYOUT),
        )
