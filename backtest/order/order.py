import dataclasses
import enum


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


@dataclasses.dataclass()
class OrderResult:
    
    order: Order
    success: bool = False
    fee: float = 0.0
    