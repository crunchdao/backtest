import yfinance

from .base import DataSource


class YahooDataSource(DataSource):

    def fetch_prices(self, symbols, start, end):
        return yfinance.download(
            tickers=symbols,
            start=start,
            end=end,
            show_errors=False
        )["Adj Close"]

    def is_closeable(self):
        return True
