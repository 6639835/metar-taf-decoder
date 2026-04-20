"""Comprehensive tests for models, constants, formatters, patterns, and utilities."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from weather_decoder.models import (
    DirectionalVisibility,
    IcingForecast,
    MetarReport,
    MilitaryColorCode,
    MinimumVisibility,
    Pressure,
    RunwayState,
    RunwayVisualRange,
    SeaCondition,
    SkyCondition,
    TafForecastPeriod,
    TafReport,
    TemperatureForecast,
    TimeRange,
    Trend,
    TrendTime,
    TurbulenceForecast,
    Visibility,
    WeatherPhenomenon,
    Wind,
    WindShear,
)

from weather_decoder.constants.weather_codes import (
    COMPOUND_WEATHER_PHENOMENA,
    WEATHER_DESCRIPTORS,
    WEATHER_INTENSITY,
    WEATHER_PHENOMENA,
)
from weather_decoder.constants.sky_codes import SKY_CONDITIONS
from weather_decoder.constants.change_codes import CHANGE_INDICATORS, TREND_TYPES
from weather_decoder.constants.military_codes import MILITARY_COLOR_CODES
from weather_decoder.constants.runway_codes import (
    RUNWAY_BRAKING,
    RUNWAY_BRAKING_RESERVED,
    RUNWAY_DEPOSIT_TYPES,
    RUNWAY_DEPTH_RESERVED,
    RUNWAY_EXTENT,
    RVR_TRENDS,
)
from weather_decoder.constants.pressure_codes import PRESSURE_TENDENCY_CHARACTERISTICS
from weather_decoder.constants.station_codes import SENSOR_STATUS, STATION_TYPES
from weather_decoder.constants.location_codes import (
    DIRECTION_ABBREV,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    LOCATION_INDICATORS,
)
from weather_decoder.constants.report_codes import (
    REPORT_MODIFIERS,
    SPECIAL_CONDITIONS,
    SPECIAL_VALUES,
)
from weather_decoder.constants.glossary_codes import CODE_GLOSSARY

from weather_decoder.formatters.common import (
    format_pressure,
    format_sky_condition,
    format_temperature,
    format_visibility,
    format_weather_group,
    format_wind,
)
from weather_decoder.constants.patterns import COMPILED_PATTERNS

from weather_decoder.parsers.time_parser import TimeParser

from weather_decoder.data.metar_data import MetarData
from weather_decoder.data.taf_data import TafData


# ===========================================================================
# Helpers
# ===========================================================================


def _make_metar(**overrides) -> MetarData:
    """Return a minimal MetarData instance, with optional field overrides."""
    defaults = dict(
        raw_metar="METAR EGLL 151751Z 00000KT 9999 SKC 20/15 Q1013",
        report_type="METAR",
        station_id="EGLL",
        observation_time=datetime(2024, 3, 15, 17, 51, tzinfo=timezone.utc),
        is_automated=False,
        is_nil=False,
        maintenance_needed=False,
        wind=None,
        visibility=None,
    )
    defaults.update(overrides)
    return MetarData(**defaults)


def _make_taf(**overrides) -> TafData:
    """Return a minimal TafData instance."""
    defaults = dict(
        raw_taf="TAF EGLL 150500Z 1506/1612 00000KT 9999 SKC",
        station_id="EGLL",
        issue_time=datetime(2024, 3, 15, 5, 0, tzinfo=timezone.utc),
        valid_period=TimeRange(
            start=datetime(2024, 3, 15, 6, 0, tzinfo=timezone.utc),
            end=datetime(2024, 3, 16, 12, 0, tzinfo=timezone.utc),
        ),
        forecast_periods=[],
    )
    defaults.update(overrides)
    return TafData(**defaults)


# ===========================================================================
# MODELS: frozen dataclasses – FrozenInstanceError
# ===========================================================================


@pytest.mark.unit
class TestFrozenDataclasses:
    """Verify that all frozen dataclasses raise FrozenInstanceError on mutation."""

    def test_wind_is_frozen(self):
        w = Wind(direction=270, speed=10, unit="KT")
        with pytest.raises(FrozenInstanceError):
            w.direction = 180  # type: ignore[misc]

    def test_visibility_is_frozen(self):
        v = Visibility(value=9999, unit="M")
        with pytest.raises(FrozenInstanceError):
            v.value = 5000  # type: ignore[misc]

    def test_directional_visibility_is_frozen(self):
        dv = DirectionalVisibility(value=3000, direction="NE")
        with pytest.raises(FrozenInstanceError):
            dv.value = 1000  # type: ignore[misc]

    def test_minimum_visibility_is_frozen(self):
        mv = MinimumVisibility(value=800, direction="SW")
        with pytest.raises(FrozenInstanceError):
            mv.value = 400  # type: ignore[misc]

    def test_runway_visual_range_is_frozen(self):
        rvr = RunwayVisualRange(runway="28L", visual_range=600, unit="M")
        with pytest.raises(FrozenInstanceError):
            rvr.visual_range = 800  # type: ignore[misc]

    def test_runway_state_is_frozen(self):
        rs = RunwayState(
            runway="28L",
            deposit="0",
            contamination="1",
            depth="00",
            braking="95",
            raw="R28L/010095",
        )
        with pytest.raises(FrozenInstanceError):
            rs.deposit = "7"  # type: ignore[misc]

    def test_weather_phenomenon_is_frozen(self):
        wx = WeatherPhenomenon(intensity="-", descriptor="SH", phenomena=("RA",))
        with pytest.raises(FrozenInstanceError):
            wx.intensity = "+"  # type: ignore[misc]

    def test_sky_condition_is_frozen(self):
        sky = SkyCondition(coverage="FEW", height=2000)
        with pytest.raises(FrozenInstanceError):
            sky.height = 3000  # type: ignore[misc]

    def test_pressure_is_frozen(self):
        p = Pressure(value=1013.2, unit="hPa")
        with pytest.raises(FrozenInstanceError):
            p.value = 1020.0  # type: ignore[misc]

    def test_sea_condition_is_frozen(self):
        sc = SeaCondition(sea_surface_temperature=15)
        with pytest.raises(FrozenInstanceError):
            sc.sea_surface_temperature = 20  # type: ignore[misc]

    def test_wind_shear_is_frozen(self):
        ws = WindShear(kind="runway", description="Wind shear at 2000 ft")
        with pytest.raises(FrozenInstanceError):
            ws.kind = "general"  # type: ignore[misc]

    def test_trend_time_is_frozen(self):
        tt = TrendTime(from_time="1200", until_time="1400")
        with pytest.raises(FrozenInstanceError):
            tt.from_time = "1300"  # type: ignore[misc]

    def test_trend_is_frozen(self):
        t = Trend(kind="TEMPO", description="temporary", raw="TEMPO 1200/1400")
        with pytest.raises(FrozenInstanceError):
            t.kind = "BECMG"  # type: ignore[misc]

    def test_military_color_code_is_frozen(self):
        mcc = MilitaryColorCode(code="BLU", description="Blue")
        with pytest.raises(FrozenInstanceError):
            mcc.code = "WHT"  # type: ignore[misc]

    def test_time_range_is_frozen(self):
        tr = TimeRange(
            start=datetime(2024, 3, 15, 6, 0, tzinfo=timezone.utc),
            end=datetime(2024, 3, 16, 6, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(FrozenInstanceError):
            tr.start = datetime(2024, 3, 15, 7, 0, tzinfo=timezone.utc)  # type: ignore[misc]

    def test_temperature_forecast_is_frozen(self):
        tf = TemperatureForecast(
            kind="TX",
            value=25,
            time=datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(FrozenInstanceError):
            tf.value = 30  # type: ignore[misc]

    def test_icing_forecast_is_frozen(self):
        icf = IcingForecast(
            intensity="moderate",
            base_ft=5000,
            top_ft=9000,
            icing_type="rime",
            raw="620504",
        )
        with pytest.raises(FrozenInstanceError):
            icf.intensity = "severe"  # type: ignore[misc]

    def test_turbulence_forecast_is_frozen(self):
        tbf = TurbulenceForecast(
            intensity="moderate",
            base_ft=6000,
            top_ft=7000,
            in_cloud=True,
            raw="520610",
        )
        with pytest.raises(FrozenInstanceError):
            tbf.intensity = "severe"  # type: ignore[misc]


# ===========================================================================
# MODELS: default field values
# ===========================================================================


@pytest.mark.unit
class TestModelDefaults:
    """Verify default field values in dataclasses."""

    def test_wind_defaults(self):
        w = Wind(direction=270, speed=10, unit="KT")
        assert w.gust is None
        assert w.is_variable is False
        assert w.variable_range is None
        assert w.is_above is False
        assert w.is_calm is False
        assert w.gust_is_above is False

    def test_visibility_defaults(self):
        v = Visibility(value=9999, unit="M")
        assert v.is_cavok is False
        assert v.is_less_than is False
        assert v.is_greater_than is False
        assert v.direction is None
        assert v.directional_visibility is None
        assert v.minimum_visibility is None
        assert v.ndv is False
        assert v.unavailable is False

    def test_runway_visual_range_defaults(self):
        rvr = RunwayVisualRange(runway="09", visual_range=800, unit="M")
        assert rvr.is_less_than is False
        assert rvr.is_more_than is False
        assert rvr.variable_range is None
        assert rvr.variable_less_than is False
        assert rvr.variable_more_than is False
        assert rvr.variable_range_is_less_than is False
        assert rvr.variable_range_is_more_than is False
        assert rvr.trend is None

    def test_runway_state_defaults(self):
        rs = RunwayState(
            runway="28L",
            deposit="0",
            contamination="1",
            depth="00",
            braking="95",
            raw="R28L/010095",
        )
        assert rs.all_runways is False
        assert rs.from_previous_report is False
        assert rs.cleared is False
        assert rs.aerodrome_closed is False

    def test_weather_phenomenon_defaults(self):
        wx = WeatherPhenomenon()
        assert wx.intensity is None
        assert wx.descriptor is None
        assert wx.phenomena == ()
        assert wx.unavailable is False

    def test_sky_condition_defaults(self):
        sky = SkyCondition(coverage="FEW", height=2000)
        assert sky.unknown_height is False
        assert sky.cb is False
        assert sky.tcu is False
        assert sky.unknown_type is False
        assert sky.system_unavailable is False

    def test_sea_condition_defaults(self):
        sc = SeaCondition(sea_surface_temperature=15)
        assert sc.state_of_sea is None
        assert sc.significant_wave_height_m is None
        assert sc.temperature_missing is False
        assert sc.state_missing is False
        assert sc.wave_height_missing is False
        assert sc.raw == ""

    def test_wind_shear_defaults(self):
        ws = WindShear(kind="runway", description="desc")
        assert ws.runway is None
        assert ws.raw is None

    def test_trend_time_defaults(self):
        tt = TrendTime()
        assert tt.from_time is None
        assert tt.until_time is None
        assert tt.at_time is None

    def test_trend_defaults(self):
        t = Trend(kind="BECMG", description="gradual change", raw="BECMG 1200/1400")
        assert t.time is None
        assert t.changes == ()

    def test_minimum_visibility_defaults(self):
        mv = MinimumVisibility(value=800)
        assert mv.direction is None

    def test_taf_forecast_period_defaults(self):
        tfp = TafForecastPeriod(change_type="FM")
        assert tfp.from_time is None
        assert tfp.to_time is None
        assert tfp.wind is None
        assert tfp.visibility is None
        assert tfp.weather == []
        assert tfp.sky == []
        assert tfp.temperatures == []
        assert tfp.nsw is False
        assert tfp.windshear == []
        assert tfp.icing == []
        assert tfp.turbulence == []
        assert tfp.unparsed_tokens == []
        assert tfp.probability is None
        assert tfp.qualifier is None

    def test_metar_report_defaults(self):
        mr = _make_metar()
        assert mr.runway_visual_ranges == []
        assert mr.runway_states == []
        assert mr.weather == []
        assert mr.recent_weather == []
        assert mr.sky == []
        assert mr.temperature is None
        assert mr.dewpoint is None
        assert mr.altimeter is None
        assert mr.sea_conditions == []
        assert mr.windshear == []
        assert mr.trends == []
        assert mr.is_corrected is False
        assert mr.remarks == ""
        assert mr.remarks_decoded == {}
        assert mr.military_color_codes == []
        assert mr.validation_warnings == []

    def test_taf_report_defaults(self):
        tr = _make_taf()
        assert tr.report_type == "TAF"
        assert tr.status == "NORMAL"
        assert tr.is_amended is False
        assert tr.is_corrected is False
        assert tr.is_cancelled is False
        assert tr.is_nil is False
        assert tr.remarks == ""
        assert tr.remarks_decoded == {}
        assert tr.temperature_forecasts == []
        assert tr.previous_valid_period is None
        assert tr.validation_warnings == []


# ===========================================================================
# MODELS: mutable dataclasses can be mutated
# ===========================================================================


@pytest.mark.unit
class TestMutableDataclasses:
    """Verify mutable dataclasses (TafForecastPeriod, MetarReport, TafReport)."""

    def test_taf_forecast_period_is_mutable(self):
        tfp = TafForecastPeriod(change_type="FM")
        wind = Wind(direction=270, speed=10, unit="KT")
        tfp.wind = wind
        assert tfp.wind is wind

    def test_metar_report_is_mutable(self):
        mr = _make_metar()
        mr.temperature = 25.0
        assert mr.temperature == 25.0

    def test_taf_report_is_mutable(self):
        tr = _make_taf()
        tr.status = "AMENDED"
        assert tr.status == "AMENDED"


# ===========================================================================
# CONSTANTS
# ===========================================================================


@pytest.mark.unit
class TestWeatherCodes:
    """Test weather_codes constants."""

    def test_weather_intensity_non_empty(self):
        assert isinstance(WEATHER_INTENSITY, dict)
        assert len(WEATHER_INTENSITY) > 0

    def test_weather_intensity_known_keys(self):
        assert "-" in WEATHER_INTENSITY
        assert "+" in WEATHER_INTENSITY
        assert "VC" in WEATHER_INTENSITY
        assert WEATHER_INTENSITY["-"] == "light"
        assert WEATHER_INTENSITY["+"] == "heavy"

    def test_weather_descriptors_non_empty(self):
        assert isinstance(WEATHER_DESCRIPTORS, dict)
        assert len(WEATHER_DESCRIPTORS) >= 8

    def test_weather_descriptors_known_keys(self):
        for code in ("MI", "PR", "BC", "DR", "BL", "SH", "TS", "FZ"):
            assert code in WEATHER_DESCRIPTORS, (
                f"{code} missing from WEATHER_DESCRIPTORS"
            )

    def test_weather_phenomena_non_empty(self):
        assert isinstance(WEATHER_PHENOMENA, dict)
        assert len(WEATHER_PHENOMENA) > 0

    def test_weather_phenomena_known_keys(self):
        # TS is a descriptor, not a phenomenon - check actual base phenomena codes
        for code in ("DZ", "RA", "SN", "FG", "GR", "BR", "HZ", "FC"):
            assert code in WEATHER_PHENOMENA, f"{code} missing from WEATHER_PHENOMENA"

    def test_compound_weather_phenomena_non_empty(self):
        assert isinstance(COMPOUND_WEATHER_PHENOMENA, dict)
        assert len(COMPOUND_WEATHER_PHENOMENA) > 0

    def test_compound_weather_phenomena_known_keys(self):
        for code in ("TSRA", "SHRA", "FZFG", "BLSN", "VCTS"):
            assert code in COMPOUND_WEATHER_PHENOMENA, (
                f"{code} missing from COMPOUND_WEATHER_PHENOMENA"
            )

    def test_all_phenomena_values_are_strings(self):
        for k, v in WEATHER_PHENOMENA.items():
            assert isinstance(v, str), f"Value for {k} is not a string"


@pytest.mark.unit
class TestSkyCodes:
    """Test sky_codes constants."""

    def test_sky_conditions_non_empty(self):
        assert isinstance(SKY_CONDITIONS, dict)
        assert len(SKY_CONDITIONS) > 0

    def test_sky_conditions_known_keys(self):
        for code in ("SKC", "CLR", "FEW", "SCT", "BKN", "OVC", "VV", "NSC", "NCD"):
            assert code in SKY_CONDITIONS, f"{code} missing from SKY_CONDITIONS"

    def test_sky_conditions_values_are_strings(self):
        for k, v in SKY_CONDITIONS.items():
            assert isinstance(v, str), f"Value for {k} is not a string"


@pytest.mark.unit
class TestChangeCodes:
    """Test change_codes constants."""

    def test_trend_types_non_empty(self):
        assert isinstance(TREND_TYPES, list)
        assert len(TREND_TYPES) > 0

    def test_trend_types_known_values(self):
        for val in ("NOSIG", "BECMG", "TEMPO"):
            assert val in TREND_TYPES

    def test_change_indicators_non_empty(self):
        assert isinstance(CHANGE_INDICATORS, list)
        assert len(CHANGE_INDICATORS) > 0

    def test_change_indicators_known_values(self):
        for val in ("TEMPO", "BECMG", "FM"):
            assert val in CHANGE_INDICATORS


@pytest.mark.unit
class TestMilitaryCodes:
    """Test military_codes constants."""

    def test_military_color_codes_non_empty(self):
        assert isinstance(MILITARY_COLOR_CODES, dict)
        assert len(MILITARY_COLOR_CODES) >= 6

    def test_military_color_codes_known_keys(self):
        for code in ("BLU", "WHT", "GRN", "YLO", "AMB", "RED"):
            assert code in MILITARY_COLOR_CODES

    def test_military_color_codes_values_are_strings(self):
        for k, v in MILITARY_COLOR_CODES.items():
            assert isinstance(v, str)


@pytest.mark.unit
class TestRunwayCodes:
    """Test runway_codes constants."""

    def test_runway_deposit_types_non_empty(self):
        assert isinstance(RUNWAY_DEPOSIT_TYPES, dict)
        assert len(RUNWAY_DEPOSIT_TYPES) > 0

    def test_runway_deposit_types_known_keys(self):
        for code in ("0", "1", "7", "/"):
            assert code in RUNWAY_DEPOSIT_TYPES

    def test_runway_braking_non_empty(self):
        assert isinstance(RUNWAY_BRAKING, dict)
        assert len(RUNWAY_BRAKING) > 0

    def test_runway_braking_known_keys(self):
        for code in ("91", "92", "93", "94", "95", "99", "//"):
            assert code in RUNWAY_BRAKING

    def test_runway_braking_reserved_is_set(self):
        assert isinstance(RUNWAY_BRAKING_RESERVED, (set, frozenset))
        assert 96 in RUNWAY_BRAKING_RESERVED
        assert 97 in RUNWAY_BRAKING_RESERVED
        assert 98 in RUNWAY_BRAKING_RESERVED

    def test_runway_depth_reserved_is_set(self):
        assert isinstance(RUNWAY_DEPTH_RESERVED, (set, frozenset))
        assert 91 in RUNWAY_DEPTH_RESERVED

    def test_rvr_trends_non_empty(self):
        assert isinstance(RVR_TRENDS, dict)
        assert len(RVR_TRENDS) >= 3

    def test_rvr_trends_known_keys(self):
        assert "U" in RVR_TRENDS
        assert "D" in RVR_TRENDS
        assert "N" in RVR_TRENDS

    def test_runway_extent_non_empty(self):
        assert isinstance(RUNWAY_EXTENT, dict)
        assert len(RUNWAY_EXTENT) > 0


@pytest.mark.unit
class TestPressureCodes:
    """Test pressure_codes constants."""

    def test_pressure_tendency_characteristics_non_empty(self):
        assert isinstance(PRESSURE_TENDENCY_CHARACTERISTICS, dict)
        assert len(PRESSURE_TENDENCY_CHARACTERISTICS) >= 9

    def test_pressure_tendency_integer_keys(self):
        for k in PRESSURE_TENDENCY_CHARACTERISTICS:
            assert isinstance(k, int), f"Key {k!r} is not an integer"

    def test_pressure_tendency_keys_range(self):
        for i in range(9):
            assert i in PRESSURE_TENDENCY_CHARACTERISTICS


@pytest.mark.unit
class TestStationCodes:
    """Test station_codes constants."""

    def test_station_types_non_empty(self):
        assert isinstance(STATION_TYPES, dict)
        assert len(STATION_TYPES) > 0

    def test_station_types_known_keys(self):
        assert "AO1" in STATION_TYPES
        assert "AO2" in STATION_TYPES

    def test_sensor_status_non_empty(self):
        assert isinstance(SENSOR_STATUS, dict)
        assert len(SENSOR_STATUS) > 0

    def test_sensor_status_known_keys(self):
        for code in ("PWINO", "TSNO", "FZRANO", "PNO", "RVRNO"):
            assert code in SENSOR_STATUS


@pytest.mark.unit
class TestLocationCodes:
    """Test location_codes constants."""

    def test_direction_abbrev_non_empty(self):
        assert isinstance(DIRECTION_ABBREV, dict)
        assert len(DIRECTION_ABBREV) >= 8

    def test_direction_abbrev_cardinal_points(self):
        for code in ("N", "E", "S", "W", "NE", "NW", "SE", "SW"):
            assert code in DIRECTION_ABBREV

    def test_lightning_frequency_non_empty(self):
        assert isinstance(LIGHTNING_FREQUENCY, dict)
        assert "FRQ" in LIGHTNING_FREQUENCY
        assert "OCNL" in LIGHTNING_FREQUENCY

    def test_lightning_types_non_empty(self):
        assert isinstance(LIGHTNING_TYPES, dict)
        for code in ("IC", "CC", "CG", "CA"):
            assert code in LIGHTNING_TYPES

    def test_location_indicators_non_empty(self):
        assert isinstance(LOCATION_INDICATORS, dict)
        assert "DSNT" in LOCATION_INDICATORS
        assert "VC" in LOCATION_INDICATORS
        assert "OHD" in LOCATION_INDICATORS


@pytest.mark.unit
class TestReportCodes:
    """Test report_codes constants."""

    def test_report_modifiers_non_empty(self):
        assert isinstance(REPORT_MODIFIERS, dict)
        assert "AUTO" in REPORT_MODIFIERS
        assert "COR" in REPORT_MODIFIERS
        assert "NIL" in REPORT_MODIFIERS

    def test_special_conditions_non_empty(self):
        assert isinstance(SPECIAL_CONDITIONS, dict)
        assert "CAVOK" in SPECIAL_CONDITIONS
        assert "NOSIG" in SPECIAL_CONDITIONS

    def test_special_values_non_empty(self):
        assert isinstance(SPECIAL_VALUES, dict)
        assert "9999" in SPECIAL_VALUES


@pytest.mark.unit
class TestGlossaryCodes:
    """Test glossary_codes constants."""

    def test_code_glossary_non_empty(self):
        assert isinstance(CODE_GLOSSARY, dict)
        assert len(CODE_GLOSSARY) > 50

    def test_code_glossary_known_entries(self):
        for token in ("METAR", "TAF", "AUTO", "CAVOK", "KT", "SM", "RMK"):
            assert token in CODE_GLOSSARY

    def test_code_glossary_values_are_strings(self):
        for k, v in CODE_GLOSSARY.items():
            assert isinstance(v, str), f"Glossary value for {k!r} is not a string"


# ===========================================================================
# FORMATTERS
# ===========================================================================


@pytest.mark.unit
class TestFormatWind:
    """Tests for format_wind()."""

    def test_none_returns_not_reported(self):
        assert format_wind(None) == "Not reported"

    def test_calm_flag(self):
        w = Wind(direction=0, speed=0, unit="KT", is_calm=True)
        assert format_wind(w) == "Calm"

    def test_calm_by_zero_values(self):
        w = Wind(direction=0, speed=0, unit="KT")
        assert format_wind(w) == "Calm"

    def test_directional_wind(self):
        w = Wind(direction=280, speed=45, unit="KT")
        result = format_wind(w)
        assert "280°" in result
        assert "45" in result
        assert "KT" in result

    def test_variable_wind(self):
        w = Wind(direction=None, speed=5, unit="KT", is_variable=True)
        result = format_wind(w)
        assert "Variable" in result
        assert "5" in result

    def test_wind_with_gust(self):
        w = Wind(direction=280, speed=45, unit="KT", gust=65)
        result = format_wind(w)
        assert "gusting" in result
        assert "65" in result

    def test_wind_is_above(self):
        w = Wind(direction=270, speed=99, unit="KT", is_above=True)
        result = format_wind(w)
        assert "above" in result
        assert "99" in result

    def test_wind_gust_is_above(self):
        w = Wind(direction=270, speed=10, unit="KT", gust=20, gust_is_above=True)
        result = format_wind(w)
        assert "at least" in result

    def test_wind_with_variable_range(self):
        w = Wind(direction=180, speed=15, unit="KT", variable_range=(150, 210))
        result = format_wind(w)
        assert "150°" in result
        assert "210°" in result
        assert "varying" in result

    def test_wind_unit_mps(self):
        w = Wind(direction=90, speed=10, unit="MPS")
        result = format_wind(w)
        assert "MPS" in result

    def test_wind_unit_kmh(self):
        w = Wind(direction=90, speed=20, unit="KMH")
        result = format_wind(w)
        assert "KMH" in result


@pytest.mark.unit
class TestFormatVisibility:
    """Tests for format_visibility()."""

    def test_none_returns_not_reported(self):
        assert format_visibility(None) == "Not reported"

    def test_cavok(self):
        v = Visibility(value=0, unit="M", is_cavok=True)
        result = format_visibility(v)
        assert "CAVOK" in result

    def test_9999_metres(self):
        v = Visibility(value=9999, unit="M")
        result = format_visibility(v)
        assert "10 km" in result

    def test_less_than_50m(self):
        v = Visibility(value=0, unit="M", is_less_than=True)
        result = format_visibility(v)
        assert "Less than" in result
        assert "50" in result

    def test_less_than_sm_fractional(self):
        v = Visibility(value=0.25, unit="SM", is_less_than=True)
        result = format_visibility(v)
        assert "Less than" in result
        assert "SM" in result

    def test_greater_than_sm(self):
        v = Visibility(value=10, unit="SM", is_greater_than=True)
        result = format_visibility(v)
        assert "Greater than" in result
        assert "10" in result
        assert "SM" in result

    def test_unavailable(self):
        v = Visibility(value=0, unit="M", unavailable=True)
        result = format_visibility(v)
        assert "Not available" in result or "automated" in result.lower()

    def test_ndv(self):
        v = Visibility(value=9999, unit="M", ndv=True)
        result = format_visibility(v)
        assert "No Directional Variation" in result

    def test_metres_km_conversion_1000(self):
        v = Visibility(value=1000, unit="M")
        result = format_visibility(v)
        assert "1 km" in result

    def test_metres_km_conversion_5000(self):
        v = Visibility(value=5000, unit="M")
        result = format_visibility(v)
        assert "5 km" in result

    def test_metres_km_conversion_fractional(self):
        v = Visibility(value=1500, unit="M")
        result = format_visibility(v)
        assert "1.5 km" in result

    def test_sm_integer(self):
        v = Visibility(value=6.0, unit="SM")
        result = format_visibility(v)
        assert "SM" in result

    def test_greater_than_km(self):
        v = Visibility(value=15, unit="KM", is_greater_than=True)
        result = format_visibility(v)
        assert "Greater than" in result

    def test_direction_appended(self):
        v = Visibility(value=5000, unit="M", direction="NE")
        result = format_visibility(v)
        assert "NE" in result

    def test_directional_visibility_appended(self):
        from weather_decoder.models import DirectionalVisibility

        dv = DirectionalVisibility(value=2000, direction="SW")
        v = Visibility(value=5000, unit="M", directional_visibility=dv)
        result = format_visibility(v)
        assert "SW" in result

    def test_minimum_visibility_appended(self):
        mv = MinimumVisibility(value=800, direction="N")
        v = Visibility(value=5000, unit="M", minimum_visibility=mv)
        result = format_visibility(v)
        assert "minimum" in result


@pytest.mark.unit
class TestFormatSkyCondition:
    """Tests for format_sky_condition()."""

    def test_skc(self):
        result = format_sky_condition(SkyCondition(coverage="SKC", height=None))
        assert "Clear" in result

    def test_clr(self):
        result = format_sky_condition(SkyCondition(coverage="CLR", height=None))
        assert "Clear" in result

    def test_nsc(self):
        result = format_sky_condition(SkyCondition(coverage="NSC", height=None))
        assert "No significant cloud" in result

    def test_ncd(self):
        result = format_sky_condition(SkyCondition(coverage="NCD", height=None))
        assert "No cloud detected" in result

    def test_vv_unknown_height(self):
        result = format_sky_condition(
            SkyCondition(coverage="VV", height=None, unknown_height=True)
        )
        assert "Vertical visibility" in result
        assert "unknown" in result.lower()

    def test_vv_known_height(self):
        result = format_sky_condition(SkyCondition(coverage="VV", height=800))
        assert "Vertical visibility" in result
        assert "800" in result

    def test_slash_unknown(self):
        result = format_sky_condition(
            SkyCondition(coverage="///", height=None, unknown_height=True)
        )
        assert "Unknown" in result

    def test_slash_known_height(self):
        result = format_sky_condition(SkyCondition(coverage="///", height=500))
        assert "500" in result

    def test_few_layer(self):
        result = format_sky_condition(SkyCondition(coverage="FEW", height=2000))
        assert "FEW" in result
        assert "2000" in result

    def test_sct_with_cb(self):
        result = format_sky_condition(
            SkyCondition(coverage="SCT", height=3000, cb=True)
        )
        assert "SCT" in result
        assert "CB" in result

    def test_bkn_with_tcu(self):
        result = format_sky_condition(
            SkyCondition(coverage="BKN", height=1500, tcu=True)
        )
        assert "BKN" in result
        assert "TCU" in result

    def test_ovc_unknown_height(self):
        result = format_sky_condition(
            SkyCondition(coverage="OVC", height=None, unknown_height=True)
        )
        assert "unknown" in result.lower()

    def test_unknown_type(self):
        result = format_sky_condition(
            SkyCondition(coverage="FEW", height=1000, unknown_type=True)
        )
        assert "unknown type" in result.lower()

    def test_system_unavailable(self):
        result = format_sky_condition(
            SkyCondition(coverage="FEW", height=1000, system_unavailable=True)
        )
        assert "not operating" in result.lower() or "unavailable" in result.lower()


@pytest.mark.unit
class TestFormatWeatherGroup:
    """Tests for format_weather_group()."""

    def test_unavailable(self):
        result = format_weather_group(WeatherPhenomenon(unavailable=True))
        assert "Not observable" in result or "automated" in result.lower()

    def test_simple_phenomenon(self):
        wx = WeatherPhenomenon(phenomena=("FG",))
        result = format_weather_group(wx)
        assert "FG" in result

    def test_intensity_descriptor_phenomenon(self):
        wx = WeatherPhenomenon(intensity="-", descriptor="SH", phenomena=("RA",))
        result = format_weather_group(wx)
        assert "-" in result
        assert "SH" in result
        assert "RA" in result

    def test_multiple_phenomena_joined(self):
        wx = WeatherPhenomenon(descriptor="TS", phenomena=("RA", "GR"))
        result = format_weather_group(wx)
        assert "RA" in result
        assert "GR" in result

    def test_empty_phenomenon_returns_empty(self):
        wx = WeatherPhenomenon()
        result = format_weather_group(wx)
        assert result == ""


@pytest.mark.unit
class TestFormatTemperature:
    """Tests for format_temperature()."""

    def test_none_returns_not_reported(self):
        assert format_temperature(None) == "Not reported"

    def test_positive_temperature(self):
        result = format_temperature(20.0)
        assert "20" in result
        assert "°C" in result

    def test_negative_temperature(self):
        result = format_temperature(-5.0)
        assert "-5" in result
        assert "°C" in result

    def test_zero_temperature(self):
        result = format_temperature(0.0)
        assert "0" in result
        assert "°C" in result


@pytest.mark.unit
class TestFormatPressure:
    """Tests for format_pressure()."""

    def test_none_returns_not_reported(self):
        assert format_pressure(None) == "Not reported"

    def test_hpa(self):
        result = format_pressure(Pressure(value=1013.2, unit="hPa"))
        assert "1013.2" in result
        assert "hPa" in result

    def test_inhg(self):
        result = format_pressure(Pressure(value=29.92, unit="inHg"))
        assert "29.92" in result
        assert "inHg" in result


# ===========================================================================
# PATTERNS
# ===========================================================================


@pytest.mark.unit
class TestCompiledPatterns:
    """Tests for COMPILED_PATTERNS dictionary."""

    EXPECTED_KEYS = [
        "metar_type",
        "station_id",
        "datetime",
        "valid_period",
        "auto",
        "wind",
        "wind_extreme",
        "wind_var",
        "visibility",
        "rvr",
        "runway_state",
        "snoclo",
        "missing_visibility",
        "missing_weather",
        "sky",
        "temperature",
        "taf_temperature",
        "altimeter",
        "qnh",
        "alt_qnh",
        "alt",
        "change_group",
        "fm",
        "remarks",
        "time_range",
    ]

    def test_all_expected_keys_present(self):
        for key in self.EXPECTED_KEYS:
            assert key in COMPILED_PATTERNS, (
                f"Key '{key}' missing from COMPILED_PATTERNS"
            )

    def test_all_values_are_compiled_patterns(self):
        for key, pat in COMPILED_PATTERNS.items():
            assert hasattr(pat, "search"), (
                f"Pattern for '{key}' is not a compiled regex"
            )

    def test_metar_type_matches_metar(self):
        assert COMPILED_PATTERNS["metar_type"].match("METAR")

    def test_metar_type_matches_speci(self):
        assert COMPILED_PATTERNS["metar_type"].match("SPECI")

    def test_metar_type_no_match_taf(self):
        assert not COMPILED_PATTERNS["metar_type"].match("TAF")

    def test_wind_pattern_normal(self):
        assert COMPILED_PATTERNS["wind"].search("28045G65KT")

    def test_wind_pattern_vrb(self):
        assert COMPILED_PATTERNS["wind"].search("VRB05KT")

    def test_wind_pattern_calm(self):
        assert COMPILED_PATTERNS["wind"].search("00000KT")

    def test_wind_pattern_mps(self):
        assert COMPILED_PATTERNS["wind"].search("09010MPS")

    def test_wind_var_pattern_match(self):
        assert COMPILED_PATTERNS["wind_var"].search("250V320")

    def test_wind_var_pattern_no_match(self):
        assert not COMPILED_PATTERNS["wind_var"].search("250")

    def test_datetime_pattern_match(self):
        assert COMPILED_PATTERNS["datetime"].search("151751Z")

    def test_datetime_pattern_no_match_short(self):
        assert not COMPILED_PATTERNS["datetime"].search("15175Z")

    def test_sky_pattern_few(self):
        assert COMPILED_PATTERNS["sky"].search("FEW020")

    def test_sky_pattern_sct_cb(self):
        assert COMPILED_PATTERNS["sky"].search("SCT030CB")

    def test_sky_pattern_ovc_tcu(self):
        assert COMPILED_PATTERNS["sky"].search("OVC010TCU")

    def test_sky_pattern_vv_unknown(self):
        assert COMPILED_PATTERNS["sky"].search("VV///")

    def test_temperature_pattern_match(self):
        assert COMPILED_PATTERNS["temperature"].match("20/15")
        assert COMPILED_PATTERNS["temperature"].match("M05/M10")

    def test_altimeter_q_match(self):
        assert COMPILED_PATTERNS["altimeter"].search("Q1013")

    def test_altimeter_a_match(self):
        assert COMPILED_PATTERNS["altimeter"].search("A2992")

    def test_rvr_pattern_basic(self):
        assert COMPILED_PATTERNS["rvr"].search("R28L/0600")

    def test_rvr_pattern_with_ft(self):
        assert COMPILED_PATTERNS["rvr"].search("R28/0600FT")

    def test_station_id_pattern(self):
        assert COMPILED_PATTERNS["station_id"].match("EGLL")
        assert COMPILED_PATTERNS["station_id"].match("KJFK")

    def test_fm_pattern(self):
        assert COMPILED_PATTERNS["fm"].match("FM151200")

    def test_remarks_pattern(self):
        assert COMPILED_PATTERNS["remarks"].search("RMK AO2 SLP013")

    def test_snoclo_pattern(self):
        assert COMPILED_PATTERNS["snoclo"].match("R/SNOCLO")
        assert not COMPILED_PATTERNS["snoclo"].match("SNOCLO")

    def test_missing_visibility_pattern(self):
        assert COMPILED_PATTERNS["missing_visibility"].match("////")
        assert not COMPILED_PATTERNS["missing_visibility"].match("///")

    def test_missing_weather_pattern(self):
        assert COMPILED_PATTERNS["missing_weather"].match("//")
        assert not COMPILED_PATTERNS["missing_weather"].match("/")


# ===========================================================================
# TIME PARSER
# ===========================================================================


@pytest.mark.unit
class TestTimeParser:
    """Tests for TimeParser utility methods."""

    # --- format_time ---

    def test_format_time_basic(self):
        dt = datetime(2024, 6, 17, 17, 51, tzinfo=timezone.utc)
        result = TimeParser.format_time(dt)
        assert result == "17 17:51 UTC"

    def test_format_time_single_digit_day_padded(self):
        dt = datetime(2024, 3, 5, 8, 3, tzinfo=timezone.utc)
        result = TimeParser.format_time(dt)
        assert result == "05 08:03 UTC"

    def test_format_time_midnight(self):
        dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = TimeParser.format_time(dt)
        assert result == "01 00:00 UTC"

    # --- get_current_utc_time ---

    def test_get_current_utc_time_not_none(self):
        result = TimeParser.get_current_utc_time()
        assert result is not None

    def test_get_current_utc_time_is_aware(self):
        result = TimeParser.get_current_utc_time()
        assert result.tzinfo is not None

    def test_get_current_utc_time_is_utc(self):
        result = TimeParser.get_current_utc_time()
        assert result.tzinfo == timezone.utc

    def test_get_current_utc_time_is_datetime(self):
        result = TimeParser.get_current_utc_time()
        assert isinstance(result, datetime)

    # --- _add_month ---

    def test_add_month_december_to_january(self):
        dt = datetime(2023, 12, 15, 10, 30, tzinfo=timezone.utc)
        result = TimeParser._add_month(dt)
        assert result.month == 1
        assert result.year == 2024
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_add_month_non_december(self):
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        result = TimeParser._add_month(dt)
        assert result.month == 2
        assert result.year == 2024

    def test_add_month_clamps_day_to_last(self):
        """January 31 -> February: day clamped to 29 (2024 is leap year)."""
        dt = datetime(2024, 1, 31, 10, 30, tzinfo=timezone.utc)
        result = TimeParser._add_month(dt)
        assert result.month == 2
        assert result.day == 29  # 2024 is a leap year

    def test_add_month_clamps_day_non_leap(self):
        """January 31 -> February in a non-leap year: clamp to 28."""
        dt = datetime(2023, 1, 31, 10, 30, tzinfo=timezone.utc)
        result = TimeParser._add_month(dt)
        assert result.month == 2
        assert result.day == 28

    def test_add_month_preserves_tzinfo(self):
        dt = datetime(2024, 3, 10, 12, 0, tzinfo=timezone.utc)
        result = TimeParser._add_month(dt)
        assert result.tzinfo == timezone.utc

    # --- _resolve_month_year ---

    def test_resolve_month_year_no_change(self):
        """Day close to current day: no month change."""
        dt = datetime(2024, 3, 15, 12, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(dt, 15)
        assert year == 2024
        assert month == 3

    def test_resolve_month_year_forward_boundary(self):
        """Day delta < -15 means report is from next month."""
        dt = datetime(2024, 1, 28, 12, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(dt, 5)
        assert month == 2
        assert year == 2024

    def test_resolve_month_year_backward_boundary(self):
        """Day delta > 15 means report is from previous month."""
        dt = datetime(2024, 2, 5, 12, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(dt, 28)
        assert month == 1
        assert year == 2024

    def test_resolve_month_year_december_backward(self):
        """Going back from January crosses year boundary to December."""
        dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(dt, 28)
        assert month == 12
        assert year == 2023

    def test_resolve_month_year_december_forward(self):
        """Going forward from December crosses year boundary to January."""
        dt = datetime(2023, 12, 28, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(dt, 5)
        assert month == 1
        assert year == 2024

    # --- parse_observation_time ---

    def test_parse_observation_time_valid(self):
        ref = datetime(2024, 3, 15, 10, 0, tzinfo=timezone.utc)
        result = TimeParser.parse_observation_time("151751Z", ref)
        assert result is not None
        assert result.day == 15
        assert result.hour == 17
        assert result.minute == 51

    def test_parse_observation_time_invalid_returns_none(self):
        result = TimeParser.parse_observation_time("invalid")
        assert result is None

    def test_parse_observation_time_uses_reference(self):
        ref = datetime(2024, 6, 15, 0, 0, tzinfo=timezone.utc)
        result = TimeParser.parse_observation_time("151200Z", ref)
        assert result is not None
        assert result.month == 6

    # --- parse_valid_period: 24:00 handling ---

    def test_parse_valid_period_24h_hour_normalized(self):
        """Hour 24 in a valid period should be normalized to 00 on the next day."""
        ref = datetime(2024, 3, 15, 0, 0, tzinfo=timezone.utc)
        result = TimeParser.parse_valid_period("1524/1600", ref)
        assert result is not None
        # from_time has hour=24 -> day 16 hour 0
        assert result.start.day == 16
        assert result.start.hour == 0

    def test_parse_valid_period_returns_time_range(self):
        ref = datetime(2024, 3, 15, 0, 0, tzinfo=timezone.utc)
        result = TimeParser.parse_valid_period("1506/1612", ref)
        assert result is not None
        assert isinstance(result, TimeRange)
        assert result.start < result.end


# ===========================================================================
# MetarData / TafData convenience wrappers
# ===========================================================================


@pytest.mark.unit
class TestMetarData:
    """Tests for MetarData wrapper."""

    def test_is_subclass_of_metar_report(self):
        mr = _make_metar()
        assert isinstance(mr, MetarReport)

    def test_wind_text_with_wind(self):
        mr = _make_metar(wind=Wind(direction=280, speed=45, unit="KT", gust=65))
        result = mr.wind_text()
        assert "280°" in result
        assert "45" in result
        assert "gusting" in result

    def test_wind_text_calm(self):
        mr = _make_metar(wind=Wind(direction=0, speed=0, unit="KT", is_calm=True))
        assert mr.wind_text() == "Calm"

    def test_wind_text_none(self):
        mr = _make_metar(wind=None)
        assert mr.wind_text() == "Not reported"

    def test_visibility_text_cavok(self):
        mr = _make_metar(visibility=Visibility(value=0, unit="M", is_cavok=True))
        result = mr.visibility_text()
        assert "CAVOK" in result

    def test_visibility_text_9999(self):
        mr = _make_metar(visibility=Visibility(value=9999, unit="M"))
        result = mr.visibility_text()
        assert "10 km" in result

    def test_visibility_text_none(self):
        mr = _make_metar(visibility=None)
        assert mr.visibility_text() == "Not reported"

    def test_station_id_stored(self):
        mr = _make_metar(station_id="KJFK")
        assert mr.station_id == "KJFK"

    def test_observation_time_stored(self):
        obs_time = datetime(2024, 3, 15, 17, 51, tzinfo=timezone.utc)
        mr = _make_metar(observation_time=obs_time)
        assert mr.observation_time == obs_time


@pytest.mark.unit
class TestTafData:
    """Tests for TafData wrapper."""

    def test_is_subclass_of_taf_report(self):
        tr = _make_taf()
        assert isinstance(tr, TafReport)

    def test_station_id_stored(self):
        tr = _make_taf(station_id="EGLL")
        assert tr.station_id == "EGLL"

    def test_valid_period_stored(self):
        vp = TimeRange(
            start=datetime(2024, 3, 15, 6, 0, tzinfo=timezone.utc),
            end=datetime(2024, 3, 16, 12, 0, tzinfo=timezone.utc),
        )
        tr = _make_taf(valid_period=vp)
        assert tr.valid_period.start == vp.start
        assert tr.valid_period.end == vp.end

    def test_forecast_periods_stored(self):
        period = TafForecastPeriod(
            change_type="FM",
            from_time=datetime(2024, 3, 15, 6, 0, tzinfo=timezone.utc),
        )
        tr = _make_taf(forecast_periods=[period])
        assert len(tr.forecast_periods) == 1
        assert tr.forecast_periods[0].change_type == "FM"

    def test_defaults(self):
        tr = _make_taf()
        assert tr.report_type == "TAF"
        assert tr.status == "NORMAL"
        assert tr.is_amended is False


# ===========================================================================
# Additional model construction / equality tests
# ===========================================================================


@pytest.mark.unit
class TestModelConstruction:
    """Tests for model field round-trips and equality."""

    def test_wind_equality(self):
        w1 = Wind(direction=270, speed=10, unit="KT")
        w2 = Wind(direction=270, speed=10, unit="KT")
        assert w1 == w2

    def test_visibility_equality(self):
        v1 = Visibility(value=9999, unit="M")
        v2 = Visibility(value=9999, unit="M")
        assert v1 == v2

    def test_pressure_fields(self):
        p = Pressure(value=1013.2, unit="hPa")
        assert p.value == 1013.2
        assert p.unit == "hPa"

    def test_icing_forecast_fields(self):
        icf = IcingForecast(
            intensity="moderate",
            base_ft=5000,
            top_ft=9000,
            icing_type="rime",
            raw="620504",
        )
        assert icf.intensity == "moderate"
        assert icf.base_ft == 5000
        assert icf.top_ft == 9000
        assert icf.icing_type == "rime"
        assert icf.raw == "620504"

    def test_turbulence_forecast_fields(self):
        tbf = TurbulenceForecast(
            intensity="severe",
            base_ft=10000,
            top_ft=20000,
            in_cloud=False,
            raw="560510",
        )
        assert tbf.intensity == "severe"
        assert tbf.in_cloud is False

    def test_time_range_ordering(self):
        start = datetime(2024, 3, 15, 6, 0, tzinfo=timezone.utc)
        end = datetime(2024, 3, 16, 12, 0, tzinfo=timezone.utc)
        tr = TimeRange(start=start, end=end)
        assert tr.start < tr.end

    def test_military_color_code_fields(self):
        mcc = MilitaryColorCode(code="RED", description="Red")
        assert mcc.code == "RED"
        assert mcc.description == "Red"

    def test_sea_condition_with_wave_height(self):
        sc = SeaCondition(
            sea_surface_temperature=18,
            state_of_sea="moderate",
            significant_wave_height_m=2.5,
        )
        assert sc.significant_wave_height_m == 2.5

    def test_wind_shear_with_runway(self):
        ws = WindShear(
            kind="runway",
            description="Wind shear at 2000 ft",
            runway="09L",
            raw="WS020/09015KT",
        )
        assert ws.runway == "09L"
        assert ws.raw == "WS020/09015KT"

    def test_trend_with_time(self):
        tt = TrendTime(from_time="1200", until_time="1400")
        t = Trend(
            kind="TEMPO",
            description="temporary",
            raw="TEMPO 1200/1400 TSRA",
            time=tt,
        )
        assert t.time is tt
        assert t.time.from_time == "1200"
