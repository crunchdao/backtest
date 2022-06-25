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
    
    # Only when ordered
    total_fees: float = 0.0
    success_count: int = 0
    failed_count: int = 0
    
    @property
    def holding_count(self) -> int:
        return len(self.holdings)
    
