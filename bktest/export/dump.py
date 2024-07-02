import abc
import datetime
import math
import os
import sys
import typing

import pandas
import readwrite

from ..utils import signum
from .base import Exporter
from .model import Snapshot


_COLUMNS = [
    "date",
    "symbol",
    "quantity",
    "price",
    "market_price",
    "equity",
    "ordered"
]


class DumpExporter(Exporter):

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

        common = [
            snapshot.nav,
            float(snapshot.ordered),
        ]

        self.rows.extend([
            (
                date,
                holding.symbol,
                holding.quantity,
                holding.price,
                holding.market_price,
                *common
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
            columns=_COLUMNS
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
                    [date, group.name, 0, math.nan, math.nan, math.nan, math.nan]
                    for date in missing
                ],
                columns=_COLUMNS,
            )

            if len(holes) > 0:
                group = pandas.concat([group, holes])
                
            group.sort_values(["date", "ordered"], inplace=True)

            price_yesterday = group["price"].shift(1)
            # TODO: Profit is a wrong name for this column..., 
            # it is just the change in price but since it is relative to the previous row and not previous date it has not real information I do not know why is it necessary to print it.
            # It is more confusing then helping.
            # Change the coulumn name equity to nav. and market_price to position value.
            
            group['profit'] = (group['price'] - price_yesterday) / price_yesterday

            return group.apply(inverse_sign_if_shorting, axis=1)

        self.dataframe = self.dataframe.groupby("symbol").apply(compute_profit)
        self.dataframe.set_index("date", inplace=True)

        if self.output_file is not None:
            if self.auto_override or not os.path.exists(self.output_file):
                readwrite.write(self.dataframe, self.output_file)
            else:
                print(
                    f"[warning] {self.output_file} already exists",
                    file=sys.stderr
                )
