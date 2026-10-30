import matplotlib.pyplot as plt
import pandas as pd
import requests

from clipwatch.detect import find_clipping

BASE = "https://api.openf1.org/v1"
SESSION = 11230      #qualifications in Australia 2026
DRIVER = 63          #Russel, who won the pole position


#fastest lap
laps = pd.DataFrame(requests.get(f"{BASE}/laps", params= {"session_key": SESSION, "driver_number": DRIVER}).json())
laps = laps.dropna(subset=["lap_duration"])
lap = laps.loc[laps["lap_duration"].idxmin()]
print("Lap", lap["lap_number"], "Time", lap["lap_duration"])


#when the lap took place
start = pd.to_datetime(lap["date_start"])
end = start + pd.Timedelta(seconds=float(lap["lap_duration"]))
s = start.strftime("%Y-%m-%dT%H:%M:%S")
e = end.strftime("%Y-%m-%dT%H:%M:%S")


#telemetry of a lap
url = f"{BASE}/car_data?session_key={SESSION}&driver_number={DRIVER}&date>{s}&date<{e}"
tel = pd.DataFrame(requests.get(url).json())
print(tel.head())


#distance calculation
tel["date"] = pd.to_datetime(tel["date"])
dt = tel["date"].diff().dt.total_seconds().fillna(0)
tel["distance"] = (tel["speed"] / 3.6 * dt).cumsum()


#plot
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
ax1.plot(tel["distance"], tel["speed"])
ax1.set_ylabel("Speed [km/h]")
ax2.plot(tel["distance"], tel["throttle"])
ax2.set_ylabel("Throttle [%]")
ax3.plot(tel["distance"], tel["brake"])
ax3.set_ylabel("Brake [%]")
ax3.set_xlabel("Distance [m]")

print(find_clipping(tel))

plt.show()