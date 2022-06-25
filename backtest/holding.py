import abc
import typing

from .order import Order, OrderResult
from .order.fee import FeeModel, ConstantFeeModel
from .utils import signum


class Holding:

    def __init__(self, symbol, quantity, price):
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def get_market_price(self) -> float:
        return self.quantity * self.price

    def merge(self, holding: "Holding") -> "Holding":
        self.quantity = holding.quantity
        self.price = holding.price

        return self

    def __str__(self):
        return f"{repr(self)}@{self.price}"

    def __repr__(self):
        return f"{self.symbol}x{self.quantity}"
    
    @staticmethod
    def from_order(order: Order):
        return Holding(order.symbol, order.quantity, order.price)


class Holder:

    def __init__(self, cash: int=1_000_000, fee_model: FeeModel=ConstantFeeModel(0)):
        self.cash = cash
        self.fee_model = fee_model
        
        self.holdings: typing.Dict[str, Holding] = dict()

    def __getitem__(self, symbol: str) -> typing.Optional[Holding]:
        return self.holdings.get(symbol, None)
    
    def __delitem__(self, symbol: str):
        del self.holdings[symbol]

    def __setitem__(self, symbol: str, holding: Holding) -> Holding:
        current: Holding = self[symbol]

        if not current:
            if holding.quantity:
                self.holdings[symbol] = holding
            
            return holding

        current.merge(holding)
        
        if not current.quantity:
            del self[symbol]
        
        return current

    def order(self, order: Order) -> OrderResult:
        result = OrderResult(order=order)
        
        if not order.symbol:
            return result

        current_holding: Holding = self[order.symbol]
        holding = Holding.from_order(order)
        
        fee = self.fee_model.get_order_fee(order)
        
        result.fee = fee
        self.cash -= fee
        
        result.success = True

        if not current_holding:
            self[order.symbol] = holding
            self.cash -= holding.get_market_price()
            return result

        previous = current_holding.quantity
        current_holding.merge(holding)
        
        if not current_holding.quantity:
            del self[order.symbol]
        
        if signum(order.quantity) != signum(previous):
            #  previous    amount     go to zero
            #  10          -5         0 - 10 = SELL 10
            #  -5          10         0 - -5 = BUY  5
            
            self.cash -= (0 - previous) * order.price
            self.cash -= order.quantity * order.price
        else:
            #  previous    amount     value
            #   10           5           5 -  10 = SELL 5
            #   10          15          15 -  10 = BUY  5
            #    5          10          10 -   5 = BUY  5
            #   15          10          10 -  15 = SELL 5
            #  -10          -5         -5  - -10 = BUY  5
            #  -10         -15         -15 - -10 = SELL 5
            #   -5         -10         -10 -  -5 = SELL 5
            #  -15         -10         -10 - -15 = BUY  5
            
            self.cash -= (order.quantity - previous) * order.price

        return result

    def get_equity(self):
        equity = self.cash

        for holding in self.holdings.values():
            equity += holding.get_market_price()

        return equity

    def get_symbols(self) -> typing.Set[str]:
        return set(self.holdings.keys())

    def get_holdings(self) -> typing.List[Holding]:
        return list(self.holdings.values())
    
