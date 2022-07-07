import datetime

import backtest
import pandas

end = datetime.date.today()
start = end - datetime.timedelta(days=88)
initial_cash = 1_000_000
quantity_in_decimal = False

data_source = backtest.data.source.YahooDataSource()

order_provider = backtest.order.provider.DataFrameOrderProvider(pandas.DataFrame([
    {"symbol": "AAPL", "quantity": +50, "date": (start + datetime.timedelta(days=10)).isoformat()},
    {"symbol": "TSLA", "quantity": -25, "date": (start + datetime.timedelta(days=10)).isoformat()},
    {"symbol": "MSFT", "quantity": +30, "date": (start + datetime.timedelta(days=20)).isoformat()},
    {"symbol": "AAPL", "quantity": -40, "date": (start + datetime.timedelta(days=20)).isoformat()},
    {"symbol": "NFLX", "quantity": -60, "date": (start + datetime.timedelta(days=30)).isoformat()},
    {"symbol": "AAPL", "quantity": +50, "date": (start + datetime.timedelta(days=30)).isoformat()},
    {"symbol": "AAPL", "quantity": +60, "date": (start + datetime.timedelta(days=40)).isoformat()},
    {"symbol": "AAPL", "quantity": +70, "date": (start + datetime.timedelta(days=50)).isoformat()},
    {"symbol": "AAPL", "quantity": +80, "date": (start + datetime.timedelta(days=60)).isoformat()},
]))

fee_model = backtest.fee.ExpressionFeeModel(
    "abs(price * quantity) * 0.1"
)

backtest.Backtester(
    start=start,
    end=end,
    order_provider=order_provider,
    initial_cash=initial_cash,
    quantity_in_decimal=quantity_in_decimal,
    data_source=data_source,
    fee_model=fee_model,
    exporters=[
        backtest.export.ConsoleExporter(),
        backtest.export.QuantStatsExporter(
            auto_override=True
        ),
    ],
).run()
