import logging
from os import getenv

from dotenv import load_dotenv

from kvira_space_bot_src.bot import TelegramApiBot


def run_bot():
    load_dotenv()
    admin_ids = getenv("ADMIN_CHATS").split(",")
    token = getenv("TELEGRAM_API_KEY")

    TelegramApiBot(admin_ids, token).run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
