import abc
import os
import sys
import typing

import pandas
import quantstats

from .base import Exporter
from .model import Snapshot

def _expect_column(dataframe: pandas.DataFrame, name: str):
    if name not in dataframe.columns:
        raise ValueError(f"column {name} not found")

class SpecificReturnExporter(Exporter):

    def __init__(
        self,
        path_or_dataframe_or_dict: typing.Union[str, pandas.DataFrame, dict],
        date_column="date",
        symbol_column="symbol",
        value_column="specific_return",
        html_output_file='sr-report.html',
        csv_output_file='sr-report.csv',
        auto_delete=False,
        auto_override=False
    ):
        super().__init__()
        
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.value_column = value_column
        self.html_output_file = html_output_file
        self.csv_output_file = csv_output_file
        self.auto_delete = auto_delete
        self.auto_override = auto_override

        if isinstance(path_or_dataframe_or_dict, dict):
            self.specific_returns = path_or_dataframe_or_dict
        else:
            self.specific_returns = SpecificReturnExporter.load_as_nested_dict(path_or_dataframe_or_dict, date_column, symbol_column, value_column)
       
        self.value = None
        self.previous_market_prices = {}
        self.history = []
        
    @abc.abstractmethod
    def initialize(self) -> None:
        if self.auto_override:
            return
        
        for file in [self.html_output_file, self.csv_output_file]:
            if file is None or not os.path.exists(file):
                continue
            
            can_delete = self.auto_delete
            if not can_delete:
                can_delete = input(f"{file}: delete file? [y/N]").lower() == 'y'
            
            if can_delete:
                os.remove(file)

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        date = snapshot.real_date

        market_prices = {
            holding.symbol: holding.market_price
            for holding in snapshot.holdings
        }
        
        if self.value is None:
            self.value = snapshot.cash + sum(market_prices.values())
        else:
            mapping = self.specific_returns.get(date, {})

            if len(mapping):
                self.value += sum([
                    market_price * mapping.get(symbol, 0) / 100
                    for symbol, market_price in self.previous_market_prices.items()
                ])
            else:
                print(f"[warning] no specific return for date={date}")
        
        self.value -= snapshot.total_fees
        
        self.history.append([date, self.value])
        self.previous_market_prices = market_prices

    @abc.abstractmethod
    def finalize(self) -> None:
        dataframe = pandas.DataFrame(self.history, columns=["date", "value"])
        dataframe.set_index("date", inplace=True)

        if not len(dataframe):
            print("[warning] cannot create specific return tearsheet: dataframe is empty", file=sys.stderr)
            return

        dataframe['profit'] = dataframe['value'] - dataframe['value'].shift(1)
        dataframe['daily_profit_pct'] = dataframe["profit"] / dataframe["value"].shift(1)

        dataframe.reset_index(inplace=True)

        dataframe['date'] = dataframe['date'].astype(str)
        dataframe['date'] = pandas.to_datetime(dataframe['date'], format="%Y-%m-%d")
        
        returns = dataframe.set_index("date").daily_profit_pct
        
        if self.csv_output_file is not None:
            if self.auto_override or not os.path.exists(self.csv_output_file):
                returns.to_csv(self.csv_output_file)
            else:
                print(f"[warning] {self.csv_output_file} already exists", file=sys.stderr)

        if self.html_output_file is not None:
            if self.auto_override or not os.path.exists(self.html_output_file):
                quantstats.reports.html(returns, output=True, download_filename=self.html_output_file)
            else:
                print(f"[warning] {self.html_output_file} already exists", file=sys.stderr)

    @staticmethod
    def load_as_nested_dict(
        path_or_dataframe: typing.Union[str, pandas.DataFrame],
        date_column="date",
        symbol_column="symbol",
        value_column="specific_return",
    ) -> pandas.DataFrame:
        if isinstance(path_or_dataframe, pandas.DataFrame):
            dataframe = path_or_dataframe
        else:
            dataframe = SpecificReturnExporter.load(path_or_dataframe, date_column, symbol_column, value_column)

        return dataframe \
            .groupby(date_column) \
            .apply(lambda x: x.set_index(symbol_column)[value_column].to_dict()) \
            .to_dict()

    @staticmethod
    def load(
        path: str,
        date_column="date",
        symbol_column="symbol",
        value_column="specific_return",
    ) -> pandas.DataFrame:
        dataframe = pandas.read_parquet(path) if path.endswith(".parquet") else pandas.read_csv(path)
        
        _expect_column(dataframe, date_column)
        _expect_column(dataframe, symbol_column)
        _expect_column(dataframe, value_column)

        dataframe[date_column] = pandas.to_datetime(dataframe[date_column]).dt.date

        return dataframe
