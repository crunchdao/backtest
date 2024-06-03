from .order import Order


class Holding:

    def __init__(self, symbol: str, quantity: float, price: float, value: float, up_to_date=False, date=None) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.value = value
        # TODO: remove up_to_date it is not necessary anymore, because of the variable last_date_updated which is more informative.
        self.up_to_date = up_to_date
        # Add date instead of up_to_date that has no information.....
        self.last_date_updated = date
        
    @property
    def market_price(self) -> float:
        return self.quantity * self.price

    def merge(self, order: Order):
        if self.symbol != order.symbol:
            raise ValueError(f"cannot add different symbol: '{self.symbol}' and '{order.symbol}'")

        self.quantity += order.quantity
        self.price = order.price
        self.value += order._value
        self.up_to_date = True

        return self

    def __str__(self) -> str:
        return f"{repr(self)}@{self.price}"

    def __repr__(self) -> str:
        return f"{self.symbol}x{self.quantity}"

    @staticmethod
    def from_order(order: Order, date=None) -> "Holding":
        return Holding(order.symbol, order.quantity, order.price, order._value, up_to_date=True, date=date)
