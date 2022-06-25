import abc

from ..order import Order


class FeeModel:

    @abc.abstractmethod
    def get_order_fee(self, order: Order) -> float:
        return 0.0
