"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_6hr_precipitation_value():
    """60021 → 0.21 inches."""
    _, decoded = RemarksParser().parse(rmk("60021"))
    assert "0.21 inches" in decoded["6-Hour Precipitation"]


@pytest.mark.unit
def test_6hr_precipitation_trace():
    """60000 → trace or none."""
    _, decoded = RemarksParser().parse(rmk("60000"))
    assert (
        "Trace" in decoded["6-Hour Precipitation"]
        or "trace" in decoded["6-Hour Precipitation"]
    )


# ===========================================================================
# 10. Peak wind (PK WND)
# ===========================================================================


@pytest.mark.unit
def test_complex_automated_precipitation_timeline_report():
    """A complex AUTO RMK with additive data should decode key FMH-1 groups consistently."""
    metar = (
        "METAR KSLN 210553Z AUTO 02014KT 5SM BR OVC009 01/M01 A2982 RMK "
        "AO2 UPB11E12B44E47FZRAB29E44SNE11B12E14 CIG 007V014 SLP107 P0000 "
        "60005 T00061011 10011 20006 400330006 51016 TSNO"
    )
    _, decoded = RemarksParser().parse(metar)

    assert (
        decoded["Station Type"] == "Automated station with precipitation discriminator"
    )
    assert decoded["Variable Ceiling"] == "700 to 1400 feet AGL"
    assert decoded["Sea Level Pressure"] == "1010.7 hPa"
    assert decoded["Precipitation Amount"] == "Less than 0.01 inches"
    assert decoded["6-Hour Precipitation"] == "0.05 inches"
    assert decoded["Temperature (tenths)"] == "0.6°C"
    assert decoded["Dewpoint (tenths)"] == "-1.1°C"
    assert decoded["6-Hour Maximum Temperature"] == "1.1°C"
    assert decoded["6-Hour Minimum Temperature"] == "0.6°C"
    assert decoded["24-Hour Maximum Temperature"] == "3.3°C"
    assert decoded["24-Hour Minimum Temperature"] == "0.6°C"
    assert decoded["Pressure Tendency"] == (
        "Increasing, then steady; or increasing then increasing more slowly; change: 1.6 hPa"
    )
    assert decoded["Sensor Status"] == "Thunderstorm information not available"
    assert "05:29 UTC: freezing rain began" in decoded["Precipitation Begin/End Times"]
    assert (
        "05:11 UTC: unknown precipitation began, snow ended"
        in decoded["Precipitation Begin/End Times"]
    )


@pytest.mark.unit
def test_jma_ri_precipitation_intensity_uses_whole_mm_per_hour():
    """RI035 is 35 mm/h in JMA automated METAR/SPECI remarks."""
    _, decoded = RemarksParser().parse(rmk("A2956 RI035"))
    assert decoded["Precipitation Intensity (JMA)"] == "35 mm/h"


@pytest.mark.unit
def test_precipitation_amount_value():
    """P0021 → 0.21 inches."""
    _, decoded = RemarksParser().parse(rmk("P0021"))
    assert "0.21 inches" in decoded["Precipitation Amount"]


@pytest.mark.unit
def test_precipitation_amount_zero():
    """P0000 → less than 0.01 inches."""
    _, decoded = RemarksParser().parse(rmk("P0000"))
    assert (
        "Less than 0.01" in decoded["Precipitation Amount"]
        or "0.00" in decoded["Precipitation Amount"]
    )


# ===========================================================================
# 22. Virga
# ===========================================================================
