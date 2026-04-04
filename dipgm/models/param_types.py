import click
import re
from datetime import timedelta

class TimeDeltaType(click.ParamType):
    name = "duration"

    def convert(self, value, param, ctx) -> timedelta:
        try:
            # --- HH:MM or HH:MM:SS ---
            if ":" in value:
                parts = value.split(":")
                if len(parts) not in (2, 3):
                    raise ValueError

                parts = list(map(int, parts))

                if len(parts) == 2:
                    hours, minutes = parts
                    seconds = 0
                else:
                    hours, minutes, seconds = parts

                if not (0 <= minutes < 60 and 0 <= seconds < 60):
                    raise ValueError

                return timedelta(hours=hours, minutes=minutes, seconds=seconds)

            # --- compact formats like 2h15m, 90m, etc. ---
            pattern = r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$"
            match = re.fullmatch(pattern, value)

            if match:
                h, m, s = match.groups()
                if h is None and m is None and s is None:
                    raise ValueError

                return timedelta(
                    hours=int(h) if h else 0,
                    minutes=int(m) if m else 0,
                    seconds=int(s) if s else 0,
                )

            raise ValueError

        except ValueError:
            self.fail(
                f"{value!r} is not a valid duration "
                "(use HH:MM, HH:MM:SS, or forms like 2h15m, 90m)",
                param,
                ctx,
            )


TIMEDELTA = TimeDeltaType()