import datetime
import unittest

from bktest.iterator import DateIterator, Postpone


class DateIteratorTest(unittest.TestCase):

    def test_iter_empty(self):
        iterator = DateIterator(None, None, False, [])
        with self.assertRaises(StopIteration):
            next(iter(iterator))

    def test_iter_double(self):
        iterator = DateIterator(datetime.date.today(), None, False, [])
        iter(iterator)

        with self.assertRaises(ValueError) as context:
            next(iter(iterator))

        self.assertEqual("double iter", str(context.exception))

    def test_should_skip_weekends_allow(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=True)
        self.assertFalse(iterator._should_skip_weekends(datetime.date(2024, 1, 20), False, []))

    def test_should_skip_weekends_week(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=False)
        self.assertFalse(iterator._should_skip_weekends(datetime.date(2024, 1, 23), False, []))

    def test_should_skip_weekends(self):
        iterator = DateIterator(None, None, False, [], allow_weekends=False)
        postponned = []
        date = datetime.date(2024, 1, 20)

        self.assertTrue(iterator._should_skip_weekends(date, True, postponned))
        self.assertEqual(postponned, [Postpone(date, "weekend")])

    def test_should_skip_holidays_allow(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=True)
        self.assertFalse(iterator._should_skip_holidays(datetime.date(2023, 12, 25), False, []))

    def test_should_skip_holidays_week(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=False)
        self.assertFalse(iterator._should_skip_holidays(datetime.date(2023, 12, 27), False, []))

    def test_should_skip_holidays(self):
        iterator = DateIterator(None, None, False, [], allow_holidays=False)
        postponned = []
        date = datetime.date(2023, 12, 25)

        self.assertTrue(iterator._should_skip_holidays(date, True, postponned))
        self.assertEqual(postponned, [Postpone(date, "holiday")])

    def test_next(self):
        iterator = iter(DateIterator(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 10),
            True,
            [
                datetime.date(2024, 1, 1),
                datetime.date(2024, 1, 4),
                datetime.date(2024, 1, 7),
                datetime.date(2024, 1, 9),
            ]
        ))

        self.assertEqual(next(iterator), (datetime.date(2024, 1, 2), False, [Postpone(datetime.date(2024, 1, 1), "holiday")]))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 3), False, []))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 4), True, []))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 5), False, []))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 8), False, [Postpone(datetime.date(2024, 1, 7), "weekend")]))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 9), True, []))
        self.assertEqual(next(iterator), (datetime.date(2024, 1, 10), False, []))
        self.assertRaises(StopIteration, lambda: next(iterator))
