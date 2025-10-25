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


def next_empty_row():
    sheet = get_sheet(TEXTS_SHEET)
    for row in itertools.count(1):
        if not sheet.cell(row, 1).value.strip:
            return row


def get_user(name: str) -> Participant | None:
    sheet = get_sheet(TEXTS_SHEET)
    for row in itertools.count(1):
        value = sheet.cell(row, 1).value.strip()
        if not value:
            return None
        if value == name:
            return get_user_by_row(row)


def get_user_by_row(row: int) -> Participant:
    sheet = get_sheet(TEXTS_SHEET)
    name = sheet.cell(row, 1).strip()
    if not name:
        # error
        pass
    clues = split_by_coma(sheet.cell(row, 2))
    for clue in clues:
        if clue not in CRYPTIDS.keys():
            # error
            pass
    return Participant(row, name, clues)


def add_user(user: str):
    try:
        return add_user_(user)
    except Exception as e:
        logging.error(f"Error while punching the user with row id {user}: {e}")
        return False


def add_user_(user: str):
    sheet = get_sheet(TEXTS_SHEET)
    row = next_empty_row()
    sheet.update_cell(row, 1, user)
