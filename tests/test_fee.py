import unittest
import backtest


class FeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.fee.FeeModel()

        self.assertEqual(0, model.get_order_fee(None))


class ConstantFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.fee.ConstantFeeModel(5)

        self.assertEqual(5, model.get_order_fee(None))


class ExpressionFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.fee.ExpressionFeeModel("5 * price * quantity")
        order = backtest.Order("AAPL", 15, 2)

        self.assertEqual(5 * order.price * order.quantity, model.get_order_fee(order))

    def test_get_order_fee_interactive_broker(self):
        model = backtest.fee.ExpressionFeeModel("max(abs(price * quantity) * 0.01, 1)")
        
        order = backtest.Order("AAPL", 1, 20)
        self.assertEqual(1, model.get_order_fee(order))
        
        order = backtest.Order("AAPL", 150, 20)
        self.assertEqual(30, model.get_order_fee(order))
