import datetime
import sys
import typing

from .fee import ConstantFeeModel, FeeModel
from .holding import Holding
from .order import CloseResult, Order, OrderResult
from .utils import is_blank

EPSILON = 1e-10


class Account:

    def __init__(
        self,
        initial_cash: int = 1_000_000,
        fee_model: FeeModel = None
    ):
        self.initial_cash = initial_cash
        self.fee_model = fee_model if fee_model else ConstantFeeModel(0)

        self.cash = initial_cash
        self.total_long = 0
        self.total_short = 0
        self._holdings: typing.Dict[str, Holding] = dict()

    # TODO: change value to equity
    @property
    def equity(self) -> float:
        return sum(
            holding.market_price
            for holding in self._holdings.values()
        )

    @property
    def equity_long(self) -> float:
        return sum(
            holding.market_price
            for holding in self._holdings.values()
            if holding.market_price > 0
        )

    @property
    def nav(self) -> float:
        return self.cash + self.equity

    @property
    def symbols(self) -> typing.Set[str]:
        return set(self._holdings.keys())

    @property
    def holdings(self) -> typing.List[Holding]:
        return list(self._holdings.values())

    def find_holding(self, symbol: str):
        return self._holdings.get(symbol, None)

    def place_order(self, order: Order, date: datetime.date) -> OrderResult:
        result = OrderResult(order=order)
        if not order.valid:
            return result

        result.success = True

        result.fee = self.fee_model.get_order_fee(order)

        self._handle_cash(order, result.fee)

        # Handle holdings in the account.
        holding = self.find_holding(order.symbol)

        if holding:
            assert holding.last_date_updated == date, "holding price is not up-to-date"
            holding.merge(order)

        else:
            self._holdings[order.symbol] = Holding(
                order.symbol,
                order.quantity,
                order.price,
                date = date
            )

        if abs(self._holdings[order.symbol].quantity) < EPSILON:  # if quantity is zero
            del self._holdings[order.symbol]
            
        return result

    def order_position(self, order: Order, date) -> OrderResult:
        relative = self.to_relative_order(order, date)

        return self.place_order(relative, date)

    def close_position(self, symbol: str, price: float = None) -> CloseResult:
        order = Order(symbol, 0, price)
        result = CloseResult(order=order)

        if not order.valid:
            # TODO: Should be an ERROR?
            return result

        holding = self.find_holding(order.symbol)

        if holding:
            order.quantity = -holding.quantity

            # If the symbol is not traded on date the price is None.
            if order.price is None:
                order.price = holding.price
                print(f"[warning] in close_position no price available for {order.symbol}, using last price: {order.price}", file=sys.stderr)

            result.fee = self.fee_model.get_order_fee(order)

            self._handle_cash(order, result.fee)

            del self._holdings[order.symbol]

            result.success = True
        else:
            # TODO: Should be an ERROR?
            result.missing = True

        return result

    def to_relative_order(self, order: Order, date: datetime.date):
        holding = self.find_holding(order.symbol)

        if not holding or order.quantity is None:
            return order

        assert holding.last_date_updated == date

        return Order(
            order.symbol,
            order.quantity - holding.quantity,
            order.price,
        )

    def _handle_cash(self, order: Order, fee: float):
        self.cash -= fee
        self.cash -= order.value
