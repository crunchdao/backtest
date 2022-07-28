import datetime

import abc
import os
import sys
import pandas
import requests
import typing
import tqdm

from ...utils import ensure_not_blank
from .base import DataSource

def chunks(l, n):
    n = max(1, n)
    return [l[i: i + n] for i in range(0, len(l), n)]

class FactsetDataSource(DataSource):

    def __init__(self, username_serial: str, api_key: str, chunk_size=100):
        self._session = requests.sessions.Session()
        self._session.auth = (
            ensure_not_blank(username_serial, "username_serial"),
            ensure_not_blank(api_key, "api_key")
        )
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        self.chunk_size = chunk_size

    @abc.abstractmethod
    def fetch_prices(self, symbols: typing.Set[str], start: datetime.date, end: datetime.date) -> pandas.DataFrame:
        prices = None

        for chunk in tqdm.tqdm(chunks(list(symbols), self.chunk_size)):
            response = self._session.post(
                "https://api.factset.com/content/factset-prices/v1/prices",
                json={
                    "ids": chunk,
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                    "frequency": "D",
                    "calendar": "FIVEDAY",
                    "adjust": "SPLIT",
                    "currency": "USD",
                },
            )

            status_code = response.status_code
            if status_code != 200:
                print(f"got status {status_code}: {response.content}", file=sys.stderr)
                continue

            dataframe = FactsetDataSource._to_dataframe(response.json())

            if prices is None:
                prices = dataframe
            else:
                prices = pandas.merge(
                    prices,
                    dataframe,
                    on="Date",
                    how="outer"
                )
        
        return prices

    @abc.abstractmethod
    def is_closeable(self) -> bool:
        return True

    @staticmethod
    def _to_dataframe(response_json: typing.Dict[str, typing.Any]) -> pandas.DataFrame:
        dataframe = pandas.DataFrame(response_json["data"])
        dataframe = dataframe[['requestId', 'date', 'price']]
        dataframe = dataframe.pivot(
            index='date', columns='requestId', values='price')
        dataframe.index.name = "Date"
        dataframe.index = pandas.to_datetime(dataframe.index)

        return dataframe
