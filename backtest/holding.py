from .order import Order


class Holding:

    def __init__(self, symbol: str, quantity: float, price: float, up_to_date: bool) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.up_to_date = up_to_date

    @property
    def market_price(self) -> float:
        return self.quantity * self.price

    def merge(self, order: Order):
        if self.symbol != order.symbol:
            raise ValueError(f"cannot add different symbol: '{self.symbol}' and '{order.symbol}'")

        self.quantity += order.quantity
        self.price = order.price
        self.up_to_date = True

        return self

    def __str__(self) -> str:
        return f"{repr(self)}@{self.price}"

    def __repr__(self) -> str:
        return f"{self.symbol}x{self.quantity}"

    @staticmethod
    def from_order(order: Order) -> "Holding":
        return Holding(order.symbol, order.quantity, order.price, True)
