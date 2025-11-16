import pytest
import os
from dotenv import load_dotenv
load_dotenv()

if os.environ.get('GOOGLE_KEY_FILE_PATH'):
    from kvira_space_bot_src.messaging import check_membership, get_message_for_user
    from kvira_space_bot_src.spreadsheets.api import WorkingMembership, Lang
    from kvira_space_bot_src.redis_tools import TelegramUser

    # Only do this tests if GOOGLE_KEY_FILE_PATH is set

    # def test_check_membership_no_pass():
    #     user = TelegramUser(user_id="1", username="Name",lang=Lang.Eng)
    #     membership = WorkingMembership(row_id=None, activated=False, membership_data={})
    #     messages = check_membership(user, membership)
    #     assert len(messages) == 1
    #     assert messages[0] == get_message_for_user('no_pass', Lang.Eng)

    # def test_check_membership_not_activated_pass():
    #     user = TelegramUser(user_id="1", username="Name",lang=Lang.Eng)
    #     membership = WorkingMembership(row_id=1, activated=False, membership_data={})
    #     messages = check_membership(user, membership)
    #     assert len(messages) == 1
    #     assert messages[0] == get_message_for_user('not_activated_pass', Lang.Eng)

    # def test_check_membership_month_pass():
    #     user = TelegramUser(user_id="1", username="Name",lang=Lang.Eng)
    #     membership = WorkingMembership(row_id=1, activated=True, membership_data={'pass_type': '30day'})
    #     messages = check_membership(user, membership)
    #     assert len(messages) == 1
    #     assert messages[0] == get_message_for_user('month_pass', Lang.Eng)

    # def test_check_membership_days_left():
    #     user = TelegramUser(user_id="1", username="Name",lang=Lang.Eng)
    #     membership = WorkingMembership(row_id=1, activated=True, membership_data={'pass_type': '5day'})
    #     messages = check_membership(user, membership)
    #     assert len(messages) == 2
    #     assert messages[0] == get_message_for_user('days_left', Lang.Eng).format(5)
    #     assert messages[1] == get_message_for_user('exp_date', Lang.Eng).format('expiration_date')

    # def test_check_membership_invalid_message():
    #     user = TelegramUser(user_id="1", username="Name",lang=Lang.Eng)
    #     membership = WorkingMembership(row_id=1, activated=True, membership_data={'pass_type': '5day'})
    #     messages = check_membership(user, membership)
    #     assert len(messages) == 2
    #     assert messages[0] == get_message_for_user('days_left', Lang.Eng).format(5)
    #     assert messages[1] == get_message_for_user('exp_date', Lang.Eng).format('expiration_date')

else:
    # Make pytest warn that the tests are skipped
    pytestmark = pytest.mark.skip(reason="GOOGLE_KEY_FILE_PATH not set")