import abc
import datetime
import os

from .base import BaseExporter
from .quants import QuantStatsExporter
from ..template import Template, PdfTemplateRenderer

class PdfExporter(BaseExporter):

    def __init__(
        self,
        quantstats_exporter: QuantStatsExporter,
        template: Template,
        output_file="report.pdf",
        auto_delete=False,
        debug=False,
    ):
        self.quantstats_exporter = quantstats_exporter
        self.output_file = output_file
        self.auto_delete = auto_delete
        self.template = template

        self.renderer = PdfTemplateRenderer(
            debug=debug,
        )
        
    @abc.abstractmethod
    def initialize(self) -> None:
        if os.path.exists(self.output_file):
            can_delete = self.auto_delete
            if not can_delete:
                can_delete = input(f"{self.output_file}: delete file? [y/N]").lower() == 'y'
            
            if can_delete:
                os.remove(self.output_file)

    @abc.abstractmethod
    def finalize(self) -> None:
        returns = self.quantstats_exporter.returns
        benchmark = self.quantstats_exporter.benchmark
        # TODO add graphs and meaningful informations

        today = datetime.date.today().isoformat()
        strategy_name = "My Strategy"

        self.template.apply({
            "2023-06-13": today,
            "2023-06-02": today,
            "2023-05-02": today,
            "Systematic Long-Shor": strategy_name,
            "Featuring Crypto Dir": strategy_name,
        })

        with open(self.output_file, "wb") as fd:
            self.renderer.render(self.template, fd)
