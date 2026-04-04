import click
from datetime import timedelta

class TimeDeltaType(click.ParamType):
    name = "HH:MM"

    def convert(self, value, param, ctx):
        try:
            parts = value.split(":")
            if len(parts) != 2:
                raise ValueError

            hours, minutes = map(int, parts)

            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError

            return timedelta(hours=hours, minutes=minutes)

        except ValueError:
            self.fail(f"{value!r} is not a valid time in HH:MM format", param, ctx)


TIMEDELTA = TimeDeltaType()