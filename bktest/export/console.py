import abc
import datetime
import json
import sys
import typing

from .base import Exporter
from .model import Snapshot


class ConsoleDelegate(Exporter):

    def __init__(self, file):
        self.file = file

    def _print(self, content):
        print(content, file=self.file)


class TextConsoleDelegate(ConsoleDelegate):

    def __init__(self, file, no_color=False, prefix="", **kwargs):
        super().__init__(file)

        self.no_color = no_color
        self.prefix = prefix
        self.days_of_the_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        if no_color:
            self.color_reset = ""
            self.color_red = ""
            self.color_magenta = ""
            self.color_green = ""
            self.color_yellow = ""
        else:
            from colorama import Back, Fore, Style
            self.color_reset = Style.RESET_ALL
            self.color_red = Fore.RED
            self.color_magenta = Fore.MAGENTA
            self.color_green = Fore.GREEN
            self.color_yellow = Fore.YELLOW

    @abc.abstractmethod
    def on_skip(self, date: datetime.date, reason: str, ordered: bool) -> None:
        day = self._day_of_the_week(date)

        line = f"{date} ({day})   {self.color_magenta}{reason}{self.color_reset}"

        if ordered:
            line += f"   {self.color_red}post-ponned order{self.color_reset}"

        self._print(line)

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        date = snapshot.date
        day = self._day_of_the_week(date)
        ordered_string = self._ordered_to_string(snapshot)
        equity = snapshot.equity
        cash = snapshot.cash
        equity_long = snapshot.equity_long
        nav = snapshot.nav

        ordered_color = self.color_green if snapshot.ordered else self.color_yellow

        line = f"{date} ({day})   {ordered_color}{ordered_string:20}{self.color_reset}    [nav={nav:12.4f}]    [equity={equity:12.4f}]    [cash={cash:12.4f}]    [equity_long={equity_long:12.4f}]]"

        if snapshot.ordered:
            holding_count = snapshot.holding_count
            line += f"    [portfolio={holding_count:4}]"

            total_fees = snapshot.total_fees
            line += f"    [fee={total_fees:12.4f}]"

            success_count = snapshot.success_count
            failed_count = snapshot.failed_count
            total = success_count + failed_count
            line += f"    [orders={success_count}/{total}]"

            if snapshot.closed_count is not None:
                closed_count = snapshot.closed_count
                closed_total = snapshot.closed_total
                line += f"    [closed={closed_count}/{closed_total}]"

        self._print(line)

    def _ordered_to_string(self, snapshot: Snapshot):
        if snapshot.ordered:
            out = "ordered"

            if snapshot.postponned is not None:
                out += f" ({snapshot.postponned})"

            return out

        return "price updated"

    def _day_of_the_week(self, date: datetime.date):
        return self.days_of_the_week[date.weekday()]

    def _print(self, content):
        if self.prefix:
            content = self.prefix + " " + content
        
        super()._print(content)


class JsonConsoleDelegate(ConsoleDelegate):

    def __init__(self, file, **kwargs):
        super().__init__(file)

        self.first = False

    @abc.abstractmethod
    def initialize(self) -> None:
        self._print("[")

    @abc.abstractmethod
    def on_skip(self, date: datetime.date, reason: str, ordered: bool) -> None:
        self._coma()

        self._print_json({
            "event": "SKIP",
            "date": str(date),
            "skipReason": reason,
            "ordered": ordered,
        })

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        self._coma()

        self._print_json({
            "event": "SNAPSHOT",
            "date": str(snapshot.date),
            "ordered": snapshot.ordered,
            "cash": snapshot.cash,
            "equity": snapshot.equity,
            "postponned": str(snapshot.postponned) if snapshot.postponned else None,
            "totalFees": snapshot.total_fees,
            "successCount": snapshot.success_count,
            "failedCount": snapshot.failed_count,
            "closed": {
                "count": snapshot.closed_count,
                "total": snapshot.closed_total
            }
        })

    @abc.abstractmethod
    def finalize(self) -> None:
        self._print("]")

    def _coma(self):
        if not self.first:
            self.first = True
            print(" ", end="", file=self.file)
        else:
            print(",", end="", file=self.file)

    def _print_json(self, object: dict):
        self._print(json.dumps(object))


class ConsoleExporter(Exporter):

    def __init__(self, format="text", file=sys.stdout, hide_skips=False, **kwargs):
        self.delegate = {
            "text": TextConsoleDelegate,
            "json": JsonConsoleDelegate
        }[format](file, **kwargs)

        self.hide_skips = hide_skips

    @abc.abstractmethod
    def initialize(self) -> None:
        self.delegate.initialize()

    @abc.abstractmethod
    def on_skip(self, date: datetime.date, reason: str, ordered: bool) -> None:
        if self.hide_skips:
            return

        self.delegate.on_skip(date, reason, ordered)

    @abc.abstractmethod
    def on_snapshot(self, snapshot: Snapshot) -> None:
        self.delegate.on_snapshot(snapshot)

    @abc.abstractmethod
    def finalize(self) -> None:
        self.delegate.finalize()
