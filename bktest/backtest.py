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
from .iterator import DateIterator,Skip


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

        # symbols in the current account.
        others = self.account.symbols

        # Enter if into the loop and save code lines.
        if self.quantity_in_decimal:
            equity = self.account.equity
            nav = self.account.nav
            #equity = nav

            for order in orders:
                symbol = order.symbol
                percent = order.quantity
                price = order.price or self.price_provider.get(price_date, symbol)
                total_return = self.price_provider.get_total_return(price_date, symbol)

                holding_cash_value = equity * percent
                if price is not None:
                    #if key_returs:
                    #    quantity = holding_cash_value
                    
                    quantity = int(holding_cash_value / price)
                    #quantity = float(holding_cash_value / price)

                    result = self.account.order_position(Order(symbol, quantity, price, nav * percent))
                    results.append(result)

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
                    results.append(result)

                    if result.success:
                        others.discard(symbol)
                    else:
                        print(f"[warning] order not placed: {symbol} @ {percent}%", file=sys.stderr)
                else:
                    print(f"[warning] cannot place order: {symbol} @ {quantity}x: no price available", file=sys.stderr)

        if self.auto_close_others:
            self._close_all(others, date, results)

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
                ExporterCollection(exporters_factory(index))
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
        caching=False, #True,
        allow_weekends=False,
        allow_holidays=False,
        holiday_provider: HolidayProvider = LegacyHolidayProvider(),
        use_returns_instead_of_prices: bool = False,
    ):
        self.order_provider = order_provider
        order_dates = order_provider.get_dates()
        start = max(next(iter(order_dates)), start) if len(order_dates) else None

        self.price_provider = PriceProvider(start, end, data_source, mapper, caching=caching)

        self.pod = _Pod(
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
            holiday_provider,
            allow_weekends,
            allow_holidays,
        )

    def update_price(self, date) -> bool:
        trading_day = False
        for holding in self.account.holdings:
            price = self.price_provider.get(date, holding.symbol)

            if price is None:
                print(f"[warning] price not updated: {holding.symbol}: keeping last: {holding.price}", file=sys.stderr)
                holding.up_to_date = False
            else:
                holding.price = price
                holding.up_to_date = True
        
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

            trading_day = trading_day or holding.up_to_date
        
        return trading_day
    def order(
        self,
        date: datetime.date,
        price_date=None,
    ):
        # Original oreders.
        orders = self.order_provider.get_orders(date, self.account)

        return self.pod.order(
            date,
            orders,
            price_date
        )

    def run(self):
        self.exporters.fire_initialize()
        pre_trading = True
        ordered = False

        date = self.date_iterator.start-datetime.timedelta(days=1)
        while date < self.date_iterator.end:
            date += datetime.timedelta(days=1)
            
            skips: typing.List[Skip] = []
            if date in self.date_iterator.order_dates:
                ordered = True
                order_date = date
            # No trading day beause of weekend or holiday.
            if self.date_iterator._should_skip_weekends(date, ordered, skips) or self.date_iterator._should_skip_holidays(date, ordered, skips):
                self.exporters.fire_skip(date, skips[0].reason, ordered)
                assert len(skips) == 1
                continue
            
            # trading_day can still be false if we missed a holiday. So we set trading_day to False if there is no price change in any asset.
            if not pre_trading:
                trading_day = self.update_values(date)
                trading_day = self.update_price(date) or trading_day
            
                if trading_day:
                    self.exporters.fire_snapshot(date, self.account, None)
                else:
                    self.exporters.fire_skip(date, 'No trading', False)
                    continue
            
            if ordered:
                result = self.order(order_date, price_date=date)
                # No trades were done so the order was given on a non-trading day and the portfolio is empty.
                if len(result.elements) == 0:
                    self.exporters.fire_skip(date, 'No trading', ordered)
                    continue
                    
                if order_date != date:
                    self.exporters.fire_snapshot(date, self.account, result, postponned=order_date)
                else:
                    self.exporters.fire_snapshot(date, self.account, result)
                ordered = False
            if pre_trading:
                self.exporters.fire_snapshot(date, self.account, None)
                pre_trading = False
                

        # for date, ordered, skips in self.date_iterator:
            
        #     skip_order = False
        #     for skip in skips:
        #         skip_order = skip_order or skip.ordered
        #         if skip.ordered: order_date=skip.date
        #         self.exporters.fire_skip(skip.date, skip.reason, skip.ordered)

        #     if not pre_tading:#  and date !=datetime.date(2024, 1, 22):
        #         trading_day = self.update_values(date)
        #         trading_day = self.update_price(date) or trading_day
        #         if trading_day:
        #             self.exporters.fire_snapshot(date, self.account, None)
        #         else:
        #             self.exporters.fire_skip(date, 'No trading', False)
        #             #continue
                
        #     if skip_order:
        #         result = self.order(order_date, price_date=date)
        #         self.exporters.fire_snapshot(date, self.account, result, postponned=order_date)
        #     elif ordered:
        #         result = self.order(date)
        #         self.exporters.fire_snapshot(date, self.account, result)
        #     if pre_tading:
        #         self.exporters.fire_snapshot(date, self.account, None)
        #         pre_tading=False
    
        self.price_provider.save()

        self.exporters.fire_finalize()

    @property
    def account(self):
        return self.pod.account

    @property
    def exporters(self):
        return self.pod.exporters
