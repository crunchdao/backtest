import datetime
import sys
import typing

from .account import Account
from .data.holidays import HolidayProvider, LegacyHolidayProvider
from .data.source.base import DataSource
from .export import Exporter, ExporterCollection
from .fee import ConstantFeeModel, FeeModel
from .order import Order, OrderProvider, ParallelOrderProvider, OrderResultCollection
from .price_provider import PriceProvider, SymbolMapper
from .iterator import DateIterator, Skip


class _Pod:

    def __init__(
        self,
        quantity_in_decimal: bool,
        auto_close_others: bool,
        price_provider: PriceProvider,
        account: Account,
        exporters: ExporterCollection,
    ):
        self.quantity_in_decimal = quantity_in_decimal
        self.auto_close_others = auto_close_others
        self.price_provider = price_provider
        self.account = account
        self.exporters = exporters

    def order(
        self,
        date: datetime.date,
        orders: typing.List[Order],
        price_date=None,
    ) -> OrderResultCollection:
        results = OrderResultCollection()

        if price_date is None:
            price_date = date

        # symbols of the current orders.
        symbols = [
            order.symbol
            for order in orders
        ]

        self.price_provider.download_missing(symbols)

        # others - symbols currently in the account.
        others = self.account.symbols

        # Account and orders' statistics for checks at the end of the execution.
        number_of_positions_start = len(others)
        new_positions_in_account = 0
        number_of_orders_not_executed = 0
        number_of_positions_in_orders = len(orders)

        # TODO Enter if into the loop and save code lines.
        if self.quantity_in_decimal:
            equity = self.account.equity
            nav = self.account.nav
            equity = nav

            for n, order in enumerate(orders):
                symbol = order.symbol
                percent = order.quantity
                price = order.price or self.price_provider.get(price_date, symbol)

                holding_cash_value = equity * percent
                if price is not None:
                    if self.price_provider.work_with_prices:
                        quantity = int(holding_cash_value / price)
                        # quantity = float(holding_cash_value / price)
                    else:
                        # TODO: enzo: check if price is indeed one? and just make sure the division is not necessary
                        quantity = float(holding_cash_value / price)

                    # TODO: For debug. Remove afterwards.
                    if quantity == 0:
                        print('quantity==0 for symbol' + str(symbol))

                    order = Order(
                        symbol,
                        quantity,
                        price,
                        nav * percent # TODO: lior: to remove
                    )

                    result = self.account.order_position(order, date=price_date)
                    results.append(result)

                    print('n= ' + str(n + 1) + ' symbol ' + str(symbol) + ' quantity= ' + str(quantity) + ' value ' + str(int(self.account._holdings[symbol].value)) + '. New in Account ' + str(not (symbol in others)) + ' account size=' + str(len(self.account.symbols)))
                    new_positions_in_account += int(symbol not in others)

                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                        number_of_orders_not_executed += 1
                else:
                    print(f"[warning] cannot place order: {symbol} @ {percent}%: no price available", file=sys.stderr)
                    number_of_orders_not_executed += 1
        else:
            for order in orders:
                symbol = order.symbol
                quantity = order.quantity
                price = order.price or self.price_provider.get(price_date, symbol)

                if price is not None:
                    result = self.account.order_position(Order(symbol, quantity, price))
                    results.append(result)

                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {quantity}x: no price available", file=sys.stderr)

        print(f"***** new_positions_in_account = {new_positions_in_account} *****")
        assert number_of_positions_start + new_positions_in_account == len(self.account.symbols), "mismatch between symbols added"

        number_of_positions_left_to_close = len(others)

        if self.auto_close_others:
            self._close_all(others, price_date, results)
            assert len(self.account.symbols) == number_of_positions_start + new_positions_in_account - number_of_positions_left_to_close, "mismatch between symbols closed"

        assert len(self.account.symbols) == number_of_positions_in_orders - number_of_orders_not_executed, "mismatch between symbols not executed"

        return results

    def _close_all(
        self,
        symbols: typing.Iterable[str],
        date: datetime.date,
        results: OrderResultCollection
    ):
        closed, total = 0, 0

        for symbol in symbols:
            price = self.price_provider.get(date, symbol)
            result = self.account.close_position(symbol, price)

            if result.missing:
                continue

            results.append(result)

            if result.success:
                closed += 1
            else:
                print(f"[warning] could not auto-close: {symbol}", file=sys.stderr)

            total += 1

        results.closed_count = closed
        results.closed_total = total

        return closed, total

    def fire_snapshot(
        self,
        date: datetime.date,
        result: OrderResultCollection,
        postponned=None
    ):
        self.exporters.fire_snapshot(
            date,
            self.account,
            result,
            postponned
        )


class ParallelBacktester:

    def __init__(
        self,
        n: int,
        start: datetime.date,
        end: datetime.date,
        order_provider: ParallelOrderProvider,
        initial_cash: int,
        quantity_in_decimal: bool,
        data_source: DataSource,
        auto_close_others: bool = True,
        exporters_factory: typing.Callable[[int], typing.List[Exporter]] = lambda index: [],
        mapper: SymbolMapper = None,
        fee_model: FeeModel = ConstantFeeModel(0.0),
        caching=True,
        allow_weekends=False,
        allow_holidays=False,
        holiday_provider: HolidayProvider = LegacyHolidayProvider(),
    ):
        self.order_provider = order_provider
        order_dates = order_provider.get_dates()
        start = max(next(iter(order_dates)), start) if len(order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching)

        self.pods = [
            _Pod(
                quantity_in_decimal,
                auto_close_others,
                self.price_provider,
                Account(initial_cash=initial_cash, fee_model=fee_model),
                ExporterCollection(exporters_factory(index)),
            )
            for index in range(n)
        ]

        self.accounts = [
            pod.account
            for pod in self.pods
        ]

        self.date_iterator = DateIterator(
            start,
            end,
            self.price_provider.is_closeable(),
            order_dates,
            holiday_provider,
            allow_weekends,
            allow_holidays
        )

    def update_price(self, date):
        cache = {}

        for pod in self.pods:
            for holding in pod.account.holdings:
                symbol = holding.symbol
                price = cache.get(symbol)
                if price is None:
                    price = cache[symbol] = self.price_provider.get(date, holding.symbol)

                if price is None:
                    print(f"[warning] price not updated: {holding.symbol}: keeping last: {holding.price}", file=sys.stderr)
                    holding.up_to_date = False
                else:
                    holding.price = price
                    holding.up_to_date = True

            pod.fire_snapshot(date, None)

    def order(
        self,
        date: datetime.date,
        price_date=None,
    ):
        orderss = self.order_provider.get_orders_list(date, self.accounts)

        for pod, orders in zip(self.pods, orderss):
            result = pod.order(
                date,
                orders,
                price_date
            )

            if price_date:
                pod.fire_snapshot(price_date, result, postponned=date)
            else:
                pod.fire_snapshot(date, result)

        return result

    def run(self):
        self._fire_initialize()

        for date, ordered, skips in self.date_iterator:
            for skip in skips:
                for pod in self.pods:
                    pod.exporters.fire_skip(skip.date, skip.reason, skip.ordered)

                if skip.ordered:
                    self.order(skip.date, price_date=date)

            self.update_price(date)

            if ordered:
                self.order(date)

        self.price_provider.save()
        self._fire_finalize()

    def _fire_initialize(self):
        for pod in self.pods:
            pod.exporters.fire_initialize()

    def _fire_finalize(self):
        for pod in self.pods:
            pod.exporters.fire_finalize()


class SimpleBacktester:

    def __init__(
        self,
        start: datetime.date,
        end: datetime.date,
        order_provider: OrderProvider,
        initial_cash: int,
        quantity_in_decimal: bool,
        data_source: DataSource,
        auto_close_others: bool = True,
        exporters: typing.List[Exporter] = [],
        mapper: SymbolMapper = None,
        fee_model: FeeModel = ConstantFeeModel(0.0),
        caching=False,  # True,
        allow_weekends=False,
        allow_holidays=False,
        holiday_provider: HolidayProvider = LegacyHolidayProvider(),
        work_with_prices=True,
    ):
        self.order_provider = order_provider
        order_dates = order_provider.get_dates()
        start = max(next(iter(order_dates)), start) if len(order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching, work_with_prices=work_with_prices)

        self.pod = _Pod(
            quantity_in_decimal,
            auto_close_others,
            self.price_provider,
            Account(initial_cash=initial_cash, fee_model=fee_model),
            ExporterCollection(exporters),
        )

        self.date_iterator = DateIterator(
            start,
            end,
            self.price_provider.is_closeable(),
            order_dates,
            holiday_provider,
            allow_weekends,
            allow_holidays,
        )

    def update_price(self, date) -> bool:
        trading_day = False

        for holding in self.account.holdings:
            # If we work with prices, we update the price else we update the quantity and the price set always equal to one.
            if self.price_provider.work_with_prices:
                price = self.price_provider.get(date, holding.symbol)

                if price is None:
                    print(f"[warning] price not updated: {holding.symbol}: keeping last: {holding.price}", file=sys.stderr)
                    holding.up_to_date = False
                else:
                    holding.price = price
                    holding.up_to_date = True
                    holding.last_date_updated = date

                trading_day = trading_day or holding.up_to_date
            else:
                total_return = self.price_provider.get_total_return(date, holding.symbol)

                if total_return is None:
                    print(f"[warning] no total_return: {holding.symbol}: keeping last value: {holding.value}", file=sys.stderr)
                    holding.up_to_date = False
                else:
                    holding.quantity *= (1 + total_return)
                    holding.up_to_date = True
                    holding.last_date_updated = date

                trading_day = trading_day or holding.up_to_date

        return trading_day

    def update_values(self, date) -> bool:
        trading_day = False

        for holding in self.account.holdings:
            total_return = self.price_provider.get_total_return(date, holding.symbol)

            if total_return is None:
                print(f"[warning] no total_return: {holding.symbol}: keeping last value: {holding.value}", file=sys.stderr)
                holding.up_to_date = False
            else:
                holding.value *= (1 + total_return)
                holding.up_to_date = True
                holding.last_date_updated = date

            trading_day = trading_day or holding.up_to_date

        return trading_day

    def order(
        self,
        date: datetime.date,
        price_date=None,
    ):
        orders = self.order_provider.get_orders(date, self.account)
        assert len(orders), "orders should not be empty"

        return self.pod.order(
            date,
            orders,
            price_date
        )

    def run(self):
        self.exporters.fire_initialize()
        pre_trading = True
        ordered = False

        one = datetime.timedelta(days=1)
        date = self.date_iterator.start - one
        while date < self.date_iterator.end:
            date += one

            if date in self.date_iterator.order_dates:
                ordered = True
                order_date = date

            # No trading day because of weekend or holiday.
            is_holiday = self.date_iterator.should_skip_holidays(date, ordered)
            is_weekend = self.date_iterator.should_skip_weekends(date, ordered)

            skip = is_holiday or is_weekend
            if skip:
                self.exporters.fire_skip(date, skip.reason, ordered)
                continue

            # trading_day can still be false if we missed a holiday. So we set trading_day to False if there is no price change in any asset.
            if not pre_trading:
                # TODO: update_values will be removed.
                trading_day = self.update_values(date)
                trading_day = self.update_price(date) or trading_day

                if not trading_day:
                    self.exporters.fire_skip(date, 'no trading: no value has been updated', False)
                    continue

                self.exporters.fire_snapshot(date, self.account, None)

            if ordered:
                result = self.order(order_date, price_date=date)

                # No trades were executed so the order was given on a non-trading day and the portfolio is empty.
                if len(result.elements) == 0:
                    self.exporters.fire_skip(date, 'no trading: no order was executed', ordered)
                    continue

                if order_date != date:
                    self.exporters.fire_snapshot(date, self.account, result, postponned=order_date)
                else:
                    self.exporters.fire_snapshot(date, self.account, result)
                ordered = False

            if pre_trading:
                self.exporters.fire_snapshot(date, self.account, None)
                pre_trading = False

        self.price_provider.save()

        self.exporters.fire_finalize()

    @property
    def account(self):
        return self.pod.account

    @property
    def exporters(self):
        return self.pod.exporters
