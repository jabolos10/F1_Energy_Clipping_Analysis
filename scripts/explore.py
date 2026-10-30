import matplotlib.pyplot as plt

from f1clip.detect import find_clipping
from f1clip.openf1 import fastest_lap_telemetry

SESSION = 11230      #qualifications in Australia 2026
DRIVER = 63          #Russel, who won the pole position


tel, lap_time = fastest_lap_telemetry(SESSION, DRIVER)
print("Lap time:", lap_time)
print(find_clipping(tel))


fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
ax1.plot(tel["distance"], tel["speed"])
ax1.set_ylabel("Speed [km/h]")
ax2.plot(tel["distance"], tel["throttle"])
ax2.set_ylabel("Throttle [%]")
ax3.plot(tel["distance"], tel["brake"])
ax3.set_ylabel("Brake [%]")
ax3.set_xlabel("Distance [m]")

plt.show()