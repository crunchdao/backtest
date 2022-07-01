import unittest
import backtest


class OrderTest(unittest.TestCase):

    def test_value(self):
        order = backtest.Order("AAPL", 15, 2)

        self.assertEqual(15*2, order.value)

    def test_direction(self):
        order = backtest.Order("AAPL", 15, 2)
        self.assertEqual(backtest.OrderDirection.BUY, order.direction)
        
        order = backtest.Order("AAPL", 0, 2)
        self.assertEqual(backtest.OrderDirection.HOLD, order.direction)
        
        order = backtest.Order("AAPL", -15, 2)
        self.assertEqual(backtest.OrderDirection.SELL, order.direction)

    def test_valid(self):
        order = backtest.Order(None, 15, 2)
        self.assertFalse(order.valid)

        order = backtest.Order("", 15, 2)
        self.assertFalse(order.valid)

        order = backtest.Order("   ", 15, 2)
        self.assertFalse(order.valid)
        
        order = backtest.Order("AAPL", 0, 2)
        self.assertFalse(order.valid)
        
        order = backtest.Order("AAPL", 15, 0)
        self.assertFalse(order.valid)
        
        order = backtest.Order("AAPL", 15, -5)
        self.assertFalse(order.valid)
        
        order = backtest.Order("AAPL", 15, 5)
        self.assertTrue(order.valid)
        
        order = backtest.Order("AAPL", -15, 5)
        self.assertTrue(order.valid)


class FeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.FeeModel()

        self.assertEqual(0, model.get_order_fee(None))


class ConstantFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.ConstantFeeModel(5)

        self.assertEqual(5, model.get_order_fee(None))


class ExpressionFeeModelTest(unittest.TestCase):

    def test_get_order_fee(self):
        model = backtest.ExpressionFeeModel("5 * price * quantity")
        order = backtest.Order("AAPL", 15, 2)

        self.assertEqual(5 * order.price * order.quantity, model.get_order_fee(order))
