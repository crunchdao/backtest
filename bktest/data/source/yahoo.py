import yfinance

from .base import DataSource
from ... import constants


class YahooDataSource(DataSource):

    def fetch_prices(self, symbols, start, end):
        prices = yfinance.download(
            tickers=symbols,
            start=start,
            end=end,
            show_errors=False
        )["Adj Close"]

        prices.index.name = constants.DEFAULT_DATE_COLUMN

        return prices

    def is_closeable(self):
        return True
