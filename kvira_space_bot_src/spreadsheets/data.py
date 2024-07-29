from enum import Enum
from dataclasses import dataclass, field

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

    @classmethod
    def get_all_membership_types(cls) -> list[str]:
        all_types = []
        for pass_type_enum in cls:
            all_types.append(pass_type_enum.value[0])
        return all_types


@dataclass
class ValidationResult:
    result: bool
    validation_erros: list = field(default_factory=lambda: list())

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
    activated: bool | None = None
    membership_data: dict | None = None
    errors: list = field(default_factory=lambda: list())

class Lang(Enum):
    """Language enum for the message to be sent to the user.
    Value represents the column number in the spreadsheet.
    """
    Eng = "eng"
    Rus = "rus"