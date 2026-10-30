import time

import pandas as pd
import requests

BASE = "https://api.openf1.org/v1"


def fetch(query):
    # free OpenF1 tier: max 30 requests per minute so wait 2 s before each one
    for attempt in range(3):
        time.sleep(2.1)
        r = requests.get(f"{BASE}/{query}", timeout=30)
        if r.status_code == 429:  # too many requests: wait longer and retry
            time.sleep(15)
            continue
        if r.status_code == 404:  # OpenF1 answers 404 when there is no data
            return pd.DataFrame()
        if r.status_code == 401:  # OpenF1 locks free access around live F1 sessions
            raise RuntimeError(
                "OpenF1 is locked during live F1 sessions "
                "(30 min before to 30 min after). Try again later."
            )
        r.raise_for_status()
        return pd.DataFrame(r.json())
    raise RuntimeError(f"OpenF1 keeps rate-limiting: {query}")

def _lap_window(session, driver):
    laps = fetch(f"laps?session_key={session}&driver_number={driver}")

    if laps.empty:
        return None, None
    laps = laps.dropna(subset=["lap_duration", "date_start"])
    
    if laps.empty:
        return None, None
    lap = laps.loc[laps["lap_duration"].idxmin()]
    
    start = pd.to_datetime(lap["date_start"], format="ISO8601")
    end = start + pd.Timedelta(seconds=float(lap["lap_duration"]))
    s = start.strftime("%Y-%m-%dT%H:%M:%S")
    e = end.strftime("%Y-%m-%dT%H:%M:%S")
    
    return s, e, float(lap["lap_duration"])

def fastest_lap_telemetry(session, driver):
    window = _lap_window(session, driver)
    if window is None:
        return None, None

    s, e, lap_time = window

    tel = fetch(f"car_data?session_key={session}&driver_number={driver}&date>{s}&date<{e}")
    if tel.empty:
        return None, None

    tel["date"] = pd.to_datetime(tel["date"], format="ISO8601")
    dt = tel["date"].diff().dt.total_seconds().fillna(0)
    tel["distance"] = (tel["speed"] / 3.6 * dt).cumsum()
    tel.attrs["window"] = (s, e) #remembered so the track position can be fetched later
    return tel, lap_time

def add_track_position(session, driver, tel):
    #adds x/y track coordinates to telemetry and it is matched by the nearest timestamp
    s, e = tel.attrs["window"]
    loc = fetch(f"location?session_key={session}&driver_number={driver}&date>{s}&date<{e}")
    
    if loc.empty:
        return None
    loc["date"] = pd.to_datetime(loc["date"], format= "ISO8601")
    return pd.merge_asof(
        tel.sort_values("date"),
        loc[["date", "x", "y"]].sort_values("date"),
        on = "date",
        direction = "nearest",
    )