import datetime
import unittest

from bktest.iterator import DateIterator, Skip


class DateIteratorTest(unittest.TestCase):

    def test_should_skip_weekends_allow(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=True)
        self.assertFalse(iterator.should_skip_weekends(datetime.date(2024, 1, 20), False))

    def test_should_skip_weekends_week(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=False)
        self.assertFalse(iterator.should_skip_weekends(datetime.date(2024, 1, 23), False))

    def test_should_skip_weekends(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=False)
        date = datetime.date(2024, 1, 20)

        self.assertEqual(Skip(date, "weekend", True), iterator.should_skip_weekends(date, True))

    def test_should_skip_holidays_allow(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=True)
        self.assertFalse(iterator.should_skip_holidays(datetime.date(2023, 12, 25), False))

    def test_should_skip_holidays_week(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=False)
        self.assertFalse(iterator.should_skip_holidays(datetime.date(2023, 12, 27), False))

    def test_should_skip_holidays(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=False)
        date = datetime.date(2023, 12, 25)

        self.assertEqual(Skip(date, "holiday", True), iterator.should_skip_holidays(date, True))
