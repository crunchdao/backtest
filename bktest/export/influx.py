import abc
import datetime
import typing

import influxdb

from .base import BaseExporter
from .model import Snapshot


class InfluxExporter(BaseExporter):

    def __init__(
        self,
        host='localhost',
        port=8086,
        database="backtest",
        measurement="snapshots",
        key=str(datetime.datetime.now())
    ):
        self.influx = influxdb.InfluxDBClient(
            host=host,
            port=port,
            database=database
        )

        self.measurement = measurement
        self.key = key

    @abc.abstractmethod
    def initialize(self) -> None:
        self.influx.query(
            f"DELETE FROM {self.measurement} WHERE \"key\" = '{self.key}'"
        )

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        self.influx.write_points([
            {
                "measurement": self.measurement,
                "tags": {
                    "key": str(self.key),
                },
                "time": str(snapshot.date),
                "fields": {
                    "cash": snapshot.cash,
                    "equity": snapshot.equity,
                    "ordered": snapshot.ordered,
                    "holding_count": snapshot.holding_count,
                    "postponned": str(snapshot.postponned) if snapshot.postponned else None,
                    "total_fee": snapshot.total_fee,
                    "success_count": snapshot.success_count,
                    "failed_count": snapshot.failed_count,
                }
            }
        ])
