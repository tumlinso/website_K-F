import datetime
import pandas as pd
from icalendar import Calendar, Event
from datetime import datetime, timezone, timedelta
from recurring_ical_events import of as recurring_events
import requests

ics_address_webcal = "https://calendar.google.com/calendar/ical/fcpabteilung16%40gmail.com/public/basic.ics"
internal_ics_path = "gym_app/static/ics/calendar.ics"

person_map = {
    'Trainerfrei': ['Geöffnet - ohne Trainer', 'geöffnet ohne Trainer', 'trainerfreie Zeit', 'n. N.', 'N.n.', 'N.N.', 'Geöffnet -ohne Trainer', 'geöffnet - ohne Trainer', 'N.N'],
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

def alias_person(df, column_name):
    for person, aliases in person_map.items():
        for alias in aliases:
            df[column_name] = df[column_name].str.replace(alias, person, regex=False)
    return df

def download_web_calendar_ics(ics_address_webcal, save_path=internal_ics_path):
    try:
        ics_content = requests.get(ics_address_webcal).text
        with open(save_path, 'w') as f:
            f.write(ics_content)
        print(f"Calendar downloaded and saved to {save_path}")
    except Exception as e:
        print(f"Error downloading calendar: {e}")

# dates since 30 days ago until 30 days in the future
def parse_ics_file(internal_ics_path, start_date=datetime.now(timezone.utc) - timedelta(days=30), end_date=datetime.now(timezone.utc) + timedelta(days=30)):
    with open(internal_ics_path, 'r') as f:
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
    return df

if __name__ == "__main__":
    download_web_calendar_ics(ics_address_webcal)
    df = parse_ics_file(internal_ics_path)
    df = alias_person(df, 'summary')
    print(df)
    
