import datetime

import pandas

#import bktest
import sys
sys.path.append('/home/lior/Projects/tools/backtest/')

from bktest.data.source import DataFrameDataSource
from bktest.data.source.yahoo import YahooDataSource
from bktest.order import DataFrameOrderProvider
from bktest.backtest import SimpleBacktester
from bktest.export import ConsoleExporter
from bktest.export import DumpExporter
from bktest.export import QuantStatsExporter

end = datetime.date(2024,6,3)
start = end - datetime.timedelta(days=200)
initial_cash = 1_000_000
quantity_in_decimal = True # False # True = weights
work_with_prices = False

data_source = YahooDataSource()


order_provider = DataFrameOrderProvider(pandas.DataFrame([
    {"symbol": "AAPL", "quantity": 0.2, "date": '2023-12-30'},
    {"symbol": "TSLA", "quantity": 0.3, "date": '2023-12-30'},
    {"symbol": "AAPL", "quantity": -0.5, "date": '2024-01-19'},
    {"symbol": "TSLA", "quantity": 0.5, "date": '2024-01-19'},
    {"symbol": "AAPL", "quantity": -0.5, "date": '2024-01-20'},
    {"symbol": "TSLA", "quantity": 0.5, "date": '2024-01-20'},
]))


SimpleBacktester(
    start=start,
    end=end,
    order_provider=order_provider,
    initial_cash=initial_cash,
    quantity_in_decimal=quantity_in_decimal,
    data_source=data_source,
    #fee_model=fee_model,
    exporters=[
        ConsoleExporter(),
        DumpExporter(
            auto_override=True
        ),
        QuantStatsExporter(
            auto_override=True
        ),
    ],
    work_with_prices=work_with_prices,
).run()
