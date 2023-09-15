import datetime
import logging
import sys
import typing
import os
import importlib
import time
import webbrowser

import click
import dotenv
import pandas
import contexttimer
import watchdog
import watchdog.observers
import watchdog.events

from .utils import is_number

dotenv.load_dotenv()


@click.group(invoke_without_command=True)
@click.option('--start', type=click.DateTime(formats=["%Y-%m-%d"]), default=None, help="Start date.")
@click.option('--end', type=click.DateTime(formats=["%Y-%m-%d"]), default=None, help="End date.")
@click.option('--offset-before-trading', type=int, default=1, show_default=True, help="Number of day to offset to push the signal before trading it.")
@click.option('--offset-before-ending', type=int, default=0, show_default=True, help="Number of day to continue the backtest after every orders.")
@click.option('--order-file', type=str, default=None, show_default=True, help="Specify an order file to use.")
@click.option('--order-files', type=str, default=None, show_default=True, help="Specify a directory containing order files to use.")
@click.option('--order-files-extension', type=click.Choice(['csv', 'parquet', 'json']), default="csv", show_default=True, help="Specify the extension of the order files.")
@click.option('--single-file-provider-column-date', type=str, default="date", show_default=True, help="Specify the date column name.")
@click.option('--single-file-provider-column-symbol', type=str, default="symbol", show_default=True, help="Specify the symbol column name.")
@click.option('--single-file-provider-column-quantity', type=str, default="quantity", show_default=True, help="Specify the quantity column name.")
@click.option('--initial-cash', type=int, default=100_000, show_default=True, help="Specify an initial cash amount.")
@click.option('--quantity-mode', type=click.Choice(['percent', 'share']), default="percent", show_default=True, help="Use percent for weight and share for units.")
@click.option('--auto-close-others', is_flag=True, help="Close the position that hasn't been provided after all of the order.")
@click.option('--weekends', is_flag=True, help="Include weekends?")
@click.option('--holidays', is_flag=True, help="Include holidays?")
@click.option('--symbol-mapping', type=str, required=False, help="Custom symbol mapping file enabling vendor-id translation.")
@click.option('--no-caching', is_flag=True, help="Disable price caching.")
@click.option('--fee-model', "fee_model_value", type=str, help="Specify a fee model. Must be a constant or an expression.")
@click.option('--console', is_flag=True, help="Enable the console exporter.")
@click.option('--console-format', type=click.Choice(['text', 'json']), default="text", show_default=True, help="Console output format.")
@click.option('--console-file', type=click.Choice(['out', 'err']), default="out", show_default=True, help="Console output destination file.")
@click.option('--console-hide-skips', is_flag=True, show_default=True, help="Should the console hide skipped days?")
@click.option('--console-text-no-color', is_flag=True, help="Disable colors in the console output.")
@click.option('--dump', is_flag=True, help="Enable the dump exporter.")
@click.option('--dump-output-file', type=str, default="dump.csv", show_default=True, help="Specify the output file.")
@click.option('--dump-auto-delete', is_flag=True, help="Should conflicting files be automatically deleted?")
@click.option('--influx', is_flag=True, help="Enable the influx exporter.")
@click.option('--influx-host', type=str, default="localhost", show_default=True, help="Influx's database host.")
@click.option('--influx-port', type=int, default=8086, show_default=True, help="Influx's database port.")
@click.option('--influx-database', type=str, default="backtest", show_default=True, help="Influx's database name.")
@click.option('--influx-measurement', type=str, default="snapshots", show_default=True, help="Influx's database table.")
@click.option('--influx-key', type=str, default="test", show_default=True, help="Key to use to uniquely identify the exported values.")
@click.option('--quantstats', is_flag=True, help="Enable the quantstats exporter.")
@click.option('--quantstats-output-file-html', type=str, default="report.html", show_default=True, help="Specify the output html file.")
@click.option('--quantstats-output-file-csv', type=str, default="report.csv", show_default=True, help="Specify the output csv file.")
@click.option('--quantstats-benchmark-ticker', type=str, default="SPY", show_default=True, help="Specify the symbol to use as a benchmark.")
@click.option('--quantstats-auto-delete', is_flag=True, help="Should conflicting files be automatically deleted?")
@click.option('--pdf', is_flag=True, help="Enable the quantstats exporter.")
@click.option('--pdf-template', type=str, default="tearsheet.sketch", show_default=True, help="Specify the template file.")
@click.option('--pdf-output-file', type=str, default="report.pdf", show_default=True, help="Specify the output pdf file.")
@click.option('--pdf-auto-delete', is_flag=True, help="Should aa conflicting file be automatically deleted?")
@click.option('--pdf-debug', is_flag=True, help="Enable renderer debugging.")
@click.option('--pdf-variable', "pdf_variables", nargs=2, multiple=True, type=(str, str), help="Specify custom variables.")
@click.option('--pdf-user-script', "pdf_user_script_paths", multiple=True, type=str, help="Specify custom scripts.")
@click.option('--specific-return', type=str, help="Enable the specific return exporter by proving a .parquet.")
@click.option('--specific-return-column-date', type=str, default="date", show_default=True, help="Specify the column name containing the dates.")
@click.option('--specific-return-column-symbol', type=str, default="symbol", show_default=True, help="Specify the column name containing the symbols.")
@click.option('--specific-return-column-value', type=str, default="specific_return", show_default=True, help="Specify the column name containing the value.")
@click.option('--specific-return-output-file-html', type=str, default="sr-report.html", show_default=True, help="Specify the output html file.")
@click.option('--specific-return-output-file-csv', type=str, default="sr-report.csv", show_default=True, help="Specify the output csv file.")
@click.option('--specific-return-auto-delete', is_flag=True, help="Should conflicting files be automatically deleted?")
@click.option('--yahoo', is_flag=True, help="Use yahoo finance as the data source.")
@click.option('--coinmarketcap', is_flag=True, help="Use coin market cap as the data source.")
@click.option('--coinmarketcap-force-mapping-refresh', is_flag=True, help="Force a mapping refresh.")
@click.option('--coinmarketcap-page-size', default=10_000, help="Specify the query page size when building the mapping.")
@click.option('--factset', is_flag=True, help="Use factset prices as the data source.")
@click.option('--factset-username-serial', type=str, envvar="FACTSET_USERNAME_SERIAL", help="Specify the factset username serial to use.")
@click.option('--factset-api-key', type=str, envvar="FACTSET_API_KEY", help="Specify the factset api key to use.")
@click.option('--file-parquet', type=str, required=False, help="Use a .parquet file as the data source.")
@click.option('--file-parquet-column-date', type=str, default="date", show_default=True, help="Specify the column name containing the dates.")
@click.option('--file-parquet-column-symbol', type=str, default="symbol", show_default=True, help="Specify the column name containing the symbols.")
@click.option('--file-parquet-column-price', type=str, default="price", show_default=True, help="Specify the column name containing the prices.")
@click.option('--rfr-file', type=str, help="Specify the path of the risk free rate file")
@click.option('--rfr-file-column-date', type=str, default="date", help="Specify the date column of the risk free rate file")
@click.pass_context
def cli(ctx: click.Context, **kwargs):
    if ctx.invoked_subcommand is None:
        main(**kwargs)


def main(
    start: datetime.datetime, end: datetime.datetime,
    offset_before_trading: int,
    offset_before_ending: int,
    order_file,
    order_files, order_files_extension,
    single_file_provider_column_date, single_file_provider_column_symbol, single_file_provider_column_quantity,
    initial_cash, quantity_mode, auto_close_others,
    weekends, holidays, symbol_mapping, no_caching,
    fee_model_value,
    console, console_format, console_file, console_hide_skips, console_text_no_color,
    dump: str, dump_output_file: str, dump_auto_delete: bool,
    influx, influx_host, influx_port, influx_database, influx_measurement, influx_key,
    quantstats, quantstats_output_file_html, quantstats_output_file_csv, quantstats_benchmark_ticker, quantstats_auto_delete,
    pdf: bool, pdf_template: str, pdf_output_file: str, pdf_auto_delete: bool, pdf_debug: bool, pdf_variables: typing.Tuple[typing.Tuple[str, str]], pdf_user_script_paths: str,
    specific_return: str, specific_return_column_date: str, specific_return_column_symbol: str, specific_return_column_value: str, specific_return_output_file_html: str, specific_return_output_file_csv: str, specific_return_auto_delete: bool,
    yahoo,
    coinmarketcap, coinmarketcap_force_mapping_refresh, coinmarketcap_page_size,
    factset: bool, factset_username_serial: str, factset_api_key: str,
    file_parquet, file_parquet_column_date, file_parquet_column_symbol, file_parquet_column_price,
    rfr_file: str, rfr_file_column_date: str
):
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

    now = datetime.date.today()

    quantity_in_decimal = quantity_mode == "percent"

    order_provider = None
    if order_file is not None:
        from .order.provider import SingleFileOrderProvider
        order_provider = SingleFileOrderProvider(
            order_file,
            offset_before_trading,
            date_column=single_file_provider_column_date,
            symbol_column=single_file_provider_column_symbol,
            quantity_column=single_file_provider_column_quantity
        )
    elif order_files is not None:
        from .order.provider import MultipleFileOrderProvider
        order_provider = MultipleFileOrderProvider(
            order_files,
            offset_before_trading,
            extension=order_files_extension
        )

    if order_provider is None:
        raise ValueError("no order provider available")

    dates = order_provider.get_dates()
    if not len(dates):
        raise ValueError("no date found")

    if start is not None:
        start = start.date()
    else:
        start = dates[0]

    if end is not None:
        end = end.date()
    else:
        end = dates[-1]

    end += datetime.timedelta(days=offset_before_ending)

    if end > now:
        end = now

        print(f"[warning] end is after today, using: {now}", file=sys.stderr)

    data_source = None
    if yahoo:
        from .data.source import YahooDataSource
        data_source = YahooDataSource()

    if coinmarketcap:
        if data_source is not None:
            raise ValueError("multiple data source provided")

        from .data.source import CoinMarketCapDataSource
        data_source = CoinMarketCapDataSource(
            force_mapping_refresh=coinmarketcap_force_mapping_refresh,
            page_size=coinmarketcap_page_size
        )

    if factset:
        if data_source is not None:
            raise ValueError("multiple data source provided")

        from .data.source import FactsetDataSource
        data_source = FactsetDataSource(
            username_serial=factset_username_serial,
            api_key=factset_api_key
        )

    if file_parquet:
        from .data.source.file import RowParquetFileDataSource
        file_data_source = RowParquetFileDataSource(
            path=file_parquet,
            date_column=file_parquet_column_date,
            symbol_column=file_parquet_column_symbol,
            price_column=file_parquet_column_price
        )

        if data_source is not None:
            print(
                f"[info] multiple data source provider, delegating: {data_source.get_name()}", file=sys.stderr)

            from .data.source import DelegateDataSource
            data_source = DelegateDataSource([
                file_data_source,
                data_source,
            ])
        else:
            data_source = file_data_source

    if data_source is None:
        from .data.source import YahooDataSource
        data_source = YahooDataSource()

        print(
            f"[warning] no data source selected, defaulting to --yahoo", file=sys.stderr)

    from .price_provider import SymbolMapper
    symbol_mapper = None if not symbol_mapping else SymbolMapper.from_file(
        symbol_mapping)

    fee_model = None
    if fee_model_value:
        if is_number(fee_model_value):
            from .fee import ConstantFeeModel
            fee_model = ConstantFeeModel(float(fee_model_value))
        else:
            from .fee import ExpressionFeeModel
            fee_model = ExpressionFeeModel(fee_model_value)
    else:
        from .fee import ConstantFeeModel
        fee_model = ConstantFeeModel(0.0)

    exporters = []
    if console:
        from .export import ConsoleExporter
        exporters.append(ConsoleExporter(
            format=console_format,
            file={
                "out": sys.stdout,
                "err": sys.stderr
            }[console_file],
            hide_skips=console_hide_skips,
            no_color=console_text_no_color
        ))

    if dump:
        from .export import DumpExporter
        exporters.append(DumpExporter(
            output_file=dump_output_file,
            auto_delete=dump_auto_delete,
        ))

    if influx:
        from .export import InfluxExporter
        exporters.append(InfluxExporter(
            host=influx_host,
            port=influx_port,
            database=influx_database,
            measurement=influx_measurement,
            key=influx_key
        ))

    if quantstats:
        from .export import QuantStatsExporter
        exporters.append(QuantStatsExporter(
            html_output_file=quantstats_output_file_html,
            csv_output_file=quantstats_output_file_csv,
            benchmark_ticker=quantstats_benchmark_ticker,
            auto_delete=quantstats_auto_delete,
        ))

    if specific_return:
        from .export import SpecificReturnExporter
        exporters.append(SpecificReturnExporter(
            specific_return,
            date_column=specific_return_column_date,
            symbol_column=specific_return_column_symbol,
            value_column=specific_return_column_value,
            html_output_file=specific_return_output_file_html,
            csv_output_file=specific_return_output_file_csv,
            auto_delete=specific_return_auto_delete,
        ))

    if pdf:
        from .export import QuantStatsExporter, DumpExporter

        quantstats_exporter = next(
            filter(lambda x: isinstance(x, QuantStatsExporter), exporters), None)
        dump_exporter = next(
            filter(lambda x: isinstance(x, DumpExporter), exporters), None)

        template = _load_template(pdf_template)

        user_scripts = []
        for index, path in enumerate(pdf_user_script_paths or list()):
            directory = os.path.dirname(path)

            spec = importlib.util.spec_from_file_location(
                f"pdf_user_code_{index}",
                path
            )

            print(path)

            print(spec)

            module = importlib.util.module_from_spec(spec)

            sys.path.insert(0, directory)
            spec.loader.exec_module(module)

            user_scripts.append(module)

        from .export import PdfExporter
        exporters.append(PdfExporter(
            quantstats_exporter=quantstats_exporter,
            dump_exporter=dump_exporter,
            template=template,
            output_file=pdf_output_file,
            auto_delete=pdf_auto_delete,
            debug=pdf_debug,
            variables=dict(pdf_variables or tuple()),
            user_scripts=user_scripts or list()
        ))

    if not len(exporters):
        from .export import ConsoleExporter
        exporters.append(ConsoleExporter())

        print(
            f"[warning] no exporter selected, defaulting to --console", file=sys.stderr)

    if rfr_file:
        rfr = pandas.read_parquet(rfr_file)
        rfr = rfr.set_index(rfr_file_column_date)
    else:
        rfr = pandas.Series(dtype="float64")

    from .backtest import Backtester
    Backtester(
        start=start,
        end=end,
        order_provider=order_provider,
        initial_cash=initial_cash,
        quantity_in_decimal=quantity_in_decimal,
        auto_close_others=auto_close_others,
        data_source=data_source,
        rfr=rfr,
        mapper=symbol_mapper,
        exporters=exporters,
        fee_model=fee_model,
        caching=not no_caching,
    ).run(
        weekends=weekends,
        holidays=holidays
    )


@cli.group(name="template")
def template_group():
    pass


@template_group.command()
@click.argument('template-path', type=click.Path(exists=True, dir_okay=False), default="tearsheet.sketch")
def info(
    template_path: str
):
    template = _load_template(template_path)

    print(f"name: {template.name}")

    keys = list(sorted((
        key
        for key in template.slots.keys()
        if key.startswith("$")
    )))

    print(f"variables:")
    for key in keys:
        print(f"  {key}")


@template_group.command()
@click.option('--output-file', type=str, default="report-test.pdf", show_default=True, help="Specify the output pdf file.")
@click.option('--debug', is_flag=True, help="Enable debug rendering.")
@click.option('--watch', is_flag=True, help="Watch and continuously re-render.")
@click.option('--open', "open_after_render", is_flag=True, help="Open after render.")
@click.argument('template-path', type=click.Path(exists=True, dir_okay=False), default="tearsheet.sketch")
def identity(
    template_path: str,
    output_file: str,
    debug: bool,
    watch: bool,
    open_after_render: bool,
):
    from .template import PdfTemplateRenderer
    renderer = PdfTemplateRenderer(debug=debug)

    def do_render():
        with contexttimer.Timer(prefix="loading", output=sys.stderr):
            template = _load_template(template_path)

        with contexttimer.Timer(prefix="rendering", output=sys.stderr):
            with open(output_file, "wb") as fd:
                renderer.render(template, fd)
        
        if open_after_render:
            webbrowser.open(output_file)

    if watch:
        do_render()

        directory = os.path.dirname(template_path) or "."
        path = os.path.join(directory, template_path)

        class Handler(watchdog.events.FileSystemEventHandler):

            def dispatch(self, event):
                if event.src_path != path:
                    return

                super().dispatch(event)

            def on_modified(self, event):
                do_render()

            def on_created(self, event):
                do_render()

        event_handler = Handler()

        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, directory, recursive=False)
        observer.start()

        try:
            print(f"watching for changes on: {template_path}")

            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("exit")
        finally:
            observer.stop()
            observer.join()
    else:
        do_render()


def _load_template(path: str):
    if path.endswith(".sketch"):
        from .template import SketchTemplateLoader
        return SketchTemplateLoader().load(path)
    else:
        raise click.Abort(f"unsupported template: {path}")
