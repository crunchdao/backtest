import abc
import datetime
import json
import os
import typing

import dateutil.parser
import pandas

from .base import OrderProvider


class FileReader:

    @staticmethod
    def CSV(path):
        dataframe = pandas.read_csv(path)
        dataframe.columns = ["symbol", "quantity"]

        return dataframe

    @staticmethod
    def JSON(path):
        with open(path, "r") as fd:
            content = json.loads(fd.read())

            dataframe = pandas.DataFrame.from_dict(content, orient='index')
            dataframe.reset_index(inplace=True)
            dataframe.columns = ["symbol", "quantity"]

            return dataframe

    @staticmethod
    def find(extension):
        if extension is None:
            raise ValueError("extension is None")

        extension = extension.lower()
        if extension == "csv":
            return FileReader.CSV
        elif extension == "json":
            return FileReader.JSON

        raise ValueError(f"extension `{extension}` is not supported")


class OrderFile:

    def __init__(self, at: datetime.date, path: str, reader=FileReader.CSV):
        self.at = at
        self.path = path
        self.reader = reader

    def read(self) -> pandas.DataFrame:
        return self.reader(self.path)

    def __lt__(self, other) -> bool:
        return self.at < other.at

    def __repr__(self) -> str:
        return self.path

    @staticmethod
    def load_from(directory: str, extension="csv", skip_until: typing.Optional[datetime.date]=None) -> typing.List["OrderFile"]:
        files = []

        reader = FileReader.find(extension)
        dot_extension = f".{extension}"

        for file in os.listdir(directory):
            if not file.endswith(dot_extension):
                continue

            at = dateutil.parser.parse(file[:-len(dot_extension)]).date()
            path = os.path.join(directory, file)

            if skip_until and skip_until > at:
                continue

            files.append(OrderFile(
                at,
                path,
                reader=reader
            ))

        files.sort()

        return files


class MultipleFileOrderProvider(OrderProvider):

    def __init__(
        self,
        directory,
        offset_before_trading: int,
        extension="csv"
    ) -> None:
        self.directory = directory

        delta = pandas.tseries.offsets.BusinessDay(offset_before_trading)

        self.order_files = {
            (order_file.at + delta).date(): order_file
            for order_file in OrderFile.load_from(
                directory,
                extension=extension
            )
        }

        self.dates = list(self.order_files.keys())
        self.dates.sort()

    @abc.abstractmethod
    def get_dates(self) -> typing.List[datetime.date]:
        return self.dates

    @abc.abstractmethod
    def get_orders_dataframe(self, date: datetime.date) -> pandas.DataFrame:
        return self.order_files[date].read()
