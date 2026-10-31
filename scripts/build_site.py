from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

from f1clip.detect import find_clipping
from f1clip.openf1 import add_track_position, fastest_lap_telemetry, fetch

# folder with the generated website (not committed, built by GitHub Actions)
OUT = Path("site")
REPO = "https://github.com/jabolos10/F1_Energy_Clipping_Analysis"

# colour palette shared by the plots and the page
BG, PANEL, INK, MUTED, GRID, ACCENT = "#0f0f14", "#18181f", "#f2f2f5", "#9a9aa8", "#2a2a33", "#ff1e3c"

# track map colours: slow = dark grey, fast = white (so red clipping zones stand out)
SPEED_CMAP = LinearSegmentedColormap.from_list("speed", ["#4a4a58", "#ffffff"])

# dark style for all plots
plt.rcParams.update({
    "figure.facecolor": PANEL, "axes.facecolor": PANEL, "savefig.facecolor": PANEL,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "grid.color": GRID,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
})


def latest_qualifying():
    # pick the most recent 2026 qualifying session that has already finished
    sessions = fetch("sessions?year=2026&session_name=Qualifying")
    sessions["date_end"] = pd.to_datetime(sessions["date_end"], format="ISO8601")
    done = sessions[sessions["date_end"] < pd.Timestamp.now(tz="UTC")]
    return done.sort_values("date_end").iloc[-1]


def analyse(session_key):
    # run the clipping detector on every driver's fastest lap
    drivers = fetch(f"drivers?session_key={session_key}")
    rows, laps = [], {}
    for _, d in drivers.iterrows():
        tel, lap_time = fastest_lap_telemetry(session_key, d["driver_number"])
        if tel is None:  # no data for this driver, skip
            continue
        events = find_clipping(tel)
        # biggest single drop on the lap
        worst = max(events, key=lambda ev: ev["loss_kmh"], default=None)
        rows.append({
            "number": d["driver_number"],
            "driver": d["name_acronym"],
            "name": d.get("full_name", d["name_acronym"]),
            "team": d["team_name"],
            "colour": "#" + d["team_colour"] if pd.notna(d["team_colour"]) else "#888888",
            "lap_time": lap_time,
            "events": len(events),
            "total_loss": sum(ev["loss_kmh"] for ev in events),
            "worst": worst["loss_kmh"] if worst else 0,
            "time_lost": round(sum(ev["time_lost_s"] for ev in events), 3),
        })
        laps[d["name_acronym"]] = (tel, events)
    # sorted by lap time = qualifying order
    df = pd.DataFrame(rows).sort_values("lap_time").reset_index(drop=True)
    return df, laps


def lap_str(seconds):
    # 94.035 -> "1:34.035"
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}"


def plot_speed_trace(tel, events):
    # speed over distance, clipping zones shaded red
    fig, ax = plt.subplots(figsize=(7, 5.6))
    for ev in events:
        ax.axvspan(ev["start_m"], ev["end_m"], color=ACCENT, alpha=0.35, lw=0)
    ax.plot(tel["distance"], tel["speed"], color=INK, lw=1.6)
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel("Speed [km/h]")
    ax.grid(axis="y", lw=0.6)
    fig.tight_layout()
    fig.savefig(OUT / "speed_trace.png", dpi=160)
    plt.close(fig)


def plot_track_map(tel, events):
    # draw the track from x/y positions, each small segment coloured by speed
    pts = tel[["x", "y"]].to_numpy()
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    fig, ax = plt.subplots(figsize=(7, 5.6))
    lc = LineCollection(segs, cmap=SPEED_CMAP, linewidths=4, capstyle="round")
    lc.set_array(tel["speed"].to_numpy()[:-1])
    ax.add_collection(lc)
    # paint clipping zones red on top
    for ev in events:
        part = tel[(tel["distance"] >= ev["start_m"]) & (tel["distance"] <= ev["end_m"])]
        ax.plot(part["x"], part["y"], color=ACCENT, lw=7, alpha=0.9, solid_capstyle="round")
    ax.autoscale()
    ax.set_aspect("equal")  # keep the real track shape
    ax.axis("off")
    cb = fig.colorbar(lc, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("Speed [km/h]")
    cb.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "track_map.png", dpi=160)
    plt.close(fig)


def plot_ranking(df):
    # horizontal bars: total speed lost per driver, in team colours
    d = df.sort_values("total_loss")
    fig, ax = plt.subplots(figsize=(10, 0.36 * len(d) + 1.2))
    ax.barh(d["driver"], d["total_loss"], color=d["colour"], height=0.65)
    # value label next to each bar
    for y, v in enumerate(d["total_loss"]):
        ax.text(v + 1, y, str(v), va="center", color=MUTED, fontsize=10)
    ax.set_xlabel("Speed lost while flat out on the throttle, summed over the lap [km/h]")
    ax.grid(axis="x", lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "ranking.png", dpi=160)
    plt.close(fig)


# page styling
CSS = """
:root { --bg:#0f0f14; --panel:#18181f; --ink:#f2f2f5; --muted:#9a9aa8; --line:#2a2a33; --accent:#ff1e3c; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:'Titillium Web',system-ui,sans-serif; line-height:1.55; }
.wrap { max-width:1080px; margin:0 auto; padding:0 16px; }
header { border-top:4px solid var(--accent); padding:40px 0 24px; }
.eyebrow { color:var(--accent); font-weight:700; letter-spacing:.12em; text-transform:uppercase; font-size:13px; }
h1 { font-size:clamp(32px,5vw,52px); line-height:1.05; margin:8px 0 12px; font-weight:900; text-transform:uppercase; }
h2 { position:relative; margin:84px 0 6px; padding-top:16px; font-size:28px; font-style:italic; font-weight:900; text-transform:uppercase; }
h2::before { content:""; position:absolute; top:0; left:0; width:120px; height:4px;
  background:linear-gradient(90deg,var(--accent) 0 80%,#fff 80% 92%,transparent 92%); }
.lead { color:var(--muted); max-width:720px; font-size:17px; margin:0; }
.pill { display:inline-block; margin-top:18px; padding:6px 14px; border:1px solid var(--line); border-radius:999px; font-size:14px; }
.sub { color:var(--muted); margin:0 0 18px; }
.card { background:var(--panel); border-radius:10px; padding:12px; border:1px solid rgba(255,255,255,.07); box-shadow:0 12px 30px rgba(0,0,0,.45); }
.card img { width:100%; display:block; border-radius:6px; }
.split { display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:start; }
@media (max-width:760px) { .split { grid-template-columns:1fr; } }
.tablewrap { overflow-x:auto; background:var(--panel); border-radius:10px; border:1px solid rgba(255,255,255,.07); box-shadow:0 12px 30px rgba(0,0,0,.45); }
table { border-collapse:collapse; width:100%; font-size:15px; min-width:640px; }
th { text-align:left; color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.06em; padding:12px 14px; border-bottom:1px solid var(--line); }
td { padding:11px 14px; border-bottom:1px solid var(--line); white-space:nowrap; }
tr:last-child td { border-bottom:none; }
td.num { font-variant-numeric:tabular-nums; }
.team { display:flex; align-items:center; gap:10px; }
.bar { width:4px; height:18px; border-radius:2px; background:var(--c); }
.hot { color:var(--accent); font-weight:700; }
.explain { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:28px; }
@media (max-width:760px) { .explain { grid-template-columns:1fr; } }
.insights { margin-top:14px; }
.tile { position:relative; overflow:hidden; border-radius:14px; padding:22px 26px;
  background:linear-gradient(180deg,rgba(255,255,255,.07) 0%,rgba(255,255,255,.02) 40%,rgba(0,0,0,.25) 100%), #15151b;
  border:1px solid rgba(255,255,255,.10); box-shadow:0 0 0 1px rgba(0,0,0,.6), 0 12px 32px rgba(0,0,0,.55); }
.tile::before { content:""; position:absolute; top:0; left:8%; right:8%; height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent); }
.tile::after { content:""; position:absolute; top:-40%; left:-30%; width:60%; height:180%; transform:rotate(18deg);
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.035),transparent); pointer-events:none; }
.tile h3 { margin:0 0 12px; font-size:20px; font-style:italic; font-weight:900; text-transform:uppercase; letter-spacing:.02em; }
.tile h3::before { content:"// "; color:var(--accent); }
.tile ul { margin:0; padding-left:20px; font-size:17px; }
.tile li { margin:5px 0; color:#d6d6de; } .tile li::marker { color:var(--accent); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin-top:14px; }
.kpi { box-shadow:inset 0 -3px 0 var(--c), 0 12px 32px rgba(0,0,0,.55); }
.kpi .label { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }
.kpi .value { font-size:30px; font-weight:700; line-height:1.2; text-shadow:0 0 22px rgba(255,255,255,.15); }
.kpi .who { color:var(--muted); font-size:14px; }
footer { color:var(--muted); font-size:14px; padding:48px 0 40px; border-top:1px solid var(--line); margin-top:56px; }
a { color:var(--ink); }
"""


def insights(df):
    # short auto-generated findings, the numbers change with every race
    pole = df.iloc[0]
    most = df.loc[df["time_lost"].idxmax()]
    least = df.loc[df["time_lost"].idxmin()]
    more_than_pole = int((df["time_lost"] > pole.time_lost).sum())
    gap_p5 = df.iloc[min(4, len(df) - 1)].lap_time - pole.lap_time
    lines = [
        f"{escape(most['name'])} lost the most time to clipping: <b>{most.time_lost:.2f} s</b> per lap.",
        f"{escape(least['name'])} lost the least: <b>{least.time_lost:.2f} s</b>.",
        (f"Pole sitter {escape(pole['name'])} lost <b>{pole.time_lost:.2f} s</b>, "
         f"less than {more_than_pole} of {len(df) - 1} rivals."),
        (f"Average time lost: <b>{df['time_lost'].mean():.2f} s</b> per lap. "
         f"The gap from P1 to P5 was <b>{gap_p5:.3f} s</b>."),
    ]
    return "".join(f"<li>{t}</li>" for t in lines)


def kpi(label, value, who, colour):
    # one stat tile, bottom stripe in team colour
    return (f'<div class="tile kpi" style="--c:{colour}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="who">{escape(who)}</div></div>')


def write_html(session, df):
    # build the whole page as one HTML file
    pole = df.iloc[0]
    most = df.loc[df["time_lost"].idxmax()]
    worst = df.loc[df["worst"].idxmax()]
    # top quarter of the field by time lost gets highlighted in red
    hot_cut = df["time_lost"].quantile(0.75)

    rows = []
    for i, r in df.iterrows():
        gap = "" if i == 0 else f"+{r.lap_time - pole.lap_time:.3f}"
        lost_cls = ' class="num hot"' if r.time_lost >= hot_cut else ' class="num"'
        rows.append(
            f"<tr><td class='num'>{i + 1}</td><td><b>{escape(r.driver)}</b> "
            f"<span style='color:var(--muted)'>{escape(str(r['name']))}</span></td>"
            f"<td><div class='team'><span class='bar' style='--c:{r.colour}'></span>{escape(str(r.team))}</div></td>"
            f"<td class='num'>{lap_str(r.lap_time)}</td><td class='num'>{gap}</td>"
            f"<td class='num'>{r.events}</td><td class='num'>{r.total_loss}</td><td class='num'>{r.worst}</td>"
            f"<td{lost_cls}>{r.time_lost:.2f}</td></tr>"
        )

    place = session.get("circuit_short_name") or session["country_name"]
    date = pd.to_datetime(session["date_end"]).strftime("%d %b %Y")
    generated = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>F1 Energy Clipping Analysis</title>
<meta name="description" content="Where 2026 F1 cars lose speed while flat out on the throttle, from real telemetry.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="wrap">
<header>
  <div class="eyebrow">2026 hybrid era · telemetry study</div>
  <h1>F1 Energy Clipping Analysis</h1>
  <p class="lead">Where 2026 F1 cars lose speed while flat out on the throttle, measured automatically
  in every driver's fastest qualifying lap from real telemetry.</p>
  <span class="pill">{escape(str(session["country_name"]))} · {escape(str(place))} · Qualifying · {date}</span>
</header>

<section class="explain">
  <div class="tile"><h3>What is clipping?</h3>
  <ul><li>2026 cars get about half their power from a battery.</li>
  <li>On long straights it runs low, so part of the engine's power recharges it instead of driving the wheels.</li>
  <li>Result: the car <b>slows down while the driver is still flat out</b>.</li></ul></div>
  <div class="tile"><h3>How it is detected</h3>
  <ul><li>Throttle ≥ 98% and brake off.</li>
  <li>Speed falls at least 5 km/h from its peak.</li>
  <li>Time lost = actual time vs holding the peak speed.</li></ul></div>
</section>

<section class="tile insights"><h3>This session in numbers</h3><ul>{insights(df)}</ul></section>

<div class="kpis">
  {kpi("Pole lap", lap_str(pole.lap_time), f"{pole.driver} · {pole.team}", pole.colour)}
  {kpi("Most time lost", f"{most.time_lost:.2f} s", f"{most.driver} · {most.team}", most.colour)}
  {kpi("Biggest single drop", f"{worst.worst} km/h", f"{worst.driver} · {worst.team}", worst.colour)}
  {kpi("Field average", f"{df['time_lost'].mean():.2f} s", "time lost per lap", "#9a9aa8")}
</div>

<h2>Where the battery runs dry</h2>
<p class="sub">{escape(pole.driver)}'s pole lap. Red = full throttle, no brake, speed falling.</p>
<div class="split">
  <div class="card"><img src="track_map.png" alt="Track map coloured by speed with clipping zones in red"></div>
  <div class="card"><img src="speed_trace.png" alt="Speed over distance with clipping zones in red"></div>
</div>

<h2>Speed lost to clipping, by driver</h2>
<p class="sub">Fastest lap of each driver. Bars in team colours.</p>
<div class="card"><img src="ranking.png" alt="Speed lost to clipping per driver"></div>

<h2>Full grid</h2>
<p class="sub">Time lost = time spent in clipping zones compared with holding the peak speed. Highlighted: top quarter of the field.</p>
<div class="tablewrap"><table>
<tr><th>#</th><th>Driver</th><th>Team</th><th>Lap</th><th>Gap</th><th>Clipping zones</th><th>Speed lost, sum [km/h]</th><th>Biggest drop [km/h]</th><th>Time lost [s]</th></tr>
{"".join(rows)}
</table></div>

<footer>
  <p><b>Method.</b> A clipping zone is a stretch with throttle ≥ 98% and no brake where speed drops at least 5 km/h
  from its peak. Rebuilt and redeployed automatically by a GitHub Actions CI/CD pipeline after every race weekend,
  only if all tests pass. <a href="{REPO}">Source code on GitHub</a>.</p>
  <p>Data: OpenF1 API. Unofficial project, not associated with Formula 1 companies. Generated {generated}.</p>
</footer>
</div></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main():
    # 1. get data, 2. detect clipping, 3. make plots, 4. write the page
    OUT.mkdir(exist_ok=True)
    session = latest_qualifying()
    print("Session:", session["country_name"], session["session_key"])
    df, laps = analyse(session["session_key"])

    pole = df.iloc[0]
    tel, events = laps[pole.driver]
    plot_speed_trace(tel, events)
    tel_xy = add_track_position(session["session_key"], pole.number, tel)
    if tel_xy is not None:
        plot_track_map(tel_xy, events)
    plot_ranking(df)
    write_html(session, df)
    print(df.drop(columns=["name"]).to_string(index=False))


if __name__ == "__main__":
    main()