"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_significant_cloud_remarks_plain_language():
    """Plain-language FMH-1 significant cloud remarks should decode."""
    _, decoded = RemarksParser().parse(rmk("CB W MOV E TCU NW APRNT ROTOR CLD NE"))
    assert "Cloud Types" in decoded
    cloud_text = decoded["Cloud Types"]
    assert "Cumulonimbus" in cloud_text
    assert "Towering cumulus" in cloud_text
    assert "Apparent rotor cloud" in cloud_text


@pytest.mark.unit
def test_density_altitude_value():
    """DENSITY ALT 3500FT → 3500 feet."""
    _, decoded = RemarksParser().parse(rmk("DENSITY ALT 3500FT"))
    assert "3500" in decoded["Density Altitude"]


@pytest.mark.unit
def test_density_altitude_negative():
    """DENSITY ALT -1000FT → negative altitude decoded."""
    _, decoded = RemarksParser().parse(rmk("DENSITY ALT -1000FT"))
    assert "Density Altitude" in decoded
    assert "-1000" in decoded["Density Altitude"]


# ===========================================================================
# 28. Extra edge cases
# ===========================================================================


@pytest.mark.unit
def test_significant_tcu_distance_range_and_movement_decoded():
    """TCU FM 20KM TO 40KM W-NW MOV E keeps range, direction, and movement."""
    _, decoded = RemarksParser().parse(rmk("TCU FM 20KM TO 40KM W-NW MOV E"))
    value = decoded["Cloud Types"]
    assert "from 20 km to 40 km to the west through northwest" in value
    assert "moving east" in value


@pytest.mark.unit
def test_pirep_cloud_layers_decoded():
    """PIREP cloud-layer base/top remarks are decoded."""
    _, decoded = RemarksParser().parse(
        rmk("PIREP ON DEP 1ST CLD BASE 017 TOP 020 2ND CLD BASE 037 TOP 047")
    )
    layers = decoded["PIREP Clouds"]
    assert layers[0] == "on dep: 1st cloud layer base 1700 ft, top 2000 ft"
    assert layers[1] == "on dep: 2nd cloud layer base 3700 ft, top 4700 ft"
