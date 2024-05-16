import datetime

import pandas

import bktest

end = datetime.date.today()
start = end - datetime.timedelta(days=38)
initial_cash = 1_000_000
quantity_in_decimal = False # True = weights

data_source = bktest.data.source.YahooDataSource()

order_provider = bktest.order.DataFrameOrderProvider(pandas.DataFrame([
    {"symbol": "AAPL", "quantity": +50, "date": (start + datetime.timedelta(days=10)).isoformat()},
    {"symbol": "TSLA", "quantity": -25, "date": (start + datetime.timedelta(days=10)).isoformat()},
    {"symbol": "AAPL", "quantity": -40, "date": (start + datetime.timedelta(days=20)).isoformat()},
    {"symbol": "TSLA", "quantity": +50, "date": (start + datetime.timedelta(days=30)).isoformat()},
    {"symbol": "AAPL", "quantity": +50, "date": (start + datetime.timedelta(days=30)).isoformat()},
]))

fee_model = bktest.fee.ExpressionFeeModel(
    "abs(price * quantity) * 0.1"
)

bktest.SimpleBacktester(
    start=start,
    end=end,
    order_provider=order_provider,
    initial_cash=initial_cash,
    quantity_in_decimal=quantity_in_decimal,
    data_source=data_source,
    fee_model=fee_model,
    exporters=[
        bktest.export.ConsoleExporter(),
        bktest.export.DumpExporter(
            auto_override=True
        ),
        # backtest.export.QuantStatsExporter(
        #     auto_override=True
        # ),
    ],
).run()
