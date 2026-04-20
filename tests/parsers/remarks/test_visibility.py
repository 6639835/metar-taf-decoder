"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_surface_visibility_value():
    """SFC VIS 3 → contains '3 SM'."""
    _, decoded = RemarksParser().parse(rmk("SFC VIS 3"))
    assert "3" in decoded["Surface Visibility"]


@pytest.mark.unit
def test_tower_visibility_value():
    """TWR VIS 5 → contains '5'."""
    _, decoded = RemarksParser().parse(rmk("TWR VIS 5"))
    assert "5" in decoded["Tower Visibility"]


@pytest.mark.unit
def test_tower_visibility_whole_plus_fraction():
    """TWR VIS 1 1/2 should preserve the mixed fraction."""
    _, decoded = RemarksParser().parse(rmk("TWR VIS 1 1/2"))
    assert decoded["Tower Visibility"] == "1 1/2 SM"


# ===========================================================================
# 13. Lightning
# ===========================================================================


@pytest.mark.unit
def test_variable_visibility_value():
    """VIS 1V3 → decoded value mentions both extents."""
    _, decoded = RemarksParser().parse(rmk("VIS 1V3"))
    val = decoded["Variable Visibility"]
    assert "1" in val and "3" in val


# ===========================================================================
# 25. Altimeter in remarks (Axxxx)
# ===========================================================================


@pytest.mark.unit
def test_visibility_lower_remark_decoded():
    """VIS LWR directional remarks are decoded."""
    _, decoded = RemarksParser().parse(rmk("VIS LWR NE-E-S"))
    assert (
        decoded["Visibility Lower"]
        == "Visibility lower to the northeast through east through south"
    )


@pytest.mark.unit
def test_jma_directional_visibility_decoded():
    """JMA compact directional visibility remarks are decoded."""
    _, decoded = RemarksParser().parse(rmk("3500E-S"))
    assert decoded["Directional Visibility (JMA)"] == [
        "3500 m to the east through south"
    ]
