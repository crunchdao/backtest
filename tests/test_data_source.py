import unittest

from backtest.data.source import DataSource


class DataSourceTest(unittest.TestCase):

    def test_get_name(self):
        class ValidNameDataSource(DataSource):
            def fetch_prices(self, symbols, start, end):
                raise NotImplementedError()

        class InvalidNameSource(DataSource):
            def fetch_prices(self, symbols, start, end):
                raise NotImplementedError()

        self.assertEqual("ValidName", ValidNameDataSource().get_name())
        self.assertEqual("InvalidNameSource", InvalidNameSource().get_name())
