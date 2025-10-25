import unittest

from kvira_space_bot_src.spreadsheets.memberships import split_by_coma


class TestProcessPunchesFromString(unittest.TestCase):
    
    def test_empty_string(self):
        self.assertEqual(split_by_coma(''), [])

    def test_whitespace_string(self):
        self.assertEqual(split_by_coma(' '), [])

    def test_single_punch(self):
        self.assertEqual(split_by_coma('6.06.2024'), ['6.06.2024'])

    def test_multiple_punches(self):
        self.assertEqual(split_by_coma('6.06.2024, 7.06.2024'), ['6.06.2024', '7.06.2024'])

    def test_punches_with_extra_spaces(self):
        self.assertEqual(split_by_coma(' 6.06.2024, 7.06.2024 '), ['6.06.2024', '7.06.2024'])

    def test_punches_with_different_formats(self):
        self.assertEqual(split_by_coma('6.06.2024,  7.06.2024,  8.06.2024 '), ['6.06.2024', '7.06.2024', '8.06.2024'])

    def test_no_punches(self):
        self.assertEqual(split_by_coma('No punches here!'), ['No punches here!'])


if __name__ == '__main__':
    unittest.main()
