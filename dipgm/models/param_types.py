from typing import Optional

import click
import re
from datetime import timedelta

from dipgm.utils import convert_string_to_timedelta

class TimeDeltaType(click.ParamType):
    name = "duration"

    def convert(self, value, param, ctx) -> Optional[timedelta]:
        try:
            return convert_string_to_timedelta(value)

        except ValueError:
            self.fail(
                f"{value!r} is not a valid duration "
                "(use HH:MM, HH:MM:SS, or forms like 2h15m, 90m)",
                param,
                ctx,
            )
            return None


TIMEDELTA = TimeDeltaType()