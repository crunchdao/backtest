import pandas

from .dataframe import DataFrameOrderProvider


class SingleFileOrderProvider(DataFrameOrderProvider):

    def __init__(self,
        path: str,
        offset_before_trading: int,
        date_column="date",
        symbol_column="symbol",
        quantity_column="quantity"
    ) -> None:
        super().__init__(
            pandas.read_csv(path),
            offset_before_trading,
            date_column=date_column,
            symbol_column=symbol_column,
            quantity_column=quantity_column
        )
