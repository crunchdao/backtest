import dataclasses
import datetime
import sys
import typing
import pandas as pd

from .account import Account
from .data.source.base import DataSource
from .export import BaseExporter, Snapshot
from .fee import ConstantFeeModel, FeeModel
from .order import Order, OrderResult
from .order.provider import OrderProvider
from .price_provider import PriceProvider, SymbolMapper


@dataclasses.dataclass()
class _MassOrderResult:

    order_results: list
    closed_count: int = None
    closed_total: int = None

    @property
    def total_fees(self):
        return sum(map(lambda x: x.fee, self.order_results), 0.0)

    @property
    def success_count(self):
        return self._count_by_success(True)

    @property
    def failed_count(self):
        return self._count_by_success(False)

    def append(self, result: OrderResult):
        return self.order_results.append(result)

    def _count_by_success(self, success_value):
        count = 0

        for result in self.order_results:
            if result.success == success_value:
                count += 1

        return count


class Backtester:

    def __init__(
        self,
        start: datetime.date,
        end: datetime.date,
        order_provider: OrderProvider,
        initial_cash: int,
        quantity_in_decimal: bool,
        data_source: DataSource,
        rfr,
        auto_close_others: bool = True,
        exporters: typing.List[BaseExporter] = [],
        mapper: SymbolMapper = None,
        fee_model: FeeModel = ConstantFeeModel(0.0),
        caching=True,
    ):
        self.end = end
        self.quantity_in_decimal = quantity_in_decimal
        self.auto_close_others = auto_close_others
        self.exporters = [] if exporters is None else exporters

        self.order_provider = order_provider
        self.order_dates = order_provider.get_dates()
        self.start = max(next(iter(self.order_dates)), start) if len(self.order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching)
        self.rfr = rfr
        self.account = Account(initial_cash=initial_cash, fee_model=fee_model)

    def order(self, date: datetime.date, price_date=None) -> _MassOrderResult:
        mass_result = _MassOrderResult(order_results=[])

        if price_date is None:
            price_date = date

        orders = self.order_provider.get_orders(date, self.account)
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
            if len(others):
                closed, total = self._close_all(others, date, mass_result)
                
                mass_result.closed_count = closed
                mass_result.closed_total = total
            else:
                mass_result.closed_count = 0
                mass_result.closed_total = 0

        return mass_result

    # def get_total_postions(self, date):
        # self.account.total_long = 0
        # self.account.total_short = 0
        # for holding in self.account.holdings:
        #     if holding.market_price < 0:
        #         self.account.total_short += holding.market_price
        #     else:
        #         self.account.total_long += holding.market_price
        # print(f"cash before: {self.account.cash}")

        # interest income on cash from short sale - amount borrowed on the long position 
        # self.account.cash += abs(self.account.total_short) * (((((rfr[rfr.date] + 0.5) / 100) + 1) ** (1/365)) - 1)
        # self.account.cash += abs(self.account.cash) * (((((4.5 - 0.17) / 100) + 1) ** (1/365)) - 1)

        # print(f"total short: {self.account.total_short}")
        # print(f"cash after: {self.account.cash}")


    def update_price(self, date):
        for holding in self.account.holdings:
            price = self.price_provider.get(date, holding.symbol)

            if price is None:
                print(f"[warning] price not updated: {holding.symbol}: keeping last: {holding.price}", file=sys.stderr)
                holding.up_to_date = False
            else:
                holding.price = price
                holding.up_to_date = True

    def run(self, weekends=False, holidays=False):
        date = self.start
        if date is None:
            return

        for exporter in self.exporters:
            exporter.initialize()

        postponned = []

        while date <= self.end:
            ordered = date in self.order_dates

            if self.price_provider.is_closeable():
                if not weekends and date.weekday() > 4:
                    self.fire_skip(date, "weekend", ordered)

                    if ordered:
                        postponned.append(date)

                    date += datetime.timedelta(days=1)
                    continue

                if not holidays:
                    from .data.holidays import holidays as days

                    if date in days:
                        self.fire_skip(date, "holiday", ordered)

                        if ordered:
                            postponned.append(date)

                        date += datetime.timedelta(days=1)
                        continue

            self.update_price(date)
            self.fire_snapshot(date, None)
            
            for postponned_date in postponned:
                result = self.order(postponned_date, price_date=date)
                self.fire_snapshot(date, result, postponned=postponned_date)

            postponned.clear()
            
            result = None
            if ordered:
                result = self.order(date)

            if len(self.rfr.index) > 0:
                self.account.interest_on_cash(self.rfr[self.rfr.index <= pd.to_datetime(date)].iloc[-1][0])
            
            if result is not None:
                self.fire_snapshot(date, result)

            date += datetime.timedelta(days=1)

        self.price_provider.save()

        for exporter in self.exporters:
            exporter.finalize()

    def fire_skip(self, date: datetime.date, reason: str, ordered: bool):
        for exporter in self.exporters:
            exporter.on_skip(date, reason, ordered)

    def fire_snapshot(self, date: datetime.date, result: _MassOrderResult, postponned=None):
        cash = float(self.account.cash)
        equity = float(self.account.equity)
        holdings = self.account.holdings
        ordered = result is not None

        snapshot = Snapshot(
            date=date,
            postponned=postponned,
            cash=cash,
            equity=equity,
            holdings=holdings,
            ordered=ordered,
        )

        if ordered:
            snapshot.total_fees = result.total_fees
            snapshot.success_count = result.success_count
            snapshot.failed_count = result.failed_count
        
            snapshot.closed_count = result.closed_count
            snapshot.closed_total = result.closed_total
            
            snapshot.order_results = result.order_results

        for exporter in self.exporters:
            exporter.on_snapshot(snapshot)

    def _close_all(self, symbols: typing.Iterable[str], date: datetime.date, mass_result: _MassOrderResult):
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
        
        return closed, total
