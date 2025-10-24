import os
from datetime import datetime
import pandas as pd
import gspread
from datetime import datetime, timedelta
import logging
from kvira_space_bot_src.spreadsheets.data import (UserPassType,
                                                   ValidationResult,
                                                   DateStorageError,
                                                   WorkingMembership,
                                                   Lang
)

USERS_SHEET = 'Memberships-bot'
TEXTS_SHEET = 'Prompts-bot'


if not os.environ.get('KVIRA_BOT_TESTS_ENV'):
    # If we are not in the tests environment, we need to load the environment variables
    GOOGLE_KEY_FILE_PATH = os.environ['GOOGLE_KEY_FILE_PATH']
    GOOGLE_DOC_ID = os.environ['GOOGLE_DOC_ID']


def split_punch_string(punches: str) -> list:
    """
    Process the punches in form of string e.g. "6.06.2024, 7.06.2024"
    and return a list of punches e.g. ['6.06.2024', '7.06.2024']
    """
    punches_list = punches.strip().split(',')
    return [punch.strip() for punch in punches_list if punch.strip()]


def get_all_user_data() -> pd.DataFrame:
    """Get all user data from the spreadsheet.
    """
    sheet = get_sheet(USERS_SHEET)
    # return pd.DataFrame(sheet.get_all_records())
    values = sheet.get_values()
    df = pd.DataFrame(values[1:], columns=values[0])
    # Drop all rows where tg_nickname is empty
    df = df.dropna(subset=['tg_nickname'])
    return df

def find_user_in_df(username: str, df: pd.DataFrame) -> pd.DataFrame:
    """Find all rows where tg_nickname == username
    """
    return df[df['tg_nickname'] == username]


def process_error_in_username(username: str) -> None:
    pass


def validate_membership_row(row: pd.Series) -> ValidationResult:
    """Check if all date rows are in the correct format.
    Returns status of validation and list of errors
    """
    # Validating pass_types:
    # TODO
    errors = list()
    
    date_columns = ['date_activated', 'exparation_date']
    for column in date_columns:
        # If not empty, check if the date is in the correct format
        if row[column] == '' or row[column] == None:
            # Empty date is valid
            pass
        else:
            try:
                datetime.strptime(row[column], '%d.%m.%Y')
            except (ValueError, TypeError) as e:
                process_error_in_username(row['tg_nickname'])
                error = DateStorageError(f"Error in {column} for user {row['tg_nickname']}. Value: {row[column]}, error {e}", row.to_dict())
                errors.append(error)
    if len(errors) > 0:
        return ValidationResult(result=False, validation_erros=errors)
    return ValidationResult(result=True, validation_erros=errors)


def find_working_membership(username, current_date: str | None = None, df: pd.DataFrame | None = None) -> WorkingMembership:
    """Find all rows where tg_nickname == username
    Return WorkingMembership object with row_id and errors
    row_id is the index of the row in the dataframe
    errors is a list of DateStorageError objects which will be used to notify admins about the errors
    """
    data = get_all_user_data() if df is None else df
    errors = list()
    if current_date is None:
        current_date = datetime.now()
    else:
        current_date = datetime.strptime(current_date, '%d.%m.%Y')
    user_df = find_user_in_df(username, data)
    if len(user_df) > 0:
        for index, row in user_df.iterrows():
            # On this step current date should be compared with activation date + 30 days
            # All dates in format dd.mm.yyyy
            # If current date is bigger than activation date + 30 days - pass
            # If current date is less than activation date + 30 days - return row
            validation_result: ValidationResult = validate_membership_row(row)
            if not validation_result.result:
                errors.extend(validation_result.validation_erros)
                logging.error(f"Error(s) encountered during validation of {username} entery")
            else:
                activation_date = row['date_activated']
                print(f"Activation date: '{activation_date}', ({activation_date != ''})")
                if activation_date == '' or activation_date == None:
                    # Pass has not been activated yet! But is valid
                    return WorkingMembership(row_id=index, activated=False, errors=errors, membership_data=row.to_dict())
                else:
                    activation_date = datetime.strptime(activation_date, '%d.%m.%Y')
                    exparation_date = activation_date + timedelta(days=30)
                    if current_date < exparation_date:
                        # This means that row is valid in 30 days period
                        # Now lets check if user has any punches
                        punches = row['punches']
                        if punches == '' or punches:
                            num_punches = len(punches.split(','))
                            if num_punches < UserPassType.get_days_count(row['pass_type']):
                                membership_data = row.to_dict()
                                return WorkingMembership(row_id=index, activated=True, errors=errors, membership_data=membership_data)
    return WorkingMembership(row_id=None, activated=None, errors=errors, membership_data=None)


def activate_membership(membership: WorkingMembership, current_date: str | None = None) -> bool:
    """Activate pass if it was not activated yet.
    """
    if membership.activated:
        return True
    if current_date is None:
        current_date = datetime.now().strftime('%d.%m.%Y')
    else:
        current_date = datetime.strptime(current_date, '%d.%m.%Y')
    sheet = get_sheet(USERS_SHEET)
    row_number = membership.row_id + 2
    sheet.update_cell(row_number, 3, current_date)
    return True


def check_if_user_exists(username: str) -> bool:
    sheet = get_sheet(USERS_SHEET)
    column_data = sheet.col_values(1)[1:]
    return username in column_data

def punch_user_day(pd_row_id: int, current_date: str | None = None):
    """Punch the user for the current day.
    """
    try:
        sheet = get_sheet(USERS_SHEET)
        # find row number of the user
        row_number = pd_row_id + 2
        # get all punches
        punches = sheet.cell(row_number, 5).value
        if punches is None or punches == '' or punches == " ":
            punches = []
        else:
            punches = punches.split(',')
            punches = [ punch.strip() for punch in punches ]
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


# def get_days_left(username: str, df: pd.DataFrame | None = None,) -> int:
#     """Days left for the user to use the pass. DEPRECATED
#     """
#     pd_row = find_user_in_df(username, df)

#     return UserPassType.get_days_count(pass_type) - len(punches)

def get_days_left_from_membership(membership: WorkingMembership) -> int:
    """Get days left from the WorkingMembership object.
    """
    pass_type = membership.membership_data['pass_type']
    punches = split_punch_string(membership.membership_data['punches'])
    return UserPassType.get_days_count(pass_type) - len(punches)

def get_expation_date(username: str) -> str:
    """Get the expiration date of the pass for the user.
    """
    sheet = get_sheet(USERS_SHEET)
    # find row number of the user
    row_number = sheet.col_values(1).index(username) + 1
    
    column_number = 4
    expation_date = sheet.cell(row_number, column_number).value
    return expation_date

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