import abc
import os
import sys

import pandas
import quantstats

from .base import BaseExporter
from .model import Snapshot

def _expect_column(dataframe: pandas.DataFrame, name: str):
    if name not in dataframe.columns:
        raise ValueError(f"column {name} not found")

class SpecificReturnExporter(BaseExporter):

    def __init__(
        self,
        path: str,
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

        self.specific_returns = pandas.read_parquet(path) if path.endswith(".parquet") else pandas.read_csv(path)
        _expect_column(self.specific_returns, date_column)
        _expect_column(self.specific_returns, symbol_column)
        _expect_column(self.specific_returns, value_column)

        self.specific_returns[self.date_column] = pandas.to_datetime(self.specific_returns[self.date_column]).dt.date

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
            mapping = self.specific_returns[self.specific_returns[self.date_column] == date] \
                .set_index(self.symbol_column) \
                .to_dict()[self.value_column]

            self.value += sum([
                market_price * mapping.get(symbol, 0) / 100
                for symbol, market_price in self.previous_market_prices.items()
            ])
        
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
