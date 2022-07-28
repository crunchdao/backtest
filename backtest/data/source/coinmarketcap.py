import abc
import datetime
import json
import os
import sys
import typing

import pandas
import requests

from .base import DataSource


class CoinMarketCapDataSource(DataSource):

    def __init__(self, force_mapping_refresh=False, page_size=10000, mapping_cache_file=".cache/coinmarketcat-mapping.json") -> None:
        super().__init__()

        self.symbol_to_id_mapping: typing.Dict[str, int] = {}

        if force_mapping_refresh or not self._load_mapping_cache(mapping_cache_file):
            self._fetch_mapping(page_size)
            self._update_mapping_cache(mapping_cache_file)

        self._already_logged = set()

    def _log_missing(self, symbol: str) -> None:
        if symbol in self._already_logged:
            return

        print(f"[warning] no id found for {symbol}", file=sys.stderr)
        self._already_logged.add(symbol)

    def _load_mapping_cache(self, cache_path: str) -> None:
        if not os.path.exists(cache_path):
            return False

        with open(cache_path, "r") as fd:
            self.symbol_to_id_mapping = json.loads(fd.read())

        # validate a sample
        self.symbol_to_id_mapping["BTC"]

        return True

    def _update_mapping_cache(self, cache_path: str) -> None:
        with open(cache_path, "w") as fd:
            fd.write(json.dumps(self.symbol_to_id_mapping, indent=4))

    def _fetch_mapping(self, page_size) -> None:
        page = 0

        while True:
            crypto_currency_map = requests.get(
                f"https://api.coinmarketcap.com/data-api/v3/map/all",
                params={
                    "listing_status": "active,untracked",
                    "exchangeAux": "is_active,status",
                    "cryptoAux": "is_active,status",
                    "start": str(1 + (page * page_size)),
                    "limit": str(page_size)
                }
            ).json()["data"]["cryptoCurrencyMap"]

            for crypto_currency in crypto_currency_map:
                id = crypto_currency["id"]
                symbol = crypto_currency["symbol"]

                self.symbol_to_id_mapping[symbol] = id

            page += 1

            if len(crypto_currency_map) != page_size:
                break

        print(f"[info] [datasource] [coinmarketcap] mapping size is {len(self.symbol_to_id_mapping)}", file=sys.stderr)

    @abc.abstractmethod
    def fetch_prices(self, symbols: typing.Set[str], start: datetime.date, end: datetime.date) -> pandas.DataFrame:
        today = pandas.to_datetime(datetime.date.today())

        prices: pandas.DataFrame = None

        for symbol in symbols:
            id = self.symbol_to_id_mapping.get(symbol)

            if id is None:
                self._log_missing(symbol)
                continue

            points = requests.get(
                f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail/chart?id={id}&range=ALL",
            ).json()["data"]["points"]

            dataframe = pandas.DataFrame([
                [key, value["v"][0]]
                for key, value in points.items()
            ], columns=["Date", symbol])

            dataframe.sort_values(by=["Date"], inplace=True)
            dataframe.reset_index(drop=True, inplace=True)
            dataframe["Date"] = pandas.to_datetime(dataframe["Date"], unit="s")

            dataframe = dataframe[dataframe["Date"] < today]

            if len(dataframe) == 0:
                continue

            if prices is None:
                prices = dataframe
            else:
                prices = pandas.merge(
                    left=prices,
                    right=dataframe,
                    on="Date",
                    how="outer"
                )

        if prices is not None:
            prices.set_index(keys="Date", drop=True, inplace=True)

        return prices

    @abc.abstractmethod
    def is_closeable(self) -> bool:
        return False
