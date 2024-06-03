import datetime
import json
import os
import sys
import typing
import warnings

import numpy
import pandas

from .data.source.base import DataSource
from . import constants


class SymbolMapper:

    def __init__(self):
        self._mapping = {}
        self._inverse_mapping = {}

    def add(self, from_: str, to: str):
        self._mapping[from_] = to
        self._inverse_mapping[to] = from_

    def map(self, symbol: str) -> str:
        return self._mapping.get(symbol, symbol)

    def unmap(self, symbol: str) -> str:
        return self._inverse_mapping.get(symbol, symbol)

    def maps(self, symbols: typing.Iterable[str]) -> typing.Iterable[str]:
        return [
            self.map(symbol)
            for symbol in symbols
        ]

    def unmaps(self, symbols: typing.Iterable[str]) -> typing.Iterable[str]:
        return [
            self.unmap(symbol)
            for symbol in symbols
        ]

    @staticmethod
    def empty() -> "SymbolMapper":
        return SymbolMapper()

    @staticmethod
    def from_file(path: str) -> "SymbolMapper":
        mapper = SymbolMapper()

        if path.endswith(".json"):
            root = None

            with open(path, "r") as fd:
                root = json.load(fd)

            if not isinstance(root, dict):
                raise ValueError("root must be an object")

            for key, value in root.items():
                if not isinstance(value, str):
                    raise ValueError(f"{key}'s value must be a string")

                mapper.add(key, value)
        else:
            raise ValueError(f"unsupported file type: {path}")

        return mapper


EPSILON = 1e-6

class PriceProvider:

    def __init__(self, start: datetime.date, end: datetime.date, data_source: DataSource, mapper: SymbolMapper, caching=True, work_with_prices=True):
        self.start = start
        self.end = end
        self.data_source = data_source
        self.mapper = mapper if mapper is not None else SymbolMapper.empty()
        self.caching = caching

        if work_with_prices and not self.data_source.data_source_contains_prices_not_returns:
            print('warning work_with_prices is true but there are no prices')
            print('setting work_with_prices to False')
            work_with_prices = False

        self.work_with_prices = work_with_prices

        self.storage = PriceProvider._create_storage(start, end, caching)
        self.total_returns = PriceProvider._create_storage(start, end, caching, name='returns')
        self.symbols = PriceProvider._create_symbols_set(self.storage)

        self.updated = False

    def download_missing(self, symbols: typing.Set[str]):
        if not isinstance(symbols, set):
            symbols = set(symbols)

        missing_symbols = symbols.difference(self.symbols)

        symbol_count = len(missing_symbols)
        if symbol_count:
            one_day = datetime.timedelta(days=1)

            prices = self.data_source.fetch_prices(
                symbols=self.mapper.maps(missing_symbols),
                start=self.start - one_day,  # Not enough since day before is not necessarily a trading day... or it's ok... because first day is the base?
                end=self.end + one_day
            )

            if prices is None:
                prices = pandas.DataFrame(
                    index=pandas.Index([], name=constants.DEFAULT_DATE_COLUMN),
                    columns=list(missing_symbols)
                )

            if symbol_count == 1:
                first = next(iter(missing_symbols))

                if isinstance(prices, pandas.Series):
                    if len(prices):
                        prices = pandas.DataFrame({
                            first: prices.values
                        }, index=pandas.Index(
                            prices.index,
                            name=constants.DEFAULT_DATE_COLUMN
                        ))
                    else:
                        prices = pandas.DataFrame({
                            first: numpy.nan
                        }, index=pandas.Index(
                            self.storage.index,
                            name=constants.DEFAULT_DATE_COLUMN
                        ))

            prices.columns = self.mapper.unmaps(prices.columns)

            for column in prices.columns:
                if prices[column].isna().values.all():
                    print(f"[warning] {column} does not have a price", file=sys.stderr)

            if self.data_source.data_source_contains_prices_not_returns:
                total_returns = prices / prices.shift(1) - 1
                shift = 1
            else:
                total_returns = prices.copy()
                shift = 0

            # If return for a specific stock exists, there was a price/trading in that day and since we work with returns the price is set to one else it is NaN.
            if not self.work_with_prices:
                abs = prices.abs()
                # TODO: enzo: check if this could works and give the same result `prices.loc[~prices.isna()] = 1`
                prices = (abs + EPSILON) / (abs + EPSILON)

                assert (prices[shift:].isna() == total_returns[shift:].isna()).all().all(), "nans are not matching between prices and total_returns"

            if self.storage is not None:
                with warnings.catch_warnings():
                    warnings.simplefilter(action='ignore', category=pandas.errors.PerformanceWarning)

                    self.storage = pandas.merge(
                        self.storage,
                        prices,
                        on=constants.DEFAULT_DATE_COLUMN,
                        how="left"
                    )
            else:
                self.storage = prices

            if self.total_returns is not None:
                with warnings.catch_warnings():
                    warnings.simplefilter(action='ignore', category=pandas.errors.PerformanceWarning)

                    self.total_returns = pandas.merge(
                        self.total_returns,
                        total_returns,
                        on=constants.DEFAULT_DATE_COLUMN,
                        how="left"
                    )
            else:
                self.total_returns = total_returns

            self.symbols.update(missing_symbols)
            self.updated = True

    def get(self, date: datetime.date, symbol: str):
        if symbol not in self.symbols:
            raise ValueError(f"{symbol} not available")

        symbol = self.mapper.map(symbol)

        value = self.storage[symbol][numpy.datetime64(date)]
        if not value or numpy.isnan(value):
            value = None

        return value

    def get_total_return(self, date: datetime.date, symbol: str):
        if symbol not in self.symbols:
            raise ValueError(f"{symbol} not available")

        symbol = self.mapper.map(symbol)

        value = self.total_returns[symbol][numpy.datetime64(date)]
        if numpy.isnan(value):
            value = None

        return value

    def save(self):
        if not self.caching or not self.updated:
            return

        path = PriceProvider._get_cache_path(self.start, self.end)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        self.storage.to_csv(path)

        path = PriceProvider._get_cache_path(self.start, self.end, name='returns')
        self.total_returns.to_csv(path)

    def is_closeable(self) -> bool:
        return self.data_source.is_closeable()

    @staticmethod
    def _create_storage(start: datetime.date, end: datetime.date, caching=True, name='prices'):
        if caching:
            path = PriceProvider._get_cache_path(start, end, name=name)

            if os.path.exists(path):
                dataframe = pandas.read_csv(path, index_col=constants.DEFAULT_DATE_COLUMN)
                dataframe.index = dataframe.index.astype(
                    'datetime64[ns]',
                    copy=False
                )

                return dataframe

        dates = []

        date = start
        while date <= end:
            dates.append(numpy.datetime64(date))
            date += datetime.timedelta(days=1)

        dataframe = pandas.DataFrame({constants.DEFAULT_DATE_COLUMN: dates, "_": numpy.nan})
        dataframe.set_index(constants.DEFAULT_DATE_COLUMN, inplace=True)

        return dataframe

    @staticmethod
    def _create_symbols_set(storage: pandas.DataFrame):
        return set([symbol for symbol in storage.columns if symbol != "_"])

    @staticmethod
    def _get_cache_path(start, end, name='prices'):
        return f".cache/{name}-s{start}-e{end}.csv"
