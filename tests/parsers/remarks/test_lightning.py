"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_lightning_contains_info():
    """LTGCG DSNT SW → decoded lightning value contains meaningful text."""
    _, decoded = RemarksParser().parse(rmk("LTGCG DSNT SW"))
    val = decoded.get("Lightning", "")
    assert len(val) > 0


@pytest.mark.unit
def test_lightning_without_type_is_supported():
    """LTG DSNT W is valid in FMH-1 and should still decode."""
    _, decoded = RemarksParser().parse(rmk("LTG DSNT W"))
    assert "Lightning" in decoded
    assert "lightning" in decoded["Lightning"].lower()


@pytest.mark.unit
def test_lightning_frequency_without_type_is_supported():
    """FRQ LTG VC is valid in FMH-1 and should still decode."""
    _, decoded = RemarksParser().parse(rmk("FRQ LTG VC"))
    assert "Lightning" in decoded
    assert "frequent" in decoded["Lightning"].lower()


# ===========================================================================
# 14. Thunderstorm location (TS)
# ===========================================================================


@pytest.mark.unit
def test_ts_ohd_mov_ne():
    """TS OHD MOV NE → Thunderstorm Location key present."""
    _, decoded = RemarksParser().parse(rmk("TS OHD MOV NE"))
    assert "Thunderstorm Location" in decoded


@pytest.mark.unit
def test_ts_dsnt_nw():
    """TS DSNT NW → Thunderstorm Location key present."""
    _, decoded = RemarksParser().parse(rmk("TS DSNT NW"))
    assert "Thunderstorm Location" in decoded


@pytest.mark.unit
def test_ts_ohd_contains_overhead():
    """TS OHD MOV NE → decoded value mentions 'overhead'."""
    _, decoded = RemarksParser().parse(rmk("TS OHD MOV NE"))
    assert "overhead" in decoded["Thunderstorm Location"].lower()


@pytest.mark.unit
def test_ts_dsnt_contains_distant():
    """TS DSNT NW → decoded value mentions 'distant'."""
    _, decoded = RemarksParser().parse(rmk("TS DSNT NW"))
    assert "distant" in decoded["Thunderstorm Location"].lower()


@pytest.mark.unit
def test_thunderstorm_begin_end_remarks():
    """TSB0159E30 should decode under a thunderstorm-specific key."""
    _, decoded = RemarksParser().parse(rmk("TSB0159E30"))
    assert "Thunderstorm Begin/End Times" in decoded
    assert "thunderstorm began" in decoded["Thunderstorm Begin/End Times"].lower()


# ===========================================================================
# 15. Pressure change (PRESFR / PRESRR)
# ===========================================================================


@pytest.mark.unit
def test_thunderstorm_begin_end_repeated_chain():
    """TSB12E13B20 → all begin/end events are decoded."""
    _, decoded = RemarksParser().parse(
        "METAR KPHX 190651Z 03008KT 10SM TS SCT100CB 26/20 A2984 RMK TSB12E13B20"
    )
    value = decoded["Thunderstorm Begin/End Times"]
    assert "06:12 UTC: thunderstorm began" in value
    assert "06:13 UTC: thunderstorm ended" in value
    assert "06:20 UTC: thunderstorm began" in value


@pytest.mark.unit
def test_jma_thunderstorm_intensity_distance_and_stationary():
    """FBL TS 5KM W MOV STN keeps intensity, distance, direction, and movement."""
    _, decoded = RemarksParser().parse(rmk("FBL TS 5KM W MOV STN"))
    value = decoded["Thunderstorm Location"]
    assert "feeble" in value
    assert "5 km to the west" in value
    assert "stationary" in value


@pytest.mark.unit
def test_stationary_not_decoded_as_south_movement():
    """MOV STNRY must decode as stationary, not as movement south."""
    _, decoded = RemarksParser().parse(rmk("TS SW-W MOV STNRY"))
    value = decoded["Thunderstorm Location"]
    assert "stationary" in value
    assert "moving south" not in value.lower()
