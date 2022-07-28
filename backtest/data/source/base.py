import abc
import datetime
import typing

import pandas


class DataSource:

    @abc.abstractmethod
    def fetch_prices(self, symbols: typing.Set[str], start: datetime.date, end: datetime.date) -> pandas.DataFrame:
        return None

    @abc.abstractmethod
    def is_closeable(self) -> bool:
        """
        Return whether or not the markat has closing hours.
        Cryptocurrencies for examples does not.
        """
        
        return True

    @abc.abstractmethod
    def get_name(self) -> str:
        class_name = self.__class__.__name__

        data_source = DataSource.__name__
        if data_source in class_name:
            return class_name.replace(data_source, "")
        
        return class_name