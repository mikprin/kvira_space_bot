import os
from datetime import datetime
from enum import Enum
import pandas as pd
import gspread
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field

if not os.environ.get('KVIRA_BOT_TESTS_ENV'):
    # If we are not in the tests environment, we need to load the environment variables
    GOOGLE_KEY_FILE_PATH = os.environ['GOOGLE_KEY_FILE_PATH']
    GOOGLE_DOC_ID = os.environ['GOOGLE_DOC_ID']


class UserPassType(Enum):
    """Types of passes that the user can have.
    Value represents the number of days the pass is valid for.
    """
    Day30_pass = ("30day", 30)
    Day5_pass = ("5day", 5)
    Day10_pass = ("10day", 10)

    @classmethod
    def get_days_count(cls, pass_type: str) -> int:
        for pass_type_enum in cls:
            if pass_type_enum.value[0] == pass_type:
                return pass_type_enum.value[1]

@dataclass
class DateStorageError:
    """Class to store all errors that can happen during the data processing.
    Must contain error codes and messages.
    And Row data if applicable.
    """
    error_message: str
    row_data: dict | None = None
    
@dataclass
class WorkingMembership():
    """Class to store all working memberships.
    """
    row_id: int | None = None
    membership_data: dict | None = None
    errors: list = field(default_factory=lambda: list())
    

class Lang(Enum):
    """Language enum for the message to be sent to the user.
    Value represents the column number in the spreadsheet.
    """
    Eng = 3
    Rus = 2

def process_punches_from_string(punches: str) -> list:
    """Process the punches in form of string e.g. "6.06.2024, 7.06.2024"
    and return a list of punches e.g. ['6.06.2024', '7.06.2024']
    """
    punches_list = punches.strip(" ").split(', ')
    punches_list = [ punch.strip() for punch in punches_list ]
    return punches_list

def get_gc():
    gc = gspread.service_account(filename=GOOGLE_KEY_FILE_PATH)
    return gc

def get_users_sheet():
    gc = get_gc()
    sheet = gc.open_by_key(GOOGLE_DOC_ID).sheet1
    return sheet

def get_user_data_pandas() -> pd.DataFrame:
    """Get all user data from the spreadsheet.
    """
    sheet = get_users_sheet()
    return pd.DataFrame(sheet.get_all_records())

def find_user_in_df(username: str, df: pd.DataFrame) -> pd.DataFrame:
    """Find all rows where tg_nickname == username
    """
    return df[df['tg_nickname'] == username]

def process_error_in_username(username: str) -> None:
    pass

def validate_date_row(row: pd.Series) -> bool:
    """Check if all date rows are in the correct format.
    """
    date_columns = ['date_activated',]
    for column in date_columns:
        try:
            datetime.strptime(row[column], '%d.%m.%Y')
        except (ValueError, TypeError):
            process_error_in_username(row['tg_nickname'])
            return False, DateStorageError(
                error_message=f"Date row {column} is not in the correct format for user {row['tg_nickname']}",
                row_data=row.to_dict()
            )
    return True, None

def find_working_membership(username, df: pd.DataFrame, current_date: str | None = None) -> WorkingMembership:
    """Find all rows where tg_nickname == username
    Return WorkingMembership object with row_id and errors
    row_id is the index of the row in the dataframe
    errors is a list of DateStorageError objects which will be used to notify admins about the errors
    """
    errors = []
    if current_date is None:
        current_date = datetime.now()
    else:
        current_date = datetime.strptime(current_date, '%d.%m.%Y')
    user_df = find_user_in_df(username, df)
    if len(user_df) > 0:
        for index, row in user_df.iterrows():
            # On this step current date should be compared with activation date + 30 days
            # All dates in format dd.mm.yyyy
            # If current date is bigger than activation date + 30 days - pass
            # If current date is less than activation date + 30 days - return row
            validation_result = validate_date_row(row)
            if not validation_result[0]:
                errors.append(validation_result[1])
                logging.error(f"Date rows are not in the correct format for user {username}")
            else:  
                activation_date = row['date_activated']
                activation_date = datetime.strptime(activation_date, '%d.%m.%Y')
                exparation_date = activation_date + timedelta(days=30)
                if current_date < exparation_date:
                    # This means that row is valid in 30 days period
                    # Now lets check if user has any punches
                    punches = row['punches']
                    if punches == '' or punches:
                        num_punches = len(punches.split(','))
                        if num_punches < UserPassType.get_days_count(row['pass_type']):
                            return WorkingMembership(row_id=index, errors=errors, membership_data=row.to_dict())
    return WorkingMembership(row_id=None, errors=errors, membership_data=None)

def check_if_user_exists(username: str) -> bool:
    sheet = get_users_sheet()
    column_data = sheet.col_values(1)[1:]
    return username in column_data

def punch_user_day(pd_row_id: int, current_date: str | None = None):
    """Punch the user for the current day.
    """
    try:
        sheet = get_users_sheet()
        # find row number of the user
        row_number = pd_row_id + 2
        # get all punches
        punches = sheet.cell(row_number, 5).value.split(', ')
        # add new punch
        if current_date is None:
            current_date = datetime.now().strftime('%d.%m.%Y')
        else:
            current_date = datetime.strptime(current_date, '%d.%m.%Y')
        punches.append(current_date)
        # update the row
        sheet.update_cell(row_number, 5, ', '.join(punches))
        
    except Exception as e:
        logging.error(f"Error while punching the user with row id {pd_row_id}: {e}")
        return False
    return True


def get_days_left(username: str, df: pd.DataFrame | None = None,) -> int:
    """Days left for the user to use the pass.
    """
    pd_row = find_user_in_df(username, df)

    return UserPassType.get_days_count(pass_type) - len(punches)

def get_days_left_from_membership(membership: WorkingMembership) -> int:
    """Get days left from the WorkingMembership object.
    """
    pass_type = membership.membership_data['pass_type']
    punches = process_punches_from_string(membership.membership_data['punches'])
    return UserPassType.get_days_count(pass_type) - len(punches)

def get_expation_date(username: str) -> str:
    """Get the expiration date of the pass for the user.
    """
    sheet = get_users_sheet()
    # find row number of the user
    row_number = sheet.col_values(1).index(username) + 1
    
    column_number = 4
    expation_date = sheet.cell(row_number, column_number).value
    return expation_date

def get_message_for_user(str_id: str, lang: Lang) -> str:
    """Get message for the user from the spreadsheet prepared for the given language.
    
    Columns in the spreadsheet correspond to the Lang enum values.
    Rows in the spreadsheet correspond to the particular phrases used by the bot.
    """
    gc = get_gc()
    sheet = gc.open_by_key(GOOGLE_DOC_ID).get_worksheet(1)
    row_number = sheet.col_values(1).index(str_id) + 1
    column_number = lang.value
    msg = sheet.cell(row_number, column_number).value
    return msg
