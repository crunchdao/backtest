import dataclasses
import datetime
import typing


@dataclasses.dataclass()
class Snapshot:
    
    date: datetime.date
    postponned: typing.Optional[datetime.date]
    cash: float
    equity: float
    holdings: typing.List["Holding"]
    ordered: bool
    equity_long: float
    nav: float
    
    # Only when ordered
    total_fees: float = 0.0
    success_count: int = 0
    failed_count: int = 0
    
    # None if `--auto-close` is not specified
    closed_count: int = None
    closed_total: int = None
    
    @property
    def holding_count(self) -> int:
        return len(self.holdings)
    
    @property
    def real_date(self) -> datetime.date:
        return self.postponned if self.postponned else self.date
