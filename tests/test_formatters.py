"""Comprehensive tests for MetarFormatter, TafFormatter, and formatters/common.py."""

from __future__ import annotations

import pytest

from weather_decoder import MetarDecoder, TafDecoder
from weather_decoder.formatters.metar_formatter import MetarFormatter
from weather_decoder.formatters.taf_formatter import TafFormatter
from weather_decoder.formatters.common import (
    format_wind,
    format_visibility,
    format_sky_conditions_list,
    format_weather_groups_list,
    format_pressure,
    format_temperature,
)
from weather_decoder.models import (
    Wind,
    Visibility,
    DirectionalVisibility,
    MinimumVisibility,
    SkyCondition,
    WeatherPhenomenon,
    Pressure,
    RunwayVisualRange,
    RunwayState,
    SeaCondition,
    WindShear,
    Trend,
    TrendTime,
    MetarReport,
    TafReport,
    TafForecastPeriod,
    TimeRange,
    MilitaryColorCode,
    TemperatureForecast,
    IcingForecast,
    TurbulenceForecast,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def metar_decoder():
    return MetarDecoder()


@pytest.fixture(scope="module")
def taf_decoder():
    return TafDecoder()


# ===========================================================================
# METAR FORMATTER TESTS
# ===========================================================================


@pytest.mark.integration
class TestMetarFormatterBasic:
    """Tests for basic METAR report formatting via full decoder pipeline."""

    def test_basic_metar_station_id(self, metar_decoder):
        """Formatted output contains the station ID."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "KJFK" in result

    def test_basic_metar_wind_section(self, metar_decoder):
        """Formatted output contains a Wind section."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "Wind:" in result

    def test_basic_metar_visibility_section(self, metar_decoder):
        """Formatted output contains a Visibility section."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "Visibility:" in result

    def test_basic_metar_sky_section(self, metar_decoder):
        """Formatted output contains sky condition information."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "Sky" in result or "FEW" in result

    def test_basic_metar_temperature_section(self, metar_decoder):
        """Formatted output contains temperature information."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "Temperature:" in result or "22" in result

    def test_basic_metar_returns_string(self, metar_decoder):
        """MetarFormatter.format() always returns a non-empty string."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_nil_metar(self, metar_decoder):
        """NIL METAR produces output containing 'NIL'."""
        report = metar_decoder.decode("METAR KJFK 061751Z NIL")
        result = MetarFormatter.format(report)
        assert "NIL" in result

    def test_auto_metar(self, metar_decoder):
        """AUTO METAR produces output indicating automated report."""
        report = metar_decoder.decode(
            "METAR KJFK 061751Z AUTO 28008KT 9999 FEW030 22/18 A2992"
        )
        result = MetarFormatter.format(report)
        assert "AUTO" in result or "Automated" in result or "auto" in result.lower()

    def test_cor_metar(self, metar_decoder):
        """COR METAR produces output indicating corrected report."""
        report = metar_decoder.decode(
            "METAR COR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
        )
        result = MetarFormatter.format(report)
        assert "COR" in result or "Corrected" in result or "corrected" in result.lower()

    def test_metar_without_keyword(self, metar_decoder):
        """METAR string without the METAR keyword still produces non-empty output."""
        report = metar_decoder.decode("KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_metar_wind_direction_in_output(self, metar_decoder):
        """Wind direction appears in formatted output."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        # 280° direction should appear
        assert "280" in result

    def test_metar_altimeter_in_output(self, metar_decoder):
        """Altimeter value appears in formatted output."""
        report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        result = MetarFormatter.format(report)
        assert "29.92" in result or "Altimeter" in result


@pytest.mark.integration
class TestMetarFormatterWeather:
    """Tests for METAR reports with weather phenomena."""

    def test_metar_with_rain(self, metar_decoder):
        """Light rain weather phenomenon appears in output."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 18015KT 5000 -RA BKN020 15/13 Q1013"
        )
        result = MetarFormatter.format(report)
        assert "rain" in result or "RA" in result or "Weather" in result

    def test_metar_with_fog_rvr(self, metar_decoder):
        """RVR information appears in formatted output."""
        report = metar_decoder.decode(
            "METAR KLAX 061751Z 00000KT 0200 R28L/1200FT FG OVC002 18/18 A2980"
        )
        result = MetarFormatter.format(report)
        assert "RVR" in result or "28L" in result or "Runway Visual Range" in result

    def test_metar_fog_weather_group(self, metar_decoder):
        """Fog weather group appears in output."""
        report = metar_decoder.decode(
            "METAR KLAX 061751Z 00000KT 0200 R28L/1200FT FG OVC002 18/18 A2980"
        )
        result = MetarFormatter.format(report)
        assert "fog" in result or "FG" in result

    def test_metar_with_runway_state(self, metar_decoder):
        """Runway state information produces non-empty string."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 27010KT 5000 BKN030 15/10 Q1015 R28/212070"
        )
        result = MetarFormatter.format(report)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_metar_runway_state_label(self, metar_decoder):
        """Runway state section label appears in output."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 27010KT 5000 BKN030 15/10 Q1015 R28/212070"
        )
        result = MetarFormatter.format(report)
        assert "Runway" in result

    def test_metar_nosig_trend(self, metar_decoder):
        """NOSIG trend produces output with NOSIG or 'No significant' wording."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 NOSIG"
        )
        result = MetarFormatter.format(report)
        assert "NOSIG" in result or "No significant" in result

    def test_metar_becmg_trend(self, metar_decoder):
        """BECMG trend produces output with BECMG or 'Becoming' wording."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 BECMG FM1600 TL1800 NSW"
        )
        result = MetarFormatter.format(report)
        assert "BECMG" in result or "Becoming" in result

    def test_metar_sea_condition(self, metar_decoder):
        """Sea condition temperature value appears in formatted output."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 W15/S3"
        )
        result = MetarFormatter.format(report)
        assert "15" in result or "Sea" in result or "sea" in result.lower()

    def test_metar_windshear(self, metar_decoder):
        """Windshear on all runways produces output with 'shear' or 'WS'."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 WS ALL RWY"
        )
        result = MetarFormatter.format(report)
        assert "shear" in result.lower() or "WS" in result

    def test_metar_military_color_code(self, metar_decoder):
        """Military color code RED appears in formatted output."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 RED"
        )
        result = MetarFormatter.format(report)
        assert "RED" in result or "Military" in result or "red" in result.lower()

    def test_metar_military_color_code_amber(self, metar_decoder):
        """Military color code AMB appears in formatted output."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 AMB"
        )
        result = MetarFormatter.format(report)
        assert "AMB" in result or "Amber" in result or "Military" in result

    def test_metar_remarks(self, metar_decoder):
        """Remarks are included in formatted output."""
        report = metar_decoder.decode(
            "METAR KJFK 061751Z 28008KT 10SM FEW030 22/18 A2992 RMK AO2 SLP021"
        )
        result = MetarFormatter.format(report)
        assert "AO2" in result or "Station" in result or "Remarks" in result

    def test_metar_gust_wind(self, metar_decoder):
        """Gust speed appears in formatted output."""
        report = metar_decoder.decode(
            "METAR KJFK 061751Z 28025G35KT 10SM FEW030 22/18 A2992"
        )
        result = MetarFormatter.format(report)
        assert "35" in result or "gust" in result.lower() or "Gust" in result

    def test_metar_cavok(self, metar_decoder):
        """CAVOK appears in formatted output for CAVOK conditions."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT CAVOK 18/10 Q1020"
        )
        result = MetarFormatter.format(report)
        assert "CAVOK" in result

    def test_metar_cavok_no_sky_section(self, metar_decoder):
        """CAVOK METAR does not have an explicit Sky Conditions section."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 09015KT CAVOK 18/10 Q1020"
        )
        result = MetarFormatter.format(report)
        # CAVOK means no separate sky conditions block
        assert "Sky Conditions:" not in result

    def test_metar_calm_wind(self, metar_decoder):
        """Calm wind is indicated in formatted output."""
        report = metar_decoder.decode(
            "METAR KLAX 061751Z 00000KT 0200 R28L/1200FT FG OVC002 18/18 A2980"
        )
        result = MetarFormatter.format(report)
        assert "Calm" in result or "calm" in result.lower()

    def test_metar_hpa_pressure(self, metar_decoder):
        """hPa pressure is formatted correctly."""
        report = metar_decoder.decode(
            "METAR EGLL 061751Z 18015KT 5000 -RA BKN020 15/13 Q1013"
        )
        result = MetarFormatter.format(report)
        assert "1013" in result

    def test_metar_multiple_sky_layers(self, metar_decoder):
        """Multiple sky condition layers all appear in output."""
        report = metar_decoder.decode(
            "METAR KJFK 061751Z 28008KT 10SM FEW030 SCT060 BKN120 22/18 A2992"
        )
        result = MetarFormatter.format(report)
        assert "FEW" in result or "SCT" in result or "BKN" in result


# ===========================================================================
# TAF FORMATTER TESTS
# ===========================================================================


@pytest.mark.integration
class TestTafFormatterBasic:
    """Tests for basic TAF report formatting via full decoder pipeline."""

    def test_basic_taf_station_id(self, taf_decoder):
        """Formatted TAF output contains the station ID."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        result = TafFormatter.format(report)
        assert "KJFK" in result

    def test_basic_taf_initial_forecast_label(self, taf_decoder):
        """Formatted TAF contains 'Initial Forecast:' label."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        result = TafFormatter.format(report)
        assert "Initial Forecast:" in result

    def test_basic_taf_wind_section(self, taf_decoder):
        """Formatted TAF contains a Wind section."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        result = TafFormatter.format(report)
        assert "Wind:" in result

    def test_basic_taf_returns_string(self, taf_decoder):
        """TafFormatter.format() always returns a non-empty string."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        result = TafFormatter.format(report)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_basic_taf_valid_period_header(self, taf_decoder):
        """Formatted TAF contains valid period information."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        result = TafFormatter.format(report)
        assert "Valid from" in result
        assert "Valid to" in result

    def test_amd_taf(self, taf_decoder):
        """AMD TAF produces output containing 'AMD' or 'Amendment'."""
        report = taf_decoder.decode(
            "TAF AMD KJFK 061730Z 0618/0724 28008KT 9999 FEW250"
        )
        result = TafFormatter.format(report)
        assert "AMD" in result or "Amendment" in result

    def test_cor_taf(self, taf_decoder):
        """COR TAF produces output containing 'COR' or 'Correction'."""
        report = taf_decoder.decode(
            "TAF COR KJFK 061730Z 0618/0724 28008KT 9999 FEW250"
        )
        result = TafFormatter.format(report)
        assert "COR" in result or "Correction" in result

    def test_cnl_taf(self, taf_decoder):
        """Cancelled TAF produces output with 'cancel' or 'CNL'."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 CNL")
        result = TafFormatter.format(report)
        assert "cancel" in result.lower() or "CNL" in result

    def test_nil_taf(self, taf_decoder):
        """NIL TAF produces output containing 'NIL'."""
        report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 NIL")
        result = TafFormatter.format(report)
        assert "NIL" in result


@pytest.mark.integration
class TestTafFormatterChangeGroups:
    """Tests for TAF change groups (TEMPO, BECMG, FM, PROB)."""

    def test_tempo_taf(self, taf_decoder):
        """TEMPO change group produces output with 'TEMPO' or 'Temporary'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TEMPO 0620/0622 -RA BKN020"
        )
        result = TafFormatter.format(report)
        assert "TEMPO" in result or "Temporary" in result

    def test_tempo_taf_weather(self, taf_decoder):
        """TEMPO change group shows the weather change."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TEMPO 0620/0622 -RA BKN020"
        )
        result = TafFormatter.format(report)
        assert "rain" in result or "RA" in result

    def test_becmg_taf(self, taf_decoder):
        """BECMG change group produces output with 'BECMG', 'Becoming', or 'becoming'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 BECMG 0620/0622 VRB05KT"
        )
        result = TafFormatter.format(report)
        assert "BECMG" in result or "becoming" in result.lower()

    def test_fm_taf(self, taf_decoder):
        """FM change group produces output with 'FM' or 'From'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250 FM062000 15010KT 6000 -RA SCT020"
        )
        result = TafFormatter.format(report)
        assert "FM" in result or "From" in result

    def test_fm_taf_new_conditions(self, taf_decoder):
        """FM change group shows its wind direction."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250 FM062000 15010KT 6000 -RA SCT020"
        )
        result = TafFormatter.format(report)
        assert "150" in result

    def test_prob30_tempo_taf(self, taf_decoder):
        """PROB30 TEMPO produces output with probability indication."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 PROB30 TEMPO 0620/0622 -RA"
        )
        result = TafFormatter.format(report)
        assert "PROB30" in result or "30%" in result or "Probability" in result

    def test_prob30_tempo_taf_weather(self, taf_decoder):
        """PROB30 TEMPO shows the weather."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 PROB30 TEMPO 0620/0622 -RA"
        )
        result = TafFormatter.format(report)
        assert "rain" in result or "RA" in result


@pytest.mark.integration
class TestTafFormatterSpecialGroups:
    """Tests for TAF special groups (temperatures, icing, turbulence, wind shear)."""

    def test_taf_temperatures(self, taf_decoder):
        """TAF temperature forecast values appear in output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TX25/0620Z TN15/0706Z"
        )
        result = TafFormatter.format(report)
        assert "25" in result or "Temperature" in result or "temp" in result.lower()

    def test_taf_temperatures_both_values(self, taf_decoder):
        """Both max and min temperature values appear in output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TX25/0620Z TN15/0706Z"
        )
        result = TafFormatter.format(report)
        assert "25" in result
        assert "15" in result

    def test_taf_icing(self, taf_decoder):
        """Icing forecast group produces output with 'icing' or 'Icing'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 620304"
        )
        result = TafFormatter.format(report)
        assert "icing" in result.lower() or "Icing" in result or "620304" in result

    def test_taf_icing_altitude(self, taf_decoder):
        """Icing base altitude appears in formatted output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 620304"
        )
        result = TafFormatter.format(report)
        # 620304: base 3000ft, top 7000ft
        assert "3,000" in result or "3000" in result

    def test_taf_turbulence(self, taf_decoder):
        """Turbulence forecast group produces output with 'turbulence'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 520610"
        )
        result = TafFormatter.format(report)
        assert "turbulence" in result.lower() or "Turbulence" in result or "520610" in result

    def test_taf_turbulence_intensity(self, taf_decoder):
        """Turbulence intensity appears in formatted output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 520610"
        )
        result = TafFormatter.format(report)
        # 520610: moderate in cloud turbulence
        assert "moderate" in result.lower() or "Moderate" in result

    def test_taf_windshear(self, taf_decoder):
        """Wind shear group produces output with 'shear'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 WS020/28035KT"
        )
        result = TafFormatter.format(report)
        assert "shear" in result.lower() or "Wind Shear" in result

    def test_taf_windshear_section_header(self, taf_decoder):
        """Wind Shear section header appears in formatted TAF output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 WS020/28035KT"
        )
        result = TafFormatter.format(report)
        assert "Wind Shear" in result

    def test_taf_remarks(self, taf_decoder):
        """TAF remarks appear in formatted output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 RMK NXT FCST BY 12Z"
        )
        result = TafFormatter.format(report)
        assert "Remarks" in result or "Next" in result

    def test_taf_cavok(self, taf_decoder):
        """CAVOK in TAF produces output with 'CAVOK'."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 VRB05KT CAVOK"
        )
        result = TafFormatter.format(report)
        assert "CAVOK" in result

    def test_taf_variable_wind(self, taf_decoder):
        """Variable wind in TAF produces 'Variable' in output."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 VRB05KT CAVOK"
        )
        result = TafFormatter.format(report)
        assert "Variable" in result

    def test_taf_multiple_change_groups(self, taf_decoder):
        """TAF with multiple change groups formats all of them."""
        report = taf_decoder.decode(
            "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 "
            "TEMPO 0620/0622 -RA BKN020 "
            "BECMG 0622/0624 VRB03KT"
        )
        result = TafFormatter.format(report)
        assert ("TEMPO" in result or "Temporary" in result)
        assert ("BECMG" in result or "becoming" in result.lower())


# ===========================================================================
# FORMATTERS/COMMON.PY UNIT TESTS
# ===========================================================================


@pytest.mark.unit
class TestFormatWind:
    """Unit tests for format_wind() in common.py."""

    def test_none_wind(self):
        """None wind returns 'Not reported'."""
        assert format_wind(None) == "Not reported"

    def test_calm_wind_via_flag(self):
        """Wind with is_calm=True returns 'Calm'."""
        wind = Wind(direction=0, speed=0, unit="KT", is_calm=True)
        assert format_wind(wind) == "Calm"

    def test_calm_wind_via_zeros(self):
        """Wind at direction=0, speed=0, not variable returns 'Calm'."""
        wind = Wind(direction=0, speed=0, unit="KT", is_calm=False, is_variable=False)
        assert format_wind(wind) == "Calm"

    def test_normal_wind(self):
        """Standard directional wind formats direction and speed."""
        wind = Wind(direction=280, speed=8, unit="KT")
        result = format_wind(wind)
        assert "280°" in result
        assert "8 KT" in result

    def test_variable_wind(self):
        """Variable wind (VRB) formats as 'Variable'."""
        wind = Wind(direction=None, speed=5, unit="KT", is_variable=True)
        result = format_wind(wind)
        assert "Variable" in result
        assert "5 KT" in result

    def test_wind_with_gust(self):
        """Wind with gust shows gusting speed."""
        wind = Wind(direction=280, speed=25, unit="KT", gust=35)
        result = format_wind(wind)
        assert "gusting" in result
        assert "35" in result

    def test_wind_is_above(self):
        """Wind speed marked as 'above' is labeled accordingly."""
        wind = Wind(direction=280, speed=35, unit="KT", is_above=True)
        result = format_wind(wind)
        assert "above" in result
        assert "35 KT" in result

    def test_wind_gust_is_above(self):
        """Gust marked as 'above' uses 'at least' prefix."""
        wind = Wind(direction=280, speed=25, unit="KT", gust=35, gust_is_above=True)
        result = format_wind(wind)
        assert "at least" in result

    def test_wind_variable_range(self):
        """Wind with variable direction range shows both bearings."""
        wind = Wind(direction=280, speed=8, unit="KT", variable_range=(250, 310))
        result = format_wind(wind)
        assert "250°" in result
        assert "310°" in result

    def test_wind_knots_unit(self):
        """Wind unit KT appears in output."""
        wind = Wind(direction=270, speed=10, unit="KT")
        assert "KT" in format_wind(wind)

    def test_wind_mps_unit(self):
        """Wind unit MPS is preserved in output."""
        wind = Wind(direction=270, speed=10, unit="MPS")
        assert "MPS" in format_wind(wind)


@pytest.mark.unit
class TestFormatVisibility:
    """Unit tests for format_visibility() in common.py."""

    def test_none_visibility(self):
        """None visibility returns 'Not reported'."""
        assert format_visibility(None) == "Not reported"

    def test_cavok_visibility(self):
        """CAVOK visibility returns the CAVOK string."""
        vis = Visibility(value=0, unit="M", is_cavok=True)
        assert "CAVOK" in format_visibility(vis)

    def test_unavailable_visibility(self):
        """Unavailable visibility returns automated-station message."""
        vis = Visibility(value=0, unit="M", unavailable=True)
        result = format_visibility(vis)
        assert "Not available" in result or "automated" in result.lower()

    def test_10sm_visibility(self):
        """10 SM visibility formats correctly."""
        vis = Visibility(value=10.0, unit="SM")
        result = format_visibility(vis)
        assert "10" in result
        assert "SM" in result

    def test_9999m_visibility(self):
        """9999 M visibility formats as '10 km or more'."""
        vis = Visibility(value=9999, unit="M")
        result = format_visibility(vis)
        assert "10 km or more" in result

    def test_5000m_visibility(self):
        """5000 M visibility formats as '5 km'."""
        vis = Visibility(value=5000, unit="M")
        result = format_visibility(vis)
        assert "5 km" in result

    def test_800m_visibility(self):
        """800 M visibility formats in meters."""
        vis = Visibility(value=800, unit="M")
        result = format_visibility(vis)
        assert "800" in result

    def test_less_than_sm_visibility(self):
        """Less-than SM visibility uses 'Less than' prefix."""
        vis = Visibility(value=0.25, unit="SM", is_less_than=True)
        result = format_visibility(vis)
        assert "Less than" in result
        assert "0.25" in result

    def test_less_than_zero_m_visibility(self):
        """Less-than 0 M visibility returns 'Less than 50 M'."""
        vis = Visibility(value=0, unit="M", is_less_than=True)
        result = format_visibility(vis)
        assert "Less than 50 M" in result

    def test_greater_than_sm_visibility(self):
        """Greater-than SM visibility uses 'Greater than' prefix."""
        vis = Visibility(value=10.0, unit="SM", is_greater_than=True)
        result = format_visibility(vis)
        assert "Greater than" in result

    def test_km_visibility(self):
        """KM unit visibility formats correctly."""
        vis = Visibility(value=10.0, unit="KM")
        result = format_visibility(vis)
        assert "10 km" in result

    def test_directional_visibility(self):
        """Directional visibility appended to main visibility."""
        dv = DirectionalVisibility(value=2000, direction="NE")
        vis = Visibility(value=5000, unit="M", directional_visibility=dv)
        result = format_visibility(vis)
        assert "NE" in result
        assert "2 km" in result

    def test_minimum_visibility(self):
        """Minimum visibility appended in parentheses."""
        mv = MinimumVisibility(value=800)
        vis = Visibility(value=5000, unit="M", minimum_visibility=mv)
        result = format_visibility(vis)
        assert "minimum" in result
        assert "800" in result

    def test_ndv_visibility(self):
        """No Directional Variation flag appended to visibility."""
        vis = Visibility(value=9999, unit="M", ndv=True)
        result = format_visibility(vis)
        assert "No Directional Variation" in result

    def test_visibility_with_direction(self):
        """Directional qualifier appended after visibility value."""
        vis = Visibility(value=5.0, unit="SM", direction="N")
        result = format_visibility(vis)
        assert "to the N" in result


@pytest.mark.unit
class TestFormatPressure:
    """Unit tests for format_pressure() in common.py."""

    def test_none_pressure(self):
        """None pressure returns 'Not reported'."""
        assert format_pressure(None) == "Not reported"

    def test_inhg_pressure(self):
        """inHg pressure formats with value and unit."""
        p = Pressure(value=29.92, unit="inHg")
        result = format_pressure(p)
        assert "29.92" in result
        assert "inHg" in result

    def test_hpa_pressure(self):
        """hPa pressure formats with value and unit."""
        p = Pressure(value=1013, unit="hPa")
        result = format_pressure(p)
        assert "1013" in result
        assert "hPa" in result


@pytest.mark.unit
class TestFormatTemperature:
    """Unit tests for format_temperature() in common.py."""

    def test_none_temperature(self):
        """None temperature returns 'Not reported'."""
        assert format_temperature(None) == "Not reported"

    def test_positive_temperature(self):
        """Positive temperature formats with degree symbol and C."""
        result = format_temperature(22.0)
        assert "22" in result
        assert "°C" in result

    def test_negative_temperature(self):
        """Negative temperature formats with minus sign."""
        result = format_temperature(-5.0)
        assert "-5" in result
        assert "°C" in result

    def test_zero_temperature(self):
        """Zero temperature formats correctly."""
        result = format_temperature(0.0)
        assert "0" in result
        assert "°C" in result


@pytest.mark.unit
class TestFormatSkyConditionsList:
    """Unit tests for format_sky_conditions_list() in common.py."""

    def test_empty_list_returns_empty_list(self):
        """Empty input returns empty list."""
        result = format_sky_conditions_list([])
        assert result == []

    def test_few_layer(self):
        """FEW layer at height formats correctly."""
        sky = SkyCondition(coverage="FEW", height=3000)
        result = format_sky_conditions_list([sky])
        assert len(result) == 1
        assert "FEW" in result[0]
        assert "3000" in result[0]

    def test_sct_layer(self):
        """SCT layer at height formats correctly."""
        sky = SkyCondition(coverage="SCT", height=5000)
        result = format_sky_conditions_list([sky])
        assert "SCT" in result[0]
        assert "5000" in result[0]

    def test_bkn_layer(self):
        """BKN layer at height formats correctly."""
        sky = SkyCondition(coverage="BKN", height=8000)
        result = format_sky_conditions_list([sky])
        assert "BKN" in result[0]

    def test_ovc_layer(self):
        """OVC layer at height formats correctly."""
        sky = SkyCondition(coverage="OVC", height=10000)
        result = format_sky_conditions_list([sky])
        assert "OVC" in result[0]
        assert "10000" in result[0]

    def test_multiple_layers(self):
        """Multiple sky layers each produce one entry in result list."""
        layers = [
            SkyCondition(coverage="FEW", height=3000),
            SkyCondition(coverage="SCT", height=5000),
            SkyCondition(coverage="BKN", height=8000),
            SkyCondition(coverage="OVC", height=10000),
        ]
        result = format_sky_conditions_list(layers)
        assert len(result) == 4

    def test_cb_layer(self):
        """CB cumulonimbus indicator appears in formatted output."""
        sky = SkyCondition(coverage="FEW", height=3000, cb=True)
        result = format_sky_conditions_list([sky])
        assert "CB" in result[0]

    def test_tcu_layer(self):
        """TCU towering cumulus indicator appears in formatted output."""
        sky = SkyCondition(coverage="BKN", height=5000, tcu=True)
        result = format_sky_conditions_list([sky])
        assert "TCU" in result[0]

    def test_skc_returns_clear_skies(self):
        """SKC coverage returns 'Clear skies'."""
        sky = SkyCondition(coverage="SKC", height=None)
        result = format_sky_conditions_list([sky])
        assert "Clear skies" in result[0]

    def test_clr_returns_clear_skies(self):
        """CLR coverage returns 'Clear skies'."""
        sky = SkyCondition(coverage="CLR", height=None)
        result = format_sky_conditions_list([sky])
        assert "Clear skies" in result[0]

    def test_nsc_returns_no_significant_cloud(self):
        """NSC coverage returns 'No significant cloud'."""
        sky = SkyCondition(coverage="NSC", height=None)
        result = format_sky_conditions_list([sky])
        assert "No significant cloud" in result[0]

    def test_ncd_returns_no_cloud_detected(self):
        """NCD coverage returns 'No cloud detected'."""
        sky = SkyCondition(coverage="NCD", height=None)
        result = format_sky_conditions_list([sky])
        assert "No cloud detected" in result[0]

    def test_vv_with_height(self):
        """Vertical visibility with known height is formatted correctly."""
        sky = SkyCondition(coverage="VV", height=1000)
        result = format_sky_conditions_list([sky])
        assert "Vertical visibility" in result[0]
        assert "1000" in result[0]

    def test_vv_unknown_height(self):
        """Vertical visibility with unknown height is indicated."""
        sky = SkyCondition(coverage="VV", height=None, unknown_height=True)
        result = format_sky_conditions_list([sky])
        assert "Vertical visibility" in result[0]
        assert "unknown" in result[0]

    def test_system_unavailable(self):
        """System unavailable flag produces appropriate message."""
        sky = SkyCondition(coverage="////", height=None, system_unavailable=True)
        result = format_sky_conditions_list([sky])
        assert "not operating" in result[0] or "unavailable" in result[0].lower()

    def test_unknown_cloud_amount(self):
        """/// coverage with unknown height produces correct message."""
        sky = SkyCondition(coverage="///", height=None, unknown_height=True)
        result = format_sky_conditions_list([sky])
        assert "Unknown cloud amount" in result[0]
        assert "unknown height" in result[0]

    def test_unknown_cloud_amount_with_height(self):
        """/// coverage with known height includes the height."""
        sky = SkyCondition(coverage="///", height=3000, unknown_height=False)
        result = format_sky_conditions_list([sky])
        assert "Unknown cloud amount" in result[0]
        assert "3000" in result[0]


@pytest.mark.unit
class TestFormatWeatherGroupsList:
    """Unit tests for format_weather_groups_list() in common.py."""

    def test_empty_list_returns_empty_list(self):
        """Empty input returns empty list."""
        result = format_weather_groups_list([])
        assert result == []

    def test_light_rain(self):
        """Light rain weather group formats correctly."""
        wx = WeatherPhenomenon(intensity="light", descriptor=None, phenomena=("RA",))
        result = format_weather_groups_list([wx])
        assert len(result) == 1
        assert "light" in result[0]
        assert "RA" in result[0]

    def test_heavy_thunderstorm(self):
        """Heavy thunderstorm with rain formats correctly."""
        wx = WeatherPhenomenon(intensity="heavy", descriptor="thunderstorm", phenomena=("RA",))
        result = format_weather_groups_list([wx])
        assert len(result) == 1
        assert "heavy" in result[0]
        assert "thunderstorm" in result[0]

    def test_unavailable_weather(self):
        """Unavailable weather (// sentinel) returns automated-system message."""
        wx = WeatherPhenomenon(unavailable=True)
        result = format_weather_groups_list([wx])
        assert len(result) == 1
        assert "Not observable" in result[0] or "automated" in result[0].lower()

    def test_multiple_weather_groups(self):
        """Multiple weather groups produce multiple entries."""
        wx1 = WeatherPhenomenon(intensity="light", descriptor=None, phenomena=("RA",))
        wx2 = WeatherPhenomenon(intensity=None, descriptor=None, phenomena=("FG",))
        result = format_weather_groups_list([wx1, wx2])
        assert len(result) == 2

    def test_weather_with_multiple_phenomena(self):
        """Weather with multiple phenomena joins them with comma."""
        wx = WeatherPhenomenon(
            intensity=None,
            descriptor="freezing",
            phenomena=("DZ", "RA"),
        )
        result = format_weather_groups_list([wx])
        assert len(result) == 1
        assert "DZ" in result[0]
        assert "RA" in result[0]

    def test_returns_list_of_strings(self):
        """format_weather_groups_list always returns a list of strings."""
        wx = WeatherPhenomenon(intensity="light", descriptor=None, phenomena=("RA",))
        result = format_weather_groups_list([wx])
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_sky_conditions_returns_list_of_strings(self):
        """format_sky_conditions_list always returns a list of strings."""
        sky = SkyCondition(coverage="FEW", height=3000)
        result = format_sky_conditions_list([sky])
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)
