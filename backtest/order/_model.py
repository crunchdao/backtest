import dataclasses
import enum

from ..utils import is_blank


class OrderDirection(enum.IntEnum):

    SELL = -1
    HOLD = 0
    BUY = 1


@dataclasses.dataclass()
class Order:

    symbol: str
    quantity: int
    price: float

    @property
    def value(self) -> float:
        return self.quantity * self.price

    @property
    def direction(self) -> OrderDirection:
        if self.quantity > 0:
            return OrderDirection.BUY

        if self.quantity < 0:
            return OrderDirection.SELL

        return OrderDirection.HOLD

    @property
    def valid(self):
        return not is_blank(self.symbol) \
            and self.price > 0


@dataclasses.dataclass()
class OrderResult:

    order: Order
    success: bool = False
    fee: float = 0.0


@dataclasses.dataclass()
class CloseResult:

    order: Order
    success: bool = False
    missing: bool = False
    fee: float = 0.0
