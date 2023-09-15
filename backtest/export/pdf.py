import abc
import datetime
import os
import typing
import quantstats
import slugify

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
        df_dump = self.dump_exporter.dataframe.reset_index().sort_values(by='date') if self.dump_exporter else None
        
        df_metrics = None
        if df_returns is not None:
            df_metrics = quantstats.reports.metrics(df_returns, benchmark=df_benchmark, display=False, mode="full")
            df_metrics.index = df_metrics.index.map(slugify.slugify)
            df_metrics.columns = df_metrics.columns.map(slugify.slugify)

        self.template.apply({
            "$date": datetime.date.today().isoformat(),
        })

        if df_returns is not None:
            self.template.apply({
                "$qs.montly-returns": lambda _: quantstats.plots.monthly_returns(df_returns, show=False, cbar=False),
                "$qs.cumulative-returns": lambda _: quantstats.plots.returns(df_returns, df_benchmark, show=False, subtitle=False),
                "$qs.cumulative-returns-volatility": lambda _: quantstats.plots.returns(df_returns, df_benchmark, match_volatility=True, show=False),
                "$qs.eoy-returns": lambda _: quantstats.plots.yearly_returns(df_returns, df_benchmark, show=False),
                "$qs.underwater-plot": lambda _: quantstats.plots.drawdown(df_returns, show=False),
            })

            def get_metric(column: str, name: str):
                try:
                    name.index(".")
                    print(f"[warning] invalid metric name: `{name}`: contains a dot")
                    name = name.replace(".", "-")
                except:
                    pass

                return df_metrics.loc[name, column]

            if df_benchmark is not None:
                self.template.apply_re({
                    r"\$qs\.metric\.(strategy|benchmark)\.(.+)": lambda _, type, metric: get_metric(type, metric),
                })
            else:
                self.template.apply_re({
                    r"\$qs\.metric\.strategy\.(.+)": lambda _, metric: get_metric("strategy", metric),
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
