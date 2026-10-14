MINUTES_PER_DAY = 24 * 60
START_MINUTES = 8 * 60
NIGHT_START_HOUR = 21
NIGHT_END_HOUR = 5


def hour_of(minutes: int) -> int:
    return (minutes % MINUTES_PER_DAY) // 60


def day_of(minutes: int) -> int:
    return minutes // MINUTES_PER_DAY + 1


def is_night(hour: int) -> bool:
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def phase_name(hour: int) -> str:
    if is_night(hour):
        return "Night"
    if hour < 12:
        return "Morning"
    if hour < 18:
        return "Afternoon"
    return "Evening"


def format_clock(minutes: int) -> str:
    minute_of_day = minutes % MINUTES_PER_DAY
    return (
        f"Day {day_of(minutes)}, {minute_of_day // 60:02d}:{minute_of_day % 60:02d}"
        f" ({phase_name(hour_of(minutes))})"
    )


def minutes_until_hour(minutes: int, target_hour: int) -> int:
    """Minutes from now until the next time the clock reads target_hour:00."""
    remaining = (target_hour * 60 - minutes % MINUTES_PER_DAY) % MINUTES_PER_DAY
    return remaining or MINUTES_PER_DAY
