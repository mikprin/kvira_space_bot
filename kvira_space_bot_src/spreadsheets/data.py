import os
from enum import Enum
from dataclasses import dataclass, field

import gspread

if not os.environ.get('KVIRA_BOT_TESTS_ENV'):
    # If we are not in the tests environment, we need to load the environment variables
    GOOGLE_KEY_FILE_PATH = os.environ['GOOGLE_KEY_FILE_PATH']
    GOOGLE_DOC_ID = os.environ['GOOGLE_DOC_ID']


class UserPassType(Enum):
    """Types of passes that the user can have.
    Value represents the number of days the pass is valid for.
    """
    Day5_pass = ("5day", 5)
    Day10_pass = ("10day", 10)
    Day30_pass = ("30day", 30)

    @classmethod
    def get_days_count(cls, pass_type: str) -> int:
        for pass_type_enum in cls:
            if pass_type_enum.value[0] == pass_type:
                return pass_type_enum.value[1]

    @classmethod
    def get_all_membership_types(cls) -> list[str]:
        all_types = []
        for pass_type_enum in cls:
            all_types.append(pass_type_enum.value[0])
        return all_types


@dataclass
class ValidationResult:
    result: bool
    validation_errors: list = field(default_factory=lambda: list())


@dataclass
class DateStorageError:
    """Class to store all errors that can happen during the data processing.
    Must contain error codes and messages.
    And Row data if applicable.
    """
    error_message: str
    row_data: dict | None = None


@dataclass
class Membership:
    """Class to store all working memberships.
    """
    row_id: int | None = None
    activated: bool | None = None
    membership_data: dict | None = None
    errors: list = field(default_factory=lambda: list())


class Lang(Enum):
    """Language enum for the message to be sent to the user.
    Value represents the column number in the spreadsheet.
    """
    Eng = "eng"
    Rus = "rus"


def get_sheet(name):
    gc = gspread.service_account(filename=GOOGLE_KEY_FILE_PATH)
    table = gc.open_by_key(GOOGLE_DOC_ID)
    worksheet_list = table.worksheets()
    # Find sheet with title USERS_SHEET_NAME
    sheet = None
    for worksheet in worksheet_list:
        if worksheet.title == name:
            sheet = worksheet
            break
    return sheet
