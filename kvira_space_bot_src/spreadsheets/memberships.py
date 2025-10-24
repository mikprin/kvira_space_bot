import pandas as pd
from datetime import datetime, timedelta
import logging
from kvira_space_bot_src.spreadsheets.data import (UserPassType,
                                                   ValidationResult,
                                                   DateStorageError,
                                                   Membership,
                                                   get_sheet
                                                   )

USERS_SHEET = 'Memberships-bot'


def split_punch_string(punches: str) -> list:
    """
    Process the punches in form of string e.g. "6.06.2024, 7.06.2024"
    and return a list of punches e.g. ['6.06.2024', '7.06.2024']
    """
    punches_list = punches.strip().split(',')
    return [punch.strip() for punch in punches_list if punch.strip()]


def get_all_user_data() -> pd.DataFrame:
    """
    Get all user data from the spreadsheet.
    """
    sheet = get_sheet(USERS_SHEET)
    # return pd.DataFrame(sheet.get_all_records())
    values = sheet.get_values()
    df = pd.DataFrame(values[1:], columns=values[0])
    # Drop all rows where tg_nickname is empty
    df = df.dropna(subset=['tg_nickname'])
    return df


def validate_membership_row(row: pd.Series) -> ValidationResult:
    """
    Check if all date rows are in the correct format.
    Returns validation status and list of errors.
    """
    # TODO: Validate tg_nickname and pass_types
    user_name = row['tg_nickname']
    date_cells = ['date_activated', 'exparation_date']
    possible_date_errors = [validate_date_cell(user_name, cell, row) for cell in date_cells]
    date_errors = [error for error in possible_date_errors if error is not None]
    if date_errors:
        return ValidationResult(result=False, validation_errors=date_errors)
    return ValidationResult(result=True)


def validate_date_cell(user_name, column, row: pd.Series):
    cell = row[column]
    if not cell.strip():
        return
    try:
        datetime.strptime(row[column], '%d.%m.%Y')
    except (ValueError, TypeError) as e:
        return DateStorageError(
            f"Error in {column} for user {user_name}. Value: {cell}, error {e}", row.to_dict()
        )


def find_working_membership(username, current_date: str | None = None, df: pd.DataFrame | None = None) -> Membership:
    """
    Find all rows where tg_nickname == username
    Return WorkingMembership object with row_id and errors
    row_id is the index of the row in the dataframe
    errors is a list of DateStorageError objects which will be used to notify admins about the errors
    """
    all_data = get_all_user_data() if df is None else df
    user_data = all_data[all_data['tg_nickname'] == username]

    current_date = datetime.now() if current_date is None \
        else datetime.strptime(current_date, '%d.%m.%Y')

    if user_data is None:
        return Membership()

    errors = list()
    for index, row in user_data.iterrows():
        # Current date is compared with expiration date = activation date + 30 days
        # If current date is bigger than activation date + 30 days - pass
        # If current date is less than activation date + 30 days - return row
        row_validation = validate_membership_row(row)
        if not row_validation.result:
            errors.extend(row_validation.validation_errors)
            logging.error(f"Error(s) {row_validation.validation_errors} encountered during validation of {username} entry")
        else:
            activation_date = row['date_activated']
            print(f"Activation date: '{activation_date}', ({activation_date != ''})")
            if activation_date is None or not activation_date.strip():
                # Pass has not been activated yet! But is valid
                return Membership(row_id=index, activated=False, errors=errors, membership_data=row.to_dict())
            else:
                activation_date = datetime.strptime(activation_date, '%d.%m.%Y')
                expiration_date = activation_date + timedelta(days=30)
                if current_date < expiration_date:
                    # This means that row is valid in 30 days period
                    # Now lets check if user has any punches
                    punches = [punch.strip() for punch in row['punches'].split(',') if punch.strip()]
                    if len(punches) < UserPassType.get_days_count(row['pass_type']):
                        membership_data = row.to_dict()
                        return Membership(row_id=index, activated=True, errors=errors, membership_data=membership_data)
    return Membership(row_id=None, activated=None, errors=errors, membership_data=None)


def activate_membership(membership: Membership, current_date: str | None = None) -> bool:
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


def get_days_left_from_membership(membership: Membership) -> int:
    """Get days left from the WorkingMembership object.
    """
    pass_type = membership.membership_data['pass_type']
    punches = split_punch_string(membership.membership_data['punches'])
    return UserPassType.get_days_count(pass_type) - len(punches)


def get_expiration_date(username: str) -> str:
    """Get the expiration date of the pass for the user.
    """
    sheet = get_sheet(USERS_SHEET)
    # find row number of the user
    row_number = sheet.col_values(1).index(username) + 1
    
    column_number = 4
    expiration_date = sheet.cell(row_number, column_number).value
    return expiration_date
