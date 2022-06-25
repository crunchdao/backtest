import pandas

from .dataframe import DataFrameOrderProvider


class SingleFileOrderProvider(DataFrameOrderProvider):

    def __init__(self,
        path: str,
        date_column="date",
        symbol_column="symbol",
        quantity_column="quantity"
    ) -> None:
        super().__init__(
            dataframe=pandas.read_csv(path),
            date_column="date",
            symbol_column="symbol",
            quantity_column="quantity"
        )
