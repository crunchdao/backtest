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
        self.cash_new = initial_cash
        self.total_long = 0
        self.total_short = 0
        self._holdings: typing.Dict[str, Holding] = dict()

    @property
    def value(self) -> float:
        return sum(
            holding.market_price
            for holding in self._holdings.values()
        )

    @property
    def equity(self) -> float:
        return self.cash + self.value
        # return self.value

    @property
    def equity_new(self) -> float:
        return sum(
            holding.value
            for holding in self._holdings.values()
        )

    @property
    def nav(self) -> float:
        return self.cash_new + self.equity_new

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

        # TODO: Add epsilon when working with returns so that quantity is float.
        if abs(order.quantity) < EPSILON:
            assert abs(order.quantity - order._value) < EPSILON
            return result

        result.fee = self.fee_model.get_order_fee(order)

        self._handle_cash(order, result.fee)

        # Handle holdings in the account.
        holding = self.find_holding(order.symbol)

        if holding:
            assert holding.last_date_updated == date, "holding price is not up-to-date"
            holding.merge(order)

            # TODO: Check - If working with values (returns and not prices) add an if ..
            if abs(holding.quantity) < EPSILON:  # if quantity is zero
                assert abs(holding.value - holding.quantity) < EPSILON
                del self._holdings[order.symbol]
        else:
            self._holdings[order.symbol] = Holding(
                order.symbol,
                order.quantity,
                order.price,
                order._value,
                up_to_date=True,
                date=date
            )

        return result

    def order_position(self, order: Order, date) -> OrderResult:
        relative = self.to_relative_order(order, date)

        return self.place_order(relative, date)

    def close_position(self, symbol: str, price: float = None) -> CloseResult:
        order = Order(symbol, 0, price)
        result = CloseResult(order=order)

        if is_blank(order.symbol):
            # TODO: Should be an ERROR?
            return result

        holding = self.find_holding(order.symbol)

        if holding:
            order.quantity = -holding.quantity
            order._value = -holding.value

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
            order._value - holding.value,
        )

    def _handle_cash(self, order: Order, fee: float):
        self.cash -= fee
        self.cash -= order.value
        self.cash_new -= order._value
