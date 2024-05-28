import numpy
import pandas

from .base import DataSource
from ... import constants


class DataFrameDataSource(DataSource):

    def __init__(
        self,
        dataframe: pandas.DataFrame,
        date_column=constants.DEFAULT_DATE_COLUMN,
        symbol_column=constants.DEFAULT_SYMBOL_COLUMN,
        price_column=constants.DEFAULT_PRICE_COLUMN,
        closeable=True,
        data_source_contains_prices_not_returns=True   # True for price, False for returns.
    ) -> None:
        super().__init__()

        dataframe = dataframe.drop_duplicates(
            subset=[symbol_column, date_column],
            keep="first"
        )

        dataframe = dataframe.pivot(
            index=date_column,
            columns=symbol_column,
            values=price_column
        )

        dataframe.index = pandas.to_datetime(dataframe.index)
        dataframe.index.name = constants.DEFAULT_DATE_COLUMN

        self.dataframe = dataframe
        self.closeable = closeable
        self.data_source_contains_prices_not_returns = data_source_contains_prices_not_returns

    def fetch_prices(self, symbols, start, end):
        symbols = set(symbols)

        missings = symbols - set(self.dataframe.columns)
        founds = symbols - missings

        prices = None
        if len(founds):
            start = pandas.to_datetime(start)
            end = pandas.to_datetime(end)

            prices = self.dataframe[
                (self.dataframe.index >= start) &
                (self.dataframe.index <= end)
            ][list(founds)].copy()
        else:
            prices = pandas.DataFrame(
                index=pandas.DatetimeIndex(
                    data=pandas.date_range(start=start, end=end),
                    name=constants.DEFAULT_DATE_COLUMN
                )
            )

        prices[list(missings)] = numpy.nan

        return prices

    def is_closeable(self):
        return self.closeable
