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

def compare_two_files_containing_dataframes(filename1, filename2) -> bool:
    assert filename1.split('.')[1] == filename2.split('.')[1], "mismatch in file types"
    
    if filename1.split('.')[1] == 'parquet':
        df0 = pandas.read_parquet(filename1)
        df1 = pandas.read_parquet(filename2)
    elif filename1.split('.')[1] == 'csv':
        df0 = pandas.read_csv(filename1)
        df1 = pandas.read_csv(filename2)
    else:
        assert False, "invalid file format specified"

    for idx, column in enumerate(df0.columns):
        print(column)
        assert df0.dtypes[idx] == df1.dtypes[idx], "type mismatch between dataframes"
        if pandas.api.types.is_integer_dtype(df0[column]):
            print(f"Column {column} is of integer type.")
            assert (df0[column].isna() == df1[column].isna()).all(), "not all NaN are equal in comparing int"
            assert (df0[~df0[column].isna()][column] == df1[~df1[column].isna()][column]).all(), "not all non-NaN are equal in comparing int"
        elif pandas.api.types.is_float_dtype(df0[column]):
            print(f"Column {column} is of float type.")
            print(max(abs(df0[~df0[column].isna()][column]/df1[~df1[column].isna()][column]-1)))
            print(max(abs(df0[~df0[column].isna()][column]-df1[~df1[column].isna()][column])))
            assert (df0[column].isna()==df1[column].isna()).all(), "not all NaN are equal in comparing float"
            assert np.allclose(df0[~df0[column].isna()][column],df1[~df1[column].isna()][column],atol=1.e-8), "not all non-NaN are equal in comparing float"
        elif pandas.api.types.is_string_dtype(df0[column]):
            print(f"Column {column} is of string type.")
            assert (df0[column] == df1[column]).all(), "not all string elements are equal in comparing str"
        elif pandas.api.types.is_bool_dtype(df0[column]):
            print(f"Column {column} is of boolean type.")
            assert (df0[column] == df1[column]).all(), "not all bool elements are equal  in comparing bool"
        else:
            print(f"Column {column} is of an unknown type: {df0[column].dtype}")
            assert False, "column is of an unknown type"    

    return True
    
compare_two_files_containing_dataframes('dump.csv', 'tests/fixtures/integration/yahoo/returns/dump.csv')
compare_two_files_containing_dataframes('report.csv', 'tests/fixtures/integration/yahoo/returns/report.csv')