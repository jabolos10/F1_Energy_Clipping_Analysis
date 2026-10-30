# ClipWatch

**Full throttle. Losing speed. Why?**

![CI](https://github.com/jabolos10/clipwatch/actions/workflows/ci.yml/badge.svg)

In 2026, Formula 1 cars became roughly half electric, and they are starving for energy. On long straights the battery runs dry, part of the engine's power is diverted to recharge it, and the car **slows down while the driver is still flat on the throttle**. The paddock calls it *super clipping*, and it is one of the defining stories of the 2026 season.

ClipWatch finds it automatically in real F1 telemetry.

---

## What it found first

![Speed, throttle and brake on Russell's pole lap](docs/melbourne-q.png)

**2026 Australian GP, qualifying, George Russell's pole lap (1:18.518)**

On the longest full-throttle section of Albert Park, the car peaks at about **327 km/h**, then bleeds speed down to about **280 km/h** before the next corner. That is roughly **45 km/h lost** with:

- the throttle pinned at 100%,
- the brake never touched.

That is not driver error, and it is not drag. It is the hybrid system harvesting energy at full throttle.

## How it works

1. Pulls car telemetry (speed, throttle, brake, gear, RPM) from the [OpenF1](https://openf1.org) API.
2. Finds every stretch where the throttle is ≥ 98% and the brake is off.
3. Flags a clipping event when speed drops by more than a set threshold inside such a stretch, then measures where it happens and how many km/h it costs.

## Why it matters

- **Energy management decides lap time in 2026.** Pole laps are roughly 1.5 to 4 seconds slower than in 2025, depending on the circuit.
- **The FIA changed the rules mid-season.** From the Miami GP onwards, teams can harvest less energy per lap, but super clipping may charge harder. The stated goal is to cut super clipping from around 8 seconds to 3–4 seconds per lap. ClipWatch is built to check that claim with data.
- **The same problem exists on the road.** Deciding where to spend and where to recover battery energy is the same challenge hybrid and electric road cars face.

## Roadmap

- [x] Telemetry exploration: clipping visible in Melbourne qualifying
- [x] `find_clipping()` detector
- [ ] Unit tests on synthetic telemetry (pytest)
- [ ] CI: linting (ruff) and tests on every push and pull request (GitHub Actions)
- [ ] CD: results site auto-built and deployed to GitHub Pages after every Grand Prix
- [ ] Team-by-team clipping comparison
- [ ] Before vs after the Miami rule change

## Tech

Python · pandas · matplotlib · OpenF1 API · pytest · ruff · GitHub Actions · GitHub Pages

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.explore
```

---

*Data: [OpenF1](https://openf1.org), unofficial and not associated with Formula 1 companies.*
