import unittest
import backtest

class HoldingTest(unittest.TestCase):

    def test_get_market_price(self):
        holding = backtest.Holding("AAPL", 15, 2)

        self.assertEqual(15*2, holding.get_market_price())

    def test_merge(self):
        holding = backtest.Holding("AAPL", 15, 2)
        other = backtest.Holding("AAPL", 30, 4)
        
        holding.merge(other)

        self.assertEqual(holding.quantity, other.quantity)
        self.assertEqual(holding.price, other.price)

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
