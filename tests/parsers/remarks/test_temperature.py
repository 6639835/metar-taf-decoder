"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_temperature_tenths_positive():
    """T02220183 → temperature 22.2°C, dewpoint 18.3°C."""
    _, decoded = RemarksParser().parse(rmk("T02220183"))
    assert "Temperature (tenths)" in decoded
    assert "Dewpoint (tenths)" in decoded
    assert decoded["Temperature (tenths)"] == "22.2°C"
    assert decoded["Dewpoint (tenths)"] == "18.3°C"


@pytest.mark.unit
def test_temperature_tenths_negative():
    """T11221050 → temperature -12.2°C, dewpoint -5.0°C."""
    _, decoded = RemarksParser().parse(rmk("T11221050"))
    assert decoded["Temperature (tenths)"] == "-12.2°C"
    assert decoded["Dewpoint (tenths)"] == "-5.0°C"


@pytest.mark.unit
def test_temperature_tenths_mixed_signs():
    """T00001156 → temperature 0.0°C, dewpoint -15.6°C.

    The sign digit for the dewpoint is the 5th character (index 4 from 'T').
    T + 0 (temp sign=pos) + 000 (temp tenths) + 1 (dew sign=neg) + 156 (dew tenths).
    """
    _, decoded = RemarksParser().parse(rmk("T00001156"))
    assert decoded["Temperature (tenths)"] == "0.0°C"
    assert decoded["Dewpoint (tenths)"] == "-15.6°C"


# ===========================================================================
# 6. Pressure tendency (5appp)
# ===========================================================================


@pytest.mark.unit
def test_24hr_temp_extremes_incomplete_not_matched():
    """40112 (only 5 digits) must NOT match the 8-digit 4snTTTsnTTT group."""
    _, decoded = RemarksParser().parse(rmk("40112"))
    assert "24-Hour Maximum Temperature" not in decoded
    assert "24-Hour Minimum Temperature" not in decoded


@pytest.mark.unit
def test_24hr_temp_max_value():
    """402500183 → max temperature 25.0°C."""
    _, decoded = RemarksParser().parse(rmk("402500183"))
    assert decoded.get("24-Hour Maximum Temperature") == "25.0°C"


@pytest.mark.unit
def test_24hr_temp_min_value():
    """402500183 → min temperature 18.3°C."""
    _, decoded = RemarksParser().parse(rmk("402500183"))
    assert decoded.get("24-Hour Minimum Temperature") == "18.3°C"


# ===========================================================================
# 8. 6-hour max/min temperature (1snTTT / 2snTTT)
# ===========================================================================


@pytest.mark.unit
def test_6hr_max_temperature_value():
    """10250 → 25.0°C."""
    _, decoded = RemarksParser().parse(rmk("10250"))
    assert decoded["6-Hour Maximum Temperature"] == "25.0°C"


@pytest.mark.unit
def test_6hr_min_temperature_value():
    """20183 → 18.3°C."""
    _, decoded = RemarksParser().parse(rmk("20183"))
    assert decoded["6-Hour Minimum Temperature"] == "18.3°C"


# ===========================================================================
# 9. 6-hour precipitation (6xxxx)
# ===========================================================================


@pytest.mark.unit
def test_impossible_additive_temperature_groups_are_warned():
    """FMH-1 additive temperature groups that contradict each other should be flagged."""
    _, decoded = RemarksParser().parse(rmk("T02281017 10161 413230322"))
    assert decoded["6-Hour Maximum Temperature"] == "16.1°C"
    assert decoded["24-Hour Maximum Temperature"] == "-32.3°C"
    assert "Additive Data Warning" in decoded
    assert "6-hour maximum temperature is lower" in decoded["Additive Data Warning"]
    assert "24-hour maximum temperature is lower" in decoded["Additive Data Warning"]


@pytest.mark.unit
def test_6hr_max_negative_temperature():
    """11050 → -5.0°C (sign digit 1 means negative)."""
    _, decoded = RemarksParser().parse(rmk("11050"))
    assert "6-Hour Maximum Temperature" in decoded
    assert decoded["6-Hour Maximum Temperature"] == "-5.0°C"


@pytest.mark.unit
def test_6hr_min_negative_temperature():
    """21050 → -5.0°C."""
    _, decoded = RemarksParser().parse(rmk("21050"))
    assert "6-Hour Minimum Temperature" in decoded
    assert decoded["6-Hour Minimum Temperature"] == "-5.0°C"


@pytest.mark.unit
def test_altitude_token_does_not_decode_as_6hr_max_temperature():
    """Altitude tokens in PIREP remarks must not match 1snTTT temperature groups."""
    _, decoded = RemarksParser().parse(
        rmk("MOD TURB OBS AT 1011Z PLUTO BTN 9000FT AND 13000FT IN CMB BY B738")
    )
    assert "6-Hour Maximum Temperature" not in decoded
