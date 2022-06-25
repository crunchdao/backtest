import abc
import datetime
import typing

import numpy
import pandas

from .base import OrderProvider


class SingleFileOrderProvider(OrderProvider):

    def __init__(self, path, date_column="date", symbol_column="symbol", quantity_column="quantity") -> None:
        self.path = path
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.quantity_column = quantity_column

        self.dataframe = pandas.read_csv(path)

        self.dataframe.rename({
            symbol_column: "symbol",
            quantity_column: "quantity"
        }, inplace=True)

        self.dates = [item.date() for item in pandas.to_datetime(self.dataframe[self.date_column].unique())]

        self.dataframe[self.date_column] = self.dataframe[self.date_column].astype(
            'datetime64[ns]',
            copy=False
        )

    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        return self.dates
    
    @abc.abstractmethod
    def get_orders_dataframe(self, date: datetime.date) -> pandas.DataFrame:
        return self.dataframe[self.dataframe[self.date_column] == numpy.datetime64(date)]
