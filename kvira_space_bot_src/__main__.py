from kvira_space_bot_src.bot import TelegramApiBot


def run_bot():
    telegram_api_bot = TelegramApiBot()
    telegram_api_bot.run()


if __name__ == "__main__":
    run_bot()
