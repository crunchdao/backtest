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
        return not utils.is_blank(self.symbol) \
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


class OrderProvider(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        return []

    @abc.abstractmethod
    def get_orders(self, date: datetime.date, account: "Account") -> typing.List[Order]:
        return []


class DataFrameOrderProvider(OrderProvider):

    def __init__(
        self,
        dataframe: pandas.DataFrame,
        offset_before_trading: int,
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
