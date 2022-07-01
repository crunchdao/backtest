import typing
import unittest
import backtest


class AccountTest(unittest.TestCase):

    def test_place_order(self):
        account = backtest.Account()

        order = backtest.Order(None, 1, 1)
        result = account.place_order(order)
        self.assertEqual(order, result.order)
        self.assertFalse(result.success)
        self.assertEqual(0, len(account.holdings))

        aapl = backtest.Order("AAPL", 15, 2)
        result = account.place_order(aapl)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value, account.equity)

        result = account.place_order(aapl)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value * 2, account.equity)

        tsla = backtest.Order("TSLA", 15, 2)
        result = account.place_order(tsla)
        self.assertTrue(result.success)
        self.assertEqual(2, len(account.holdings))
        self.assertEqual(account.cash + tsla.value + aapl.value * 2, account.equity)

        aapl_short = backtest.Order("AAPL", -15, 2)

        result = account.place_order(aapl_short)
        self.assertEqual(2, len(account.holdings))
        self.assertEqual(account.cash + tsla.value + aapl.value, account.equity)

        result = account.place_order(aapl_short)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + tsla.value, account.equity)

    def test_close_position(self):
        account = backtest.Account()

        result = account.close_position(None)
        self.assertFalse(result.success)

        result = account.close_position("AAPL")
        self.assertTrue(result.success)
        self.assertEqual(0, result.order.quantity)
        self.assertEqual(None, result.order.price)

        result = account.close_position("AAPL", 42.0)
        self.assertTrue(result.success)
        self.assertEqual(0, result.order.quantity)
        self.assertEqual(42.0, result.order.price)

        aapl = backtest.Order("AAPL", 15, 2)
        result = account.place_order(aapl)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value, account.equity)

        result = account.close_position("TSLA")
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))

        result = account.close_position("AAPL")
        self.assertTrue(result.success)
        self.assertEqual(0, len(account.holdings))
        self.assertEqual(account.initial_cash, account.equity)

    def test_value(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(aapl.market_price + tsla.market_price, account.value)

    def test_equity(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(account.initial_cash + aapl.market_price + tsla.market_price, account.equity)

    def test_symbols(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(set([aapl.symbol, tsla.symbol]), account.symbols)

    def test_symbols(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual([aapl, tsla], account.holdings)

    @staticmethod
    def _create_dummy(add=True) -> typing.Tuple[backtest.Account, backtest.Holding, backtest.Holding]:
        account = backtest.Account()

        aapl = backtest.Holding("AAPL", 15, 2)
        tsla = backtest.Holding("TSLA", 30, 4)

        for holding in [aapl, tsla]:
            account._holdings[holding.symbol] = holding

        return account, aapl, tsla
