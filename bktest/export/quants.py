import abc
import os
import sys
import warnings

import pandas
import quantstats
import seaborn

from .base import Exporter
from .model import Snapshot


class QuantStatsExporter(Exporter):

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

        self.rows = []

        warnings.filterwarnings(
            action='ignore',
            category=UserWarning,
            module=seaborn.__name__
        )

    @abc.abstractmethod
    def initialize(self) -> None:
        if self.auto_override:
            return

        for file in [self.html_output_file, self.csv_output_file]:
            if file is None or not os.path.exists(file):
                continue

            can_delete = self.auto_delete
            if not can_delete:
                can_delete = input(
                    f"{file}: delete file? [y/N]").lower() == 'y'

            if can_delete:
                os.remove(file)

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        if snapshot.ordered:
            return
        
        date = snapshot.date
        if snapshot.postponned is not None:
            date = snapshot.postponned

        self.rows.append(
            (date, snapshot.nav)
        )

    @abc.abstractmethod
    def finalize(self) -> None:
        value_column_name = "nav"
        self.dataframe = pandas.DataFrame(
            self.rows,
            columns=["date", value_column_name]
        ).set_index("date")

        self.dataframe.to_csv('temp_qs.csv')
        if not len(self.dataframe):
            print(
                "[warning] cannot create tearsheet: dataframe is empty",
                file=sys.stderr
            )

            return

        history_df = self.dataframe.copy()

        history_df['profit'] = history_df[value_column_name] - \
            history_df[value_column_name].shift(1)
        history_df['daily_profit_pct'] = history_df["profit"] / \
            history_df[value_column_name].shift(1)

        history_df.reset_index(inplace=True)

        history_df['date'] = history_df['date'].astype(str)
        history_df['date'] = pandas.to_datetime(
            history_df['date'],
            format="%Y-%m-%d"
        )
        # TODO: remove after debuging.
        history_df.to_csv('history_df.csv')
        
        if self.benchmark_ticker:
            bench = quantstats.utils.download_returns(self.benchmark_ticker)

            bench = bench.reset_index()
            bench = bench.rename(columns={"Date": "date", "Close": "close"})

            bench['date'] = pandas.to_datetime(
                bench['date'],
                format="%Y-%m-%d"
            ).dt.tz_localize(None)

            merged = history_df.merge(bench, on='date', how='inner')

            merged.set_index('date', drop=True, inplace=True)

            returns = merged.daily_profit_pct
            benchmark = merged.close
        else:
            returns = history_df.set_index("date").daily_profit_pct
            benchmark = None

        if self.csv_output_file is not None:
            if self.auto_override or not os.path.exists(self.csv_output_file):
                returns.to_csv(self.csv_output_file)
            else:
                print(
                    f"[warning] {self.csv_output_file} already exists",
                    file=sys.stderr
                )

        self.returns = returns
        self.benchmark = benchmark

        if self.html_output_file is not None:
            if self.auto_override or not os.path.exists(self.html_output_file):
                quantstats.reports.html(
                    returns,
                    benchmark=benchmark,
                    output=self.html_output_file,
                    active_returns=False
                )
            else:
                print(
                    f"[warning] {self.html_output_file} already exists",
                    file=sys.stderr
                )
