from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from django.conf import settings
from django.core.cache import cache


OPENING_HOURS = {
    0: (time(6, 30), time(22, 0)),
    1: (time(8, 30), time(22, 0)),
    2: (time(6, 30), time(22, 0)),
    3: (time(8, 30), time(22, 0)),
    4: (time(6, 30), time(22, 0)),
    5: (time(13, 0), time(17, 30)),
    6: (time(10, 0), time(14, 30)),
}

WEEKDAY_NAMES = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def get_home_live_status(now: datetime | None = None) -> dict[str, object]:
    gym_timezone = ZoneInfo(settings.GYM_TIMEZONE)
    current_time = now.astimezone(gym_timezone) if now else datetime.now(gym_timezone)

    open_status = _build_open_status(current_time)
    trainer_status = _build_trainer_status(current_time)
    return {**open_status, **trainer_status}


def _build_open_status(current_time: datetime) -> dict[str, object]:
    hours = OPENING_HOURS.get(current_time.weekday())
    if hours:
        opens_at = current_time.replace(
            hour=hours[0].hour,
            minute=hours[0].minute,
            second=0,
            microsecond=0,
        )
        closes_at = current_time.replace(
            hour=hours[1].hour,
            minute=hours[1].minute,
            second=0,
            microsecond=0,
        )
        if opens_at <= current_time < closes_at:
            return {
                "is_open": True,
                "status_label": "Jetzt geöffnet",
                "status_detail": f"Heute bis {closes_at.strftime('%H:%M')} Uhr",
            }

    next_opening = _get_next_opening(current_time)
    return {
        "is_open": False,
        "status_label": "Derzeit geschlossen",
        "status_detail": _format_next_opening_text(current_time, next_opening),
    }


def _build_trainer_status(current_time: datetime) -> dict[str, str]:
    calendar_url = settings.TRAINER_CALENDAR_ICS_URL
    if not calendar_url:
        return {
            "trainer_name": "Kalender noch nicht verbunden",
            "trainer_detail": "Google-Kalender-ICS-URL hinterlegen, damit hier der aktuelle Trainer live erscheint.",
        }

    current_event = _get_current_calendar_event(current_time)
    if current_event:
        return {
            "trainer_name": _clean_event_summary(current_event["summary"]),
            "trainer_detail": f"Im Kalender bis {current_event['end'].strftime('%H:%M')} Uhr eingetragen.",
        }

    next_event = _get_next_calendar_event(current_time)
    if next_event:
        return {
            "trainer_name": "Aktuell kein Trainertermin",
            "trainer_detail": _format_next_event_text(current_time, next_event),
        }

    return {
        "trainer_name": "Kein Kalendereintrag gefunden",
        "trainer_detail": "Der Kalender ist verbunden, liefert aktuell aber keinen Trainereinsatz.",
    }


def _get_next_opening(current_time: datetime) -> datetime:
    for day_offset in range(0, 8):
        candidate_date = (current_time + timedelta(days=day_offset)).date()
        weekday = candidate_date.weekday()
        if weekday not in OPENING_HOURS:
            continue

        opening_time, _ = OPENING_HOURS[weekday]
        opening_datetime = datetime.combine(candidate_date, opening_time, tzinfo=current_time.tzinfo)
        if opening_datetime > current_time:
            return opening_datetime

    return current_time


def _format_next_opening_text(current_time: datetime, next_opening: datetime) -> str:
    if next_opening.date() == current_time.date():
        return f"Öffnet heute um {next_opening.strftime('%H:%M')} Uhr"
    if next_opening.date() == (current_time + timedelta(days=1)).date():
        return f"Öffnet morgen um {next_opening.strftime('%H:%M')} Uhr"
    weekday_name = WEEKDAY_NAMES[next_opening.weekday()]
    return f"Öffnet {weekday_name} um {next_opening.strftime('%H:%M')} Uhr"


def _format_next_event_text(current_time: datetime, event: dict[str, object]) -> str:
    event_start = event["start"]
    if event_start.date() == current_time.date():
        return f"Nächster Eintrag heute ab {event_start.strftime('%H:%M')} Uhr: {_clean_event_summary(event['summary'])}"
    if event_start.date() == (current_time + timedelta(days=1)).date():
        return f"Nächster Eintrag morgen ab {event_start.strftime('%H:%M')} Uhr: {_clean_event_summary(event['summary'])}"
    weekday_name = WEEKDAY_NAMES[event_start.weekday()]
    return f"Nächster Eintrag {weekday_name} ab {event_start.strftime('%H:%M')} Uhr: {_clean_event_summary(event['summary'])}"


def _get_current_calendar_event(current_time: datetime) -> dict[str, object] | None:
    active_events = []
    for event in _get_calendar_events():
        current_occurrence = _get_current_occurrence(event, current_time)
        if current_occurrence:
            active_events.append(current_occurrence)

    if not active_events:
        return None
    return min(active_events, key=lambda item: item["end"])


def _get_next_calendar_event(current_time: datetime) -> dict[str, object] | None:
    next_events = []
    for event in _get_calendar_events():
        next_occurrence = _get_next_occurrence(event, current_time)
        if next_occurrence:
            next_events.append(next_occurrence)

    if not next_events:
        return None
    return min(next_events, key=lambda item: item["start"])


def _get_calendar_events() -> list[dict[str, object]]:
    cache_key = "gym_app_live_status_calendar_events"
    cached_events = cache.get(cache_key)
    if cached_events is not None:
        return cached_events

    calendar_url = settings.TRAINER_CALENDAR_ICS_URL
    if not calendar_url:
        return []

    request = Request(
        calendar_url,
        headers={"User-Agent": "KPlusFFitnessstudio/1.0"},
    )

    try:
        with urlopen(request, timeout=settings.TRAINER_CALENDAR_TIMEOUT_SECONDS) as response:
            calendar_text = response.read().decode("utf-8")
    except (URLError, TimeoutError, ValueError):
        cache.set(cache_key, [], settings.LIVE_STATUS_CACHE_SECONDS)
        return []

    try:
        events = _parse_ics_events(calendar_text, ZoneInfo(settings.GYM_TIMEZONE))
    except (ValueError, KeyError):
        cache.set(cache_key, [], settings.LIVE_STATUS_CACHE_SECONDS)
        return []

    cache.set(cache_key, events, settings.LIVE_STATUS_CACHE_SECONDS)
    return events


def _parse_ics_events(calendar_text: str, default_timezone: ZoneInfo) -> list[dict[str, object]]:
    unfolded_lines = _unfold_ics_lines(calendar_text)
    events = []
    current_event_lines: list[str] = []
    inside_event = False

    for line in unfolded_lines:
        if line == "BEGIN:VEVENT":
            inside_event = True
            current_event_lines = []
            continue
        if line == "END:VEVENT":
            inside_event = False
            parsed_event = _parse_event(current_event_lines, default_timezone)
            if parsed_event:
                events.append(parsed_event)
            continue
        if inside_event:
            current_event_lines.append(line)

    return events


def _unfold_ics_lines(calendar_text: str) -> list[str]:
    unfolded_lines: list[str] = []
    for raw_line in calendar_text.splitlines():
        line = raw_line.rstrip("\r")
        if line.startswith((" ", "\t")) and unfolded_lines:
            unfolded_lines[-1] += line[1:]
        else:
            unfolded_lines.append(line)
    return unfolded_lines


def _parse_event(event_lines: list[str], default_timezone: ZoneInfo) -> dict[str, object] | None:
    event_data: dict[str, object] = {"exdates": []}

    for line in event_lines:
        property_name, params, value = _parse_property(line)

        if property_name == "RECURRENCE-ID":
            return None
        if property_name == "SUMMARY":
            event_data["summary"] = _unescape_ical_text(value)
        elif property_name == "DTSTART":
            event_data["start"] = _parse_ics_datetime(value, params, default_timezone)
        elif property_name == "DTEND":
            event_data["end"] = _parse_ics_datetime(value, params, default_timezone)
        elif property_name == "RRULE":
            event_data["rrule"] = value
        elif property_name == "EXDATE":
            event_data["exdates"].extend(_parse_ics_datetime_list(value, params, default_timezone))

    if "start" not in event_data or "end" not in event_data:
        return None

    duration = event_data["end"] - event_data["start"]
    if duration <= timedelta(0):
        return None

    return {
        "summary": event_data.get("summary", "Trainer laut Kalender"),
        "start": event_data["start"],
        "end": event_data["end"],
        "duration": duration,
        "rrule": event_data.get("rrule"),
        "exdates": event_data["exdates"],
    }


def _parse_property(line: str) -> tuple[str, dict[str, str], str]:
    property_blob, value = line.split(":", 1)
    parts = property_blob.split(";")
    property_name = parts[0].upper()
    params = {}

    for param_blob in parts[1:]:
        if "=" not in param_blob:
            continue
        key, param_value = param_blob.split("=", 1)
        params[key.upper()] = param_value

    return property_name, params, value


def _parse_ics_datetime_list(
    value: str,
    params: dict[str, str],
    default_timezone: ZoneInfo,
) -> list[datetime]:
    return [
        _parse_ics_datetime(item, params, default_timezone)
        for item in value.split(",")
        if item
    ]


def _parse_ics_datetime(
    value: str,
    params: dict[str, str],
    default_timezone: ZoneInfo,
) -> datetime:
    timezone_name = params.get("TZID")
    value_type = params.get("VALUE")

    if value_type == "DATE" or len(value) == 8:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=default_timezone)

    if value.endswith("Z"):
        return _parse_datetime_with_formats(
            value,
            ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%MZ"),
            timezone.utc,
        ).astimezone(default_timezone)

    event_timezone = ZoneInfo(timezone_name) if timezone_name else default_timezone
    return _parse_datetime_with_formats(
        value,
        ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"),
        event_timezone,
    )


def _parse_datetime_with_formats(value: str, formats: tuple[str, ...], tzinfo) -> datetime:
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).replace(tzinfo=tzinfo)
        except ValueError:
            continue
    raise ValueError(f"Unsupported ICS datetime value: {value}")


def _get_current_occurrence(event: dict[str, object], current_time: datetime) -> dict[str, object] | None:
    if not event["rrule"]:
        if event["start"] <= current_time < event["end"]:
            return {
                "summary": event["summary"],
                "start": event["start"],
                "end": event["end"],
            }
        return None

    rule = rrulestr(str(event["rrule"]), dtstart=event["start"])
    occurrence_start = rule.before(current_time, inc=True)
    if occurrence_start is None:
        return None

    occurrence_start = _ensure_timezone(occurrence_start, event["start"].tzinfo)
    if _is_excluded(occurrence_start, event["exdates"]):
        return None

    occurrence_end = occurrence_start + event["duration"]
    if occurrence_start <= current_time < occurrence_end:
        return {
            "summary": event["summary"],
            "start": occurrence_start,
            "end": occurrence_end,
        }
    return None


def _get_next_occurrence(event: dict[str, object], current_time: datetime) -> dict[str, object] | None:
    if not event["rrule"]:
        if event["start"] > current_time:
            return {
                "summary": event["summary"],
                "start": event["start"],
                "end": event["end"],
            }
        return None

    rule = rrulestr(str(event["rrule"]), dtstart=event["start"])
    occurrence_start = rule.after(current_time, inc=False)
    attempts = 0

    while occurrence_start is not None and attempts < 20:
        occurrence_start = _ensure_timezone(occurrence_start, event["start"].tzinfo)
        if not _is_excluded(occurrence_start, event["exdates"]):
            return {
                "summary": event["summary"],
                "start": occurrence_start,
                "end": occurrence_start + event["duration"],
            }
        occurrence_start = rule.after(occurrence_start, inc=False)
        attempts += 1

    return None


def _ensure_timezone(value: datetime, tzinfo) -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=tzinfo)


def _is_excluded(candidate_start: datetime, excluded_starts: list[datetime]) -> bool:
    for excluded_start in excluded_starts:
        if abs((candidate_start - excluded_start).total_seconds()) < 1:
            return True
    return False


def _unescape_ical_text(value: str) -> str:
    return (
        value.replace("\\\\", "\\")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\n", " ")
        .replace("\\N", " ")
    )


def _clean_event_summary(summary: str) -> str:
    cleaned_summary = summary.strip()
    for prefix in ("Trainer:", "trainer:", "Coach:", "coach:"):
        if cleaned_summary.startswith(prefix):
            return cleaned_summary[len(prefix):].strip()
    return cleaned_summary
