import abc
import datetime
import functools
import typing

import numpy
import pandas

from .base import OrderProvider


class DataFrameOrderProvider(OrderProvider):

    def __init__(self,
            dataframe: pandas.DataFrame,
            date_column="date",
            symbol_column="symbol",
            quantity_column="quantity"
        ) -> None:
        self.dataframe = dataframe

        self.dataframe.rename(columns={
            date_column: "date",
            symbol_column: "symbol",
            quantity_column: "quantity"
        }, inplace=True)

        self.dataframe["date"] = self.dataframe["date"].astype('datetime64[ns]', copy=False)

    @functools.cache
    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        return [
            item.date()
            for item in pandas.to_datetime(self.dataframe["date"].unique())
        ]
    
    @abc.abstractmethod
    def get_orders_dataframe(self, date: datetime.date) -> pandas.DataFrame:
        return self.dataframe[self.dataframe["date"] == numpy.datetime64(date)]
