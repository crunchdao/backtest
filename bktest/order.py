import abc
import dataclasses
import datetime
import enum
import functools
import typing

import numpy
import pandas

from . import constants, utils


class OrderDirection(enum.IntEnum):

    SELL = -1
    HOLD = 0
    BUY = 1


@dataclasses.dataclass()
class Order:

    symbol: str
    quantity: int
    price: float = None

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
        if self.symbol is None:
            return False

        if self.symbol == 0:
            return False

        if isinstance(self.symbol, str) and utils.is_blank(self.symbol):
            return False

        if self.price is not None and self.price <= 0:
            return False

        return True


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


class OrderProvider(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        pass

    @abc.abstractmethod
    def get_orders(
        self,
        date: datetime.date,
        account: "Account"
    ) -> typing.List[Order]:
        pass


class ParallelOrderProvider(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        pass

    @abc.abstractmethod
    def get_orders_list(
        self,
        date: datetime.date,
        accounts: typing.List["Account"]
    ) -> typing.List[typing.List[Order]]:
        pass


class DataFrameOrderProvider(OrderProvider):

    def __init__(
        self,
        dataframe: pandas.DataFrame,
        offset_before_trading: int = 0,
        date_column=constants.DEFAULT_DATE_COLUMN,
        symbol_column=constants.DEFAULT_SYMBOL_COLUMN,
        quantity_column=constants.DEFAULT_QUANTITY_COLUMN
    ) -> None:
        if not isinstance(dataframe, pandas.DataFrame):
            dataframe = pandas.DataFrame(dataframe)

        dataframe = dataframe[[
            date_column,
            symbol_column,
            quantity_column
        ]].copy()

        dataframe[date_column] = dataframe[date_column].astype(
            'datetime64[ns]',
            copy=False
        )

        if offset_before_trading != 0:
            delta = pandas.tseries.offsets.BusinessDay(offset_before_trading)
            dataframe["date"] += delta

        self.date_column = date_column
        self.symbol_column = symbol_column
        self.quantity_column = quantity_column
        self.dataframe = dataframe

    @functools.cache
    def get_dates(self):
        dates = self.dataframe[self.date_column].unique()

        return [
            item.date()
            for item in pandas.to_datetime(dates)
        ]

    def get_orders(self, date, account):
        orders = self.dataframe[
            self.dataframe[self.date_column] == numpy.datetime64(date)
        ]

        return DataFrameOrderProvider.convert(
            orders,
            self.symbol_column,
            self.quantity_column
        )

    @staticmethod
    def convert(
        dataframe: pandas.DataFrame,
        symbol_column=constants.DEFAULT_SYMBOL_COLUMN,
        quantity_column=constants.DEFAULT_QUANTITY_COLUMN
    ):
        return [
            Order(
                symbol=row[symbol_column],
                quantity=row[quantity_column],
                price=None,
            )
            for _, row in dataframe.iterrows()
        ]


@dataclasses.dataclass()
class OrderResultCollection:

    elements: typing.List[OrderResult] = dataclasses.field(default_factory=list)
    closed_count: int = None
    closed_total: int = None

    @property
    def total_fees(self):
        return sum(map(lambda x: x.fee, self.elements), 0.0)

    @property
    def success_count(self):
        return self._count_by_success(True)

    @property
    def failed_count(self):
        return self._count_by_success(False)

    def append(self, result: OrderResult):
        return self.elements.append(result)

    def _count_by_success(self, success_value):
        count = 0

        for result in self.elements:
            if result.success == success_value:
                count += 1

        return count
