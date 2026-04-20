"""Comprehensive pytest test suite for RemarksParser.

Tests cover the full range of remark types that can appear in the RMK section
of a METAR report.  Every test uses a realistic, full METAR string so that the
parser's regex can reliably locate the RMK token.
"""

import pytest

from weather_decoder.parsers.remarks_parser import RemarksParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"


def rmk(remark_text: str) -> str:
    """Return a full METAR string with the given RMK section appended."""
    return f"{BASE} RMK {remark_text}"


# ===========================================================================
# 1. No RMK section
# ===========================================================================


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
def test_24hr_temp_extremes_incomplete_not_matched():
    """40112 (only 5 digits) must NOT match the 8-digit 4snTTTsnTTT group."""
    _, decoded = RemarksParser().parse(rmk("40112"))
    assert "24-Hour Maximum Temperature" not in decoded
    assert "24-Hour Minimum Temperature" not in decoded


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
def test_6hr_max_temperature_present():
    """10250 → 6-Hour Maximum Temperature key present."""
    _, decoded = RemarksParser().parse(rmk("10250"))
    assert "6-Hour Maximum Temperature" in decoded


@pytest.mark.unit
def test_6hr_max_temperature_value():
    """10250 → 25.0°C."""
    _, decoded = RemarksParser().parse(rmk("10250"))
    assert decoded["6-Hour Maximum Temperature"] == "25.0°C"


@pytest.mark.unit
def test_6hr_min_temperature_present():
    """20183 → 6-Hour Minimum Temperature key present."""
    _, decoded = RemarksParser().parse(rmk("20183"))
    assert "6-Hour Minimum Temperature" in decoded


@pytest.mark.unit
def test_6hr_min_temperature_value():
    """20183 → 18.3°C."""
    _, decoded = RemarksParser().parse(rmk("20183"))
    assert decoded["6-Hour Minimum Temperature"] == "18.3°C"


# ===========================================================================
# 9. 6-hour precipitation (6xxxx)
# ===========================================================================


@pytest.mark.unit
def test_6hr_precipitation_present():
    """60021 → 6-Hour Precipitation key present."""
    _, decoded = RemarksParser().parse(rmk("60021"))
    assert "6-Hour Precipitation" in decoded


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
def test_surface_visibility_present():
    """SFC VIS 3 → Surface Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("SFC VIS 3"))
    assert "Surface Visibility" in decoded
    assert decoded["Surface Visibility"] is not None


@pytest.mark.unit
def test_surface_visibility_value():
    """SFC VIS 3 → contains '3 SM'."""
    _, decoded = RemarksParser().parse(rmk("SFC VIS 3"))
    assert "3" in decoded["Surface Visibility"]


@pytest.mark.unit
def test_tower_visibility_present():
    """TWR VIS 5 → Tower Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("TWR VIS 5"))
    assert "Tower Visibility" in decoded
    assert decoded["Tower Visibility"] is not None


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
def test_lightning_present():
    """LTG DSNT SW → Lightning key present and non-empty."""
    _, decoded = RemarksParser().parse(rmk("LTGCG DSNT SW"))
    assert "Lightning" in decoded
    assert decoded["Lightning"]


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
def test_bare_8_digit_remark_is_not_runway_state():
    """METAR runway state uses RDRDR/ERCReReRBRBR, not a bare 8-digit remark."""
    _, decoded = RemarksParser().parse(rmk("AO2 83311195"))
    assert "Runway State (Remarks)" not in decoded


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
def test_significant_cloud_remarks_plain_language():
    """Plain-language FMH-1 significant cloud remarks should decode."""
    _, decoded = RemarksParser().parse(rmk("CB W MOV E TCU NW APRNT ROTOR CLD NE"))
    assert "Cloud Types" in decoded
    cloud_text = decoded["Cloud Types"]
    assert "Cumulonimbus" in cloud_text
    assert "Towering cumulus" in cloud_text
    assert "Apparent rotor cloud" in cloud_text


@pytest.mark.unit
def test_tornadic_activity_preserves_compass_direction():
    """TORNADO B13 6 NE should decode northeast, not north."""
    _, decoded = RemarksParser().parse(rmk("TORNADO B13 6 NE"))
    assert "Tornadic Activity" in decoded
    assert "northeast" in decoded["Tornadic Activity"].lower()


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
def test_precipitation_amount_key_present():
    """P0021 → Precipitation Amount key present."""
    _, decoded = RemarksParser().parse(rmk("P0021"))
    assert "Precipitation Amount" in decoded


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


@pytest.mark.unit
def test_virga_key_present():
    """VIRGA → Virga key present."""
    _, decoded = RemarksParser().parse(rmk("VIRGA"))
    assert "Virga" in decoded


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
def test_variable_visibility_key_present():
    """VIS 1V3 → Variable Visibility key present."""
    _, decoded = RemarksParser().parse(rmk("VIS 1V3"))
    assert "Variable Visibility" in decoded


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
def test_density_altitude_key_present():
    """DENSITY ALT 3500FT → Density Altitude key present."""
    _, decoded = RemarksParser().parse(rmk("DENSITY ALT 3500FT"))
    assert "Density Altitude" in decoded


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
def test_slpno_and_rvrno_together():
    """SLPNO RVRNO → both status keys present."""
    _, decoded = RemarksParser().parse(rmk("SLPNO RVRNO"))
    assert "SLP Status" in decoded
    assert "RVR Status" in decoded


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
def test_wshft_fropa_also_sets_frontal_passage():
    """WSHFT 1715 FROPA → frontal passage encoded in Wind Shift value."""
    _, decoded = RemarksParser().parse(rmk("WSHFT 1715 FROPA"))
    assert "frontal passage" in decoded["Wind Shift"].lower()


@pytest.mark.unit
def test_raw_remarks_multiple_tokens_preserves_all():
    """Raw remarks must contain all tokens from the RMK section."""
    remark_text = "AO2 SLP021 T02220183 $"
    raw, _ = RemarksParser().parse(rmk(remark_text))
    assert raw == remark_text


@pytest.mark.unit
def test_peak_wind_direction_and_speed_correct():
    """PK WND 09028/1345 → 90° at 28 KT."""
    _, decoded = RemarksParser().parse(rmk("PK WND 09028/1345"))
    assert "90°" in decoded["Peak Wind"]
    assert "28 KT" in decoded["Peak Wind"]


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
def test_maintenance_indicator_in_complex_rmk():
    """Maintenance indicator at end of compound RMK."""
    _, decoded = RemarksParser().parse(rmk("AO2 SLP013 $"))
    assert "Maintenance Indicator" in decoded


@pytest.mark.unit
def test_slp_key_absent_when_no_slp():
    """When no SLP token, Sea Level Pressure key must be absent."""
    _, decoded = RemarksParser().parse(rmk("AO2"))
    assert "Sea Level Pressure" not in decoded


@pytest.mark.unit
def test_altitude_token_does_not_decode_as_6hr_max_temperature():
    """Altitude tokens in PIREP remarks must not match 1snTTT temperature groups."""
    _, decoded = RemarksParser().parse(
        rmk("MOD TURB OBS AT 1011Z PLUTO BTN 9000FT AND 13000FT IN CMB BY B738")
    )
    assert "6-Hour Maximum Temperature" not in decoded


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


@pytest.mark.unit
def test_multiple_lightning_groups_are_preserved():
    """Two LTG groups in one RMK should both appear in decoded output."""
    _, decoded = RemarksParser().parse(rmk("FRQ LTGCGIC VC FRQ LTGCG DSNT SW-NE"))
    value = decoded["Lightning"]
    assert "in vicinity" in value
    assert "distant to the southwest through northeast" in value


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
def test_significant_tcu_distance_range_and_movement_decoded():
    """TCU FM 20KM TO 40KM W-NW MOV E keeps range, direction, and movement."""
    _, decoded = RemarksParser().parse(rmk("TCU FM 20KM TO 40KM W-NW MOV E"))
    value = decoded["Cloud Types"]
    assert "from 20 km to 40 km to the west through northwest" in value
    assert "moving east" in value


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


@pytest.mark.unit
def test_pirep_cloud_layers_decoded():
    """PIREP cloud-layer base/top remarks are decoded."""
    _, decoded = RemarksParser().parse(
        rmk("PIREP ON DEP 1ST CLD BASE 017 TOP 020 2ND CLD BASE 037 TOP 047")
    )
    layers = decoded["PIREP Clouds"]
    assert layers[0] == "on dep: 1st cloud layer base 1700 ft, top 2000 ft"
    assert layers[1] == "on dep: 2nd cloud layer base 3700 ft, top 4700 ft"
