import abc
import datetime
import typing

from .model import Snapshot


class BaseExporter:

    @abc.abstractmethod
    def initialize(self) -> None:
        pass

    @abc.abstractmethod
    def on_skip(self, date: datetime.date, reason: str, ordered: bool) -> None:
        pass

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        pass

    @abc.abstractmethod
    def finalize(self) -> None:
        pass
