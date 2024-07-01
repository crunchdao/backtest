import unittest

import bktest

import datetime

class HoldingTest(unittest.TestCase):

    def test_market_price(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(15 * 2, holding.market_price)

    def test_merge(self):
        today = datetime.date.today()
        price = 2
        holding = bktest.Holding("AAPL", 15, price, today)
        order = bktest.Order("AAPL", 30, price)

        expected_quantity = holding.quantity + order.quantity
        expected_value = holding.market_price + order.price * order.quantity

        holding.merge(order)

        self.assertEqual(expected_quantity, holding.quantity)
        self.assertEqual(expected_value, holding.market_price)
        self.assertEqual(order.price, holding.price)
        self.assertEqual(holding.last_date_updated, today)

    def test_str(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(str(holding), "AAPLx15@2")

    def test_repr(self):
        holding = bktest.Holding("AAPL", 15, 2, None)

        self.assertEqual(repr(holding), "AAPLx15")
