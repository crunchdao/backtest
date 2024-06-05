import unittest

import bktest


class OrderTest(unittest.TestCase):

    def test_value(self):
        order = bktest.Order("AAPL", 15, 2)

        self.assertEqual(15*2, order.value)

    def test_direction(self):
        order = bktest.Order("AAPL", 15, 2)
        self.assertEqual(bktest.OrderDirection.BUY, order.direction)

        order = bktest.Order("AAPL", 0, 2)
        self.assertEqual(bktest.OrderDirection.HOLD, order.direction)

        order = bktest.Order("AAPL", -15, 2)
        self.assertEqual(bktest.OrderDirection.SELL, order.direction)

    def test_valid(self):
        order = bktest.Order(None, 15, 2)
        self.assertFalse(order.valid)
        
        order = bktest.Order(0, 15, 2)
        self.assertFalse(order.valid)

        order = bktest.Order("", 15, 2)
        self.assertFalse(order.valid)

        order = bktest.Order("   ", 15, 2)
        self.assertFalse(order.valid)

        order = bktest.Order("AAPL", 15, 0)
        self.assertFalse(order.valid)

        order = bktest.Order("AAPL", 15, -5)
        self.assertFalse(order.valid)

        order = bktest.Order("AAPL", 15, 5)
        self.assertTrue(order.valid)

        order = bktest.Order("AAPL", -15, 5)
        self.assertTrue(order.valid)

        order = bktest.Order(1234, -15, 5)
        self.assertTrue(order.valid)
