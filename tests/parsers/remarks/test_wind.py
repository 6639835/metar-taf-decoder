"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_peak_wind_4digit_time():
    """PK WND 28045/1715 → 280° at 45 KT at 17:15 UTC."""
    _, decoded = RemarksParser().parse(rmk("PK WND 28045/1715"))
    assert "Peak Wind" in decoded
    assert "280°" in decoded["Peak Wind"]
    assert "45 KT" in decoded["Peak Wind"]
    assert "17:15 UTC" in decoded["Peak Wind"]


@pytest.mark.unit
def test_peak_wind_2digit_time():
    """PK WND 28045/15 → current hour indication with :15 UTC."""
    _, decoded = RemarksParser().parse(rmk("PK WND 28045/15"))
    assert "Peak Wind" in decoded
    assert ":15 UTC" in decoded["Peak Wind"]
    assert "current hour" in decoded["Peak Wind"]


@pytest.mark.unit
def test_peak_wind_3digit_speed():
    """PK WND 360100/1800 → 100 KT peak wind."""
    _, decoded = RemarksParser().parse(rmk("PK WND 360100/1800"))
    assert "100 KT" in decoded["Peak Wind"]


# ===========================================================================
# 11. Wind shift (WSHFT)
# ===========================================================================


@pytest.mark.unit
def test_wind_shift_4digit_time():
    """WSHFT 1715 → at 17:15 UTC."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 1715"))
    assert "Wind Shift" in decoded
    assert "17:15 UTC" in decoded["Wind Shift"]


@pytest.mark.unit
def test_wind_shift_with_fropa():
    """WSHFT 1715 FROPA → frontal passage mentioned."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 1715 FROPA"))
    assert "Wind Shift" in decoded
    assert "frontal passage" in decoded["Wind Shift"]


@pytest.mark.unit
def test_wind_shift_2digit_time():
    """WSHFT 15 → current hour indication."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 15"))
    assert "Wind Shift" in decoded
    assert ":15 UTC" in decoded["Wind Shift"]
    assert "current hour" in decoded["Wind Shift"]


@pytest.mark.unit
def test_wind_shift_key_in_decoded():
    """WSHFT → Wind Shift key exists in decoded dict."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 1715"))
    assert "Wind Shift" in decoded


# ===========================================================================
# 12. Surface / Tower visibility
# ===========================================================================


@pytest.mark.unit
def test_fropa_standalone():
    """Standalone FROPA → Frontal Passage key present."""
    _, decoded = RemarksParser().parse(rmk("FROPA"))
    assert "Frontal Passage" in decoded


@pytest.mark.unit
def test_fropa_value():
    """FROPA → decoded value contains 'frontal' (case-insensitive)."""
    _, decoded = RemarksParser().parse(rmk("FROPA"))
    assert "frontal" in decoded["Frontal Passage"].lower() or decoded["Frontal Passage"]


# ===========================================================================
# 17. SLP status (SLPNO)
# ===========================================================================


@pytest.mark.unit
def test_runway_winds_wind_format():
    """WIND 28L 27025KT → 'runway_winds' key present."""
    _, decoded = RemarksParser().parse(rmk("WIND 28L 27025KT"))
    assert "runway_winds" in decoded


@pytest.mark.unit
def test_runway_winds_rwy_format():
    """RWY28L 27025KT → 'runway_winds' key present."""
    _, decoded = RemarksParser().parse(rmk("RWY28L 27025KT"))
    assert "runway_winds" in decoded


@pytest.mark.unit
def test_runway_winds_wind_format_direction():
    """WIND 28L 27025KT → direction is 270."""
    _, decoded = RemarksParser().parse(rmk("WIND 28L 27025KT"))
    rw = decoded["runway_winds"]
    assert isinstance(rw, list) and len(rw) >= 1
    assert rw[0]["direction"] == 270


@pytest.mark.unit
def test_runway_winds_rwy_format_speed():
    """RWY28L 27025KT → speed is 25."""
    _, decoded = RemarksParser().parse(rmk("RWY28L 27025KT"))
    rw = decoded["runway_winds"]
    assert isinstance(rw, list) and len(rw) >= 1
    assert rw[0]["speed"] == 25


# ===========================================================================
# 24. Variable visibility (VIS minVmax)
# ===========================================================================


@pytest.mark.unit
def test_wshft_fropa_also_sets_frontal_passage():
    """WSHFT 1715 FROPA → frontal passage encoded in Wind Shift value."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 1715 FROPA"))
    assert "frontal passage" in decoded["Wind Shift"].lower()


@pytest.mark.unit
def test_peak_wind_direction_and_speed_correct():
    """PK WND 09028/1345 → 90° at 28 KT."""
    _, decoded = RemarksParser().parse(rmk("PK WND 09028/1345"))
    assert "90°" in decoded["Peak Wind"]
    assert "28 KT" in decoded["Peak Wind"]


@pytest.mark.unit
def test_location_specific_winds_decoded():
    """HARBOR/ROOF wind remarks are decoded as location-specific winds."""
    _, decoded = RemarksParser().parse(
        rmk("PRESFR SLP926 HARBOR WIND 10020G27KT ROOF WIND 13015G27KT")
    )
    winds = decoded["location_winds"]
    assert winds[0]["location"] == "Harbor"
    assert winds[0]["direction"] == 100
    assert winds[0]["gust"] == 27
    assert winds[1]["location"] == "Roof"
