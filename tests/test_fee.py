import unittest

import bktest


class ConstantFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = bktest.fee.ConstantFeeModel(5)

        self.assertEqual(5, model.get_order_fee(None))


class ExpressionFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = bktest.fee.ExpressionFeeModel("5 * price * quantity")
        order = bktest.Order("AAPL", 15, 2)

        self.assertEqual(5 * order.price * order.quantity, model.get_order_fee(order))

    def test_get_order_fee_interactive_broker(self):
        model = bktest.fee.ExpressionFeeModel("max(abs(price * quantity) * 0.01, 1)")
        
        order = bktest.Order("AAPL", 1, 20)
        self.assertEqual(1, model.get_order_fee(order))
        
        order = bktest.Order("AAPL", 150, 20)
        self.assertEqual(30, model.get_order_fee(order))
