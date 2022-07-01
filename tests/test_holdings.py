import unittest
import backtest

class HoldingTest(unittest.TestCase):

    def test_market_price(self):
        holding = backtest.Holding("AAPL", 15, 2)

        self.assertEqual(15*2, holding.market_price)

    def test_merge(self):
        holding = backtest.Holding("AAPL", 15, 2)
        order = backtest.Order("AAPL", 30, 4)

        expected_quantity = holding.quantity + order.quantity
        
        holding.merge(order)

        self.assertEqual(expected_quantity, holding.quantity)
        self.assertEqual(order.price, holding.price)

    def test_str(self):
        holding = backtest.Holding("AAPL", 15, 2)
        
        self.assertEqual(str(holding), "AAPLx15@2")

    def test_repr(self):
        holding = backtest.Holding("AAPL", 15, 2)
        
        self.assertEqual(repr(holding), "AAPLx15")

    def from_order(self):
        order = backtest.Order("AAPL", 15, 2)
        holding = backtest.Holding.from_order(order)
        
        self.assertEqual(order.symbol, holding.symbol)
        self.assertEqual(order.quantity, holding.quantity)
        self.assertEqual(order.price, holding.price)
