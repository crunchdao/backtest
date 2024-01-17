import abc
import os
import sys
import math
import typing
import datetime

from ..utils import signum

import pandas

from .base import BaseExporter
from .model import Snapshot


class DumpExporter(BaseExporter):

    def __init__(
        self,
        output_file='dump.csv',
        auto_delete=False,
        auto_override=False
    ):
        self.output_file = output_file
        self.auto_delete = auto_delete
        self.auto_override = auto_override
        
        self.all_dates = set()
        self.rows = []

    @abc.abstractmethod
    def initialize(self) -> None:
        if self.auto_override:
            return

        for file in [self.output_file]:
            if file is None or not os.path.exists(file):
                continue

            can_delete = self.auto_delete
            if not can_delete:
                can_delete = input(
                    f"{file}: delete file? [y/N]"
                ).lower() == 'y'

            if can_delete:
                os.remove(file)

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        date = snapshot.date
        self.all_dates.add(date)

        if snapshot.postponned is not None:
            date = snapshot.postponned
        
        self.rows.extend([
            (
                date,
                holding.symbol,
                holding.quantity,
                holding.price,
                holding.market_price,
                snapshot.equity
            )
            for holding in snapshot.holdings
        ])

    def get_missing_dates(self, dates: typing.Set[datetime.date]):
        return list(filter(
            lambda x: x not in dates,
            self.all_dates
        ))

    @abc.abstractmethod
    def finalize(self) -> None:
        self.dataframe = pandas.DataFrame(
            self.rows,
            columns=["date", "symbol", "quantity", "price", "market_price", "equity"]
        )
        
        if not len(self.dataframe):
            print(
                "[warning] cannot create dump: dataframe is empty",
                file=sys.stderr
            )
            
            return

        def inverse_sign_if_shorting(row: pandas.Series):
            if signum(row['quantity']) == -1:
                row['profit'] = row['profit'] * -1

            return row

        def compute_profit(group: pandas.DataFrame):
            missing = self.get_missing_dates(group["date"].unique())
            holes = pandas.DataFrame(
                [
                    [date, group.name, 0, math.nan, math.nan, math.nan]
                    for date in missing
                ],
                columns=["date", "symbol", "quantity", "price", "market_price", "equity"],
            )

            group = pandas.concat([group, holes])
            group.sort_values("date", inplace=True)

            price_yesterday = group["price"].shift(1)

            group['profit'] = (group['price'] - price_yesterday) / price_yesterday

            return group.apply(inverse_sign_if_shorting, axis=1)

        self.dataframe = self.dataframe.groupby("symbol").apply(compute_profit)
        self.dataframe.set_index("date", inplace=True)

        if self.output_file is not None:
            if self.auto_override or not os.path.exists(self.output_file):
                self.dataframe.to_csv(self.output_file)
            else:
                print(
                    f"[warning] {self.output_file} already exists",
                    file=sys.stderr
                )
