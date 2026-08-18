import pytest
from app.engine.time_utils import (
    validate_time_string,
    time_to_minutes,
    minutes_to_time,
    signed_time_delta,
    absolute_time_delta,
    sleep_duration_hours,
)


def test_validate_time_string():
    assert validate_time_string("00:00") is True
    assert validate_time_string("06:30") is True
    assert validate_time_string("23:59") is True
    assert validate_time_string("24:00") is False
    assert validate_time_string("25:30") is False
    assert validate_time_string("99:99") is False
    assert validate_time_string("12:60") is False
    assert validate_time_string("abc") is False
    assert validate_time_string("7:30") is False


def test_time_to_minutes():
    assert time_to_minutes("00:00") == 0
    assert time_to_minutes("01:00") == 60
    assert time_to_minutes("12:30") == 750
    assert time_to_minutes("23:59") == 1439
    with pytest.raises(ValueError):
        time_to_minutes("24:00")


def test_signed_time_delta_edge_cases():
    # 23:30 -> 00:30 = +60 (1 hour later)
    assert signed_time_delta("00:30", "23:30") == 60
    # 00:30 -> 23:30 = -60 (1 hour earlier)
    assert signed_time_delta("23:30", "00:30") == -60
    # Target 00:15, Actual 23:55 = -20 (20m earlier)
    assert signed_time_delta("23:55", "00:15") == -20
    # Target 23:45, Actual 00:10 = +25 (25m later)
    assert signed_time_delta("00:10", "23:45") == 25


def test_absolute_time_delta():
    assert absolute_time_delta("13:00", "06:00") == 420
    assert absolute_time_delta("23:30", "00:30") == 60


def test_sleep_duration_hours():
    assert sleep_duration_hours("23:00", "07:00") == 8.0
    assert sleep_duration_hours("02:00", "10:00") == 8.0
    assert sleep_duration_hours("04:30", "13:00") == 8.5
    assert sleep_duration_hours("00:00", "06:30") == 6.5
