import abc
import datetime

from typing import List

import pandas


class OrderProvider:

    @abc.abstractmethod
    def get_dates(self) -> List[datetime.date]:
        return []

    @abc.abstractmethod
    def get_orders_dataframe(self, date: datetime.date) -> pandas.DataFrame:
        pass
