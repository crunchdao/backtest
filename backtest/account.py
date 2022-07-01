import sys
import typing

from backtest.utils import is_blank

from .holding import Holding
from .order import Order, OrderResult, CloseResult
from .fee import FeeModel, ConstantFeeModel


class Account:

    def __init__(
        self,
        initial_cash: int = 1_000_000,
        fee_model: FeeModel = None
    ):
        self.initial_cash = initial_cash
        self.fee_model = fee_model if fee_model else ConstantFeeModel(0)

        self.cash = initial_cash
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

    @property
    def symbols(self) -> typing.Set[str]:
        return set(self._holdings.keys())

    @property
    def holdings(self) -> typing.List[Holding]:
        return list(self._holdings.values())

    def find_holding(self, symbol: str):
        return self._holdings.get(symbol, None)

    def place_order(self, order: Order) -> OrderResult:
        result = OrderResult(order=order)
        if not order.valid:
            return result

        result.success = True

        if order.quantity == 0:
            return result

        result.fee = self.fee_model.get_order_fee(order)

        self._handle_cash(order, result.fee)

        holding = self.find_holding(order.symbol)

        if holding:
            holding.merge(order)

            if not holding.quantity:
                del self._holdings[order.symbol]
        else:
            self._holdings[order.symbol] = Holding.from_order(order)

        return result

    def order_position(self, order: Order) -> OrderResult:
        relative = self.to_relative_order(order)

        return self.place_order(relative)

    def close_position(self, symbol: str, price: float = None) -> CloseResult:
        order = Order(symbol, 0, price)
        result = CloseResult(order=order)

        if is_blank(order.symbol):
            return result

        result.success = True

        holding = self.find_holding(order.symbol)

        if holding:
            order.quantity = -holding.quantity

            if order.price is None:
                order.price = holding.price
                print(f"[warning] no price available for {order.symbol}, using last price: {order.price}", file=sys.stderr)

            result.fee = self.fee_model.get_order_fee(order)

            self._handle_cash(order, result.fee)

            del self._holdings[order.symbol]
        else:
            result.missing = True

        return result

    def to_relative_order(self, order: Order):
        holding = self.find_holding(order.symbol)

        if not holding or order.quantity is None:
            return order

        return Order(
            order.symbol,
            order.quantity - holding.quantity,
            order.price
        )

    def _handle_cash(self, order: Order, fee: float):
        self.cash -= fee
        self.cash -= order.value
