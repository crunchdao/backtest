import unittest

import bktest


class HoldingTest(unittest.TestCase):

    def test_market_price(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(15 * 2, holding.market_price)

    def test_merge(self):
        holding = bktest.Holding("AAPL", 15, 2, 15 * 2, False)
        order = bktest.Order("AAPL", 30, 4, 30 * 4)

        expected_quantity = holding.quantity + order.quantity
        expected_value = holding.value + order._value

        holding.merge(order)

        self.assertEqual(expected_quantity, holding.quantity)
        self.assertEqual(expected_value, holding.value)
        self.assertEqual(order.price, holding.price)
        self.assertTrue(holding.up_to_date)

    def test_str(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(str(holding), "AAPLx15@2")

    def test_repr(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(repr(holding), "AAPLx15")
