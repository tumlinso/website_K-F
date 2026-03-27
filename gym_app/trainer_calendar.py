from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .autoparse_cal import load_processed_calendar_csv, sync_calendar
from .live_status import OPENING_HOURS
from .trainer_profiles import (
    get_trainer_display_name,
    get_trainer_palette,
    is_trainer_free,
)


CALENDAR_CACHE_KEY = "gym_app_trainer_calendar_days"
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


def _build_opening_hours_payload(event_date) -> dict[str, object] | None:
    hours = OPENING_HOURS.get(event_date.weekday())
    if not hours:
        return None

    opens_at, closes_at = hours
    start_minutes = max(0, _minutes_since_calendar_start(opens_at.hour, opens_at.minute))
    end_minutes = min(
        CALENDAR_DAY_TOTAL_MINUTES,
        _minutes_since_calendar_start(closes_at.hour, closes_at.minute),
    )
    duration_minutes = max(0, end_minutes - start_minutes)

    if duration_minutes <= 0:
        return None

    return {
        "opens_label": opens_at.strftime("%H:%M"),
        "closes_label": closes_at.strftime("%H:%M"),
        "top_percent": round((start_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
        "height_percent": round((duration_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
    }


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


def get_trainer_calendar_days(limit_days: int | None = None) -> list[dict[str, object]]:
    if limit_days is None:
        limit_days = settings.TRAINER_CALENDAR_VIEW_DAYS

    cache_key = f"{CALENDAR_CACHE_KEY}_{limit_days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    df = _load_calendar_df()
    if df.empty:
        cache.set(cache_key, [], settings.TRAINER_CALENDAR_CACHE_SECONDS)
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
        if is_trainer_free(trainer_name):
            continue

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
                "top_percent": round((start_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
                "height_percent": round((duration_minutes / CALENDAR_DAY_TOTAL_MINUTES) * 100, 3),
            }
        )

    days = []
    for day_offset in range(limit_days):
        event_date = (window_start + timedelta(days=day_offset)).date()
        days.append(
            {
                "iso_date": event_date.isoformat(),
                "weekday": WEEKDAY_NAMES[event_date.weekday()],
                "date_label": event_date.strftime("%d.%m.%Y"),
                "is_today": event_date == now.date(),
                "events": grouped_events.get(event_date, []),
                "opening_hours": _build_opening_hours_payload(event_date),
            }
        )

    cache.set(cache_key, days, settings.TRAINER_CALENDAR_CACHE_SECONDS)
    return days
