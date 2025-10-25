import itertools
import logging
from dataclasses import dataclass

from kvira_space_bot_src.spreadsheets.data import get_sheet, split_by_coma

TEXTS_SHEET = 'HalloweenQuest-bot'

CRYPTIDS = {
    "yeti": "Yeti",
    "paklya": "Paklya",
}


@dataclass
class Participant:
    row: int
    name: str
    clues: [str]

    def cryptids(self) -> [str]:
        return [CRYPTIDS[clue] for clue in self.clues]


def ensure_user_added(name: str):
    if not get_user(name):
        add_user(name)


def handle_clue(username: str, clue: str):
    pass


def next_empty_row():
    sheet = get_sheet(TEXTS_SHEET)
    for row in itertools.count(1):
        name = get_cell_stripped(row, 1, sheet)
        if not name:
            return row


def get_user(name: str) -> Participant | None:
    sheet = get_sheet(TEXTS_SHEET)
    for row in itertools.count(1):
        value = get_cell_stripped(row, 1, sheet)
        if not value:
            return None
        if value == name:
            return get_user_by_row(row)


def get_user_by_row(row: int) -> Participant:
    sheet = get_sheet(TEXTS_SHEET)
    name = get_cell_stripped(row, 1, sheet)
    if not name:
        # error
        pass
    clues = split_by_coma(get_cell_stripped(row, 2, sheet))
    for clue in clues:
        if clue not in CRYPTIDS.keys():
            # error
            pass
    return Participant(row, name, clues)


def get_cell_stripped(row, column, sheet):
    value = sheet.cell(row, column).value
    if not value or not value.strip():
        return None
    return value.strip()


def add_user(user: str):
    try:
        return add_user_(user)
    except Exception as e:
        logging.error(f"Error while adding user with row id {user}: {e}")
        return False


def add_user_(user: str):
    sheet = get_sheet(TEXTS_SHEET)
    row = next_empty_row()
    sheet.update_cell(row, 1, user)
