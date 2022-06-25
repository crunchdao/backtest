import datetime
import os
import typing

import numpy
import pandas

from backtest.data.source.base import DataSource
import json


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


class PriceProvider:

    def __init__(self, start: datetime.date, end: datetime.date, data_source: DataSource, mapper: SymbolMapper, caching=True):
        self.start = start
        self.end = end
        self.data_source = data_source
        self.mapper = mapper if mapper is not None else SymbolMapper.empty()
        self.caching = caching

        self.storage = PriceProvider._create_storage(start, end, caching)
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
                start=self.start - one_day,
                end=self.end + one_day
            )

            if symbol_count == 1:
                first = next(iter(missing_symbols))

                if isinstance(prices, pandas.Series):
                    if len(prices):
                        prices = pandas.DataFrame({
                            first: prices.values
                        }, index=pandas.Index(
                            prices.index,
                            name="Date"
                        ))
                    else:
                        prices = pandas.DataFrame({
                            first: numpy.nan
                        }, index=pandas.Index(
                            self.storage.index,
                            name="Date"
                        ))
            
            prices.columns = self.mapper.unmaps(prices.columns)
            for column in prices.columns:
                if prices[column].isna().values.all():
                    print(f"[warning] {column} does not have a price", file=sys.stderr)
            
            if self.storage is not None:
                self.storage = pandas.merge(
                    self.storage,
                    prices,
                    on='Date',
                    how="left"
                )
            else:
                self.storage = prices

            self.symbols.update(missing_symbols)
            self.updated = True

    def get(self, date: datetime.date, symbol: str):
        if symbol not in self.symbols:
            raise ValueError(f"{symbol} not available")
        
        symbol = self.mapper.map(symbol)
        """print(symbol, self.storage)
        print(symbol, self.storage.columns)"""
        # print(f"{symbol} getting {date}")
        return self.storage[symbol][numpy.datetime64(date)]

    def save(self):
        if not self.caching or not self.updated:
            return

        path = PriceProvider._get_cache_path(self.start, self.end)
        
        parent = os.path.dirname(path)
        os.makedirs(parent, exist_ok=True)
        
        self.storage.to_csv(path)
    
    def is_closeable(self) -> bool:
        return self.data_source.is_closeable()

    @staticmethod
    def _create_storage(start: datetime.date, end: datetime.date, caching=True):
        if caching:
            path = PriceProvider._get_cache_path(start, end)
    
            if os.path.exists(path):
                dataframe = pandas.read_csv(path, index_col="Date")
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

        dataframe = pandas.DataFrame({"Date": dates, "_": numpy.nan})
        dataframe.set_index("Date", inplace=True)

        return dataframe

    @staticmethod
    def _create_symbols_set(storage: pandas.DataFrame):
        return set([symbol for symbol in storage.columns if symbol != "_"])

    @staticmethod
    def _get_cache_path(start, end):
        return f".cache/prices-s{start}-e{end}.csv"
