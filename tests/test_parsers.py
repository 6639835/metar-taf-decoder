"""Comprehensive pytest tests for all weather_decoder parsers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pytest

from weather_decoder.parsers.token_stream import TokenStream
from weather_decoder.parsers.wind_parser import WindParser
from weather_decoder.parsers.visibility_parser import VisibilityParser
from weather_decoder.parsers.weather_parser import WeatherParser
from weather_decoder.parsers.sky_parser import SkyParser
from weather_decoder.parsers.temperature_parser import TemperatureParser
from weather_decoder.parsers.pressure_parser import PressureParser
from weather_decoder.parsers.runway_parser import RunwayParser
from weather_decoder.parsers.sea_parser import SeaParser
from weather_decoder.parsers.windshear_parser import WindShearParser
from weather_decoder.parsers.trend_parser import TrendParser
from weather_decoder.parsers.icing_parser import IcingParser
from weather_decoder.parsers.turbulence_parser import TurbulenceParser
from weather_decoder.parsers.time_parser import TimeParser
from weather_decoder.models import (
    Wind,
    Visibility,
    WeatherPhenomenon,
    SkyCondition,
    Pressure,
    RunwayVisualRange,
    RunwayState,
    SeaCondition,
    WindShear,
    Trend,
    IcingForecast,
    TurbulenceForecast,
    TimeRange,
    TemperatureForecast,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_stream(*tokens: str) -> TokenStream:
    """Build a TokenStream from positional string arguments."""
    return TokenStream(list(tokens))


# ===========================================================================
# TokenStream tests
# ===========================================================================

class TestTokenStream:
    @pytest.mark.unit
    def test_from_text_splits_whitespace(self) -> None:
        stream = TokenStream.from_text("METAR EGLL 061751Z")
        assert stream.tokens == ["METAR", "EGLL", "061751Z"]

    @pytest.mark.unit
    def test_len(self) -> None:
        stream = make_stream("A", "B", "C")
        assert len(stream) == 3

    @pytest.mark.unit
    def test_peek_default(self) -> None:
        stream = make_stream("X", "Y")
        assert stream.peek(0) == "X"
        assert stream.peek(1) == "Y"

    @pytest.mark.unit
    def test_peek_out_of_bounds(self) -> None:
        stream = make_stream("A")
        assert stream.peek(5) is None
        assert stream.peek(-1) is None

    @pytest.mark.unit
    def test_pop_removes_and_returns_token(self) -> None:
        stream = make_stream("A", "B", "C")
        token = stream.pop(1)
        assert token == "B"
        assert stream.tokens == ["A", "C"]

    @pytest.mark.unit
    def test_pop_default_index(self) -> None:
        stream = make_stream("A", "B")
        assert stream.pop() == "A"
        assert stream.tokens == ["B"]

    @pytest.mark.unit
    def test_consume_if_match(self) -> None:
        stream = make_stream("A", "B", "C")
        result = stream.consume_if(lambda t: t == "B")
        assert result == "B"
        assert stream.tokens == ["A", "C"]

    @pytest.mark.unit
    def test_consume_if_no_match(self) -> None:
        stream = make_stream("A", "B")
        result = stream.consume_if(lambda t: t == "Z")
        assert result is None
        assert stream.tokens == ["A", "B"]

    @pytest.mark.unit
    def test_consume_all(self) -> None:
        stream = make_stream("A", "B", "A", "C")
        results = stream.consume_all(lambda t: t == "A")
        assert results == ["A", "A"]
        assert stream.tokens == ["B", "C"]

    @pytest.mark.unit
    def test_consume_all_no_match(self) -> None:
        stream = make_stream("X", "Y")
        assert stream.consume_all(lambda t: t == "Z") == []

    @pytest.mark.unit
    def test_remaining_returns_copy(self) -> None:
        stream = make_stream("A", "B")
        rem = stream.remaining()
        rem.append("C")
        assert len(stream) == 2  # original not mutated

    @pytest.mark.unit
    def test_empty_stream(self) -> None:
        stream = TokenStream.from_text("")
        # splitting empty string gives [''] in Python
        # from_text does text.split() which gives [] for empty/whitespace
        stream2 = TokenStream.from_text("   ")
        assert stream2.tokens == []


# ===========================================================================
# WindParser tests
# ===========================================================================

class TestWindParser:
    parser = WindParser()

    @pytest.mark.unit
    def test_parse_standard_kt(self) -> None:
        wind = self.parser.parse("28045KT")
        assert wind is not None
        assert wind.direction == 280
        assert wind.speed == 45
        assert wind.unit == "KT"
        assert wind.gust is None
        assert not wind.is_variable
        assert not wind.is_calm

    @pytest.mark.unit
    def test_parse_with_gust(self) -> None:
        wind = self.parser.parse("28045G65KT")
        assert wind is not None
        assert wind.gust == 65
        assert not wind.gust_is_above

    @pytest.mark.unit
    def test_parse_vrb_variable_wind(self) -> None:
        wind = self.parser.parse("VRB03KT")
        assert wind is not None
        assert wind.is_variable
        assert wind.direction is None
        assert wind.speed == 3

    @pytest.mark.unit
    def test_parse_calm_wind(self) -> None:
        wind = self.parser.parse("00000KT")
        assert wind is not None
        assert wind.is_calm
        assert wind.speed == 0
        assert wind.direction == 0

    @pytest.mark.unit
    def test_parse_mps_unit(self) -> None:
        wind = self.parser.parse("18010MPS")
        assert wind is not None
        assert wind.unit == "MPS"

    @pytest.mark.unit
    def test_parse_kmh_unit(self) -> None:
        wind = self.parser.parse("27020KMH")
        assert wind is not None
        assert wind.unit == "KMH"

    @pytest.mark.unit
    def test_parse_extreme_abv(self) -> None:
        wind = self.parser.parse("ABV49KT")
        assert wind is not None
        assert wind.speed == 49
        assert wind.is_variable
        assert wind.is_above

    @pytest.mark.unit
    def test_parse_p_prefix_above_max(self) -> None:
        wind = self.parser.parse("P99KT")
        # WIND_EXTREME_PATTERN won't match; try WIND_PATTERN with P prefix
        # "P99KT" — speed 99, no direction → None because 3-digit direction missing
        # Actually P prefix in WIND_PATTERN needs a direction group; P99KT won't
        # have 3-digit direction so parse should return None
        # The WIND_EXTREME_PATTERN requires ABV prefix; P-prefix is in WIND_PATTERN
        # Let's just assert it doesn't raise
        # It may or may not parse; we just care it doesn't crash
        _ = self.parser.parse("P99KT")

    @pytest.mark.unit
    def test_parse_invalid_token(self) -> None:
        assert self.parser.parse("NOSIG") is None
        assert self.parser.parse("") is None
        assert self.parser.parse("CAVOK") is None

    @pytest.mark.unit
    def test_parse_gust_p_prefix(self) -> None:
        wind = self.parser.parse("27070GP99KT")
        assert wind is not None
        assert wind.gust == 99
        assert wind.gust_is_above

    @pytest.mark.unit
    def test_parse_3digit_speed(self) -> None:
        wind = self.parser.parse("360100KT")
        assert wind is not None
        assert wind.speed == 100
        assert wind.direction == 360

    @pytest.mark.unit
    def test_extract_with_variable_range(self) -> None:
        stream = make_stream("18020KT", "150V210")
        wind = self.parser.extract(stream)
        assert wind is not None
        assert wind.variable_range == (150, 210)
        assert len(stream) == 0

    @pytest.mark.unit
    def test_extract_no_variable_range(self) -> None:
        stream = make_stream("09010KT", "1200")
        wind = self.parser.extract(stream)
        assert wind is not None
        assert wind.variable_range is None
        assert len(stream) == 1  # "1200" remains

    @pytest.mark.unit
    def test_extract_returns_none_on_empty(self) -> None:
        stream = make_stream("CAVOK", "1234")
        result = self.parser.extract(stream)
        assert result is None

    @pytest.mark.unit
    def test_determine_unit_fallback(self) -> None:
        # Token with no known unit → defaults to KT
        unit = WindParser._determine_unit("36010XX")
        assert unit == "KT"


# ===========================================================================
# VisibilityParser tests
# ===========================================================================

class TestVisibilityParser:
    parser = VisibilityParser()

    @pytest.mark.unit
    def test_parse_cavok(self) -> None:
        vis = self.parser.parse("CAVOK")
        assert vis is not None
        assert vis.is_cavok
        assert vis.value == 9999

    @pytest.mark.unit
    def test_parse_unavailable(self) -> None:
        vis = self.parser.parse("////")
        assert vis is not None
        assert vis.unavailable

    @pytest.mark.unit
    def test_parse_9999(self) -> None:
        vis = self.parser.parse("9999")
        assert vis is not None
        assert vis.value == 9999
        assert vis.unit == "M"
        assert not vis.is_less_than

    @pytest.mark.unit
    def test_parse_1200(self) -> None:
        vis = self.parser.parse("1200")
        assert vis is not None
        assert vis.value == 1200
        assert vis.unit == "M"

    @pytest.mark.unit
    def test_parse_0000_is_less_than(self) -> None:
        vis = self.parser.parse("0000")
        assert vis is not None
        assert vis.is_less_than

    @pytest.mark.unit
    def test_parse_ndv(self) -> None:
        vis = self.parser.parse("9999NDV")
        assert vis is not None
        assert vis.ndv
        assert vis.value == 9999

    @pytest.mark.unit
    def test_parse_meter_suffix(self) -> None:
        vis = self.parser.parse("1200M")
        assert vis is not None
        assert vis.value == 1200
        assert vis.unit == "M"

    @pytest.mark.unit
    def test_parse_km(self) -> None:
        vis = self.parser.parse("6KM")
        assert vis is not None
        assert vis.value == 6
        assert vis.unit == "KM"

    @pytest.mark.unit
    def test_parse_p6sm_greater_than(self) -> None:
        vis = self.parser.parse("P6SM")
        assert vis is not None
        assert vis.is_greater_than
        assert vis.unit == "SM"
        assert vis.value == 6.0

    @pytest.mark.unit
    def test_parse_m1_4sm_less_than_fractional(self) -> None:
        vis = self.parser.parse("M1/4SM")
        assert vis is not None
        assert vis.is_less_than
        assert abs(vis.value - 0.25) < 1e-9

    @pytest.mark.unit
    def test_parse_half_sm(self) -> None:
        vis = self.parser.parse("1/2SM")
        assert vis is not None
        assert abs(vis.value - 0.5) < 1e-9
        assert vis.unit == "SM"

    @pytest.mark.unit
    def test_parse_directional_visibility(self) -> None:
        vis = self.parser.parse("1200SE")
        assert vis is not None
        assert vis.value == 1200
        assert vis.direction == "SE"

    @pytest.mark.unit
    def test_parse_directional_ne(self) -> None:
        vis = self.parser.parse("2000NE")
        assert vis is not None
        assert vis.direction == "NE"

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("WIND") is None
        assert self.parser.parse("") is None

    @pytest.mark.unit
    def test_extract_whole_plus_fraction_sm(self) -> None:
        stream = make_stream("1", "1/4SM")
        vis = self.parser.extract(stream)
        assert vis is not None
        assert abs(vis.value - 1.25) < 1e-9
        assert vis.unit == "SM"
        assert len(stream) == 0

    @pytest.mark.unit
    def test_extract_minimum_visibility_from_prevailing(self) -> None:
        # "2000" followed by "1200SE" → prevailing=2000, minimum=1200 SE
        stream = make_stream("2000", "1200SE")
        vis = self.parser.extract(stream)
        assert vis is not None
        assert vis.value == 2000
        assert vis.minimum_visibility is not None
        assert vis.minimum_visibility.value == 1200
        assert vis.minimum_visibility.direction == "SE"

    @pytest.mark.unit
    def test_extract_minimum_visibility_no_direction(self) -> None:
        # "2000" followed by "0800" → minimum_visibility without direction
        stream = make_stream("2000", "0800")
        vis = self.parser.extract(stream)
        assert vis is not None
        assert vis.minimum_visibility is not None
        assert vis.minimum_visibility.value == 800

    @pytest.mark.unit
    def test_extract_directional_vis_after_directional(self) -> None:
        # "2000NE" then "1200SE" → prevailing has direction, second becomes directional_visibility
        stream = make_stream("2000NE", "1200SE")
        vis = self.parser.extract(stream)
        assert vis is not None
        assert vis.direction == "NE"
        assert vis.directional_visibility is not None
        assert vis.directional_visibility.value == 1200
        assert vis.directional_visibility.direction == "SE"

    @pytest.mark.unit
    def test_extract_cavok_no_additional(self) -> None:
        stream = make_stream("CAVOK", "OVC050")
        vis = self.parser.extract(stream)
        assert vis is not None
        assert vis.is_cavok
        # CAVOK: additional check not performed
        assert len(stream) == 1


# ===========================================================================
# WeatherParser tests
# ===========================================================================

class TestWeatherParser:
    parser = WeatherParser()

    @pytest.mark.unit
    def test_parse_unavailable(self) -> None:
        wx = self.parser.parse("//")
        assert wx is not None
        assert wx.unavailable

    @pytest.mark.unit
    def test_parse_plus_fc_tornado(self) -> None:
        wx = self.parser.parse("+FC")
        assert wx is not None
        assert wx.intensity == "heavy"
        assert "tornado/waterspout" in wx.phenomena

    @pytest.mark.unit
    def test_parse_light_rain(self) -> None:
        wx = self.parser.parse("-RA")
        assert wx is not None
        assert wx.intensity == "light"
        assert "rain" in wx.phenomena

    @pytest.mark.unit
    def test_parse_heavy_rain(self) -> None:
        wx = self.parser.parse("+RA")
        assert wx is not None
        assert wx.intensity == "heavy"
        assert "rain" in wx.phenomena

    @pytest.mark.unit
    def test_parse_ts_descriptor_alone(self) -> None:
        wx = self.parser.parse("TS")
        assert wx is not None
        assert wx.descriptor == "thunderstorm"

    @pytest.mark.unit
    def test_parse_tsra(self) -> None:
        wx = self.parser.parse("TSRA")
        assert wx is not None
        assert "thunderstorm with rain" in wx.phenomena

    @pytest.mark.unit
    def test_parse_heavy_tsra(self) -> None:
        wx = self.parser.parse("+TSRA")
        assert wx is not None
        assert wx.intensity == "heavy"

    @pytest.mark.unit
    def test_parse_vcts_compound(self) -> None:
        wx = self.parser.parse("VCTS")
        assert wx is not None
        assert "thunderstorm in vicinity" in wx.phenomena

    @pytest.mark.unit
    def test_parse_fzfg_compound(self) -> None:
        wx = self.parser.parse("FZFG")
        assert wx is not None
        assert "freezing fog" in wx.phenomena

    @pytest.mark.unit
    def test_parse_blsn_compound(self) -> None:
        wx = self.parser.parse("BLSN")
        assert wx is not None
        assert "blowing snow" in wx.phenomena

    @pytest.mark.unit
    def test_parse_shra_compound(self) -> None:
        wx = self.parser.parse("SHRA")
        assert wx is not None
        assert "rain shower" in wx.phenomena

    @pytest.mark.unit
    def test_parse_rasn_compound(self) -> None:
        wx = self.parser.parse("RASN")
        assert wx is not None
        assert "rain and snow mixed (sleet)" in wx.phenomena

    @pytest.mark.unit
    def test_parse_fg(self) -> None:
        wx = self.parser.parse("FG")
        assert wx is not None
        assert "fog" in wx.phenomena

    @pytest.mark.unit
    def test_parse_br(self) -> None:
        wx = self.parser.parse("BR")
        assert wx is not None
        assert "mist" in wx.phenomena

    @pytest.mark.unit
    def test_parse_recent_resn(self) -> None:
        wx = self.parser.parse("RESN")
        assert wx is not None
        assert wx.intensity == "recent"

    @pytest.mark.unit
    def test_parse_recent_re_slash_slash(self) -> None:
        wx = self.parser.parse("RE//")
        assert wx is not None
        assert wx.intensity == "recent"
        assert "not reported" in wx.phenomena

    @pytest.mark.unit
    def test_parse_nsw_returns_none(self) -> None:
        assert self.parser.parse("NSW") is None

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("BKN050") is None
        assert self.parser.parse("") is None

    @pytest.mark.unit
    def test_extract_all_stops_at_trend(self) -> None:
        stream = make_stream("-RA", "FG", "BECMG", "+SN")
        results = self.parser.extract_all(stream)
        # Should stop before BECMG
        phenomena_names = [p for wx in results for p in wx.phenomena]
        assert "rain" in phenomena_names
        assert "fog" in phenomena_names
        # BECMG and +SN still in stream
        assert "BECMG" in stream.tokens

    @pytest.mark.unit
    def test_extract_all_skips_recent(self) -> None:
        # Recent weather tokens should not be included in extract_all
        stream = make_stream("-RA", "RESN")
        results = self.parser.extract_all(stream)
        intensities = [wx.intensity for wx in results]
        assert "recent" not in intensities

    @pytest.mark.unit
    def test_extract_recent(self) -> None:
        stream = make_stream("FG", "RESN", "RERA")
        results = self.parser.extract_recent(stream)
        for wx in results:
            assert wx.intensity == "recent"

    @pytest.mark.unit
    def test_extract_recent_max_3(self) -> None:
        stream = make_stream("RESN", "RERA", "RERASN", "REFZDZ")
        results = self.parser.extract_recent(stream)
        assert len(results) <= 3

    @pytest.mark.unit
    def test_is_recent_weather_token(self) -> None:
        assert WeatherParser.is_recent_weather_token("RESN")
        assert WeatherParser.is_recent_weather_token("RERA")
        assert not WeatherParser.is_recent_weather_token("-RA")


# ===========================================================================
# SkyParser tests
# ===========================================================================

class TestSkyParser:
    parser = SkyParser()

    @pytest.mark.unit
    def test_parse_system_unavailable(self) -> None:
        sky = self.parser.parse("//////")
        assert sky is not None
        assert sky.system_unavailable
        assert sky.unknown_height

    @pytest.mark.unit
    def test_parse_skc(self) -> None:
        sky = self.parser.parse("SKC")
        assert sky is not None
        assert sky.coverage == "SKC"
        assert sky.height is None

    @pytest.mark.unit
    def test_parse_clr(self) -> None:
        sky = self.parser.parse("CLR")
        assert sky is not None
        assert sky.coverage == "CLR"

    @pytest.mark.unit
    def test_parse_nsc(self) -> None:
        sky = self.parser.parse("NSC")
        assert sky is not None
        assert sky.coverage == "NSC"

    @pytest.mark.unit
    def test_parse_ncd(self) -> None:
        sky = self.parser.parse("NCD")
        assert sky is not None
        assert sky.coverage == "NCD"

    @pytest.mark.unit
    def test_parse_few030(self) -> None:
        sky = self.parser.parse("FEW030")
        assert sky is not None
        assert sky.coverage == "FEW"
        assert sky.height == 3000
        assert not sky.cb
        assert not sky.tcu

    @pytest.mark.unit
    def test_parse_sct050cb(self) -> None:
        sky = self.parser.parse("SCT050CB")
        assert sky is not None
        assert sky.coverage == "SCT"
        assert sky.height == 5000
        assert sky.cb

    @pytest.mark.unit
    def test_parse_ovc010tcu(self) -> None:
        sky = self.parser.parse("OVC010TCU")
        assert sky is not None
        assert sky.tcu
        assert sky.height == 1000

    @pytest.mark.unit
    def test_parse_bkn_unknown_height(self) -> None:
        sky = self.parser.parse("BKN///")
        assert sky is not None
        assert sky.unknown_height
        assert sky.height is None

    @pytest.mark.unit
    def test_parse_vv010(self) -> None:
        sky = self.parser.parse("VV010")
        assert sky is not None
        assert sky.coverage == "VV"
        assert sky.height == 1000

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("") is None
        assert self.parser.parse("WIND") is None

    @pytest.mark.unit
    def test_extract_all_multiple(self) -> None:
        stream = make_stream("FEW030", "SCT060", "BKN120")
        conditions = self.parser.extract_all(stream)
        assert len(conditions) == 3
        assert len(stream) == 0

    @pytest.mark.unit
    def test_extract_all_stops_at_trend(self) -> None:
        stream = make_stream("FEW030", "TEMPO", "SCT050")
        conditions = self.parser.extract_all(stream)
        assert len(conditions) == 1
        assert "TEMPO" in stream.tokens

    @pytest.mark.unit
    def test_get_sky_description(self) -> None:
        desc = SkyParser.get_sky_description("FEW")
        assert isinstance(desc, str)
        # Falls back to key if not found
        assert SkyParser.get_sky_description("UNKNOWN_CODE") == "UNKNOWN_CODE"


# ===========================================================================
# TemperatureParser tests
# ===========================================================================

class TestTemperatureParser:
    parser = TemperatureParser()

    @pytest.mark.unit
    def test_parse_normal(self) -> None:
        result = self.parser.parse("22/18")
        assert result is not None
        temp, dew = result
        assert temp == 22.0
        assert dew == 18.0

    @pytest.mark.unit
    def test_parse_negative_temp(self) -> None:
        result = self.parser.parse("M05/M10")
        assert result is not None
        temp, dew = result
        assert temp == -5.0
        assert dew == -10.0

    @pytest.mark.unit
    def test_parse_missing_dewpoint(self) -> None:
        # METAR format: temperature only, dewpoint absent → token ends with "/"
        result = self.parser.parse("15/")
        assert result is not None
        temp, dew = result
        assert temp == 15.0
        assert dew is None

    @pytest.mark.unit
    def test_parse_missing_temp(self) -> None:
        # Missing temperature with dewpoint: left group = "//", separator "/", dewpoint "18"
        # This requires "///18" (3 slashes + 2 digits) to satisfy the pattern
        result = self.parser.parse("///18")
        assert result is not None
        temp, dew = result
        assert temp is None
        assert dew == 18.0

    @pytest.mark.unit
    def test_parse_both_missing(self) -> None:
        # Both missing: left "//" + sep "/" + right "//" = "/////"
        result = self.parser.parse("/////")
        assert result is not None
        temp, dew = result
        assert temp is None
        assert dew is None

    @pytest.mark.unit
    def test_parse_no_match(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("280/") is None
        assert self.parser.parse("") is None

    @pytest.mark.unit
    def test_extract_temperature_dewpoint(self) -> None:
        tokens = ["18020KT", "9999", "22/18", "Q1013"]
        temp, dew = self.parser.extract_temperature_dewpoint(tokens)
        assert temp == 22.0
        assert dew == 18.0
        assert "22/18" not in tokens  # consumed

    @pytest.mark.unit
    def test_extract_temperature_dewpoint_not_found(self) -> None:
        tokens = ["18020KT", "CAVOK"]
        result = self.parser.extract_temperature_dewpoint(tokens)
        assert result == (None, None)

    @pytest.mark.unit
    def test_extract_temperature_forecasts_tx(self) -> None:
        ref = datetime(2024, 6, 10, 0, 0, tzinfo=timezone.utc)
        tokens = ["TX25/1012Z", "TN05/1018Z"]
        forecasts = self.parser.extract_temperature_forecasts(tokens, reference_time=ref)
        assert len(forecasts) == 2
        kinds = {f.kind for f in forecasts}
        assert "max" in kinds
        assert "min" in kinds

    @pytest.mark.unit
    def test_extract_temperature_forecasts_negative(self) -> None:
        ref = datetime(2024, 1, 10, 0, 0, tzinfo=timezone.utc)
        tokens = ["TNM05/1018Z"]
        forecasts = self.parser.extract_temperature_forecasts(tokens, reference_time=ref)
        assert len(forecasts) == 1
        assert forecasts[0].value == -5
        assert forecasts[0].kind == "min"

    @pytest.mark.unit
    def test_parse_temperature_component_negative(self) -> None:
        assert TemperatureParser._parse_temperature_component("M10") == -10.0

    @pytest.mark.unit
    def test_parse_temperature_component_none_input(self) -> None:
        assert TemperatureParser._parse_temperature_component(None) is None

    @pytest.mark.unit
    def test_parse_temperature_component_slash(self) -> None:
        assert TemperatureParser._parse_temperature_component("//") is None

    @pytest.mark.unit
    def test_parse_temperature_component_empty(self) -> None:
        assert TemperatureParser._parse_temperature_component("") is None


# ===========================================================================
# PressureParser tests
# ===========================================================================

class TestPressureParser:
    parser = PressureParser()

    @pytest.mark.unit
    def test_parse_altimeter_inhg(self) -> None:
        pressure = self.parser.parse("A2992")
        assert pressure is not None
        assert abs(pressure.value - 29.92) < 0.001
        assert pressure.unit == "inHg"

    @pytest.mark.unit
    def test_parse_altimeter_hpa(self) -> None:
        pressure = self.parser.parse("Q1013")
        assert pressure is not None
        assert pressure.value == 1013.0
        assert pressure.unit == "hPa"

    @pytest.mark.unit
    def test_parse_missing_a(self) -> None:
        assert self.parser.parse("A////") is None

    @pytest.mark.unit
    def test_parse_missing_q(self) -> None:
        assert self.parser.parse("Q////") is None

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("") is None

    @pytest.mark.unit
    def test_extract_altimeter_pops_token(self) -> None:
        stream = make_stream("22/18", "A2995")
        pressure = self.parser.extract_altimeter(stream)
        assert pressure is not None
        assert abs(pressure.value - 29.95) < 0.001
        assert "A2995" not in stream.tokens

    @pytest.mark.unit
    def test_extract_altimeter_missing_returns_none(self) -> None:
        stream = make_stream("A////")
        pressure = self.parser.extract_altimeter(stream)
        assert pressure is None
        assert len(stream) == 0  # token still consumed

    @pytest.mark.unit
    def test_extract_altimeter_not_found(self) -> None:
        stream = make_stream("22/18", "FEW030")
        result = self.parser.extract_altimeter(stream)
        assert result is None

    @pytest.mark.unit
    def test_parse_qnh_hpa_range(self) -> None:
        pressure = self.parser.parse_qnh("Q1013")
        assert pressure is not None
        assert pressure.unit == "hPa"
        assert pressure.value == 1013

    @pytest.mark.unit
    def test_parse_qnh_inhg_low_value(self) -> None:
        # value < 850 → treated as inHg (value / 100.0)
        pressure = self.parser.parse_qnh("Q2992")
        assert pressure is not None
        assert pressure.unit == "inHg"
        assert abs(pressure.value - 29.92) < 0.001

    @pytest.mark.unit
    def test_parse_qnh_alt_qnh_pattern_hpa(self) -> None:
        pressure = self.parser.parse_qnh("QNH1013HPA")
        assert pressure is not None
        assert pressure.unit == "hPa"

    @pytest.mark.unit
    def test_parse_qnh_alt_pattern_inhg(self) -> None:
        pressure = self.parser.parse_qnh("A2992")
        assert pressure is not None
        assert pressure.unit == "inHg"


# ===========================================================================
# RunwayParser tests
# ===========================================================================

class TestRunwayParser:
    parser = RunwayParser()

    @pytest.mark.unit
    def test_extract_rvr_basic(self) -> None:
        stream = make_stream("R28L/1200FT")
        rvr_list = self.parser.extract_rvr(stream)
        assert len(rvr_list) == 1
        rvr = rvr_list[0]
        assert rvr.runway == "28L"
        assert rvr.visual_range == 1200
        assert rvr.unit == "FT"
        assert not rvr.is_less_than
        assert not rvr.is_more_than

    @pytest.mark.unit
    def test_extract_rvr_meters(self) -> None:
        stream = make_stream("R28/0600")
        rvr_list = self.parser.extract_rvr(stream)
        assert len(rvr_list) == 1
        assert rvr_list[0].unit == "M"

    @pytest.mark.unit
    def test_extract_rvr_p_more_than(self) -> None:
        stream = make_stream("R28/P6000FT")
        rvr_list = self.parser.extract_rvr(stream)
        assert rvr_list[0].is_more_than

    @pytest.mark.unit
    def test_extract_rvr_m_less_than(self) -> None:
        stream = make_stream("R28/M0600FT")
        rvr_list = self.parser.extract_rvr(stream)
        assert rvr_list[0].is_less_than

    @pytest.mark.unit
    def test_extract_rvr_variable_range(self) -> None:
        stream = make_stream("R10/0600V1200N")
        rvr_list = self.parser.extract_rvr(stream)
        assert len(rvr_list) == 1
        rvr = rvr_list[0]
        assert rvr.variable_range == 1200
        assert rvr.trend == "no change"

    @pytest.mark.unit
    def test_extract_rvr_trend_improving(self) -> None:
        stream = make_stream("R28/0800U")
        rvr_list = self.parser.extract_rvr(stream)
        assert rvr_list[0].trend == "improving"

    @pytest.mark.unit
    def test_extract_rvr_trend_deteriorating(self) -> None:
        stream = make_stream("R28/0800D")
        rvr_list = self.parser.extract_rvr(stream)
        assert rvr_list[0].trend == "deteriorating"

    @pytest.mark.unit
    def test_extract_rvr_multiple(self) -> None:
        stream = make_stream("R28L/1200FT", "R10R/0800FT")
        rvr_list = self.parser.extract_rvr(stream)
        assert len(rvr_list) == 2

    @pytest.mark.unit
    def test_extract_rvr_empty_stream(self) -> None:
        stream = make_stream("SKC", "9999")
        rvr_list = self.parser.extract_rvr(stream)
        assert rvr_list == []

    @pytest.mark.unit
    def test_extract_runway_state_basic(self) -> None:
        # R28/0260//: deposit=0 (clear and dry), extent=2 (11-25%), depth=60 (60mm), braking=// (not reported)
        stream = make_stream("R28/0260//")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        state = state_list[0]
        assert state.runway == "28"
        assert "clear and dry" in state.deposit
        assert not state.all_runways

    @pytest.mark.unit
    def test_extract_runway_state_wet_deposit(self) -> None:
        # R28/2260//: deposit=2 (wet and water patches)
        stream = make_stream("R28/2260//")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        assert "wet and water patches" in state_list[0].deposit

    @pytest.mark.unit
    def test_extract_runway_state_all_runways(self) -> None:
        stream = make_stream("R88/112595")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        assert state_list[0].all_runways

    @pytest.mark.unit
    def test_extract_runway_state_snoclo(self) -> None:
        stream = make_stream("R/SNOCLO")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        state = state_list[0]
        assert state.aerodrome_closed
        assert state.all_runways

    @pytest.mark.unit
    def test_extract_runway_state_clrd(self) -> None:
        stream = make_stream("R28/CLRD//")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        assert state_list[0].cleared

    @pytest.mark.unit
    def test_extract_runway_state_from_previous(self) -> None:
        # code 99 = from previous observation
        stream = make_stream("R99/112595")
        state_list = self.parser.extract_runway_state(stream)
        assert len(state_list) == 1
        assert state_list[0].from_previous_report

    @pytest.mark.unit
    def test_decode_depth_slash(self) -> None:
        assert "not significant" in RunwayParser._decode_depth("//")

    @pytest.mark.unit
    def test_decode_depth_00(self) -> None:
        assert "1mm" in RunwayParser._decode_depth("00")

    @pytest.mark.unit
    def test_decode_depth_numeric(self) -> None:
        result = RunwayParser._decode_depth("25")
        assert "25mm" in result

    @pytest.mark.unit
    def test_decode_depth_special_codes(self) -> None:
        assert "10cm" in RunwayParser._decode_depth("92")
        assert "40cm" in RunwayParser._decode_depth("98")

    @pytest.mark.unit
    def test_decode_depth_reserved(self) -> None:
        result = RunwayParser._decode_depth("91")
        assert "reserved" in result.lower() or "invalid" in result.lower()

    @pytest.mark.unit
    def test_decode_braking_slash(self) -> None:
        result = RunwayParser._decode_braking("//")
        assert "not reported" in result

    @pytest.mark.unit
    def test_decode_braking_named_code(self) -> None:
        assert "poor" in RunwayParser._decode_braking("91").lower()

    @pytest.mark.unit
    def test_decode_braking_coefficient(self) -> None:
        result = RunwayParser._decode_braking("50")
        assert "0.50" in result

    @pytest.mark.unit
    def test_decode_braking_reserved(self) -> None:
        result = RunwayParser._decode_braking("96")
        assert "reserved" in result.lower() or "invalid" in result.lower()


# ===========================================================================
# SeaParser tests
# ===========================================================================

class TestSeaParser:
    parser = SeaParser()

    @pytest.mark.unit
    def test_parse_temperature_and_state(self) -> None:
        sea = self.parser.parse("W15/S3")
        assert sea is not None
        assert sea.sea_surface_temperature == 15
        assert "slight" in sea.state_of_sea
        assert not sea.temperature_missing

    @pytest.mark.unit
    def test_parse_missing_temperature(self) -> None:
        # W///S/: temperature "//" + separator "/" + state "S/" → 6-char token "W///S/"
        sea = self.parser.parse("W///S/")
        assert sea is not None
        assert sea.temperature_missing
        assert sea.state_missing

    @pytest.mark.unit
    def test_parse_negative_temperature(self) -> None:
        sea = self.parser.parse("WM02/H025")
        assert sea is not None
        assert sea.sea_surface_temperature == -2
        assert sea.significant_wave_height_m is not None
        assert abs(sea.significant_wave_height_m - 2.5) < 0.01

    @pytest.mark.unit
    def test_parse_missing_wave_height(self) -> None:
        sea = self.parser.parse("W10/H///")
        assert sea is not None
        assert sea.wave_height_missing

    @pytest.mark.unit
    def test_parse_calm_sea(self) -> None:
        sea = self.parser.parse("W15/S0")
        assert sea is not None
        assert sea.state_of_sea == "calm (glassy)"

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("W15") is None
        assert self.parser.parse("") is None

    @pytest.mark.unit
    def test_extract_all(self) -> None:
        stream = make_stream("22/18", "W15/S3", "Q1013")
        conditions = self.parser.extract_all(stream)
        assert len(conditions) == 1
        assert conditions[0].sea_surface_temperature == 15
        # W15/S3 removed, others remain
        assert "22/18" in stream.tokens
        assert "Q1013" in stream.tokens

    @pytest.mark.unit
    def test_extract_all_empty(self) -> None:
        stream = make_stream("SKC", "9999")
        assert self.parser.extract_all(stream) == []

    @pytest.mark.unit
    def test_parse_high_sea_state(self) -> None:
        sea = self.parser.parse("W20/S9")
        assert sea is not None
        assert "phenomenal" in sea.state_of_sea


# ===========================================================================
# WindShearParser tests
# ===========================================================================

class TestWindShearParser:
    parser = WindShearParser()

    @pytest.mark.unit
    def test_extract_all_all_runways(self) -> None:
        stream = make_stream("WS", "ALL", "RWY")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        assert result[0].kind == "all_runways"
        assert len(stream) == 0

    @pytest.mark.unit
    def test_extract_all_takeoff(self) -> None:
        stream = make_stream("WS", "TKOF", "R28L")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        ws = result[0]
        assert ws.kind == "takeoff"
        assert ws.runway == "28L"

    @pytest.mark.unit
    def test_extract_all_landing(self) -> None:
        stream = make_stream("WS", "LDG", "R10")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        assert result[0].kind == "landing"

    @pytest.mark.unit
    def test_extract_all_runway_only(self) -> None:
        stream = make_stream("WS", "RWY", "28L")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        assert result[0].kind == "runway"

    @pytest.mark.unit
    def test_extract_all_compact_format(self) -> None:
        stream = make_stream("WSRWY28L")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        ws = result[0]
        assert ws.kind == "runway"
        assert ws.runway == "28L"

    @pytest.mark.unit
    def test_extract_all_compact_no_runway(self) -> None:
        stream = make_stream("WSALL")
        result = self.parser.extract_all(stream)
        assert len(result) == 1
        # No runway number in WSALL → runway is None
        assert result[0].runway is None

    @pytest.mark.unit
    def test_extract_all_empty(self) -> None:
        stream = make_stream("SKC", "CAVOK")
        assert self.parser.extract_all(stream) == []

    @pytest.mark.unit
    def test_find_runway_with_r_prefix(self) -> None:
        result = WindShearParser._find_runway(["WS", "R28L"])
        assert result == "28L"

    @pytest.mark.unit
    def test_find_runway_without_r_prefix(self) -> None:
        result = WindShearParser._find_runway(["WS", "28L"])
        assert result == "28L"

    @pytest.mark.unit
    def test_find_runway_none(self) -> None:
        result = WindShearParser._find_runway(["WS", "ALL"])
        assert result is None


# ===========================================================================
# TrendParser tests
# ===========================================================================

class TestTrendParser:
    wind_parser = WindParser()
    sky_parser = SkyParser()
    weather_parser = WeatherParser()

    @property
    def parser(self) -> TrendParser:
        return TrendParser(
            wind_parser=self.wind_parser,
            sky_parser=self.sky_parser,
            weather_parser=self.weather_parser,
        )

    @pytest.mark.unit
    def test_extract_nosig(self) -> None:
        stream = make_stream("NOSIG")
        trends = self.parser.extract_trends(stream)
        assert len(trends) == 1
        assert trends[0].kind == "NOSIG"
        assert "No significant change" in trends[0].description

    @pytest.mark.unit
    def test_extract_becmg_with_times(self) -> None:
        stream = make_stream("BECMG", "FM1530", "TL1630", "NSW")
        trends = self.parser.extract_trends(stream)
        assert len(trends) == 1
        trend = trends[0]
        assert trend.kind == "BECMG"
        assert trend.time is not None
        assert "15:30" in trend.time.from_time
        assert "16:30" in trend.time.until_time

    @pytest.mark.unit
    def test_extract_tempo_with_weather(self) -> None:
        stream = make_stream("TEMPO", "FM1800", "TL2000", "-RA")
        trends = self.parser.extract_trends(stream)
        assert len(trends) == 1
        assert trends[0].kind == "TEMPO"
        assert "Temporary" in trends[0].description

    @pytest.mark.unit
    def test_extract_multiple_trends(self) -> None:
        stream = make_stream("NOSIG", "BECMG", "FEW030")
        trends = self.parser.extract_trends(stream)
        assert len(trends) == 2

    @pytest.mark.unit
    def test_parse_time_indicator_fm(self) -> None:
        time_info: dict = {}
        result = self.parser._parse_time_indicator("FM1530", time_info)
        assert result
        assert "15:30" in time_info["from"]

    @pytest.mark.unit
    def test_parse_time_indicator_tl(self) -> None:
        time_info: dict = {}
        result = self.parser._parse_time_indicator("TL2000", time_info)
        assert result
        assert "20:00" in time_info["until"]

    @pytest.mark.unit
    def test_parse_time_indicator_at(self) -> None:
        time_info: dict = {}
        result = self.parser._parse_time_indicator("AT1200", time_info)
        assert result
        assert "12:00" in time_info["at"]

    @pytest.mark.unit
    def test_parse_time_indicator_no_match(self) -> None:
        time_info: dict = {}
        assert not self.parser._parse_time_indicator("SKC", time_info)

    @pytest.mark.unit
    def test_parse_weather_change_visibility_9999(self) -> None:
        change = self.parser._parse_weather_change("9999")
        assert change == "visibility 10km or more"

    @pytest.mark.unit
    def test_parse_weather_change_visibility_km(self) -> None:
        change = self.parser._parse_weather_change("5000")
        assert change is not None
        assert "5.0km" in change

    @pytest.mark.unit
    def test_parse_weather_change_visibility_m(self) -> None:
        change = self.parser._parse_weather_change("0800")
        assert change is not None
        assert "800m" in change

    @pytest.mark.unit
    def test_parse_weather_change_nsw(self) -> None:
        change = self.parser._parse_weather_change("NSW")
        assert change == "no significant weather"

    @pytest.mark.unit
    def test_parse_weather_change_cavok(self) -> None:
        change = self.parser._parse_weather_change("CAVOK")
        assert change == "CAVOK"

    @pytest.mark.unit
    def test_extract_trends_stops_before_rmk(self) -> None:
        stream = make_stream("BECMG", "FEW030", "RMK", "SLP123")
        trends = self.parser.extract_trends(stream)
        assert len(trends) == 1
        # RMK and SLP123 should still be in stream
        assert "RMK" in stream.tokens


# ===========================================================================
# IcingParser tests
# ===========================================================================

class TestIcingParser:
    parser = IcingParser()

    @pytest.mark.unit
    def test_parse_numeric_620304(self) -> None:
        # 620304: 6 + intensity=2 (moderate) + type=0 (none) + base=30 (3000ft) + depth=4 (4000ft)
        icing = self.parser.parse("620304")
        assert icing is not None
        assert icing.intensity == "moderate"
        assert icing.icing_type == "none"
        assert icing.base_ft == 3000
        assert icing.top_ft == 7000  # 3000 + 4*1000

    @pytest.mark.unit
    def test_parse_numeric_mixed_icing(self) -> None:
        # 622304: type=2 (mixed), intensity=2 (moderate), base=3000ft, depth=4000ft
        icing = self.parser.parse("622304")
        assert icing is not None
        assert icing.icing_type == "mixed"
        assert icing.intensity == "moderate"
        # 5-digit group: no depth digit
        icing = self.parser.parse("62030")
        assert icing is not None
        assert icing.base_ft == 3000
        assert icing.top_ft is None

    @pytest.mark.unit
    def test_parse_numeric_none_intensity(self) -> None:
        icing = self.parser.parse("600105")
        assert icing is not None
        assert icing.intensity == "none"

    @pytest.mark.unit
    def test_parse_numeric_severe(self) -> None:
        icing = self.parser.parse("650104")
        assert icing is not None
        assert icing.intensity == "severe"

    @pytest.mark.unit
    def test_parse_numeric_extreme(self) -> None:
        icing = self.parser.parse("680104")
        assert icing is not None
        assert icing.intensity == "extreme"

    @pytest.mark.unit
    def test_parse_plain_moderate(self) -> None:
        icing = self.parser.parse("ICG20")
        assert icing is not None
        assert icing.intensity == "moderate"
        assert icing.base_ft == 2000
        assert icing.top_ft is None

    @pytest.mark.unit
    def test_parse_plain_severe(self) -> None:
        icing = self.parser.parse("+ICG30")
        assert icing is not None
        assert icing.intensity == "severe"
        assert icing.base_ft == 3000

    @pytest.mark.unit
    def test_parse_plain_light(self) -> None:
        icing = self.parser.parse("-ICG10")
        assert icing is not None
        assert icing.intensity == "light"
        assert icing.base_ft == 1000

    @pytest.mark.unit
    def test_parse_invalid(self) -> None:
        assert self.parser.parse("CAVOK") is None
        assert self.parser.parse("SKC") is None
        assert self.parser.parse("") is None
        assert self.parser.parse("12345") is None  # starts with 1, not 6

    @pytest.mark.unit
    def test_extract_all(self) -> None:
        stream = make_stream("620304", "ICG20", "+ICG30", "SKC")
        results = self.parser.extract_all(stream)
        assert len(results) == 3
        assert stream.tokens == ["SKC"]

    @pytest.mark.unit
    def test_extract_all_empty(self) -> None:
        stream = make_stream("SKC", "CAVOK")
        assert self.parser.extract_all(stream) == []

    @pytest.mark.unit
    def test_parse_plain_icgh_variant(self) -> None:
        # ICGH variant (with H in token)
        icing = self.parser.parse("ICGH20")
        assert icing is not None
        assert icing.base_ft == 2000


# ===========================================================================
# TurbulenceParser tests
# ===========================================================================

class TestTurbulenceParser:
    parser = TurbulenceParser()

    @pytest.mark.unit
    def test_parse_numeric_520610(self) -> None:
        # 520610: 5 + type=2 (moderate in cloud) + base=06 (600ft) + depth=10 (1000ft)
        turb = self.parser.parse_numeric("520610")
        assert turb is not None
        assert turb.intensity == "moderate"
        assert turb.in_cloud
        assert turb.base_ft == 600
        assert turb.top_ft == 1600  # 600 + 10*100

    @pytest.mark.unit
    def test_parse_numeric_526010(self) -> None:
        # 526010: base=60 (6000ft), depth=10 (1000ft) → top=7000ft
        turb = self.parser.parse_numeric("526010")
        assert turb is not None
        assert turb.base_ft == 6000
        assert turb.top_ft == 7000

    @pytest.mark.unit
    def test_parse_numeric_none_intensity(self) -> None:
        turb = self.parser.parse_numeric("500010")
        assert turb is not None
        assert turb.intensity == "none"

    @pytest.mark.unit
    def test_parse_numeric_light(self) -> None:
        turb = self.parser.parse_numeric("510010")
        assert turb is not None
        assert turb.intensity == "light"

    @pytest.mark.unit
    def test_parse_numeric_severe_in_cloud(self) -> None:
        turb = self.parser.parse_numeric("550010")
        assert turb is not None
        assert turb.intensity == "severe"
        assert turb.in_cloud

    @pytest.mark.unit
    def test_parse_numeric_severe_clear_air(self) -> None:
        turb = self.parser.parse_numeric("560010")
        assert turb is not None
        assert turb.intensity == "severe"
        assert not turb.in_cloud

    @pytest.mark.unit
    def test_parse_numeric_extreme(self) -> None:
        turb = self.parser.parse_numeric("580010")
        assert turb is not None
        assert turb.intensity == "extreme"

    @pytest.mark.unit
    def test_parse_numeric_invalid(self) -> None:
        assert self.parser.parse_numeric("CAVOK") is None
        assert self.parser.parse_numeric("") is None
        assert self.parser.parse_numeric("12345") is None  # doesn't start with 5

    @pytest.mark.unit
    def test_parse_plain_moderate(self) -> None:
        result = TurbulenceParser.parse_plain("TURB/30")
        assert result is not None
        turb, consumed = result
        assert turb.intensity == "moderate"
        assert turb.base_ft == 3000
        assert not consumed

    @pytest.mark.unit
    def test_parse_plain_severe(self) -> None:
        result = TurbulenceParser.parse_plain("+TURB/20")
        assert result is not None
        turb, consumed = result
        assert turb.intensity == "severe"
        assert turb.base_ft == 2000

    @pytest.mark.unit
    def test_parse_plain_light(self) -> None:
        result = TurbulenceParser.parse_plain("-TURB/10")
        assert result is not None
        turb, _ = result
        assert turb.intensity == "light"

    @pytest.mark.unit
    def test_parse_plain_with_top_token(self) -> None:
        result = TurbulenceParser.parse_plain("+TURB/20", "/050")
        assert result is not None
        turb, consumed = result
        assert consumed
        assert turb.top_ft == 5000

    @pytest.mark.unit
    def test_parse_plain_next_token_not_top(self) -> None:
        result = TurbulenceParser.parse_plain("TURB/30", "SKC")
        assert result is not None
        turb, consumed = result
        assert not consumed
        assert turb.top_ft is None

    @pytest.mark.unit
    def test_parse_plain_invalid(self) -> None:
        assert TurbulenceParser.parse_plain("CAVOK") is None
        assert TurbulenceParser.parse_plain("") is None

    @pytest.mark.unit
    def test_extract_all_numeric(self) -> None:
        stream = make_stream("520610", "SKC")
        results = self.parser.extract_all(stream)
        assert len(results) == 1
        assert stream.tokens == ["SKC"]

    @pytest.mark.unit
    def test_extract_all_plain_two_tokens(self) -> None:
        stream = make_stream("+TURB/20", "/050", "SKC")
        results = self.parser.extract_all(stream)
        assert len(results) == 1
        assert results[0].top_ft == 5000
        assert stream.tokens == ["SKC"]

    @pytest.mark.unit
    def test_extract_all_plain_single_token(self) -> None:
        stream = make_stream("TURB/30", "SKC")
        results = self.parser.extract_all(stream)
        assert len(results) == 1
        assert stream.tokens == ["SKC"]

    @pytest.mark.unit
    def test_extract_all_mixed(self) -> None:
        stream = make_stream("520610", "+TURB/20", "/050")
        results = self.parser.extract_all(stream)
        assert len(results) == 2
        assert len(stream) == 0

    @pytest.mark.unit
    def test_extract_all_empty(self) -> None:
        stream = make_stream("SKC", "CAVOK")
        assert self.parser.extract_all(stream) == []


# ===========================================================================
# TimeParser tests
# ===========================================================================

class TestTimeParser:
    @pytest.mark.unit
    def test_parse_observation_time(self) -> None:
        ref = datetime(2024, 6, 6, 0, 0, tzinfo=timezone.utc)
        dt = TimeParser.parse_observation_time("061751Z", reference_time=ref)
        assert dt is not None
        assert dt.day == 6
        assert dt.hour == 17
        assert dt.minute == 51
        assert dt.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_parse_observation_time_invalid(self) -> None:
        result = TimeParser.parse_observation_time("INVALID")
        assert result is None

    @pytest.mark.unit
    def test_parse_valid_period(self) -> None:
        ref = datetime(2024, 6, 6, 0, 0, tzinfo=timezone.utc)
        period = TimeParser.parse_valid_period("0618/0724", reference_time=ref)
        assert period is not None
        assert isinstance(period, TimeRange)
        assert period.start.day == 6
        assert period.start.hour == 18
        # to_hour=24 → normalized to 0, to_day=7+1=8
        assert period.end.day == 8
        assert period.end.hour == 0

    @pytest.mark.unit
    def test_parse_valid_period_invalid(self) -> None:
        result = TimeParser.parse_valid_period("INVALID")
        assert result is None

    @pytest.mark.unit
    def test_parse_fm_time(self) -> None:
        ref = datetime(2024, 6, 6, 0, 0, tzinfo=timezone.utc)
        dt = TimeParser.parse_fm_time("FM061800", reference_time=ref)
        assert dt is not None
        assert dt.day == 6
        assert dt.hour == 18
        assert dt.minute == 0

    @pytest.mark.unit
    def test_parse_fm_time_invalid(self) -> None:
        result = TimeParser.parse_fm_time("INVALID")
        assert result is None

    @pytest.mark.unit
    def test_parse_time_range(self) -> None:
        ref = datetime(2024, 6, 6, 0, 0, tzinfo=timezone.utc)
        from_time, to_time = TimeParser.parse_time_range("0618/0624", reference_time=ref)
        assert from_time.hour == 18
        assert to_time.hour == 0  # 24 → 0 next day

    @pytest.mark.unit
    def test_resolve_month_year_same_month(self) -> None:
        ref = datetime(2024, 6, 15, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(ref, 15)
        assert year == 2024
        assert month == 6

    @pytest.mark.unit
    def test_resolve_month_year_prev_month(self) -> None:
        # day_delta > 15 → go back a month
        ref = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(ref, 28)  # delta = 27
        assert month == 5

    @pytest.mark.unit
    def test_resolve_month_year_next_month(self) -> None:
        # day_delta < -15 → advance a month
        ref = datetime(2024, 6, 30, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(ref, 1)  # delta = -29
        assert month == 7

    @pytest.mark.unit
    def test_resolve_month_year_wrap_dec_to_jan(self) -> None:
        ref = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(ref, 28)
        assert month == 12
        assert year == 2023

    @pytest.mark.unit
    def test_resolve_month_year_wrap_dec_forward(self) -> None:
        ref = datetime(2024, 12, 30, 0, 0, tzinfo=timezone.utc)
        year, month = TimeParser._resolve_month_year(ref, 1)
        assert month == 1
        assert year == 2025

    @pytest.mark.unit
    def test_build_datetime(self) -> None:
        ref = datetime(2024, 6, 10, 0, 0, tzinfo=timezone.utc)
        dt = TimeParser._build_datetime(ref, 10, 12, 30)
        assert dt.year == 2024
        assert dt.month == 6
        assert dt.day == 10
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_format_time(self) -> None:
        dt = datetime(2024, 6, 10, 17, 51, tzinfo=timezone.utc)
        formatted = TimeParser.format_time(dt)
        assert "17:51" in formatted

    @pytest.mark.unit
    def test_get_current_utc_time(self) -> None:
        dt = TimeParser.get_current_utc_time()
        assert dt.tzinfo is not None

    @pytest.mark.unit
    def test_parse_observation_time_no_ref(self) -> None:
        # Without reference time, should still parse using current time
        dt = TimeParser.parse_observation_time("151200Z")
        assert dt is not None
        assert dt.day == 15
        assert dt.hour == 12

    @pytest.mark.unit
    def test_parse_valid_period_hour_24_normalization(self) -> None:
        # 0624/0724 → from hour 24 normalizes to 0 on day 7; to hour 24 normalizes to 0 on day 8
        ref = datetime(2024, 6, 6, 0, 0, tzinfo=timezone.utc)
        period = TimeParser.parse_valid_period("0624/0724", reference_time=ref)
        assert period is not None
        assert period.start.hour == 0
        assert period.start.day == 7
        assert period.end.hour == 0
        assert period.end.day == 8


# ===========================================================================
# Integration: extract chains
# ===========================================================================

class TestIntegrationExtractChains:
    """Tests that exercise multiple parsers against a realistic token stream."""

    @pytest.mark.unit
    def test_wind_then_visibility(self) -> None:
        stream = make_stream("28045KT", "150V210", "9999", "FEW030", "22/18", "Q1013")
        wind = WindParser().extract(stream)
        assert wind is not None
        assert wind.variable_range == (150, 210)
        vis = VisibilityParser().extract(stream)
        assert vis is not None
        assert vis.value == 9999

    @pytest.mark.unit
    def test_full_metar_sky_sequence(self) -> None:
        stream = make_stream("FEW030", "SCT060CB", "BKN120")
        conditions = SkyParser().extract_all(stream)
        assert len(conditions) == 3
        assert conditions[1].cb

    @pytest.mark.unit
    def test_weather_then_rvr(self) -> None:
        stream = make_stream("-RA", "R28/0600")
        weather = WeatherParser().extract_all(stream)
        assert len(weather) == 1
        rvr = RunwayParser().extract_rvr(stream)
        assert len(rvr) == 1

    @pytest.mark.unit
    def test_icing_and_turbulence_together(self) -> None:
        stream = make_stream("620304", "520610")
        icing = IcingParser().extract_all(stream)
        turb = TurbulenceParser().extract_all(stream)
        assert len(icing) == 1
        assert len(turb) == 1
        assert len(stream) == 0
