import abc

from ..order import Order
from .base import FeeModel


class ConstantFeeModel(FeeModel):
    
    def __init__(self, value: float):
        super().__init__()
        
        self.value = value

    @abc.abstractmethod
    def get_order_fee(self, order: Order) -> float:
        return self.value
