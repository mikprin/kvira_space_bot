import logging

from kvira_space_bot_src.spreadsheets.data import Lang, get_sheet

TEXTS_SHEET = 'Prompts-bot'


def get_message_for_user_from_google(str_id: str, lang: Lang) -> str:
    """Get message for the user from the spreadsheet prepared for the given language.

    Columns in the spreadsheet correspond to the Lang enum values.
    Rows in the spreadsheet correspond to the particular phrases used by the bot.
    """
    sheet = get_sheet(TEXTS_SHEET)
    row_number = sheet.col_values(1).index(str_id) + 1
    column_number = lang.value
    msg = sheet.cell(row_number, column_number).value
    return msg


def get_all_text_json() -> dict:
    """Get all messages from the spreadsheet and return them as a dictionary."""
    sheet = get_sheet(TEXTS_SHEET)
    listed_data = sheet.get_all_records()
    dicted_data = dict()
    # It is now in format list[dict]
    # We need to convert it to dict[str, dict]
    for item in listed_data:
        if 'msg_type' not in item:
            logging.error(f"msg_type is not in the item {item}")
        else:
            dicted_data[item['msg_type']] = item
    return dicted_data
