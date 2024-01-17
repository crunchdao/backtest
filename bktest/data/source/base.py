import abc
import datetime
import typing

import pandas


class DataSource(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch_prices(
        self,
        symbols: typing.Set[str],
        start: datetime.date,
        end: datetime.date
    ) -> pandas.DataFrame:
        raise NotImplementedError()

    def is_closeable(self) -> bool:
        """
        Return whether or not the markat has closing hours.
        Cryptocurrencies for examples does not.
        """

        return True

    def get_name(self) -> str:
        base_name = DataSource.__name__

        if self.__class__ == DataSource:
            return base_name

        class_name = self.__class__.__name__
        if base_name in class_name:
            return class_name.replace(base_name, "")

        return class_name
