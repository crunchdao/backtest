import abc
import datetime
import json
import os
import sys
import typing

import numpy
import pandas
import pyarrow
import pyarrow.parquet
import requests
import tqdm

from ..base import DataSource


def _expect_column(table: pyarrow.lib.Table, name: str, type: str):
    for field in table.schema:
        if field.name == name:
            if field.type != type:
                raise ValueError(f"field {name} expected type {type} but got: {field.type}")
            else:
                return True
    
    raise ValueError(f"field {name} not found")


class RowParquetFileDataSource(DataSource):

    def __init__(self, path: str, date_column="date", symbol_column="symbol", price_column="price") -> None:
        super().__init__()
        
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.price_column = price_column
        
        table = pyarrow.parquet.read_table(path, memory_map=True)
        
        _expect_column(table, date_column, "date32[day]")
        _expect_column(table, symbol_column, "string")
        _expect_column(table, price_column, "double")
        
        dataframe = table.to_pandas()
        dataframe = dataframe.drop_duplicates(subset=[symbol_column, date_column], keep="first")
        dataframe = dataframe.pivot(index=date_column, columns=symbol_column, values=price_column)
        dataframe.index = pandas.to_datetime(dataframe.index)
        
        dataframe.index.name = "Date"
        
        self.storage = dataframe

    @abc.abstractmethod
    def fetch_prices(self, symbols: typing.Set[str], start: datetime.date, end: datetime.date) -> pandas.DataFrame:
        symbols = set(symbols)
        
        missings = symbols - set(self.storage.columns)
        founds = symbols - missings
        
        prices = None
        if len(founds):
            start = pandas.to_datetime(start)
            end = pandas.to_datetime(end)
            
            prices = self.storage[(self.storage.index >= start) & (self.storage.index <= end)][list(founds)].copy()
        else:
            prices = pandas.DataFrame(
                index=pandas.DatetimeIndex(
                    data=pandas.date_range(start=start, end=end),
                    name="Date"
                )
            )
        
        prices[list(missings)] = numpy.nan
        
        return prices

    @abc.abstractmethod
    def is_closeable(self) -> bool:
        return True
