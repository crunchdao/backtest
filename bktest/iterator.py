import dataclasses
import datetime
import typing

from .data.holidays import HolidayProvider, LegacyHolidayProvider


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
        holiday_provider: HolidayProvider = LegacyHolidayProvider(),
        allow_weekends=False,
        allow_holidays=False,
    ):
        self.start = start
        self.end = end
        self.closable = closable
        self.order_dates = order_dates
        self.holiday_provider = holiday_provider
        self.allow_weekends = allow_weekends
        self.allow_holidays = allow_holidays

        self._date = None

    def should_skip_weekends(
        self,
        date: datetime.date,
        ordered: bool
    ) -> typing.Union[bool, Skip]:
        if self.allow_weekends or date.weekday() <= 4:
            return False

        return Skip(
            date,
            "weekend",
            ordered
        )

    def should_skip_holidays(
        self,
        date: datetime.date,
        ordered: bool
    ) -> typing.Union[bool, Skip]:
        if self.allow_holidays or not self.holiday_provider.is_holiday(date):
            return False

        return Skip(
            date,
            "holiday",
            ordered
        )
