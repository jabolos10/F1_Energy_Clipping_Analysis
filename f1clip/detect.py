def find_clipping(tel, min_loss=5.0, full_throttle=98):
    results = []
    start = None

    for i in range(len(tel) + 1):
        full = (
            i < len(tel)
            and tel["throttle"].iloc[i] >= full_throttle
            and tel["brake"].iloc[i] == 0
        )

        if full and start is None:
            start = i  #here starts the moment of full throttle

        elif not full and start is not None:
            seg = tel.iloc[start:i]   #whole distance of full throttle -> telemetry data from this distance saved to seg

            peak = seg["speed"].idxmax()     #row with the highest speed
            peak_speed = tel.loc[peak, "speed"]
            end_speed = seg["speed"].iloc[-1]   #speed at the end of the distance
            loss = peak_speed - end_speed

            if loss >= min_loss:      #if difference in km/h is bigger than 5km/h for full throttle
                
                # time lost: actual time from peak to end due to clipping vs holding peak speed
                part = tel.loc[peak:seg.index[-1]]  #time from peak to end
                ds = part["distance"].diff().iloc[1:] #distance between readings
                actual = (ds / (part["speed"].iloc[1:] / 3.6)).sum()
                ideal = ds.sum() / (peak_speed / 3.6) 

                results.append({
                    "start_m": round(tel.loc[peak, "distance"]),
                    "end_m": round(seg["distance"].iloc[-1]),
                    "loss_kmh": round(loss),
                    "time_lost_s": round(actual - ideal, 3),
                })

            start = None   #distance closed, we are searching for the new one

    return results