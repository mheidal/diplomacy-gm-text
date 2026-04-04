
from dataclasses import dataclass
import datetime
import uuid


@dataclass
class ScheduledCommand:
    offset: datetime.timedelta
    command: str
    uuid: uuid.UUID