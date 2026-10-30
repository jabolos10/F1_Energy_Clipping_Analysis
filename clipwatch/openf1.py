import time

import pandas as pd
import requests

BASE = "https://api.openf1.org/v1"


def fetch(query):
    # free OpenF1 tier: max 30 requests per minute, so wait 2 s before each one
    for attempt in range(3):
        time.sleep(2.1)
        r = requests.get(f"{BASE}/{query}", timeout=30)
        if r.status_code == 429:  # too many requests: wait longer and retry
            time.sleep(15)
            continue
        if r.status_code == 404:  # OpenF1 answers 404 when there is no data
            return pd.DataFrame()
        r.raise_for_status()
        return pd.DataFrame(r.json())
    raise RuntimeError(f"OpenF1 keeps rate-limiting: {query}")


def fastest_lap_telemetry(session, driver):
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

    tel = fetch(f"car_data?session_key={session}&driver_number={driver}&date>{s}&date<{e}")
    if tel.empty:
        return None, None

    tel["date"] = pd.to_datetime(tel["date"], format="ISO8601")
    dt = tel["date"].diff().dt.total_seconds().fillna(0)
    tel["distance"] = (tel["speed"] / 3.6 * dt).cumsum()
    return tel, float(lap["lap_duration"])