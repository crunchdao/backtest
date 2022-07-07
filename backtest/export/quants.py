import abc
import datetime
import os
import sys
import typing
import warnings

import pandas
import quantstats
import seaborn

from .base import BaseExporter
from .model import Snapshot


class QuantStatsExporter(BaseExporter):

    def __init__(
        self,
        html_output_file='report.html',
        csv_output_file='report.csv',
        benchmark_ticker="SPY",
        auto_delete=False,
        auto_override=False
    ):
        self.html_output_file = html_output_file
        self.csv_output_file = csv_output_file
        self.benchmark_ticker = benchmark_ticker
        self.auto_delete = auto_delete
        self.auto_override = auto_override
        
        self.data_frame = pandas.DataFrame(columns=["date", "equity"])
        self.data_frame.set_index("date", inplace=True)
        
        warnings.filterwarnings(action='ignore', category=UserWarning, module=seaborn.__name__)
        
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
        date = snapshot.date
        if snapshot.postponned is not None:
            date = snapshot.postponned
        
        self.data_frame = pandas.concat([
            self.data_frame,
            pandas.DataFrame(
                [[date, snapshot.equity]],
                columns=["date", "equity"],
            )
        ], axis=0)

    @abc.abstractmethod
    def finalize(self) -> None:
        if not len(self.data_frame):
            print("[warning] cannot create tearsheet: dataframe is empty", file=sys.stderr)
            return
        
        history_df = self.data_frame.copy()
        history_df.set_index("date", inplace=True)

        history_df['profit'] = history_df['equity'] - history_df['equity'].shift(1)
        history_df['daily_profit_pct'] = history_df["profit"] / history_df["equity"].shift(1)

        # history_df['profit'].fillna(0, inplace=True)
        # history_df['daily_profit_pct'].fillna(0, inplace=True)

        history_df.reset_index(inplace=True)

        bench = quantstats.utils.download_returns(self.benchmark_ticker)
        bench = bench.reset_index()
        bench = bench.rename(columns={"Date": "date", "Close": "close"})

        history_df['date'] = history_df['date'].astype(str)
        bench['date'] = bench['date'].astype(str)

        history_df['date'] = pandas.to_datetime(history_df['date'], format="%Y-%m-%d")
        bench['date'] = pandas.to_datetime(bench['date'], format="%Y-%m-%d")

        merged = history_df.merge(bench, on='date', how='inner')
        merged.set_index('date', drop=True, inplace=True)
        
        if self.csv_output_file is not None:
            if self.auto_override or not os.path.exists(self.csv_output_file):
                merged.to_csv(self.csv_output_file)
            else:
                print(f"[warning] {self.csv_output_file} already exists", file=sys.stderr)

        if self.html_output_file is not None:
            if self.auto_override or not os.path.exists(self.html_output_file):
                quantstats.reports.html(merged.daily_profit_pct, merged.close, output=True, download_filename=self.html_output_file)
            else:
                print(f"[warning] {self.html_output_file} already exists", file=sys.stderr)
