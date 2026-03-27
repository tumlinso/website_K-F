from __future__ import annotations

from hashlib import md5

from .autoparse_cal import person_map


NO_TRAINER_LABEL = "Geoeffnet - ohne Trainer"

BRIGHT_FALLBACK_COLORS = [
    "#55d6ff",
    "#ffb347",
    "#8ce99a",
    "#ff8fab",
    "#6c9cff",
    "#36d399",
    "#ffcb77",
    "#a78bfa",
    "#4dd7c0",
    "#ff9f68",
    "#83e377",
    "#f9a8d4",
    "#38bdf8",
    "#ffd166",
    "#5eead4",
    "#fca5a5",
    "#93c5fd",
    "#bef264",
    "#fdba74",
    "#67e8f9",
    "#f0abfc",
    "#7dd3fc",
    "#c4b5fd",
    "#86efac",
    "#fcd34d",
    "#fb7185",
    "#22d3ee",
    "#a3e635",
    "#fda4af",
    "#2dd4bf",
    "#fde68a",
    "#60a5fa",
    "#34d399",
    "#f9a8d4",
]

TRAINER_COLOR_OVERRIDES = {
    NO_TRAINER_LABEL: "#9ca3af",
    "Felix Blumenschein": "#ff6f61",
    "Richard Leger": "#6ee7b7",
    "Gavin Tumlinson": "#ffe34d",
    "Xander Tumlinson": "#2e8b57",
    "Korbinian Biermeier": "#ff4fa3",
}

_CANONICAL_NAMES = list(person_map.keys())


def normalize_trainer_name(name: str) -> str:
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


def strip_trainer_prefix(name: str) -> str:
    cleaned_name = str(name).strip()
    for prefix in ("Trainer:", "trainer:", "Coach:", "coach:"):
        if cleaned_name.startswith(prefix):
            return cleaned_name[len(prefix):].strip()
    return cleaned_name


def _build_alias_lookup() -> dict[str, str]:
    alias_lookup: dict[str, str] = {}
    for canonical_name, aliases in person_map.items():
        alias_lookup[normalize_trainer_name(canonical_name)] = canonical_name
        for alias in aliases:
            alias_lookup[normalize_trainer_name(alias)] = canonical_name
    return alias_lookup


_ALIAS_LOOKUP = _build_alias_lookup()


def canonicalize_trainer_name(name: str) -> str:
    cleaned_name = strip_trainer_prefix(name)
    if not cleaned_name:
        return ""
    normalized_name = normalize_trainer_name(cleaned_name)
    return _ALIAS_LOOKUP.get(normalized_name, cleaned_name)


def _build_first_name_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for canonical_name in _CANONICAL_NAMES:
        normalized_name = normalize_trainer_name(canonical_name)
        if normalized_name == NO_TRAINER_LABEL:
            continue
        first_name = canonical_name.split()[0]
        normalized_first_name = normalize_trainer_name(first_name)
        counts[normalized_first_name] = counts.get(normalized_first_name, 0) + 1
    return counts


_FIRST_NAME_COUNTS = _build_first_name_counts()


def get_trainer_display_name(name: str) -> str:
    canonical_name = canonicalize_trainer_name(name)
    normalized_name = normalize_trainer_name(canonical_name)

    if not canonical_name:
        return ""
    if normalized_name == NO_TRAINER_LABEL:
        return "Ohne Trainer"

    name_parts = canonical_name.split()
    first_name = name_parts[0]
    if len(name_parts) == 1:
        return first_name

    if _FIRST_NAME_COUNTS.get(normalize_trainer_name(first_name), 0) > 1:
        return f"{first_name} {name_parts[-1][0]}."
    return first_name


def _pick_text_color(background_hex: str) -> str:
    color_value = background_hex.lstrip("#")
    red = int(color_value[0:2], 16)
    green = int(color_value[2:4], 16)
    blue = int(color_value[4:6], 16)
    luminance = ((0.299 * red) + (0.587 * green) + (0.114 * blue)) / 255
    return "#111111" if luminance > 0.63 else "#f8f8f8"


def _build_palette_lookup() -> dict[str, dict[str, str]]:
    palette_lookup: dict[str, dict[str, str]] = {}
    fallback_index = 0

    for canonical_name in sorted(_CANONICAL_NAMES, key=normalize_trainer_name):
        if canonical_name in TRAINER_COLOR_OVERRIDES:
            accent = TRAINER_COLOR_OVERRIDES[canonical_name]
        else:
            accent = BRIGHT_FALLBACK_COLORS[fallback_index % len(BRIGHT_FALLBACK_COLORS)]
            fallback_index += 1

        palette_lookup[normalize_trainer_name(canonical_name)] = {
            "accent": accent,
            "text": _pick_text_color(accent),
        }

    return palette_lookup


_PALETTE_LOOKUP = _build_palette_lookup()


def get_trainer_palette(name: str) -> dict[str, str]:
    canonical_name = canonicalize_trainer_name(name)
    normalized_name = normalize_trainer_name(canonical_name)

    if normalized_name in _PALETTE_LOOKUP:
        return _PALETTE_LOOKUP[normalized_name]

    accent = BRIGHT_FALLBACK_COLORS[int(md5(normalized_name.encode("utf-8")).hexdigest()[:6], 16) % len(BRIGHT_FALLBACK_COLORS)]
    return {
        "accent": accent,
        "text": _pick_text_color(accent),
    }


def is_trainer_free(name: str) -> bool:
    return normalize_trainer_name(canonicalize_trainer_name(name)) == NO_TRAINER_LABEL
