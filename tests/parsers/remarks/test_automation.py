"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_station_type_ao2():
    """AO2 → Station Type decoded and not None."""
    _, decoded = RemarksParser().parse(rmk("AO2"))
    assert "Station Type" in decoded
    assert decoded["Station Type"] is not None


@pytest.mark.unit
def test_station_type_ao1():
    """AO1 → Station Type decoded and not None."""
    _, decoded = RemarksParser().parse(rmk("AO1"))
    assert "Station Type" in decoded
    assert decoded["Station Type"] is not None


@pytest.mark.unit
def test_station_type_ao2a():
    """AO2A → Station Type decoded and not None."""
    _, decoded = RemarksParser().parse(rmk("AO2A"))
    assert "Station Type" in decoded
    assert decoded["Station Type"] is not None


@pytest.mark.unit
def test_station_type_ao2_value():
    """AO2 → exact decoded value."""
    _, decoded = RemarksParser().parse(rmk("AO2"))
    assert "precipitation discriminator" in decoded["Station Type"].lower()


@pytest.mark.unit
def test_station_type_ao1_value():
    """AO1 → no precipitation discriminator language."""
    _, decoded = RemarksParser().parse(rmk("AO1"))
    assert decoded["Station Type"] is not None
    # AO1 means *without* precipitation discriminator
    assert (
        "without" in decoded["Station Type"].lower()
        or "cannot" in decoded["Station Type"].lower()
    )


# ===========================================================================
# 4. Sea Level Pressure (SLP)
# ===========================================================================


@pytest.mark.unit
def test_rvrno_key_present():
    """RVRNO → RVR Status key present."""
    _, decoded = RemarksParser().parse(rmk("RVRNO"))
    assert "RVR Status" in decoded


@pytest.mark.unit
def test_rvrno_value_non_empty():
    """RVRNO → decoded value is non-empty."""
    _, decoded = RemarksParser().parse(rmk("RVRNO"))
    assert decoded["RVR Status"]


@pytest.mark.unit
def test_sensor_status_retains_secondary_location():
    """VISNO/CHINO with a location should keep that location in the decoded text."""
    _, decoded = RemarksParser().parse(rmk("VISNO RWY11 CHINO RWY11"))
    assert "Sensor Status" in decoded
    assert "RWY11" in decoded["Sensor Status"]


@pytest.mark.unit
def test_tsno_uses_fmh1_wording():
    """TSNO should use the FMH-1 glossary wording."""
    _, decoded = RemarksParser().parse(rmk("TSNO"))
    assert "Sensor Status" in decoded
    assert decoded["Sensor Status"] == "Thunderstorm information not available"


@pytest.mark.unit
def test_maintenance_indicator_key_present():
    """RMK $ → Maintenance Indicator key present."""
    _, decoded = RemarksParser().parse(rmk("$"))
    assert "Maintenance Indicator" in decoded


@pytest.mark.unit
def test_maintenance_indicator_value():
    """RMK $ → decoded value is non-empty."""
    _, decoded = RemarksParser().parse(rmk("$"))
    assert decoded["Maintenance Indicator"]


# ===========================================================================
# 21. Precipitation amount (P group)
# ===========================================================================


@pytest.mark.unit
def test_slpno_and_rvrno_together():
    """SLPNO RVRNO → both status keys present."""
    _, decoded = RemarksParser().parse(rmk("SLPNO RVRNO"))
    assert "SLP Status" in decoded
    assert "RVR Status" in decoded


@pytest.mark.unit
def test_maintenance_indicator_in_complex_rmk():
    """Maintenance indicator at end of compound RMK."""
    _, decoded = RemarksParser().parse(rmk("AO2 SLP013 $"))
    assert "Maintenance Indicator" in decoded
