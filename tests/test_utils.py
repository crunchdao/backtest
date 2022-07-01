import unittest
import backtest.utils


class UtilsTest(unittest.TestCase):

    def test_signum(self):
        self.assertEqual(backtest.utils.signum(1), 1)
        self.assertEqual(backtest.utils.signum(0), 0)
        self.assertEqual(backtest.utils.signum(-1), -1)

    def test_is_int(self):
        self.assertTrue(backtest.utils.is_int("1"))

        self.assertFalse(backtest.utils.is_int("1.5"))
        self.assertFalse(backtest.utils.is_int("hello"))

    def test_is_float(self):
        self.assertTrue(backtest.utils.is_float("1.5"))
        self.assertTrue(backtest.utils.is_float("1"))

        self.assertFalse(backtest.utils.is_float("hello"))

    def test_is_number(self):
        self.assertTrue(backtest.utils.is_number("1.5"))
        self.assertTrue(backtest.utils.is_number("1"))

        self.assertFalse(backtest.utils.is_number("hello"))
