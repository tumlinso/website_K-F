from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from hashlib import md5
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .autoparse_cal import load_processed_calendar_csv, sync_calendar


CALENDAR_CACHE_KEY = "gym_app_trainer_calendar_days"
CALENDAR_CACHE_SECONDS = 300
NO_TRAINER_LABEL = "Geoeffnet - ohne Trainer"

WEEKDAY_NAMES = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}


def _normalize_name(name: str) -> str:
    return (
        str(name)
        .replace("ö", "oe")
        .replace("Ö", "Oe")
        .replace("ä", "ae")
        .replace("Ä", "Ae")
        .replace("ü", "ue")
        .replace("Ü", "Ue")
        .strip()
    )


def _trainer_palette(name: str) -> dict[str, str]:
    normalized = _normalize_name(name)
    if normalized == NO_TRAINER_LABEL:
        return {
            "accent": "#4f535a",
            "soft": "#ececef",
            "text": "#111111",
        }

    hue = int(md5(normalized.encode("utf-8")).hexdigest()[:6], 16) % 360
    return {
        "accent": f"hsl({hue} 68% 44%)",
        "soft": f"hsl({hue} 72% 93%)",
        "text": "#111111",
    }


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
        palette = _trainer_palette(trainer_name)

        grouped_events[start.date()].append(
            {
                "trainer_name": trainer_name,
                "time_label": f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')} Uhr",
                "start_iso": start.isoformat(),
                "end_iso": end.isoformat(),
                "accent": palette["accent"],
                "soft": palette["soft"],
                "text": palette["text"],
                "is_trainer_free": _normalize_name(trainer_name) == NO_TRAINER_LABEL,
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
