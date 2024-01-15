import abc

from .order import Order
import py_expression_eval


class FeeModel(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_order_fee(self, order: Order) -> float:
        return 0.0


class ConstantFeeModel(FeeModel):

    def __init__(self, value: float):
        super().__init__()

        self.value = value

    def get_order_fee(self, order):
        return self.value


class ExpressionFeeModel(FeeModel):

    def __init__(self, expression: str):
        super().__init__()

        parser = py_expression_eval.Parser()
        self.expression = parser.parse(expression)

    def get_order_fee(self, order):
        return self.expression.evaluate({
            'quantity': order.quantity,
            'price': order.price,
        })
