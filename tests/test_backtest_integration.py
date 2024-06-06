import unittest
import datetime
import pandas
import os
import numpy

from bktest.data.source import DataFrameDataSource
from bktest.order import DataFrameOrderProvider
from bktest.backtest import SimpleBacktester
from bktest.export import ConsoleExporter
from bktest.export import DumpExporter
from bktest.export import QuantStatsExporter


def fixture_path(subpath: str):
    return os.path.join(
        os.path.dirname(__file__),
        "fixtures/integration",
        subpath
    )


class BacktestIntegrationTest(unittest.TestCase):

    def test_constituents(self):
        start = datetime.date(1998, 11, 1)
        end = datetime.date(2000, 11, 30)
        initial_cash = 1_000_000
        quantity_in_decimal = True
        work_with_prices = False

        # Set the order provider data.
        orders_dataframe = pandas.read_csv(fixture_path("constituents/orders.csv"))
        years = orders_dataframe['dateYYYYMM'] // 100
        months = orders_dataframe['dateYYYYMM'] % 100
        years += months // 12
        months = (months % 12) + 1
        orders_dataframe['date'] = pandas.to_datetime({'year': years, 'month': months, 'day': 2})

        order_provider = DataFrameOrderProvider(
            orders_dataframe,
            date_column="date",
            symbol_column="id",
            quantity_column="weight"
        )

        # Set the returns data.
        dataframe = pandas.read_parquet(fixture_path("constituents/returns.parquet"))
        dataframe['date'] = pandas.to_datetime(dataframe['date'], format='%Y%m%d')

        file_data_source = DataFrameDataSource(
            dataframe,
            date_column="date",
            symbol_column="id",
            price_column="ret",
            data_source_contains_prices_not_returns=False,  # False for returns.
        )

        SimpleBacktester(
            start=start,
            end=end,
            order_provider=order_provider,
            initial_cash=initial_cash,
            quantity_in_decimal=quantity_in_decimal,
            data_source=file_data_source,
            exporters=[
                ConsoleExporter(),
                DumpExporter(
                    output_file="/tmp/dump.csv",
                    auto_override=True
                ),
                QuantStatsExporter(
                    html_output_file='/tmp/report.html',
                    csv_output_file='/tmp/report.csv',
                    auto_override=True
                ),
            ],
            work_with_prices=work_with_prices,
        ).run()

        dump_original = pandas.read_parquet(fixture_path("constituents/dump.parquet"))
        dump_new = pandas.read_csv("/tmp/dump.csv")

        self.assertTrue(numpy.allclose(dump_original["equity"], dump_new["equity"]))


    # def test_yahoo_prices(self):
    #     end = datetime.date(2024,6,3)
    #     start = end - datetime.timedelta(days=200)
    #     initial_cash = 1_000_000
    #     quantity_in_decimal = True
    #     work_with_prices = True

    #     data_source = YahooDataSource()

    #     order_provider = DataFrameOrderProvider(pandas.DataFrame([
    #         {"symbol": "AAPL", "quantity": 0.2, "date": '2023-12-30'},
    #         {"symbol": "TSLA", "quantity": 0.3, "date": '2023-12-30'},
    #         {"symbol": "AAPL", "quantity": -0.5, "date": '2024-01-19'},
    #         {"symbol": "TSLA", "quantity": 0.5, "date": '2024-01-19'},
    #         {"symbol": "AAPL", "quantity": -0.5, "date": '2024-01-20'},
    #         {"symbol": "TSLA", "quantity": 0.5, "date": '2024-01-20'},
    #     ]))

    #     backtester = SimpleBacktester(
    #         start=start,
    #         end=end,
    #         order_provider=order_provider,
    #         initial_cash=initial_cash,
    #         quantity_in_decimal=quantity_in_decimal,
    #         data_source=data_source,
    #         exporters=[
    #             ConsoleExporter(),
    #             DumpExporter(
    #                 output_file="/tmp/dump.csv",
    #                 auto_override=True,
    #             ),
    #             QuantStatsExporter(
    #                 html_output_file='/tmp/report.html',
    #                 csv_output_file='/tmp/report.csv',
    #                 auto_override=True
    #             ),
    #         ],
    #         work_with_prices=work_with_prices,
    #     )

    #     backtester.run()

    #     breakpoint()

    #     dump_original = pandas.read_csv(fixture_path("yahoo/prices/dump.csv"))
    #     dump_new = pandas.read_csv("/tmp/dump.csv")
