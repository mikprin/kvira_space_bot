import itertools
import logging
from dataclasses import dataclass

from kvira_space_bot_src.spreadsheets.data import get_sheet, split_by_coma

TEXTS_SHEET = 'HalloweenQuest-bot'

CLUES = {
    "underneath": "Zaratan",
    "mordax": "Inkanyamba",
    "усы": "PopeLickMonster",
    "diamond": "VoronezhGiant",
    "kitchen": "Batsquatch",
    "кухня": "Batsquatch",
    "coquina": "Batsquatch",
    "portret": "Kraken",
    "щоциер3гпр": "Paklya",
}

CRYPTID_NAMES = {
    "Zaratan": "Zaratan",
    "Inkanyamba": "Inkanyamba",
    "PopeLickMonster": "Pope Lick Monster",
    "VoronezhGiant": "Voronezh Giant",
    "Batsquatch": "Batsquatch",
    "Kraken": "Kraken",
    "Paklya": "Paklya",
}


@dataclass
class Participant:
    row: int
    name: str
    cryptids: [str]


def ensure_and_get_user(name: str) -> Participant | None:
    user = get_user(name)
    if not user:
        return add_user(name)
    return user


def add_cryptid(user: Participant, cryptid: str) -> bool:
    sheet = get_sheet(TEXTS_SHEET)
    cryptid_list = get_cell_stripped(user.row, 2, sheet)
    cryptids = split_by_coma(cryptid_list)
    if cryptid in cryptids:
        return False
    if not cryptid_list:
        sheet.update_cell(user.row, 2, cryptid)
    else:
        sheet.update_cell(user.row, 2, f"{cryptid_list}, {cryptid}")
    # TODO: handle exception
    return True


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
    cryptids = split_by_coma(get_cell_stripped(row, 2, sheet))
    for cryptid in cryptids:
        if cryptid not in CLUES.values():
            # error
            pass
    return Participant(row, name, cryptids)


def get_cell_stripped(row, column, sheet):
    value = sheet.cell(row, column).value
    if not value or not value.strip():
        return None
    return value.strip()


def add_user(name: str) -> Participant | None:
    try:
        return add_user_(name)
    except Exception as e:
        logging.error(f"Error while adding user with row id {name}: {e}")
        return None


def add_user_(name: str) -> Participant:
    sheet = get_sheet(TEXTS_SHEET)
    row = next_empty_row()
    sheet.update_cell(row, 1, name)
    return Participant(row, name, [])
