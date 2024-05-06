import datetime
import typing
import dataclasses


@dataclasses.dataclass()
class Skip:

    date: datetime.date
    reason: str
    ordered: bool


class DateIterator:

    def __init__(
        self,
        start: datetime.date,
        end: datetime.date,
        closable: bool,
        order_dates: typing.List[datetime.date],
        allow_weekends=False,
        allow_holidays=False
    ):
        self.start = start
        self.end = end
        self.closable = closable
        self.order_dates = order_dates
        self.allow_weekends = allow_weekends
        self.allow_holidays = allow_holidays
        self.skips = []

        self._date = None

    def __iter__(self):
        if self.start is None:
            return iter([])

        if self._date is not None:
            raise ValueError("double iter")

        self._date = self.start
        return self

    def _should_skip_weekends(
        self,
        date: datetime.date,
        ordered: bool,
        skips: typing.List[Skip]
    ) -> bool:
        if self.allow_weekends or date.weekday() <= 4:
            return False

        skips.append(Skip(
            date,
            "weekend",
            ordered
        ))

        return True

    def _should_skip_holidays(
        self,
        date: datetime.date,
        ordered: bool,
        skips: typing.List[Skip]
    ) -> bool:
        from .data.holidays import holidays

        if self.allow_holidays or date not in holidays:
            return False

        skips.append(Skip(
            date,
            "holiday",
            ordered
        ))

        return True

    def __next__(self):
        skips: typing.List[Skip] = []

        while self._date <= self.end:
            date = datetime.date.fromisoformat(str(self._date))
            self._date += datetime.timedelta(days=1)

            ordered = date in self.order_dates

            if self.closable:
                if self._should_skip_weekends(date, ordered, skips):
                    continue

                if self._should_skip_holidays(date, ordered, skips):
                    continue

            return date, ordered, skips

        raise StopIteration
