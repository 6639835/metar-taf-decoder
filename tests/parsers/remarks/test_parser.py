"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_no_rmk_returns_empty_string():
    """No RMK token: raw_remarks should be an empty string."""
    raw, decoded = RemarksParser().parse(
        "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
    )
    assert raw == ""


@pytest.mark.unit
def test_no_rmk_returns_empty_dict():
    """No RMK token: decoded dict should be empty."""
    raw, decoded = RemarksParser().parse(
        "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
    )
    assert decoded == {}


# ===========================================================================
# 2. Raw remarks string sanity
# ===========================================================================


@pytest.mark.unit
def test_raw_remarks_does_not_include_rmk_keyword():
    """raw_remarks must NOT start with the literal 'RMK'."""
    raw, _ = RemarksParser().parse(rmk("AO2 SLP021"))
    assert not raw.startswith("RMK")


@pytest.mark.unit
def test_raw_remarks_equals_text_after_rmk():
    """raw_remarks should be exactly the text following 'RMK '."""
    raw, _ = RemarksParser().parse(rmk("AO2 SLP021 T02220183"))
    assert raw == "AO2 SLP021 T02220183"


@pytest.mark.unit
def test_raw_remarks_single_token():
    """A single-token RMK produces the token itself as raw_remarks."""
    raw, _ = RemarksParser().parse(rmk("AO2"))
    assert raw == "AO2"


# ===========================================================================
# 3. Station type (AO1 / AO2 / A02A)
# ===========================================================================


@pytest.mark.unit
def test_bare_8_digit_remark_is_not_runway_state():
    """METAR runway state uses RDRDR/ERCReReRBRBR, not a bare 8-digit remark."""
    _, decoded = RemarksParser().parse(rmk("AO2 83311195"))
    assert "Runway State (Remarks)" not in decoded


@pytest.mark.unit
def test_multiple_remark_items_all_present():
    """AO2 SLP021 T02220183 → three keys decoded."""
    metar = (
        "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992 RMK AO2 SLP021 T02220183"
    )
    _, decoded = RemarksParser().parse(metar)
    assert "Station Type" in decoded
    assert "Sea Level Pressure" in decoded
    assert "Temperature (tenths)" in decoded


@pytest.mark.unit
def test_multiple_remark_items_values_correct():
    """AO2 SLP021 T02220183 → each decoded value is correct."""
    metar = (
        "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992 RMK AO2 SLP021 T02220183"
    )
    _, decoded = RemarksParser().parse(metar)
    assert decoded["Sea Level Pressure"] == "1002.1 hPa"
    assert decoded["Temperature (tenths)"] == "22.2°C"
    assert decoded["Dewpoint (tenths)"] == "18.3°C"


# ===========================================================================
# 27. Density altitude
# ===========================================================================


@pytest.mark.unit
def test_raw_remarks_multiple_tokens_preserves_all():
    """Raw remarks must contain all tokens from the RMK section."""
    remark_text = "AO2 SLP021 T02220183 $"
    raw, _ = RemarksParser().parse(rmk(remark_text))
    assert raw == remark_text
