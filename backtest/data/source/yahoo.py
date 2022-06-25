import abc
import datetime
import typing

import pandas
import yfinance

from .base import DataSource


class YahooDataSource(DataSource):

    @abc.abstractmethod
    def fetch_prices(self, symbols: typing.Set[str], start: datetime.date, end: datetime.date) -> pandas.DataFrame:
        return yfinance.download(
            tickers=symbols,
            start=start,
            end=end,
            show_errors=False
        )["Adj Close"]

    @abc.abstractmethod
    def is_closeable(self) -> bool:
        return True
