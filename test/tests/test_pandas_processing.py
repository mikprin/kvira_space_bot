import pandas as pd

import os
os.environ['KVIRA_BOT_TESTS_ENV'] = 'True'

from kvira_space_bot_src.spreadsheets.api import (
    find_working_membership,
    WorkingMembership,
    DateStorageError,
    get_days_left_from_membership,
)

def test_get_current_membership():
    
    records = [{'tg_nickname': 'Dark',
        'pass_type': '5day',
        'date_activated': '1.1.2024',
        'exparation_date': '30.1.2024',
        'punches': '01.01.2024, 04.01.2024, 08.01.2024, 15.01.2024, 20.01.2024'},
        {'tg_nickname': 'Puk',
        'pass_type': '5day',
        'date_activated': '2.1.2024',
        'exparation_date': '2.2.2024',
        'punches': '01.01.2024, 04.01.2024, 08.01.2024, 15.01.2024, 20.01.2024'},
        {'tg_nickname': 'Miksolo',
        'pass_type': '30day',
        'date_activated': '1.7.2024',
        'exparation_date': '1.08.2024',
        'punches': '01.07.2024, 02.07.2024, 05.07.2024'},
        {'tg_nickname': 'SomeDude',
        'pass_type': '5day',
        'date_activated': '',
        'exparation_date': '',
        'punches': ''},
        {'tg_nickname': 'Puk',
        'pass_type': '10day',
        'date_activated': '5.7.2024',
        'exparation_date': '5.08.2024',
        'punches': ''},
        {'tg_nickname': 'TravelFan123',
        'pass_type': '5day',
        'date_activated': '3.7.2024',
        'exparation_date': '3.08.2024',
        'punches': '03.15.2024, 03.18.2024, 03.20.2024'},
        {'tg_nickname': 'Wanderlust',
        'pass_type': '10day',
        'date_activated': '6.6.2024',
        'exparation_date': '',
        'punches': '6.06.2024, 7.06.2024, 8.06.2024'},
        {'tg_nickname': 'ErrorSample',
        'pass_type': '2day',
        'date_activated': 1.1,
        'exparation_date': '',
        'punches': '1,1'}]
    
    df = pd.DataFrame(records)
    
    res: WorkingMembership = find_working_membership('Wanderlust', df, current_date='05.06.2024')
    assert type(res) is WorkingMembership
    assert res.row_id == 6, f"Index of Wanderlust is {res.row_id} instead of 6"
    
    res = find_working_membership('SomeDude', df, current_date='06.06.2024')
    assert type(res) is WorkingMembership
    assert res.row_id is None
    
    res = find_working_membership('Puk', df, current_date='06.06.2024')
    assert type(res) is WorkingMembership
    assert res.row_id == 4, f"Index of working pass for Puk is {res.row_id} instead of 4"
    assert res.membership_data['exparation_date'] == '5.08.2024'
    assert res.membership_data['punches'] == ''
    
    res = find_working_membership('ErrorSample', df, current_date='06.06.2024')
    assert type(res) is WorkingMembership
    assert res.row_id is None
    assert len(res.errors) == 1
    assert type(res.errors[0]) is DateStorageError
    
    

def test_get_days_left_from_membership():
    
    membership = WorkingMembership(
        row_id=0,
        errors=[],
        membership_data={
            'tg_nickname': 'Dark',
            'pass_type': '5day',
            'date_activated': '1.1.2024',
            'exparation_date': '30.1.2024',
            'punches': '01.01.2024, 04.01.2024, 15.01.2024, 20.01.2024'
        }
    )
    
    days_left = get_days_left_from_membership(membership)
    assert days_left == 1, f"Days left for Dark is {days_left} instead of 1"
    
    membership = WorkingMembership(
        row_id=0,
        errors=[],
        membership_data={
            'tg_nickname': 'Dark',
            'pass_type': '10day',
            'date_activated': '1.1.2024',
            'exparation_date': '30.1.2024',
            'punches': '01.01.2024, 04.01.2024, 15.01.2024, 20.01.2024'
        }
    )
    
    days_left = get_days_left_from_membership(membership)
    assert days_left == 6, f"Days left for Dark is {days_left} instead of 6"