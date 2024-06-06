import datetime

import pandas
import polars as pl
import numpy as np
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

start = datetime.date(1998,11,1)
end = datetime.date(2000,11,30)
initial_cash = 1_000_000
quantity_in_decimal = True # False # True = weights
work_with_prices = False

# Set the order provider data.
file_name='example/test_constituents_orders.csv'
fields = ["dateYYYYMM", "id","weight"]
orders_dataframe = pandas.read_csv(file_name, usecols=fields)
years=orders_dataframe['dateYYYYMM']//100
months=orders_dataframe['dateYYYYMM']%100
years+=months//12
months = (months%12)+1
orders_dataframe['date']=pandas.to_datetime({'year':years, 'month':months,'day':2})

order_provider = DataFrameOrderProvider(
  orders_dataframe,
  date_column="date",
  symbol_column="id",
  quantity_column="weight"
)

# Set the returns data.
file_name='example/test_constituents_returns.csv'
fields = ["date", "id","ret"]
dataframe = pandas.read_csv(file_name, usecols=fields)

years = dataframe['date'].values//10000
months = (dataframe['date'].values%10000)//100
days = dataframe['date'].values%100

dates=pandas.to_datetime({'year':years, 'month':months,'day':days})
dataframe['date']=pandas.to_datetime(dataframe['date'], format='%Y%m%d')

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

pandas.read_csv('dump.csv').to_parquet('dump.parquet', index=False)