"""Remarks parser behavior tests."""

import pytest

from weather_decoder.parsers.remarks import RemarksParser

from .helpers import rmk


@pytest.mark.unit
def test_slp_above_500():
    """SLP021 → 1002.1 hPa (value < 500 → add to 1000)."""
    _, decoded = RemarksParser().parse(rmk("AO2 SLP021"))
    assert "Sea Level Pressure" in decoded
    assert decoded["Sea Level Pressure"] == "1002.1 hPa"


@pytest.mark.unit
def test_slp_below_500():
    """SLP521 → 952.1 hPa (value >= 500 → add to 900)."""
    _, decoded = RemarksParser().parse(rmk("SLP521"))
    assert "Sea Level Pressure" in decoded
    assert decoded["Sea Level Pressure"] == "952.1 hPa"


@pytest.mark.unit
def test_slp_boundary_500():
    """SLP500 is exactly on the boundary → 950.0 hPa."""
    _, decoded = RemarksParser().parse(rmk("SLP500"))
    assert "Sea Level Pressure" in decoded
    assert decoded["Sea Level Pressure"] == "950.0 hPa"


@pytest.mark.unit
def test_slp_000():
    """SLP000 → 1000.0 hPa."""
    _, decoded = RemarksParser().parse(rmk("SLP000"))
    assert decoded["Sea Level Pressure"] == "1000.0 hPa"


# ===========================================================================
# 5. Temperature to tenths (T group)
# ===========================================================================


@pytest.mark.unit
def test_pressure_tendency_present():
    """58020 → Pressure Tendency key present."""
    _, decoded = RemarksParser().parse(rmk("58020"))
    assert "Pressure Tendency" in decoded


@pytest.mark.unit
def test_pressure_tendency_value():
    """58020 → change of 2.0 hPa in the decoded string."""
    _, decoded = RemarksParser().parse(rmk("58020"))
    assert "2.0 hPa" in decoded["Pressure Tendency"]


@pytest.mark.unit
def test_pressure_tendency_zero():
    """50000 → change of 0.0 hPa."""
    _, decoded = RemarksParser().parse(rmk("50000"))
    assert "0.0 hPa" in decoded["Pressure Tendency"]


# ===========================================================================
# 7. 24-hour temperature extremes (4snTTTsnTTT)
# ===========================================================================


@pytest.mark.unit
def test_24hr_temp_extremes_present():
    """402500183 → both 24-hour max and min temperature keys.

    Format: 4 + sign(0/1) + TTT + sign(0/1) + TTT  (9 chars total after the '4').
    402500183 = 4 | 0 (pos) | 250 (max=25.0) | 0 (pos) | 183 (min=18.3).
    """
    _, decoded = RemarksParser().parse(rmk("402500183"))
    assert (
        "24-Hour Maximum Temperature" in decoded
        or "24-Hour Minimum Temperature" in decoded
    )


@pytest.mark.unit
def test_6hr_max_temperature_present():
    """10250 → 6-Hour Maximum Temperature key present."""
    _, decoded = RemarksParser().parse(rmk("10250"))
    assert "6-Hour Maximum Temperature" in decoded


@pytest.mark.unit
def test_6hr_min_temperature_present():
    """20183 → 6-Hour Minimum Temperature key present."""
    _, decoded = RemarksParser().parse(rmk("20183"))
    assert "6-Hour Minimum Temperature" in decoded


@pytest.mark.unit
def test_6hr_precipitation_present():
    """60021 → 6-Hour Precipitation key present."""
    _, decoded = RemarksParser().parse(rmk("60021"))
    assert "6-Hour Precipitation" in decoded


@pytest.mark.unit
def test_surface_visibility_present():
    """SFC VIS 3 → Surface Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("SFC VIS 3"))
    assert "Surface Visibility" in decoded
    assert decoded["Surface Visibility"] is not None


@pytest.mark.unit
def test_tower_visibility_present():
    """TWR VIS 5 → Tower Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("TWR VIS 5"))
    assert "Tower Visibility" in decoded
    assert decoded["Tower Visibility"] is not None


@pytest.mark.unit
def test_lightning_present():
    """LTG DSNT SW → Lightning key present and non-empty."""
    _, decoded = RemarksParser().parse(rmk("LTGCG DSNT SW"))
    assert "Lightning" in decoded
    assert decoded["Lightning"]


@pytest.mark.unit
def test_presfr():
    """PRESFR → Pressure Change == 'Pressure falling rapidly'."""
    _, decoded = RemarksParser().parse(rmk("PRESFR"))
    assert decoded["Pressure Change"] == "Pressure falling rapidly"


@pytest.mark.unit
def test_presrr():
    """PRESRR → Pressure Change == 'Pressure rising rapidly'."""
    _, decoded = RemarksParser().parse(rmk("PRESRR"))
    assert decoded["Pressure Change"] == "Pressure rising rapidly"


# ===========================================================================
# 16. Frontal passage (FROPA)
# ===========================================================================


@pytest.mark.unit
def test_slpno_key_present():
    """SLPNO → SLP Status key present."""
    _, decoded = RemarksParser().parse(rmk("SLPNO"))
    assert "SLP Status" in decoded


@pytest.mark.unit
def test_slpno_value():
    """SLPNO → decoded value mentions 'not available' or similar."""
    _, decoded = RemarksParser().parse(rmk("SLPNO"))
    val = decoded["SLP Status"].lower()
    assert "not available" in val or "sea level pressure" in val


# ===========================================================================
# 18. RVR status (RVRNO)
# ===========================================================================


@pytest.mark.unit
def test_tornadic_activity_preserves_compass_direction():
    """TORNADO B13 6 NE should decode northeast, not north."""
    _, decoded = RemarksParser().parse(rmk("TORNADO B13 6 NE"))
    assert "Tornadic Activity" in decoded
    assert "northeast" in decoded["Tornadic Activity"].lower()


@pytest.mark.unit
def test_qfe_with_hpa():
    """QFE728/0971 → decoded QFE contains '728 mmHg'."""
    _, decoded = RemarksParser().parse(rmk("QFE728/0971"))
    assert "QFE" in decoded
    assert "728 mmHg" in decoded["QFE"]


@pytest.mark.unit
def test_qfe_without_hpa():
    """QFE728 (no hPa part) → decoded QFE contains '728 mmHg'."""
    _, decoded = RemarksParser().parse(rmk("QFE728"))
    assert "QFE" in decoded
    assert "728 mmHg" in decoded["QFE"]


@pytest.mark.unit
def test_qfe_with_hpa_value_included():
    """QFE728/0971 → decoded QFE contains the hPa figure."""
    _, decoded = RemarksParser().parse(rmk("QFE728/0971"))
    assert "971" in decoded["QFE"]


# ===========================================================================
# 20. Maintenance indicator ($)
# ===========================================================================


@pytest.mark.unit
def test_precipitation_amount_key_present():
    """P0021 → Precipitation Amount key present."""
    _, decoded = RemarksParser().parse(rmk("P0021"))
    assert "Precipitation Amount" in decoded


@pytest.mark.unit
def test_virga_key_present():
    """VIRGA → Virga key present."""
    _, decoded = RemarksParser().parse(rmk("VIRGA"))
    assert "Virga" in decoded


@pytest.mark.unit
def test_variable_visibility_key_present():
    """VIS 1V3 → Variable Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("VIS 1V3"))
    assert "Variable Visibility" in decoded


@pytest.mark.unit
def test_altimeter_remarks_key_present():
    """RMK A2992 → Altimeter (Remarks) key present."""
    _, decoded = RemarksParser().parse(rmk("A2992"))
    assert "Altimeter (Remarks)" in decoded


@pytest.mark.unit
def test_altimeter_remarks_value():
    """RMK A2992 → 29.92 inHg."""
    _, decoded = RemarksParser().parse(rmk("A2992"))
    assert decoded["Altimeter (Remarks)"] == "29.92 inHg"


# ===========================================================================
# 26. Multiple decoded items in one RMK
# ===========================================================================


@pytest.mark.unit
def test_density_altitude_key_present():
    """DENSITY ALT 3500FT → Density Altitude key present."""
    _, decoded = RemarksParser().parse(rmk("DENSITY ALT 3500FT"))
    assert "Density Altitude" in decoded


@pytest.mark.unit
def test_presfr_not_matched_as_presrr():
    """PRESFR must decode as falling, not rising."""
    _, decoded = RemarksParser().parse(rmk("PRESFR"))
    assert "falling" in decoded["Pressure Change"].lower()
    assert "rising" not in decoded["Pressure Change"].lower()


@pytest.mark.unit
def test_presrr_not_matched_as_presfr():
    """PRESRR must decode as rising, not falling."""
    _, decoded = RemarksParser().parse(rmk("PRESRR"))
    assert "rising" in decoded["Pressure Change"].lower()
    assert "falling" not in decoded["Pressure Change"].lower()


@pytest.mark.unit
def test_slp_key_absent_when_no_slp():
    """When no SLP token, Sea Level Pressure key must be absent."""
    _, decoded = RemarksParser().parse(rmk("AO2"))
    assert "Sea Level Pressure" not in decoded


@pytest.mark.unit
def test_multiple_lightning_groups_are_preserved():
    """Two LTG groups in one RMK should both appear in decoded output."""
    _, decoded = RemarksParser().parse(rmk("FRQ LTGCGIC VC FRQ LTGCG DSNT SW-NE"))
    value = decoded["Lightning"]
    assert "in vicinity" in value
    assert "distant to the southwest through northeast" in value
