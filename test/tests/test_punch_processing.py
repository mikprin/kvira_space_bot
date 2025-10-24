import unittest

from kvira_space_bot_src.spreadsheets.memberships import split_punch_string

class TestProcessPunchesFromString(unittest.TestCase):
    
    def test_empty_string(self):
        self.assertEqual(split_punch_string(''), [])

    def test_whitespace_string(self):
        self.assertEqual(split_punch_string(' '), [])

    def test_single_punch(self):
        self.assertEqual(split_punch_string('6.06.2024'), ['6.06.2024'])

    def test_multiple_punches(self):
        self.assertEqual(split_punch_string('6.06.2024, 7.06.2024'), ['6.06.2024', '7.06.2024'])

    def test_punches_with_extra_spaces(self):
        self.assertEqual(split_punch_string(' 6.06.2024, 7.06.2024 '), ['6.06.2024', '7.06.2024'])

    def test_punches_with_different_formats(self):
        self.assertEqual(split_punch_string('6.06.2024,  7.06.2024,  8.06.2024 '), ['6.06.2024', '7.06.2024', '8.06.2024'])

    def test_no_punches(self):
        self.assertEqual(split_punch_string('No punches here!'), ['No punches here!'])

if __name__ == '__main__':
    unittest.main()
