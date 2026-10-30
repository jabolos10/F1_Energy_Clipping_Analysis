import pandas as pd
import pytest

from f1clip.detect import find_clipping


def make_tel(speed, throttle, brake):
    #fake lap: reading every 50m
    return pd.DataFrame({
        "distance": [i*50 for i in range(len(speed))],
        "speed": speed,
        "throttle": throttle,
        "brake": brake,
    })

def test_detects_clipping():
    #full throttle: the car accelerates to 320 and later on the speed falls down to 290
    tel = make_tel([250, 280, 300, 320, 310, 300, 290], [100]*7, [0]*7)
    result = find_clipping(tel)
    assert len(result) == 1
    assert result[0]["loss_kmh"] == 30
    assert result[0]["start_m"] == 150    #peak in the 4th reading: 3* 50
    assert result[0]["end_m"] == 300
    assert result[0]["time_lost_s"] == pytest.approx(0.114, abs=0.001)

def test_braking_is_not_clipping():
    tel = make_tel([320, 300, 250, 200], [0]*4, [100]*4)
    assert find_clipping(tel) == []

def test_partial_throttle_is_not_clipping():
    tel = make_tel([300, 290, 280, 270], [50]*4, [0]*4)
    assert find_clipping(tel) == []

def test_small_drop_is_ignored():
    #drop of speed being 3km/h is a noise, below threshold being 5km/h
    tel = make_tel([300, 310, 307], [100]*3, [0]*3)
    assert find_clipping(tel) == []

def test_two_straights_give_two_events():
    #two straight divided by braking
    tel = make_tel(
        [300, 320, 300, 150, 300, 320, 310],
        [100, 100, 100, 0, 100, 100, 100],
        [0, 0, 0, 100, 0, 0, 0],
    )
    assert [r["loss_kmh"] for r in find_clipping(tel)] == [20, 10]