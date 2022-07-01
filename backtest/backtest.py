import dataclasses
import datetime
import sys
import typing

import numpy

from .data.source.base import DataSource
from .export import BaseExporter, Snapshot
from .account import Account
from .order import Order, OrderResult
from .order.fee import FeeModel, ConstantFeeModel
from .order.provider.base import OrderProvider
from .price_provider import PriceProvider, SymbolMapper


@dataclasses.dataclass()
class _MassOrderResult:
    
    order_results: list
    
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
        auto_close_others: bool=True,
        exporters: typing.List[BaseExporter]=[],
        mapper: SymbolMapper=None,
        fee_model: FeeModel=ConstantFeeModel(0.0),
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
        self.account = Account(cash=initial_cash, fee_model=fee_model)

    def order(self, date: datetime.date, price_date=None) -> _MassOrderResult:
        mass_result = _MassOrderResult(order_results=[])
        
        if price_date is None:
            price_date = date
        
        orders_dataframe = self.order_provider.get_orders_dataframe(date)

        symbols = orders_dataframe["symbol"].tolist()

        self.price_provider.download_missing(symbols)
        
        others = self.account.symbols

        if self.quantity_in_decimal:
            equity = self.account.equity

            for _, row in orders_dataframe.iterrows():
                symbol = row["symbol"]
                percent = row["quantity"]

                holding_cash_value = equity * percent
                price = self.price_provider.get(price_date, symbol)
                if price and not numpy.isnan(price):
                    quantity = int(holding_cash_value / price)

                    

                    result = self.account.order(Order(symbol, quantity, price))
                    mass_result.append(result)
                    
                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {percent}%: no price available", file=sys.stderr)
        else:
            for _, row in orders_dataframe.iterrows():
                symbol = row["symbol"]
                quantity = int(row["quantity"])

                price = self.price_provider.get(price_date, symbol)
                if price and not numpy.isnan(price):
                    result = self.account.order(Order(symbol, quantity, price))
                    mass_result.append(result)
                    
                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {quantity}x: no price available", file=sys.stderr)
        
        if self.auto_close_others and len(others):
            closed = 0
            
            for symbol in others:
                holding = self.account[symbol]
                
                if not holding:
                    continue
                
                price = self.price_provider.get(date, symbol)
                if not price or numpy.isnan(price):
                    price = holding.price
                    print(f"[warning] no price available for {symbol}, using last price: {price}", file=sys.stderr)
                
                result = self.account.order(Order(symbol, -holding.quantity, price))
                mass_result.append(result)
                
                if result.success:
                    closed += 1
                else:
                    print(f"[warning] could not auto-close: {symbol} @ {percent}%", file=sys.stderr)
            
            print(f"[info] auto closed: {closed}/{len(others)}", file=sys.stderr)
    
        return mass_result

    def update_price(self, date):
        for holding in self.account.holdings:
            price = self.price_provider.get(date, holding.symbol)

            if price and not numpy.isnan(price):
                holding.price = price

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
            
            for postponned_date in postponned:
                result = self.order(postponned_date, price_date=date)
                self.fire_snapshot(date, result, postponned=postponned_date)
            
            postponned.clear()
            
            result = None
            if ordered:
                result = self.order(date)
            else:
                self.update_price(date)

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
        
        for exporter in self.exporters:
            exporter.on_snapshot(snapshot)
        
