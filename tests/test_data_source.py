import unittest
from backtest.data.source import DataSource


class ValidNameDataSource(DataSource):
    pass

class InvalidNameSource(DataSource):
    pass


class DataSourceTest(unittest.TestCase):

    def test_get_name(self):
        self.assertEqual("DataSource", DataSource().get_name())
        self.assertEqual("ValidName", ValidNameDataSource().get_name())
        self.assertEqual("InvalidNameSource", InvalidNameSource().get_name())
