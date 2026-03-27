from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .autoparse_cal import load_processed_calendar_csv, sync_calendar
from .trainer_profiles import (
    get_trainer_display_name,
    get_trainer_palette,
    is_trainer_free,
)


CALENDAR_CACHE_KEY = "gym_app_trainer_calendar_days"
CALENDAR_CACHE_SECONDS = 300
CALENDAR_DAY_START_HOUR = 6
CALENDAR_DAY_END_HOUR = 22
CALENDAR_DAY_TOTAL_MINUTES = (CALENDAR_DAY_END_HOUR - CALENDAR_DAY_START_HOUR) * 60

WEEKDAY_NAMES = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}


def _minutes_since_calendar_start(hour: int, minute: int) -> int:
    return (hour * 60 + minute) - (CALENDAR_DAY_START_HOUR * 60)


def get_trainer_calendar_time_markers() -> list[dict[str, object]]:
    markers = []
    for hour in range(CALENDAR_DAY_START_HOUR, CALENDAR_DAY_END_HOUR + 1, 2):
        position = ((hour - CALENDAR_DAY_START_HOUR) * 60 / CALENDAR_DAY_TOTAL_MINUTES) * 100
        markers.append(
            {
                "label": f"{hour:02d}:00",
                "position_percent": round(position, 3),
            }
        )
    return markers


def _load_calendar_df():
    try:
        return sync_calendar()
    except Exception:
        return load_processed_calendar_csv()


def get_trainer_calendar_days(limit_days: int = 10) -> list[dict[str, object]]:
    cache_key = f"{CALENDAR_CACHE_KEY}_{limit_days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    df = _load_calendar_df()
    if df.empty:
        cache.set(cache_key, [], CALENDAR_CACHE_SECONDS)
        return []

    tz = ZoneInfo(settings.GYM_TIMEZONE)
    now = timezone.now().astimezone(tz)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=limit_days)

    df = df.dropna(subset=["start", "end"]).sort_values("start")

    grouped_events: dict[object, list[dict[str, object]]] = defaultdict(list)

    for row in df.itertuples(index=False):
        start = row.start.to_pydatetime().astimezone(tz)
        end = row.end.to_pydatetime().astimezone(tz)

        if end < window_start or start >= window_end:
            continue

        trainer_name = str(row.name).strip()
        palette = get_trainer_palette(trainer_name)

        start_minutes = max(0, _minutes_since_calendar_start(start.hour, start.minute))
        end_minutes = min(
            CALENDAR_DAY_TOTAL_MINUTES,
            _minutes_since_calendar_start(end.hour, end.minute),
        )
        duration_minutes = max(60, end_minutes - start_minutes)

        grouped_events[start.date()].append(
            {
                "trainer_name": get_trainer_display_name(trainer_name),
                "time_label": f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')} Uhr",
                "start_iso": start.isoformat(),
                "end_iso": end.isoformat(),
                "accent": palette["accent"],
                "text": palette["text"],
                "is_trainer_free": is_trainer_free(trainer_name),
                "top_percent": round((start_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
                "height_percent": round((duration_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
            }
        )

    days = []
    for event_date in sorted(grouped_events.keys()):
        days.append(
            {
                "iso_date": event_date.isoformat(),
                "weekday": WEEKDAY_NAMES[event_date.weekday()],
                "date_label": event_date.strftime("%d.%m.%Y"),
                "is_today": event_date == now.date(),
                "events": grouped_events[event_date],
            }
        )

    cache.set(cache_key, days, CALENDAR_CACHE_SECONDS)
    return days
