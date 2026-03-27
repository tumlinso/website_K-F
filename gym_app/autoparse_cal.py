from pathlib import Path
import os

import pandas as pd
from icalendar import Calendar
from datetime import datetime, timezone, timedelta
from recurring_ical_events import of as recurring_events
import requests

BASE_DIR = Path(__file__).resolve().parents[1]
ics_address_webcal = "https://calendar.google.com/calendar/ical/fcpabteilung16%40gmail.com/public/basic.ics"
internal_ics_path = BASE_DIR / "gym_app" / "static" / "ics" / "calendar.ics"
processed_csv_path = BASE_DIR / "gym_app" / "static" / "ics" / "processed_calendar.csv"

person_map = {
    'Geöffnet - ohne Trainer': ['Geöffnet - ohne Trainer', 'geöffnet ohne Trainer', 'trainerfreie Zeit', 'n. N.', 'N.n.', 'N.N.', 'Geöffnet -ohne Trainer', 'geöffnet - ohne Trainer', 'N.N'],
    'Felix Gansmeier': ['Felix G.', 'Felix G'],
    'Thomas Gansmeier': ['Thomas G.', 'Thomas G', 'Thomas'],
    'Jonah Wodarz': ['Jonah', 'Jonah W.'],
    'Tobi Fraunholz': ['Tobi'],
    'Emma Lehner': ['Emma', 'Emma L.'],
    'Felix Blumenschein': ['Felix B.', 'Felix B', 'Fellix', 'Felix'],
    'Britta Schneider' : ['Britta', 'Laurenz o. Britta', 'Britta S.'],
    'Laurenz Schneider': ['Laurenz', 'Laurenz S.'],
    'Linus Schneider': ['Linus', 'Linus S.'],
    'Tassilo Friedrich': ['Tassilo', 'Tassilo F.'],
    'Elisabeth Sandler': ['Elisabeth', 'Elisbeth'],
    'Richard Leger' : ['Richie', 'Richi'],
    'Gavin Tumlinson': ['Gavin'],
    'Xander Tumlinson': ['Xander'],
    'Felix Kameritsch': ['Felix K.', 'Felix K'],
    'Maxi Kameritsch': ['Maxi', 'Maxi K.'],
    'Fabian Vogt': ['Fabian', 'Fabian V.', 'Fabi'],
    'Jo Mittermeier': ['Jo'],
    'Angela Mittermeier': ['Angela'],
    'Isabelle Noll' : ['Isabelle', 'Isa'],
    'Ines Drescher' : ['Ines'],
    'Karin Sikora' : ['Karin'],
    'Gisela Lehner' : ['Gisela'],
    'Vincent Schweigler' : ['Vincent'],
    'Korbinian Biermeier': ['Korbi', 'Korbinian', 'Körbchen'],
    'Jaro Woyack' : ['Jaro'],
    'Gabriela Baum' : ['Gabi', 'Gabriela'],
    'Dominic Müller' : ['Dominic', 'Domi', 'Dominik'],
    'Shkelqim Istrefi' : ['Shkelqim', 'Shkeli'],
    'Thorsten Straub' : ['Thorsten', 'Thosten']
}

drop_keys_caseless = [
    'abwesend',
    'nicht mehr',
    'bauarbeit',
    'bgkv',
    'Geburtsag',
    'abwesenheit',
    'Delegierten',
    'Lehrgang',
    'zoom',
    'klos',
    'lockdown',
    'Corona',
    'schichten',
    'elternzeit',
    'fortbildung',
    'ferien',
    'abteilung',
    '0000',
    'quarantäne',
    'isolation',
    'praktikum',
    'geräte',
    'Urlaub',
    'studio',
    'prüfung',
    'sperrt',
    ' AU', 
    'geschlossen',
    'Geburtstag',
    'feier'
    ]

drop_keys_cased = [
    'ET ',
    'TP ', 
    ' ET',
    ' TP',
]

def download_web_calendar_ics(ics_address_webcal, save_path=internal_ics_path):
    try:
        response = requests.get(ics_address_webcal, timeout=10)
        response.raise_for_status()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Calendar downloaded and saved to {save_path}")
        return True
    except Exception as e:
        print(f"Error downloading calendar: {e}")
        return False

def _get_sync_interval_seconds():
    return int(os.getenv("TRAINER_CALENDAR_SYNC_INTERVAL_SECONDS", "1800"))


def _get_parse_window_days():
    lookback_days = int(os.getenv("TRAINER_CALENDAR_SYNC_PAST_DAYS", "2"))
    lookahead_days = int(os.getenv("TRAINER_CALENDAR_SYNC_FUTURE_DAYS", "21"))
    return lookback_days, lookahead_days


def _file_is_fresh(path, max_age_seconds):
    path = Path(path)
    if not path.exists():
        return False
    file_age_seconds = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return file_age_seconds < max_age_seconds


def parse_ics_file(internal_ics_path, start_date=None, end_date=None, lookback_days=None, lookahead_days=None):
    if start_date is None or end_date is None:
        default_lookback_days, default_lookahead_days = _get_parse_window_days()
        if lookback_days is None:
            lookback_days = default_lookback_days
        if lookahead_days is None:
            lookahead_days = default_lookahead_days

        now = datetime.now(timezone.utc)
        if start_date is None:
            start_date = now - timedelta(days=lookback_days)
        if end_date is None:
            end_date = now + timedelta(days=lookahead_days)

    with Path(internal_ics_path).open("r", encoding="utf-8") as f:
        calendar = Calendar.from_ical(f.read())
    
    events = []
    flattened = recurring_events(calendar).between(start_date, end_date)

    for component in flattened:
        if component.name == "VEVENT":
            event = {}
            if component.get("status") == "CANCELLED": continue

            event['name'] = str(component.get('summary'))
            event['start'] = component.get('dtstart').dt
            event['end'] = component.get('dtend').dt
            events.append(event)
    
    df = pd.DataFrame(events)

    for col in ['start', 'end']:
        df[col] = pd.to_datetime(df[col], utc=True, errors='coerce')
    df['name'] = df['name'].str.strip()

    return df

def drop_all_day_events(df):
    df = df[(df['start'].dt.time != datetime.min.time()) &
                          (df['end'].dt.time != datetime.min.time())]
    return df

def drop_irrelevant_events(df):
    pattern_caseless = '|'.join(drop_keys_caseless)
    filter_mask = df['name'].str.contains(pattern_caseless, case=False, na=False)
    pattern_cased = '|'.join(drop_keys_cased)
    filter_mask_cased = df['name'].str.contains(pattern_cased, case=True, na=False)
    filter_mask = filter_mask | filter_mask_cased
    df = df[~filter_mask]
    return df

def drop_invalid(df, person_map, column_name='name'):
    valid_names = list(person_map.keys())
    df = df[df[column_name].isin(valid_names)]
    return df

def alias_person(df, person_map, column_name='name'):
    for main_name, aliases in person_map.items():
        for alias in aliases:
            df.loc[df[column_name] == alias, column_name] = main_name
    return df

def process_calendar_df(df, person_map, column_name='name'):
    df = drop_all_day_events(df)
    df = drop_irrelevant_events(df)
    df = alias_person(df, person_map, column_name=column_name)
    df = drop_invalid(df, person_map, column_name=column_name)
    return df

def save_to_csv(df, path=processed_csv_path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def load_processed_calendar_csv(path=processed_csv_path):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["name", "start", "end"])

    df = pd.read_csv(path, parse_dates=["start", "end"])
    for col in ["start", "end"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    return df

def sync_calendar(
        ics_address_webcal = ics_address_webcal,
        internal_ics_path = internal_ics_path,
        person_map = person_map,
        processed_csv = processed_csv_path,
        sync_interval_seconds = None,
        lookback_days = None,
        lookahead_days = None,
        ):
    if sync_interval_seconds is None:
        sync_interval_seconds = _get_sync_interval_seconds()

    if _file_is_fresh(processed_csv, sync_interval_seconds):
        return load_processed_calendar_csv(processed_csv)

    download_ok = download_web_calendar_ics(ics_address_webcal, internal_ics_path)
    if not download_ok:
        if Path(processed_csv).exists():
            return load_processed_calendar_csv(processed_csv)
        if not Path(internal_ics_path).exists():
            raise RuntimeError(
                f"Could not download the ICS feed and no local file exists at {internal_ics_path}"
            )

    df = parse_ics_file(
        internal_ics_path,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )
    if df.empty:
        save_to_csv(df, processed_csv)
        return df

    df = process_calendar_df(df, person_map)
    save_to_csv(df, processed_csv)
    return df

if __name__ == "__main__":
    df = sync_calendar()
    print(df)
    print(f"Processed calendar saved to {BASE_DIR / 'gym_app' / 'static' / 'ics' / 'processed_calendar.csv'}")
