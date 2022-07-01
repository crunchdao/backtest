import typing

from backtest.utils import is_blank

from .holding import Holding
from .order import Order, OrderResult, CloseResult
from .order.fee import FeeModel, ConstantFeeModel


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

    def place_order(self, order: Order) -> OrderResult:
        result = OrderResult(order=order)
        if not order.valid:
            return result

        result.success = True
        result.fee = self.fee_model.get_order_fee(order)

        self._handle_cash(order, result.fee)

        holding = self._holdings.get(order.symbol, None)

        if holding:
            holding.merge(order)

            if not holding.quantity:
                del self._holdings[order.symbol]
        else:
            self._holdings[order.symbol] = Holding.from_order(order)

        return result

    def close_position(self, symbol: str, price: float = None) -> CloseResult:
        order = Order(symbol, 0, price)
        result = CloseResult(order=order)

        if is_blank(symbol):
            return result

        result.success = True

        holding = self._holdings.get(symbol, None)

        if holding:
            order.quantity = -holding.quantity

            if order.price is None:
                order.price = holding.price

            result.fee = self.fee_model.get_order_fee(order)

            self._handle_cash(order, result.fee)

            del self._holdings[order.symbol]

        return result

    def _handle_cash(self, order: Order, fee: float):
        self.cash -= fee
        self.cash -= order.value