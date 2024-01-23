import datetime
import sys
import typing

from .account import Account
from .data.source.base import DataSource
from .export import Exporter, ExporterCollection
from .fee import ConstantFeeModel, FeeModel
from .order import Order, OrderProvider, ParallelOrderProvider, OrderResultCollection
from .price_provider import PriceProvider, SymbolMapper
from .iterator import DateIterator


class _Runner:

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
        mass_result = OrderResultCollection()

        if price_date is None:
            price_date = date

        symbols = [
            order.symbol
            for order in orders
        ]

        self.price_provider.download_missing(symbols)

        others = self.account.symbols

        if self.quantity_in_decimal:
            equity = self.account.equity

            for order in orders:
                symbol = order.symbol
                percent = order.quantity
                price = order.price or self.price_provider.get(price_date, symbol)

                holding_cash_value = equity * percent
                if price is not None:
                    quantity = int(holding_cash_value / price)

                    result = self.account.order_position(Order(symbol, quantity, price))
                    mass_result.append(result)

                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {percent}%: no price available", file=sys.stderr)
        else:
            for order in orders:
                symbol = order.symbol
                quantity = order.quantity
                price = order.price or self.price_provider.get(price_date, symbol)

                if price is not None:
                    result = self.account.order_position(Order(symbol, quantity, price))
                    mass_result.append(result)

                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {quantity}x: no price available", file=sys.stderr)

        if self.auto_close_others:
            self._close_all(others, date, mass_result)

        return mass_result

    def _close_all(
        self,
        symbols: typing.Iterable[str],
        date: datetime.date,
        mass_result: OrderResultCollection
    ):
        closed, total = 0, 0

        for symbol in symbols:
            price = self.price_provider.get(date, symbol)
            result = self.account.close_position(symbol, price)

            if result.missing:
                continue

            mass_result.append(result)

            if result.success:
                closed += 1
            else:
                print(f"[warning] could not auto-close: {symbol}", file=sys.stderr)

            total += 1

        mass_result.closed_count = closed
        mass_result.closed_total = total

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
        weekends=False,
        holidays=False,
    ):
        self.order_provider = order_provider
        order_dates = order_provider.get_dates()
        start = max(next(iter(order_dates)), start) if len(order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching)

        self.runners = [
            _Runner(
                quantity_in_decimal,
                auto_close_others,
                self.price_provider,
                Account(initial_cash=initial_cash, fee_model=fee_model),
                ExporterCollection(exporters_factory(index))
            )
            for index in range(n)
        ]
        
        self.accounts = [
            runner.account
            for runner in self.runners
        ]

        self.date_iterator = DateIterator(
            start,
            end,
            self.price_provider.is_closeable(),
            order_dates,
            weekends,
            holidays
        )

    def update_price(self, date):
        cache = {}

        for runner in self.runners:
            for holding in runner.account.holdings:
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

            runner.fire_snapshot(date, None)

    def order(
        self,
        date: datetime.date,
        price_date=None,
    ):
        orderss = self.order_provider.get_orders_list(date, self.accounts)

        for runner, orders in zip(self.runners, orderss):
            result = runner.order(
                date,
                orders,
                price_date
            )

            if price_date:
                runner.fire_snapshot(price_date, result, postponned=date)
            else:
                runner.fire_snapshot(date, result)

        return result

    def run(self):
        self._fire_initialize()

        for date, ordered, postponned in self.date_iterator:
            for postpone in postponned:
                for runner in self.runners:
                    runner.exporters.fire_skip(postpone.date, postpone.reason, postpone.ordered)

                self.order(postpone.date, price_date=date)

            self.update_price(date)

            if ordered:
                self.order(date)

        self.price_provider.save()
        self._fire_finalize()

    def _fire_initialize(self):
        for runner in self.runners:
            runner.exporters.fire_initialize()

    def _fire_finalize(self):
        for runner in self.runners:
            runner.exporters.fire_finalize()


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
        caching=True,
        weekends=False,
        holidays=False,
    ):
        self.order_provider = order_provider
        order_dates = order_provider.get_dates()
        start = max(next(iter(order_dates)), start) if len(order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching)

        self.runner = _Runner(
            quantity_in_decimal,
            auto_close_others,
            self.price_provider,
            Account(initial_cash=initial_cash, fee_model=fee_model),
            ExporterCollection(exporters)
        )

        self.date_iterator = DateIterator(
            start,
            end,
            self.price_provider.is_closeable(),
            order_dates,
            weekends,
            holidays
        )

    def update_price(self, date):
        for holding in self.account.holdings:
            price = self.price_provider.get(date, holding.symbol)

            if price is None:
                print(f"[warning] price not updated: {holding.symbol}: keeping last: {holding.price}", file=sys.stderr)
                holding.up_to_date = False
            else:
                holding.price = price
                holding.up_to_date = True

    def order(
        self,
        date: datetime.date,
        price_date=None,
    ):
        orders = self.order_provider.get_orders(date, self.account)

        return self.runner.order(
            date,
            orders,
            price_date
        )

    def run(self):
        self.exporters.fire_initialize()

        for date, ordered, postponned in self.date_iterator:
            for postpone in postponned:
                self.exporters.fire_skip(postpone.date, postpone.reason, postpone.ordered)

                if postpone.ordered:
                    result = self.order(postpone.date, price_date=date)
                    self.exporters.fire_snapshot(date, self.account, result, postponned=postpone.date)

            self.update_price(date)
            self.exporters.fire_snapshot(date, self.account, None)

            if ordered:
                result = self.order(date)

                self.exporters.fire_snapshot(date, self.account, result)

        self.price_provider.save()

        self.exporters.fire_finalize()

    @property
    def account(self):
        return self.runner.account

    @property
    def exporters(self):
        return self.runner.exporters
