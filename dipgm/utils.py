from datetime import timedelta
import re

def convert_string_to_timedelta(value: str) -> timedelta:
    value = "".join(value)
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
    pattern = r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, value)

    if match:
        d, h, m, s = match.groups()
        if d is None and h is None and m is None and s is None:
            raise ValueError

        return timedelta(
            days=int(d) if d else 0,
            hours=int(h) if h else 0,
            minutes=int(m) if m else 0,
            seconds=int(s) if s else 0,
        )

    raise ValueError