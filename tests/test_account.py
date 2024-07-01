import typing
import unittest
import datetime

import bktest

invalid = bktest.Order(None, 1, 1)
aapl = bktest.Order("AAPL", 42, 1)
aapl_hold = bktest.Order("AAPL", 0, 1)
aapl_short = bktest.Order("AAPL", -42, 1)
tsla = bktest.Order("TSLA", 15, 2)
cash = 1000000
rfr = 4.17
today = datetime.date.today()


class AccountTest(unittest.TestCase):

    def test_place_order(self):
        account = bktest.Account()

        result = account.place_order(invalid, today)
        self.assertEqual(invalid, result.order)
        self.assertFalse(result.success)
        self.assertEqual(0, len(account.holdings))

        result = account.place_order(aapl, today)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value, account.nav)

        result = account.place_order(aapl, today)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value * 2, account.nav)

        result = account.place_order(tsla, today)
        self.assertTrue(result.success)
        self.assertEqual(2, len(account.holdings))
        self.assertEqual(account.cash + tsla.value + aapl.value * 2, account.nav)

        result = account.place_order(aapl_short, today)
        self.assertEqual(2, len(account.holdings))
        self.assertEqual(account.cash + tsla.value + aapl.value, account.nav)

        result = account.place_order(aapl_short, today)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + tsla.value, account.nav)

    def test_order_position(self):
        account = bktest.Account()

        result = account.order_position(invalid, today)
        self.assertFalse(result.success)

        result = account.order_position(aapl, today)
        self.assertTrue(result.success)
        self.assertEqual(aapl.quantity, result.order.quantity)
        holding = account.find_holding(aapl.symbol)
        self.assertIsNotNone(holding)
        self.assertEqual(aapl.quantity, holding.quantity)
        self.assertEqual(aapl.price, holding.price)

        result = account.order_position(aapl, today)
        self.assertTrue(result.success)
        self.assertEqual(0, result.order.quantity)
        holding = account.find_holding(aapl.symbol)
        self.assertIsNotNone(holding)
        self.assertEqual(aapl.quantity, holding.quantity)
        self.assertEqual(aapl.price, holding.price)

        result = account.order_position(aapl_short, today)
        self.assertTrue(result.success)
        self.assertEqual(aapl_short.quantity * 2, result.order.quantity)
        holding = account.find_holding(aapl.symbol)
        self.assertIsNotNone(holding)
        self.assertEqual(aapl_short.quantity, holding.quantity)
        self.assertEqual(aapl_short.price, holding.price)

    def test_close_position(self):
        account = bktest.Account()

        result = account.close_position(None)
        self.assertFalse(result.success)

        result = account.close_position(aapl.symbol)
        self.assertTrue(result.missing)
        self.assertEqual(0, result.order.quantity)
        self.assertEqual(None, result.order.price)

        result = account.close_position(aapl.symbol, 42.0)
        self.assertTrue(result.missing)
        self.assertEqual(0, result.order.quantity)
        self.assertEqual(42.0, result.order.price)

        result = account.place_order(aapl, today)
        self.assertTrue(result.success)
        self.assertEqual(1, len(account.holdings))
        self.assertEqual(account.cash + aapl.value, account.nav)

        result = account.close_position(tsla.symbol)
        self.assertTrue(result.missing)
        self.assertEqual(1, len(account.holdings))

        result = account.close_position(aapl.symbol)
        self.assertTrue(result.success)
        self.assertEqual(0, len(account.holdings))
        self.assertEqual(account.initial_cash, account.nav)

    def test_equity(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(aapl.market_price + tsla.market_price, account.equity)

    def test_equity_long(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(aapl.market_price + tsla.market_price, account.equity)
        
        account, aapl, tsla = AccountTest._create_dummy_two()

        self.assertEqual(aapl.market_price, account.equity_long)
        
    def test_nav(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(account.initial_cash + aapl.market_price + tsla.market_price, account.nav)

    def test_symbols(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(set([aapl.symbol, tsla.symbol]), account.symbols)

    def test_symbols(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual([aapl, tsla], account.holdings)

    def test_find_holding(self):
        account, aapl, tsla = AccountTest._create_dummy()

        self.assertEqual(aapl, account.find_holding(aapl.symbol))
        self.assertEqual(tsla, account.find_holding(tsla.symbol))

        self.assertIsNone(account.find_holding("CRUNCH"))

    def test_to_relative_order(self):
        account = bktest.Account()

        self.assertEqual(aapl, account.to_relative_order(aapl, today))
        self.assertEqual(aapl_hold, account.to_relative_order(aapl_hold, today))
        self.assertEqual(aapl_short, account.to_relative_order(aapl_short, today))

        result = account.place_order(aapl, today)
        self.assertTrue(result.success)

        relative = account.to_relative_order(aapl, today)
        self.assertEqual(0, relative.quantity)

        relative = account.to_relative_order(aapl_hold, today)
        self.assertEqual(-aapl.quantity, relative.quantity)

        relative = account.to_relative_order(aapl_short, today)
        self.assertEqual(aapl_short.quantity * 2, relative.quantity)

        order = bktest.Order("AAPL", 44, 1)
        relative = account.to_relative_order(order, today)
        self.assertEqual(2, relative.quantity)

        account = bktest.Account()
        result = account.place_order(aapl_short, today)

        relative = account.to_relative_order(aapl_short, today)
        self.assertEqual(0, relative.quantity)

        relative = account.to_relative_order(aapl_hold, today)
        self.assertEqual(aapl.quantity, relative.quantity)

        relative = account.to_relative_order(aapl, today)
        self.assertEqual(aapl.quantity * 2, relative.quantity)

        order = bktest.Order("AAPL", -44, 1)
        relative = account.to_relative_order(order, today)
        self.assertEqual(-2, relative.quantity)

    @staticmethod
    def _create_dummy(add=True) -> typing.Tuple[bktest.Account, bktest.Holding, bktest.Holding]:
        account = bktest.Account()

        aapl = bktest.Holding("AAPL", 15, 2)
        tsla = bktest.Holding("TSLA", 30, 4)

        for holding in [aapl, tsla]:
            account._holdings[holding.symbol] = holding

        return account, aapl, tsla

    @staticmethod
    def _create_dummy_two(add=True) -> typing.Tuple[bktest.Account, bktest.Holding, bktest.Holding]:
        account = bktest.Account()

        aapl = bktest.Holding("AAPL", 15, 2)
        tsla = bktest.Holding("TSLA", -30, 4)

        for holding in [aapl, tsla]:
            account._holdings[holding.symbol] = holding

        return account, aapl, tsla
