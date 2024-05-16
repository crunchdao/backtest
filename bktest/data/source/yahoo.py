import yfinance

from .base import DataSource
from ... import constants


class YahooDataSource(DataSource):

    def fetch_prices(self, symbols, start, end, field="Adj Close"):
        prices = yfinance.download(
            tickers=symbols,
            start=start,
            end=end,
            show_errors=False
        )[field]

        prices.index.name = constants.DEFAULT_DATE_COLUMN

        return prices

    def is_closeable(self):
        return True
