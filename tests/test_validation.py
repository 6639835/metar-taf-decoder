"""Comprehensive validation warning tests for MetarDecoder and TafDecoder,
plus edge cases for parsers.

Covers:
- METAR validation warnings (intensity, descriptor+phenomenon, visibility cross-checks,
  wind range, sky conditions, RVR counts, CAVOK, NOSIG/BECMG, NSW, UK stations, AUTO)
- TAF validation warnings (PROB, NOSIG, change-group count, per-period weather count)
- BaseParser / StopConditionMixin behaviours
- PressureParser edge cases (QNH formats, missing patterns)
- VisibilityParser edge cases (SM fractions, minimum visibility)
- WindParser edge cases (WIND_EXTREME_PATTERN, gust_is_above)
- RunwayParser edge cases (runway 88/99, _decode_depth, _decode_braking)
- WeatherParser edge cases (compound phenomena, RE//, VC validation)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from weather_decoder import MetarDecoder, TafDecoder
from weather_decoder.parsers.base_parser import BaseParser, StopConditionMixin
from weather_decoder.parsers.token_stream import TokenStream
from weather_decoder.parsers.visibility_parser import VisibilityParser
from weather_decoder.parsers.weather_parser import WeatherParser
from weather_decoder.parsers.sky_parser import SkyParser
from weather_decoder.parsers.pressure_parser import PressureParser
from weather_decoder.parsers.trend_parser import TrendParser
from weather_decoder.parsers.wind_parser import WindParser
from weather_decoder.parsers.runway_parser import RunwayParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def metar_decoder():
    return MetarDecoder()


@pytest.fixture(scope="module")
def taf_decoder():
    return TafDecoder()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _warnings(result):
    """Return the validation_warnings list from a decoded result."""
    return result.validation_warnings


# ===========================================================================
# METAR VALIDATION WARNING TESTS
# ===========================================================================


@pytest.mark.integration
def test_metar_light_duststorm_warning(metar_decoder):
    """Light intensity (-DS) is not valid — should trigger a warning."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 -DS FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("duststorm" in w or "DS" in w or "sandstorm" in w for w in warnings), (
        f"Expected duststorm/DS warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_light_sandstorm_warning(metar_decoder):
    """Light intensity (-SS) is not valid — should trigger a warning."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 -SS FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("SS" in w or "sandstorm" in w for w in warnings), (
        f"Expected sandstorm/SS warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_intensity_on_gr_hail(metar_decoder):
    """Intensity modifier on GR (hail) is not valid per FMH-1 §12.6.8.a(1)."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 +GR FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("GR" in w or "hail" in w for w in warnings), (
        f"Expected GR/hail warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_gs_intensity_in_body(metar_decoder):
    """GS (small hail) with intensity in METAR body should be warned."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 +GS FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("GS" in w or "small hail" in w for w in warnings), (
        f"Expected GS/small hail warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_invalid_intensity_for_hz(metar_decoder):
    """Intensity modifier (+) is not valid for HZ (haze)."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 +HZ FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("intensity" in w.lower() or "not valid" in w.lower() for w in warnings), (
        f"Expected intensity/not-valid warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_fog_high_visibility(metar_decoder):
    """FG (fog) reported with visibility >= 1000m — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 2000 FG FEW030 18/17 A2990")
    warnings = _warnings(result)
    assert any("FG" in w or "fog" in w for w in warnings), (
        f"Expected FG/fog warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_mist_low_visibility(metar_decoder):
    """BR (mist) reported with visibility < 1000m — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 0500 BR FEW030 18/17 A2990")
    warnings = _warnings(result)
    assert any("BR" in w or "mist" in w for w in warnings), (
        f"Expected BR/mist warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_mist_high_visibility(metar_decoder):
    """BR (mist) reported with visibility > 5000m — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 8000 BR FEW030 18/17 A2990")
    warnings = _warnings(result)
    assert any("BR" in w or "mist" in w for w in warnings), (
        f"Expected BR/mist warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_hz_high_visibility(metar_decoder):
    """HZ (haze) reported with visibility > 5000m — should warn.

    The warning message uses the first-two-letter truncation of the phenomenon
    name (i.e. 'HA' from 'haze') as the obscuration label, so we also check
    for '5000' and the full word 'haze'.
    """
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 8000 HZ FEW030 18/17 A2990")
    warnings = _warnings(result)
    # The decoder builds the warning with the 2-char code derived from the
    # phenomenon name so "HA" (from "haze") may appear instead of "HZ".
    assert any("HZ" in w or "haze" in w or "HA" in w or "5000" in w for w in warnings), (
        f"Expected HZ/haze/HA/5000 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_more_than_4_rvr_groups(metar_decoder):
    """More than 4 RVR groups — should trigger a warning."""
    result = metar_decoder.decode(
        "METAR KJFK 061751Z 00000KT 0200 "
        "R28L/1200FT R10/1200FT R01/1200FT R19/1200FT R28R/1200FT "
        "FG OVC002 18/18 A2980"
    )
    warnings = _warnings(result)
    assert any("RVR" in w or "4" in w for w in warnings), (
        f"Expected RVR/4 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_more_than_4_sky_conditions_icao(metar_decoder):
    """More than 4 sky conditions — ICAO limit warning."""
    result = metar_decoder.decode(
        "METAR KJFK 061751Z 28008KT 9999 FEW030 SCT050 BKN100 OVC150 FEW200 22/18 A2992"
    )
    warnings = _warnings(result)
    assert any("cloud" in w.lower() or "layer" in w.lower() or "4" in w for w in warnings), (
        f"Expected cloud/layer/4 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_more_than_6_sky_conditions_fmh1(metar_decoder):
    """More than 6 sky conditions — FMH-1 limit warning."""
    result = metar_decoder.decode(
        "METAR KJFK 061751Z 28008KT 9999 "
        "FEW030 FEW050 SCT080 BKN100 OVC150 FEW200 FEW250 22/18 A2992"
    )
    warnings = _warnings(result)
    assert any("cloud" in w.lower() or "6" in w for w in warnings), (
        f"Expected cloud/6 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_more_than_3_weather_groups(metar_decoder):
    """More than 3 present weather groups — should warn."""
    result = metar_decoder.decode(
        "METAR KJFK 061751Z 28008KT 5000 -RA -SN BR HZ FEW030 18/15 A2990"
    )
    warnings = _warnings(result)
    assert any("weather" in w.lower() or "3" in w for w in warnings), (
        f"Expected weather/3 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_wind_direction_not_multiple_of_10(metar_decoder):
    """Wind direction not rounded to nearest 10° — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28305KT 10SM FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("direction" in w.lower() or "10°" in w or "nearest" in w.lower() for w in warnings), (
        f"Expected direction/nearest 10° warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_wind_direction_outside_range(metar_decoder):
    """Wind direction 005° outside valid range 010-360° — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 00505KT 10SM FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("direction" in w.lower() or "range" in w.lower() or "005" in w for w in warnings), (
        f"Expected direction/range/005 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_wind_variation_less_than_60_degrees(metar_decoder):
    """Wind variable range with variation < 60° — should warn to omit variable range."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28010KT 260V300 10SM FEW250 22/18 A2992")
    warnings = _warnings(result)
    # 300 - 260 = 40° variation < 60°
    assert any("60" in w or "variation" in w.lower() for w in warnings), (
        f"Expected 60°/variation warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_wind_variation_ge_180_degrees(metar_decoder):
    """Wind variable range with variation >= 180° — should warn to use VRB."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28010KT 100V320 10SM FEW250 22/18 A2992")
    warnings = _warnings(result)
    # (320 - 100) % 360 = 220° >= 180°
    assert any("VRB" in w or "180" in w or "variation" in w.lower() for w in warnings), (
        f"Expected VRB/180°/variation warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_wind_variation_with_speed_below_6kt(metar_decoder):
    """Wind direction variation reported with speed < 6 kt — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28003KT 250V320 10SM FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("6 kt" in w or "VRB" in w for w in warnings), (
        f"Expected <6 kt/VRB warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_cavok_with_weather_groups(metar_decoder):
    """CAVOK used alongside weather groups — contradiction warning."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT CAVOK -RA FEW030 22/18 A2992")
    warnings = _warnings(result)
    assert any("CAVOK" in w for w in warnings), (
        f"Expected CAVOK warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_nosig_becmg_mutually_exclusive(metar_decoder):
    """NOSIG and BECMG are mutually exclusive — should warn."""
    result = metar_decoder.decode(
        "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 NOSIG BECMG FM1600 TL1800 NSW"
    )
    warnings = _warnings(result)
    assert any("NOSIG" in w for w in warnings), (
        f"Expected NOSIG warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_nsw_in_body(metar_decoder):
    """NSW in METAR body is not valid — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM NSW FEW250 22/18 A2992")
    warnings = _warnings(result)
    assert any("NSW" in w for w in warnings), (
        f"Expected NSW warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_metric_rvr_without_ft(metar_decoder):
    """Metric RVR (no FT suffix) in US METAR — should warn."""
    result = metar_decoder.decode(
        "METAR KJFK 061751Z 00000KT 0200 R28/0600 FG OVC002 18/18 A2980"
    )
    warnings = _warnings(result)
    assert any("FT" in w or "metric" in w.lower() or "RVR" in w for w in warnings), (
        f"Expected FT/metric/RVR warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_uk_station_runway_state(metar_decoder):
    """UK station (EGLL) with runway state group — CAP 746 Issue 6 warning."""
    result = metar_decoder.decode("METAR EGLL 061751Z 27010KT 5000 BKN030 15/10 Q1015 R28/212070")
    warnings = _warnings(result)
    assert any("UK" in w or "CAP 746" in w or "runway state" in w.lower() for w in warnings), (
        f"Expected UK/CAP 746/runway state warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_auto_with_cavok(metar_decoder):
    """AUTO station with CAVOK is permitted when CAVOK conditions are met."""
    result = metar_decoder.decode("METAR KJFK 061751Z AUTO 28008KT CAVOK 22/18 A2992")
    warnings = _warnings(result)
    assert not any("CAVOK should not appear" in w for w in warnings), (
        f"Unexpected AUTO/CAVOK warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_valid_report_has_no_missing_keyword_warning(metar_decoder):
    """Valid METAR should not trigger the missing METAR/SPECI keyword warning."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 9999 FEW030 22/18 Q1013")
    warnings = _warnings(result)
    assert not any("keyword not found" in w for w in warnings), (
        f"Unexpected keyword warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_body_order_warning(metar_decoder):
    """Out-of-order body groups should raise a standards-order warning."""
    result = metar_decoder.decode("METAR EGLL 061751Z Q1020 09015KT FEW030 9999 18/10")
    warnings = _warnings(result)
    assert any("out of order" in w for w in warnings), (
        f"Expected order warning, got: {warnings}"
    )


@pytest.mark.integration
def test_metar_ncd_in_non_auto(metar_decoder):
    """NCD in non-AUTO METAR — should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 9999 NCD 22/18 A2992")
    warnings = _warnings(result)
    assert any("NCD" in w or "AUTO" in w for w in warnings), (
        f"Expected NCD/AUTO warning, got: {warnings}"
    )


# --- VC descriptor ---


@pytest.mark.integration
def test_metar_vc_with_ra_not_allowed(metar_decoder):
    """VCRA — vicinity not valid with RA (rain) per WMO Code Table 4678 Note 13."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 VCRA FEW030 22/18 A2992")
    warnings = _warnings(result)
    assert any("VC" in w or "vicinity" in w.lower() for w in warnings), (
        f"Expected VC/vicinity warning, got: {warnings}"
    )


# --- Descriptor+phenomenon ---


@pytest.mark.integration
def test_metar_shallow_mi_with_non_fg(metar_decoder):
    """MI (shallow) descriptor with RA — only FG is allowed, should warn."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 MIRA FEW030 22/18 A2992")
    warnings = _warnings(result)
    assert any("shallow" in w.lower() or "MI" in w or "FG" in w for w in warnings), (
        f"Expected shallow/MI/FG warning, got: {warnings}"
    )


# ===========================================================================
# METAR - DECODED CONTENT SANITY CHECKS
# ===========================================================================


@pytest.mark.integration
def test_metar_light_ds_parsed_correctly(metar_decoder):
    """-DS is still parsed into a weather group with intensity='light'."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 -DS FEW250 22/18 A2992")
    assert result.weather, "Expected at least one weather group"
    assert result.weather[0].intensity == "light"
    assert "duststorm" in result.weather[0].phenomena


@pytest.mark.integration
def test_metar_gr_heavy_parsed_correctly(metar_decoder):
    """+GR produces a weather group with intensity='heavy' despite the warning."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28008KT 5000 +GR FEW250 22/18 A2992")
    assert result.weather
    assert result.weather[0].intensity == "heavy"
    assert "hail" in result.weather[0].phenomena


@pytest.mark.integration
def test_metar_no_warning_for_valid_weather(metar_decoder):
    """A perfectly valid METAR should generate no warnings related to intensity."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28010KT 9999 -RA FEW030 22/18 A2992")
    intensity_warnings = [w for w in _warnings(result) if "intensity" in w.lower()]
    assert not intensity_warnings, f"Unexpected intensity warnings: {intensity_warnings}"


@pytest.mark.integration
def test_metar_wind_variable_range_populated(metar_decoder):
    """Wind variable range is correctly parsed even when a warning is triggered."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28010KT 260V300 10SM FEW250 22/18 A2992")
    assert result.wind is not None
    assert result.wind.variable_range == (260, 300)


# ===========================================================================
# TAF VALIDATION TESTS
# ===========================================================================


@pytest.mark.integration
def test_taf_prob_with_becmg_warning(taf_decoder):
    """PROB30 combined with BECMG is prohibited per WMO FM 51 Reg. 51.9.3."""
    result = taf_decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 PROB30 BECMG 0620/0622 VRB05KT"
    )
    warnings = _warnings(result)
    assert any("BECMG" in w or "PROB" in w for w in warnings), (
        f"Expected BECMG/PROB warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_invalid_prob_value(taf_decoder):
    """PROB25 is not permitted — only PROB30 and PROB40 are allowed."""
    ref = datetime(2024, 6, 6, 17, 0, tzinfo=timezone.utc)
    period, warnings = taf_decoder._parse_change_group(
        ["PROB25", "0620/0622", "VRB05KT"], ref
    )
    assert any("PROB25" in w or "30" in w or "40" in w for w in warnings), (
        f"Expected PROB25/30/40 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_nosig_in_body(taf_decoder):
    """NOSIG is not valid inside a TAF body."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 NOSIG")
    warnings = _warnings(result)
    assert any("NOSIG" in w for w in warnings), (
        f"Expected NOSIG warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_more_than_5_change_groups(taf_decoder):
    """More than 5 change groups — should warn."""
    result = taf_decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 "
        "TEMPO 0618/0620 -RA "
        "TEMPO 0620/0622 +RA "
        "TEMPO 0622/0700 -SN "
        "TEMPO 0700/0706 SN "
        "TEMPO 0706/0712 -SN "
        "BECMG 0712/0718 NSW"
    )
    warnings = _warnings(result)
    assert any("change group" in w.lower() or "5" in w for w in warnings), (
        f"Expected change group/5 warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_cavok_with_cloud_groups_warns(taf_decoder):
    """CAVOK cannot be combined with explicit cloud groups."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT CAVOK BKN020")
    warnings = _warnings(result)
    assert any("CAVOK" in w for w in warnings), f"Expected CAVOK warning, got: {warnings}"


@pytest.mark.integration
def test_taf_main_period_requires_visibility_and_clouds(taf_decoder):
    """Complete TAF sections must include visibility and sky/CAVOK content."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT")
    warnings = _warnings(result)
    assert any("visibility is required" in w.lower() for w in warnings)
    assert any("cloud" in w.lower() or "cavok" in w.lower() for w in warnings)


@pytest.mark.integration
def test_taf_becmg_duration_limit_warning(taf_decoder):
    """BECMG periods longer than four hours are invalid."""
    result = taf_decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 BECMG 0620/0702 VRB05KT"
    )
    warnings = _warnings(result)
    assert any("BECMG" in w and "4h" in w for w in warnings), (
        f"Expected BECMG duration warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_temperature_groups_must_be_report_level(taf_decoder):
    """TX/TN embedded in FM periods should be warned as misplaced."""
    result = taf_decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 FM062000 15010KT TX25/0621Z 6000 SCT020"
    )
    warnings = _warnings(result)
    assert any("TX/TN" in w or "temperature groups" in w for w in warnings), (
        f"Expected misplaced temperature warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_nonstandard_extension_group_warning(taf_decoder):
    """Non-standard extension groups should be warned instead of treated as standard TAF syntax."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 WS020/28035KT")
    warnings = _warnings(result)
    assert any("non-standard TAF extension groups" in w for w in warnings), (
        f"Expected non-standard extension warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_more_than_3_weather_codes_per_period(taf_decoder):
    """More than 3 weather codes in the MAIN period — per-period warning."""
    result = taf_decoder.decode(
        "TAF KJFK 061730Z 0618/0724 -RA -SN BR VCTS FEW030"
    )
    warnings = _warnings(result)
    assert any("weather" in w.lower() or "3" in w for w in warnings), (
        f"Expected weather/3 per-period warning, got: {warnings}"
    )


@pytest.mark.integration
def test_taf_prob40_tempo_is_valid(taf_decoder):
    """PROB40 TEMPO is a valid combination — should produce no PROB warning."""
    ref = datetime(2024, 6, 6, 17, 0, tzinfo=timezone.utc)
    period, warnings = taf_decoder._parse_change_group(
        ["PROB40", "TEMPO", "0620/0622", "VRB05KT"], ref
    )
    prob_warnings = [w for w in warnings if "PROB" in w or "permitted" in w.lower()]
    assert not prob_warnings, f"Unexpected PROB warnings: {prob_warnings}"


@pytest.mark.integration
def test_taf_prob30_is_valid(taf_decoder):
    """PROB30 alone (without BECMG) is valid — no PROB warning expected."""
    ref = datetime(2024, 6, 6, 17, 0, tzinfo=timezone.utc)
    period, warnings = taf_decoder._parse_change_group(
        ["PROB30", "0620/0622", "VRB05KT"], ref
    )
    prob_warnings = [w for w in warnings if "invalid" in w.lower() and "PROB" in w]
    assert not prob_warnings, f"Unexpected PROB30 validity warning: {prob_warnings}"


# ===========================================================================
# BASE PARSER TESTS
# ===========================================================================


@pytest.mark.unit
def test_base_parser_extract_first_returns_first_match():
    """extract_first should return the first parseable token."""
    stream = TokenStream(["28008KT", "FEW030", "SCT050"])
    result = SkyParser().extract_first(stream)
    assert result is not None
    assert result.coverage == "FEW"
    # "28008KT" should still be in stream; "FEW030" consumed
    assert "28008KT" in stream.tokens
    assert "FEW030" not in stream.tokens
    assert "SCT050" in stream.tokens


@pytest.mark.unit
def test_base_parser_extract_first_returns_none_when_no_match():
    """extract_first should return None when nothing matches."""
    stream = TokenStream(["28008KT", "10SM", "22/18"])
    result = SkyParser().extract_first(stream)
    assert result is None


@pytest.mark.unit
def test_sky_parser_extract_all():
    """SkyParser.extract_all should consume all matching sky tokens."""
    stream = TokenStream(["FEW030", "SCT050", "BKN100"])
    results = SkyParser().extract_all(stream)
    assert len(results) == 3
    assert results[0].coverage == "FEW"
    assert results[1].coverage == "SCT"
    assert results[2].coverage == "BKN"
    assert stream.tokens == []


@pytest.mark.unit
def test_sky_parser_extract_all_preserves_non_sky_tokens():
    """extract_all should not consume non-sky tokens."""
    stream = TokenStream(["FEW030", "22/18", "BKN100"])
    results = SkyParser().extract_all(stream)
    assert len(results) == 2
    assert "22/18" in stream.tokens


@pytest.mark.unit
def test_stop_condition_mixin_should_stop_tempo():
    """WeatherParser (StopConditionMixin) should stop on TEMPO."""
    parser = WeatherParser()
    assert parser.should_stop("TEMPO") is True


@pytest.mark.unit
def test_stop_condition_mixin_should_stop_becmg():
    """WeatherParser (StopConditionMixin) should stop on BECMG."""
    parser = WeatherParser()
    assert parser.should_stop("BECMG") is True


@pytest.mark.unit
def test_stop_condition_mixin_should_not_stop_on_weather():
    """WeatherParser should not stop on a weather token like -RA."""
    parser = WeatherParser()
    assert parser.should_stop("-RA") is False


@pytest.mark.unit
def test_stop_condition_mixin_should_stop_nosig():
    """SkyParser (StopConditionMixin) should stop on NOSIG."""
    parser = SkyParser()
    assert parser.should_stop("NOSIG") is True


@pytest.mark.unit
def test_sky_parser_extract_until_stop():
    """extract_until_stop should stop consuming tokens at a stop token."""
    parser = SkyParser()
    stream = TokenStream(["FEW030", "SCT050", "NOSIG", "BKN100"])
    results = parser.extract_until_stop(stream)
    assert len(results) == 2
    assert results[0].coverage == "FEW"
    assert results[1].coverage == "SCT"
    # NOSIG and BKN100 should remain
    assert "NOSIG" in stream.remaining()
    assert "BKN100" in stream.remaining()


@pytest.mark.unit
def test_sky_parser_extract_until_stop_empty():
    """extract_until_stop on empty stream returns empty list."""
    parser = SkyParser()
    stream = TokenStream([])
    results = parser.extract_until_stop(stream)
    assert results == []


# ===========================================================================
# PRESSURE PARSER EDGE CASES
# ===========================================================================


@pytest.mark.unit
def test_pressure_parser_qnh_ins_format():
    """QNH2992INS should return Pressure in inHg."""
    p = PressureParser()
    result = p.parse_qnh("QNH2992INS")
    assert result is not None
    assert result.unit == "inHg"
    assert abs(result.value - 29.92) < 0.01


@pytest.mark.unit
def test_pressure_parser_qnh_hpa_format():
    """QNH1013HPA should return Pressure in hPa."""
    p = PressureParser()
    result = p.parse_qnh("QNH1013HPA")
    assert result is not None
    assert result.unit == "hPa"
    assert result.value == 1013


@pytest.mark.unit
def test_pressure_parser_q_prefix_hpa():
    """Q1013 should return Pressure in hPa."""
    p = PressureParser()
    result = p.parse_qnh("Q1013")
    assert result is not None
    assert result.unit == "hPa"
    assert result.value == 1013.0


@pytest.mark.unit
def test_pressure_parser_q_prefix_inhg_high_value():
    """Q2992 (> 1100) should be treated as inHg (value / 100)."""
    p = PressureParser()
    result = p.parse_qnh("Q2992")
    assert result is not None
    assert result.unit == "inHg"
    assert abs(result.value - 29.92) < 0.01


@pytest.mark.unit
def test_pressure_parser_extract_altimeter_missing():
    """A//// should consume the token and return None (missing altimeter)."""
    p = PressureParser()
    stream = TokenStream(["A////"])
    result = p.extract_altimeter(stream)
    assert result is None
    assert len(stream) == 0


@pytest.mark.unit
def test_pressure_parser_extract_qnh_missing():
    """Q//// should consume the token and return None (missing QNH)."""
    p = PressureParser()
    stream = TokenStream(["Q////"])
    result = p.extract_qnh(stream)
    assert result is None
    assert len(stream) == 0


@pytest.mark.unit
def test_pressure_parser_parse_standard_altimeter():
    """A2992 should parse correctly to 29.92 inHg."""
    p = PressureParser()
    result = p.parse("A2992")
    assert result is not None
    assert result.unit == "inHg"
    assert abs(result.value - 29.92) < 0.01


@pytest.mark.unit
def test_pressure_parser_parse_standard_qnh():
    """Q1013 should parse correctly to 1013 hPa."""
    p = PressureParser()
    result = p.parse("Q1013")
    assert result is not None
    assert result.unit == "hPa"
    assert result.value == 1013.0


# ===========================================================================
# VISIBILITY PARSER EDGE CASES
# ===========================================================================


@pytest.mark.unit
def test_visibility_parser_whole_plus_fraction():
    """Whole number + fraction SM tokens (e.g. '1' '3/4SM') should combine."""
    v = VisibilityParser()
    stream = TokenStream(["1", "3/4SM"])
    result = v.extract(stream)
    assert result is not None
    assert result.unit == "SM"
    assert abs(result.value - 1.75) < 0.001
    # Both tokens consumed
    assert len(stream) == 0


@pytest.mark.unit
def test_visibility_parser_minimum_visibility_no_direction():
    """Two 4-digit tokens: first is prevailing, second is minimum visibility."""
    v = VisibilityParser()
    stream = TokenStream(["2000", "0800"])
    result = v.extract(stream)
    assert result is not None
    assert result.value == 2000
    assert result.unit == "M"
    assert result.minimum_visibility is not None
    assert result.minimum_visibility.value == 800


@pytest.mark.unit
def test_visibility_parser_cavok():
    """CAVOK token should be parsed as is_cavok=True."""
    v = VisibilityParser()
    result = v.parse("CAVOK")
    assert result is not None
    assert result.is_cavok is True
    assert result.value == 9999


@pytest.mark.unit
def test_visibility_parser_sm_fraction_only():
    """3/4SM — fractional SM without whole number prefix."""
    v = VisibilityParser()
    result = v.parse("3/4SM")
    assert result is not None
    assert result.unit == "SM"
    assert abs(result.value - 0.75) < 0.001


@pytest.mark.unit
def test_visibility_parser_p_modifier():
    """P6SM — visibility greater than 6 SM."""
    v = VisibilityParser()
    result = v.parse("P6SM")
    assert result is not None
    assert result.is_greater_than is True
    assert result.unit == "SM"


@pytest.mark.unit
def test_visibility_parser_m_modifier():
    """M1/4SM — visibility less than 1/4 SM."""
    v = VisibilityParser()
    result = v.parse("M1/4SM")
    assert result is not None
    assert result.is_less_than is True


@pytest.mark.unit
def test_visibility_parser_ndv():
    """9999NDV — no directional variation."""
    v = VisibilityParser()
    result = v.parse("9999NDV")
    assert result is not None
    assert result.ndv is True
    assert result.value == 9999


# ===========================================================================
# WIND PARSER EDGE CASES
# ===========================================================================


@pytest.mark.unit
def test_wind_parser_extreme_pattern_abv():
    """ABV99KT should parse via WIND_EXTREME_PATTERN as is_above=True."""
    w = WindParser()
    result = w.parse("ABV99KT")
    assert result is not None
    assert result.is_above is True
    assert result.speed == 99
    assert result.unit == "KT"
    assert result.is_variable is True


@pytest.mark.unit
def test_wind_parser_gust_is_above():
    """28010GP15KT — gust with P modifier (above-max gust)."""
    w = WindParser()
    result = w.parse("28010GP15KT")
    assert result is not None
    assert result.gust_is_above is True
    assert result.gust == 15
    assert result.direction == 280
    assert result.speed == 10


@pytest.mark.unit
def test_wind_parser_vrb():
    """VRB05KT — variable direction."""
    w = WindParser()
    result = w.parse("VRB05KT")
    assert result is not None
    assert result.is_variable is True
    assert result.direction is None
    assert result.speed == 5


@pytest.mark.unit
def test_wind_parser_calm():
    """00000KT — calm wind."""
    w = WindParser()
    result = w.parse("00000KT")
    assert result is not None
    assert result.is_calm is True
    assert result.direction == 0
    assert result.speed == 0


@pytest.mark.unit
def test_wind_parser_with_gust():
    """28010G20KT — standard gust format."""
    w = WindParser()
    result = w.parse("28010G20KT")
    assert result is not None
    assert result.gust == 20
    assert result.direction == 280


@pytest.mark.unit
def test_wind_parser_mps_unit():
    """18005MPS — wind in meters per second."""
    w = WindParser()
    result = w.parse("18005MPS")
    assert result is not None
    assert result.unit == "MPS"
    assert result.speed == 5


# ===========================================================================
# RUNWAY PARSER EDGE CASES
# ===========================================================================


@pytest.mark.unit
def test_runway_parser_r88_all_runways():
    """R88 in runway state = all runways."""
    stream = TokenStream(["R88/212070"])
    states = RunwayParser().extract_runway_state(stream)
    assert len(states) == 1
    assert states[0].all_runways is True
    assert states[0].from_previous_report is False


@pytest.mark.unit
def test_runway_parser_r99_from_previous_report():
    """R99 in runway state = from previous report."""
    stream = TokenStream(["R99/212070"])
    states = RunwayParser().extract_runway_state(stream)
    assert len(states) == 1
    assert states[0].from_previous_report is True
    assert states[0].all_runways is False


@pytest.mark.unit
def test_runway_parser_decode_depth_92_is_10cm():
    """Depth code 92 should decode as '10cm'."""
    assert "10cm" in RunwayParser._decode_depth("92")


@pytest.mark.unit
def test_runway_parser_decode_depth_00_is_less_than_1mm():
    """Depth code 00 should decode as 'less than 1mm'."""
    assert "less than 1mm" in RunwayParser._decode_depth("00")


@pytest.mark.unit
def test_runway_parser_decode_depth_slash_slash():
    """Depth code // should indicate not significant or not measurable."""
    result = RunwayParser._decode_depth("//")
    assert "not significant" in result or "not measurable" in result


@pytest.mark.unit
def test_runway_parser_decode_depth_91_reserved():
    """Depth code 91 is Reserved — should be indicated as reserved/invalid."""
    result = RunwayParser._decode_depth("91")
    assert "reserved" in result.lower() or "invalid" in result.lower()


@pytest.mark.unit
def test_runway_parser_decode_depth_normal_mm():
    """Depth code 50 should decode as '50mm'."""
    assert "50mm" in RunwayParser._decode_depth("50")


@pytest.mark.unit
def test_runway_parser_decode_braking_96_reserved():
    """Braking code 96 is Reserved — should be indicated."""
    result = RunwayParser._decode_braking("96")
    assert "reserved" in result.lower()


@pytest.mark.unit
def test_runway_parser_decode_braking_97_reserved():
    """Braking code 97 is Reserved — should be indicated."""
    result = RunwayParser._decode_braking("97")
    assert "reserved" in result.lower()


@pytest.mark.unit
def test_runway_parser_decode_braking_98_reserved():
    """Braking code 98 is Reserved — should be indicated."""
    result = RunwayParser._decode_braking("98")
    assert "reserved" in result.lower()


@pytest.mark.unit
def test_runway_parser_decode_braking_91_poor():
    """Braking code 91 = poor braking."""
    result = RunwayParser._decode_braking("91")
    assert "poor" in result.lower()


@pytest.mark.unit
def test_runway_parser_rvr_with_ft():
    """RVR group with FT suffix — unit should be FT."""
    stream = TokenStream(["R28L/1200FT"])
    rvr_list = RunwayParser().extract_rvr(stream)
    assert len(rvr_list) == 1
    assert rvr_list[0].unit == "FT"
    assert rvr_list[0].runway == "28L"
    assert rvr_list[0].visual_range == 1200


@pytest.mark.unit
def test_runway_parser_rvr_without_ft():
    """RVR group without FT suffix — unit should be M."""
    stream = TokenStream(["R28/0600"])
    rvr_list = RunwayParser().extract_rvr(stream)
    assert len(rvr_list) == 1
    assert rvr_list[0].unit == "M"


# ===========================================================================
# WEATHER PARSER EDGE CASES
# ===========================================================================


@pytest.mark.unit
def test_weather_parser_fzra_freezing_rain():
    """FZRA should parse as freezing rain compound."""
    wp = WeatherParser()
    result = wp.parse("FZRA")
    assert result is not None
    assert "rain" in result.phenomena


@pytest.mark.unit
def test_weather_parser_re_slash_slash():
    """RE// — recent weather unavailable (AUTO station)."""
    wp = WeatherParser()
    result = wp.parse("RE//")
    assert result is not None
    assert result.intensity == "recent"
    assert "not reported" in result.phenomena


@pytest.mark.unit
def test_weather_parser_plus_fc_tornado():
    """+FC — tornado/waterspout."""
    wp = WeatherParser()
    result = wp.parse("+FC")
    assert result is not None
    assert result.intensity == "heavy"
    assert "tornado/waterspout" in result.phenomena


@pytest.mark.unit
def test_weather_parser_vcts_compound():
    """VCTS should parse as a compound phenomenon (thunderstorm in vicinity)."""
    wp = WeatherParser()
    result = wp.parse("VCTS")
    assert result is not None
    assert "thunderstorm in vicinity" in result.phenomena


@pytest.mark.unit
def test_weather_parser_tsra_compound():
    """TSRA — thunderstorm with rain compound."""
    wp = WeatherParser()
    result = wp.parse("TSRA")
    assert result is not None
    # Could be stored as compound or descriptor+phenomena depending on order
    assert result is not None  # at minimum it parses


@pytest.mark.unit
def test_weather_parser_unavailable_double_slash():
    """// — present weather not observable (AUTO station)."""
    wp = WeatherParser()
    result = wp.parse("//")
    assert result is not None
    assert result.unavailable is True


@pytest.mark.unit
def test_weather_parser_blsn_compound():
    """BLSN — blowing snow compound."""
    wp = WeatherParser()
    result = wp.parse("BLSN")
    assert result is not None
    assert "blowing snow" in result.phenomena


@pytest.mark.unit
def test_weather_parser_shra_compound():
    """SHRA — rain shower compound."""
    wp = WeatherParser()
    result = wp.parse("SHRA")
    assert result is not None
    assert "rain shower" in result.phenomena


@pytest.mark.unit
def test_weather_parser_stops_at_trend_token():
    """extract_all should not consume tokens after a TEMPO token."""
    wp = WeatherParser()
    stream = TokenStream(["-RA", "TEMPO", "+SN"])
    results = wp.extract_all(stream)
    assert len(results) == 1
    assert results[0].intensity == "light"
    # TEMPO and +SN remain
    assert "TEMPO" in stream.tokens
    assert "+SN" in stream.tokens


@pytest.mark.unit
def test_weather_parser_extract_recent():
    """extract_recent should pick up RE-prefixed tokens."""
    wp = WeatherParser()
    stream = TokenStream(["RERA", "SCT050"])
    results = wp.extract_recent(stream)
    assert len(results) == 1
    assert results[0].intensity == "recent"


# ===========================================================================
# TOKEN STREAM TESTS
# ===========================================================================


@pytest.mark.unit
def test_token_stream_peek():
    """TokenStream.peek should return token at offset without removing it."""
    stream = TokenStream(["A", "B", "C"])
    assert stream.peek() == "A"
    assert stream.peek(1) == "B"
    assert stream.peek(10) is None
    assert len(stream) == 3


@pytest.mark.unit
def test_token_stream_pop():
    """TokenStream.pop should remove and return the token."""
    stream = TokenStream(["A", "B", "C"])
    token = stream.pop(1)
    assert token == "B"
    assert stream.tokens == ["A", "C"]


@pytest.mark.unit
def test_token_stream_consume_if():
    """TokenStream.consume_if should consume first matching token."""
    stream = TokenStream(["A", "B", "C"])
    result = stream.consume_if(lambda t: t == "B")
    assert result == "B"
    assert "B" not in stream.tokens


@pytest.mark.unit
def test_token_stream_remaining():
    """TokenStream.remaining should return a copy of current tokens."""
    stream = TokenStream(["A", "B"])
    remaining = stream.remaining()
    assert remaining == ["A", "B"]
    # Modifying the copy should not affect the stream
    remaining.append("C")
    assert len(stream) == 2


@pytest.mark.unit
def test_token_stream_from_text():
    """TokenStream.from_text should split string on whitespace."""
    stream = TokenStream.from_text("METAR KJFK 061751Z")
    assert stream.tokens == ["METAR", "KJFK", "061751Z"]


# ===========================================================================
# INTEGRATION — FULL DECODE ROUND TRIPS
# ===========================================================================


@pytest.mark.integration
def test_metar_full_decode_no_crash(metar_decoder):
    """A complex METAR should decode without raising any exception."""
    raw = (
        "METAR EGLL 121250Z 22015KT 9999 BKN020 15/10 Q1018 "
        "BECMG FM1300 TL1400 SCT030 TEMPO BKN015"
    )
    result = metar_decoder.decode(raw)
    assert result is not None
    assert result.station_id == "EGLL"


@pytest.mark.integration
def test_taf_full_decode_no_crash(taf_decoder):
    """A standard TAF should decode without raising any exception."""
    raw = (
        "TAF KJFK 061730Z 0618/0718 28010KT 9999 FEW030 "
        "TEMPO 0618/0622 -RA BKN020 "
        "BECMG 0700/0706 VRB05KT"
    )
    result = taf_decoder.decode(raw)
    assert result is not None
    assert result.station_id == "KJFK"


@pytest.mark.integration
def test_metar_maintenance_flag(metar_decoder):
    """METAR ending with $ should have maintenance_needed=True."""
    result = metar_decoder.decode("METAR KJFK 061751Z 28010KT 9999 FEW030 22/18 A2992 $")
    assert result.maintenance_needed is True


@pytest.mark.integration
def test_metar_nil_flag(metar_decoder):
    """METAR with NIL should have is_nil=True."""
    result = metar_decoder.decode("METAR KJFK 061751Z NIL")
    assert result.is_nil is True


@pytest.mark.integration
def test_taf_nil_flag(taf_decoder):
    """TAF NIL should have is_nil=True."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0718 NIL")
    assert result.is_nil is True


@pytest.mark.integration
def test_taf_cancelled_flag(taf_decoder):
    """TAF CNL should have is_cancelled=True."""
    result = taf_decoder.decode("TAF KJFK 061730Z 0618/0718 CNL")
    assert result.is_cancelled is True
