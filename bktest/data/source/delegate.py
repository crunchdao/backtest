import datetime
import typing

import numpy
import pandas

from .base import DataSource


class DelegateDataSource(DataSource):

    def __init__(self, delegates: typing.List[DataSource]):
        self.delegates = delegates

    def fetch_prices(self, symbols, start, end):
        prices = None

        for delegate in self.delegates:
            remaining_symbols = DelegateDataSource._find_remaining(
                symbols, prices)
            if not len(remaining_symbols):
                break

            dataframe = delegate.fetch_prices(remaining_symbols, start, end)
            if dataframe is not None:
                dataframe.dropna(axis=1, how='all', inplace=True)

            if prices is None:
                prices = dataframe
            elif dataframe is not None:
                prices = pandas.merge(
                    prices,
                    dataframe,
                    on="Date",
                    how="outer"
                )

        remaining_symbols = DelegateDataSource._find_remaining(symbols, prices)
        if len(remaining_symbols):
            prices[remaining_symbols] = numpy.nan

        return prices

    def is_closeable(self):
        return True

    @staticmethod
    def _find_remaining(symbols: typing.Set[str], prices: pandas):
        if prices is None:
            return list(symbols)

        return list(set(symbols) - set(prices.columns))
