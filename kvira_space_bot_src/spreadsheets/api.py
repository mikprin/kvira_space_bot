import os
from datetime import datetime
from enum import Enum

import gspread


KEY_FILE_PATH = os.environ['KEY_FILE_PATH']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']

gc = gspread.service_account(filename=KEY_FILE_PATH)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1


class UserPassType(Enum):
    Day30_pass = ("30day", 30)
    Day5_pass = ("5day", 5)
    Day10_pass = ("10day", 10)

    @classmethod
    def get_days_count(cls, pass_type: str) -> int:
        for pass_type_enum in cls:
            if pass_type_enum.value[0] == pass_type:
                return pass_type_enum.value[1]


class Lang(Enum):
    Eng = 3
    Rus = 2


def check_if_user_exists(username: str) -> bool:
    column_data = sheet.col_values(1)[1:]
    return username in column_data


def punch_user_day(username: str):
    # find row number of the user
    row_number = sheet.col_values(1).index(username) + 1
    # get all punches
    punches = sheet.cell(row_number, 5).value.split(', ')
    # add new punch
    punches.append(datetime.now().strftime('%d.%m.%Y'))
    # update the row
    sheet.update_cell(row_number, 5, ', '.join(punches))


def get_days_left(username: str) -> int:
    # find row number of the user
    row_number = sheet.col_values(1).index(username) + 1
    # get all punches
    punches = sheet.cell(row_number, 5).value.split(', ')
    # get pass type
    pass_type = sheet.cell(row_number, 2).value

    return UserPassType.get_days_count(pass_type) - len(punches)


def get_message_for_user(str_id: str, lang: Lang) -> str:
    sheet = gc.open_by_key(SPREADSHEET_ID).get_worksheet(1)
    row_number = sheet.col_values(1).index(str_id) + 1
    column_number = lang.value
    msg = sheet.cell(row_number, column_number).value
    return msg
