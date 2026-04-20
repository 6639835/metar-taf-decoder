"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_tornadic_activity_end_only_is_supported():
    """TORNADO E15 6 NE should decode even without a begin time."""
    _, decoded = RemarksParser().parse(rmk("TORNADO E15 6 NE"))
    assert "Tornadic Activity" in decoded
    assert "ended" in decoded["Tornadic Activity"].lower()


# ===========================================================================
# 19. QFE format
# ===========================================================================


@pytest.mark.unit
def test_virga_value_non_empty():
    """VIRGA → decoded value non-empty."""
    _, decoded = RemarksParser().parse(rmk("VIRGA"))
    assert decoded["Virga"]


@pytest.mark.unit
def test_virga_value_contains_virga():
    """VIRGA → decoded value mentions 'virga' or 'precipitation'."""
    _, decoded = RemarksParser().parse(rmk("VIRGA"))
    val = decoded["Virga"].lower()
    assert "virga" in val or "precipitation" in val


@pytest.mark.unit
def test_virga_direction_range_with_and_is_not_corrupted():
    """VIRGA DSNT SE-SW AND W should not expand N inside AND."""
    _, decoded = RemarksParser().parse(rmk("VIRGA DSNT SE-SW AND W"))
    assert decoded["Virga"] == (
        "Virga (precipitation not reaching ground) distant "
        "to the southeast through southwest and west"
    )


# ===========================================================================
# 23. Runway winds
# ===========================================================================


@pytest.mark.unit
def test_directional_shower_remark_decoded():
    """SHRA DSNT S-N is plain-language weather location information."""
    _, decoded = RemarksParser().parse(rmk("SHRA DSNT S-N"))
    assert (
        decoded["Weather Location"] == "shower rain distant to the south through north"
    )


@pytest.mark.unit
def test_jma_pirep_turbulence_decoded():
    """JMA MOD TURB OBS AT ... RMK is decoded into PIREP turbulence entries."""
    _, decoded = RemarksParser().parse(
        rmk("MOD TURB OBS AT 1033Z 25NM E NARITA BTN 13000FT AND 10000FT IN DES B77W")
    )
    reports = decoded["PIREP Turbulence"]
    assert len(reports) == 1
    assert "Moderate turbulence observed at 10:33 UTC" in reports[0]
    assert "descent by B77W" in reports[0]


@pytest.mark.unit
def test_jma_fcst_amd_trends_decoded():
    """FCST AMD trend blocks in Japanese RMK are decoded."""
    _, decoded = RemarksParser().parse(
        rmk(
            "FCST AMD 0715 TEMPO 0708 4000 FEW015CU SCT020CU "
            "BECMG 0809 -SHRA TEMPO 0911 NSW FEW015CU"
        )
    )
    assert decoded["Forecast Amendment"] == "Amended forecast issued at 07:15 UTC"
    trends = decoded["Forecast Trends"]
    assert "Temporary 07:00-08:00 UTC" in trends[0]
    assert "visibility 4.0km" in trends[0]
    assert "Becoming 08:00-09:00 UTC: light shower rain" in trends[1]
    assert "no significant weather" in trends[2]
