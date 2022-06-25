import abc

import py_expression_eval

from ..order import Order
from .base import FeeModel


class ExpressionFeeModel(FeeModel):
    
    def __init__(self, expression: str):
        super().__init__()
        
        parser = py_expression_eval.Parser()
        self.expression = parser.parse(expression)

    @abc.abstractmethod
    def get_order_fee(self, order: Order) -> float:
        return self.expression.evaluate({
            'quantity': order.quantity,
            'price': order.price,
        })
