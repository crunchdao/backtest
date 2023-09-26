import abc
import datetime
import os
import typing
import quantstats
import slugify
import pandas

from .base import BaseExporter
from .quants import QuantStatsExporter
from .dump import DumpExporter
from ..template import Template, PdfTemplateRenderer


_EMPTY_DICT = dict()


class PdfExporter(BaseExporter):

    def __init__(
        self,
        quantstats_exporter: typing.Optional[QuantStatsExporter],
        dump_exporter: typing.Optional[DumpExporter],
        template: Template,
        output_file="report.pdf",
        auto_delete=False,
        debug=False,
        variables: typing.Dict[str, str] = _EMPTY_DICT,
        user_scripts: "module" = list(),
    ):
        self.quantstats_exporter = quantstats_exporter
        self.dump_exporter = dump_exporter
        self.output_file = output_file
        self.auto_delete = auto_delete
        self.template = template
        self.variables = variables
        self.user_scripts = user_scripts

        self.renderer = PdfTemplateRenderer(
            debug=debug,
        )

    @abc.abstractmethod
    def initialize(self) -> None:
        if os.path.exists(self.output_file):
            can_delete = self.auto_delete
            if not can_delete:
                can_delete = input(
                    f"{self.output_file}: delete file? [y/N]").lower() == 'y'

            if can_delete:
                os.remove(self.output_file)

    @abc.abstractmethod
    def finalize(self) -> None:
        df_returns = self.quantstats_exporter.returns if self.quantstats_exporter else None
        df_benchmark = self.quantstats_exporter.benchmark if self.quantstats_exporter else None

        df_dump = None
        if self.dump_exporter and self.dump_exporter.dataframe is not None:
            df_dump = self.dump_exporter.dataframe.reset_index().sort_values(by='date')

        if df_benchmark is not None:
            df_benchmark.name = "RUSSELL (1000)"

        df_metrics, df_drowdowns = None, None
        if df_returns is not None:
            df_returns.name = "Strategy"
            df_metrics = quantstats.reports.metrics(df_returns, benchmark=df_benchmark, display=False, mode="full")
            df_metrics.index = df_metrics.index.map(slugify.slugify)
            df_metrics.columns = df_metrics.columns.map(slugify.slugify)

            df_drowdowns = quantstats.stats.to_drawdown_series(df_returns)
            if not df_drowdowns.empty:
                details = quantstats.stats.drawdown_details(df_drowdowns)
                df_drowdowns = details.sort_values(
                    by=details.columns[4],
                    ascending=True
                )[:5]

            if df_drowdowns.empty:
                df_drowdowns = None
            else:
                df_drowdowns["start"] = pandas.to_datetime(df_drowdowns["start"])
                df_drowdowns["end"] = pandas.to_datetime(df_drowdowns["end"])

        self.template.apply({
            "$date": datetime.date.today().isoformat(),
        })

        figsize = (8, 5)

        if df_returns is not None:
            self.template.apply({
                "$qs.montly-returns": lambda _: quantstats.plots.monthly_returns(df_returns, show=False, cbar=False, figsize=(figsize[0], figsize[0]*.5)),
                "$qs.cumulative-returns": lambda _: quantstats.plots.returns(df_returns, df_benchmark, show=False, subtitle=False),
                "$qs.cumulative-returns-volatility": lambda _: quantstats.plots.returns(df_returns, df_benchmark, match_volatility=df_benchmark is not None, show=False),
                "$qs.eoy-returns": lambda _: quantstats.plots.yearly_returns(df_returns, df_benchmark, show=False),
                "$qs.underwater-plot": lambda _: quantstats.plots.drawdown(df_returns, show=False),
            })

            # TODO Use name% format instead
            NOT_PERCENT = [
                "sharpe",
                "avg-drawdown-days",
                "kurtosis",
                "sortino",
            ]

            def get_metric(column: str, name: str):
                try:
                    name.index(".")
                    print(f"[warning] invalid metric name: `{name}`: contains a dot")
                    name = name.replace(".", "-")
                except:
                    pass

                value = df_metrics.loc[name, column]
                if name in NOT_PERCENT:
                    return value
                else:
                    value *= 100
                    return f"{value:.2f}%"

            def get_drawdown(n: int, key: typing.Union[typing.Literal["dates"], typing.Literal["value"]]):
                if df_drowdowns is not None and len(df_drowdowns) >= n:
                    index = n - 1
                    row = df_drowdowns.iloc[index]
                else:
                    row = None

                if key == "dates":
                    if row is None:
                        return "----/--/-- - ----/--/--"

                    start = row["start"].strftime('%Y/%m/%d')
                    end = row["end"].strftime('%Y/%m/%d')

                    return f"{start} - {end}"
                else:
                    if row is None:
                        return "--%"

                    value = row["max drawdown"]
                    return f"{value:.2f}%"

            if df_benchmark is not None:
                self.template.apply_re({
                    r"\$qs\.metric\.(strategy|benchmark)\.(.+)": lambda _, type, metric: get_metric(type, metric),
                })
            else:
                self.template.apply_re({
                    r"\$qs\.metric\.strategy\.(.+)": lambda _, metric: get_metric("strategy", metric),
                })

        self.template.apply_re({
            r"\$qs\.worst-drawdowns\.(\d+).(dates|value)": lambda _, n, key: get_drawdown(int(n), key),
        })

        self.template.apply(self.variables)

        for user_script in self.user_scripts:
            get_template_values = getattr(user_script, "get_template_values", None)
            if not callable(get_template_values):
                continue

            values, values_re = get_template_values(**locals())
            self.template.apply(values)
            self.template.apply_re(values_re)

        with open(self.output_file, "wb") as fd:
            self.renderer.render(self.template, fd)
