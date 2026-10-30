from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from clipwatch.detect import find_clipping
from clipwatch.openf1 import fastest_lap_telemetry, fetch

OUT = Path("site")


def latest_qualifying():
    sessions = fetch("sessions?year=2026&session_name=Qualifying")
    sessions["date_end"] = pd.to_datetime(sessions["date_end"], format="ISO8601")
    done = sessions[sessions["date_end"] < pd.Timestamp.now(tz="UTC")]
    return done.sort_values("date_end").iloc[-1]


def analyse(session_key):
    drivers = fetch(f"drivers?session_key={session_key}")
    rows, laps = [], {}
    for _, d in drivers.iterrows():
        tel, lap_time = fastest_lap_telemetry(session_key, d["driver_number"])
        if tel is None:
            continue
        events = find_clipping(tel)
        rows.append({
            "driver": d["name_acronym"],
            "team": d["team_name"],
            "colour": "#" + d["team_colour"] if pd.notna(d["team_colour"]) else "#888888",
            "lap_time": lap_time,
            "events": len(events),
            "total_loss": sum(ev["loss_kmh"] for ev in events),
            "worst": max((ev["loss_kmh"] for ev in events), default=0),
        })
        laps[d["name_acronym"]] = (tel, events)
    return pd.DataFrame(rows).sort_values("lap_time"), laps


def plot_ranking(df):
    df = df.sort_values("total_loss")
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(df) + 1))
    ax.barh(df["driver"], df["total_loss"], color=df["colour"])
    ax.set_xlabel("Speed lost while flat out, summed over the lap [km/h]")
    fig.tight_layout()
    fig.savefig(OUT / "ranking.png", dpi=120)
    plt.close(fig)


def plot_pole_lap(driver, tel, events):
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(tel["distance"], tel["speed"], color="#2a78d6")
    for ev in events:
        ax.axvspan(ev["start_m"], ev["end_m"], color="#e34948", alpha=0.25)
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel("Speed [km/h]")
    ax.set_title(f"{driver}, fastest lap (red = clipping)")
    fig.tight_layout()
    fig.savefig(OUT / "pole_lap.png", dpi=120)
    plt.close(fig)


def write_html(session, df):
    rows = "\n".join(
        f"<tr><td>{i}</td><td>{escape(r.driver)}</td><td>{escape(str(r.team))}</td>"
        f"<td>{r.lap_time:.3f}</td><td>{r.events}</td><td>{r.total_loss}</td><td>{r.worst}</td></tr>"
        for i, r in enumerate(df.itertuples(), start=1)
    )
    title = f"{session['country_name']} {session['year']}, qualifying"
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClipWatch</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 16px; }}
img {{ max-width: 100%; }} table {{ border-collapse: collapse; width: 100%; }}
td, th {{ padding: 4px 8px; border-bottom: 1px solid #ddd; text-align: left; }}
</style></head><body>
<h1>ClipWatch</h1>
<p>Where 2026 F1 cars lose speed while flat out on the throttle (super clipping).
Updated automatically by GitHub Actions after every Grand Prix.
<a href="https://github.com/jabolos10/clipwatch">Source code</a>.</p>
<h2>{escape(title)}</h2>
<img src="pole_lap.png" alt="Speed trace of the fastest lap with clipping zones">
<img src="ranking.png" alt="Speed lost to clipping per driver">
<table><tr><th>#</th><th>Driver</th><th>Team</th><th>Lap [s]</th>
<th>Clipping zones</th><th>Total loss [km/h]</th><th>Worst [km/h]</th></tr>
{rows}
</table>
<p><small>Data: OpenF1 (unofficial). Generated {pd.Timestamp.now(tz="UTC"):%Y-%m-%d %H:%M} UTC.</small></p>
</body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    session = latest_qualifying()
    print("Session:", session["country_name"], session["session_key"])
    df, laps = analyse(session["session_key"])
    pole = df.iloc[0]["driver"]
    plot_pole_lap(pole, *laps[pole])
    plot_ranking(df)
    write_html(session, df)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()