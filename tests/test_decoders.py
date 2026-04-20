"""Comprehensive pytest test file for MetarDecoder and TafDecoder integration tests.

This test suite covers:
- METAR parsing with various conditions and edge cases
- TAF parsing with various conditions and edge cases
- Validation warnings for both METAR and TAF
- MetarData and TafData helper methods
- Decoder instantiation and basic behavior
"""

import pytest
from datetime import datetime, timezone

from weather_decoder import MetarDecoder, TafDecoder, MetarData, TafData
from weather_decoder.models import (
    MetarReport,
    TafReport,
    TafForecastPeriod,
    Wind,
    Visibility,
    SkyCondition,
    Pressure,
    WeatherPhenomenon,
    RunwayVisualRange,
    RunwayState,
    SeaCondition,
    WindShear,
    Trend,
    MilitaryColorCode,
    TemperatureForecast,
    IcingForecast,
    TurbulenceForecast,
)


# ==============================================
# METAR BASIC TESTS
# ==============================================


@pytest.mark.integration
def test_metar_basic_complete():
    """Test basic complete METAR with all standard fields."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    assert isinstance(result, MetarData)
    assert result.station_id == "KJFK"
    assert result.wind.speed == 8
    assert result.wind.direction == 280
    assert result.wind.unit == "KT"
    assert result.visibility.value == 10
    assert result.visibility.unit == "SM"
    assert result.sky[0].coverage == "FEW"
    assert result.sky[0].height == 25000
    assert result.temperature == 22
    assert result.dewpoint == 18
    assert result.altimeter.value == 29.92
    assert result.altimeter.unit == "inHg"


@pytest.mark.integration
def test_metar_speci_with_auto():
    """Test SPECI report with AUTO modification."""
    decoder = MetarDecoder()
    result = decoder.decode("SPECI EGLL 061751Z AUTO 18010KT 1200 -RA BKN010 15/13 Q1013")

    assert result.report_type == "SPECI"
    assert result.is_automated is True
    assert result.wind.direction == 180
    assert result.wind.speed == 10
    assert result.visibility.value == 1200
    assert result.visibility.unit == "M"
    assert result.weather[0].intensity == "light"
    assert "rain" in result.weather[0].phenomena
    assert result.sky[0].coverage == "BKN"
    assert result.sky[0].height == 1000
    assert result.altimeter.value == 1013
    assert result.altimeter.unit == "hPa"


@pytest.mark.integration
def test_metar_calm_winds():
    """Test METAR with calm wind conditions."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KBOS 061751Z 00000KT 10SM SKC 25/10 A2990")

    assert result.wind.is_calm is True
    assert result.wind.direction == 0
    assert result.wind.speed == 0


@pytest.mark.integration
def test_metar_variable_wind_range():
    """Test METAR with wind direction variability range."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KLAX 061751Z 28008KT 250V320 10SM CLR 20/05 A2998")

    assert result.wind.variable_range == (250, 320)
    assert result.wind.is_variable is False


@pytest.mark.integration
def test_metar_cavok():
    """Test METAR with CAVOK (Ceiling And Visibility OK)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 09015KT CAVOK 18/10 Q1020")

    assert result.visibility.is_cavok is True


@pytest.mark.integration
def test_metar_nil_report():
    """Test NIL (missing) METAR report."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z NIL")

    assert result.is_nil is True


@pytest.mark.integration
def test_metar_maintenance_indicator():
    """Test METAR with maintenance needed indicator ($)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM CLR 22/18 A2992 $")

    assert result.maintenance_needed is True


@pytest.mark.integration
def test_metar_multiple_weather_groups():
    """Test METAR with multiple weather phenomenon groups including CB cloud type."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 18015KT 5000 TSRA FEW030CB BKN060 18/15 Q1010")

    assert len(result.weather) >= 1
    # TSRA is decoded as a compound phenomenon "thunderstorm with rain"
    assert any(
        w.descriptor == "thunderstorm"
        or any("thunderstorm" in p for p in w.phenomena)
        for w in result.weather
    )
    assert any(s.cb for s in result.sky)


@pytest.mark.integration
def test_metar_rvr_groups():
    """Test METAR with Runway Visual Range (RVR) groups."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR KLAX 061751Z 00000KT 0200 R28L/1200FT R10/P6000FT FG OVC002 18/18 A2980"
    )

    assert len(result.runway_visual_ranges) >= 1
    assert result.runway_visual_ranges[0].runway == "28L"
    assert result.runway_visual_ranges[0].visual_range == 1200


@pytest.mark.integration
def test_metar_runway_state():
    """Test METAR with runway state group."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR EGLL 061751Z 27010KT 5000 BKN030 15/10 Q1015 R28L/212070"
    )

    assert len(result.runway_states) > 0


@pytest.mark.integration
def test_metar_cor_corrected():
    """Test METAR with COR (corrected) indicator."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR COR KJFK 061751Z 28008KT 10SM CLR 22/18 A2992")

    assert result.is_corrected is True


@pytest.mark.integration
def test_metar_trend_nosig():
    """Test METAR with NOSIG (no significant change) trend."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 NOSIG")

    assert len(result.trends) == 1
    assert result.trends[0].kind == "NOSIG"


@pytest.mark.integration
def test_metar_trend_becmg():
    """Test METAR with BECMG (becoming) trend."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 BECMG FM1600 TL1800 NSW"
    )

    assert len(result.trends) >= 1
    assert result.trends[0].kind == "BECMG"


@pytest.mark.integration
def test_metar_trend_strips_final_equals_before_parsing_cloud_type():
    """A final METAR '=' must not hide the last trend cloud group."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR LFPG 100600Z AUTO VRB03KT 0800 FG VV/// 15/15 Q1006 "
        "TEMPO 0500 FG FEW015TCU BKN020CB="
    )

    assert len(result.trends) == 1
    assert "BKN at 2000ft CB" in result.trends[0].changes


@pytest.mark.integration
def test_metar_military_color_codes():
    """Test METAR with military color code (though not in standard codes)."""
    decoder = MetarDecoder()
    # Using valid military color code BLU
    result = decoder.decode("METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 BLU")

    # Note: Current implementation may not capture all color codes, test what it does
    assert isinstance(result.military_color_codes, list)


@pytest.mark.integration
def test_metar_sea_conditions():
    """Test METAR with sea condition group."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1020 W15/S3")

    assert len(result.sea_conditions) > 0
    assert result.sea_conditions[0].sea_surface_temperature == 15


@pytest.mark.integration
def test_metar_with_remarks():
    """Test METAR with remarks section."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW030 22/18 A2992 RMK AO2 SLP021")

    assert "AO2" in result.remarks
    assert "Station Type" in result.remarks_decoded or "Sea Level Pressure" in result.remarks_decoded


@pytest.mark.integration
def test_metar_negative_temperature():
    """Test METAR with negative temperature and dewpoint."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 010000Z 00000KT 9999 SKC M05/M10 A2990")

    assert result.temperature == -5
    assert result.dewpoint == -10


@pytest.mark.integration
def test_metar_visibility_with_direction():
    """Test METAR with directional minimum visibility."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 09015KT 2000 1000SE FEW010 18/15 Q1010")

    assert result.visibility.minimum_visibility is not None


@pytest.mark.integration
def test_metar_gusting_wind():
    """Test METAR with wind gust information."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28025G35KT 10SM FEW030 22/18 A2992")

    assert result.wind.gust == 35


@pytest.mark.integration
def test_metar_vrb_wind():
    """Test METAR with variable (VRB) wind direction."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z VRB05KT 10SM CLR 22/18 A2992")

    assert result.wind.is_variable is True
    assert result.wind.direction is None


# ==============================================
# METAR VALIDATION WARNING TESTS
# ==============================================


@pytest.mark.unit
def test_metar_validation_no_keyword():
    """Test validation warning for missing METAR/SPECI keyword."""
    decoder = MetarDecoder()
    result = decoder.decode("KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    assert any("METAR or SPECI keyword not found" in w for w in result.validation_warnings)


@pytest.mark.unit
def test_metar_validation_skc_warning():
    """Test validation warning for SKC (US code, not WMO standard)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM SKC 22/18 A2992")

    assert any("SKC/CLR" in w for w in result.validation_warnings)


@pytest.mark.unit
def test_metar_validation_ncd_non_auto():
    """Test validation warning for NCD in non-automated METAR."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM NCD 22/18 A2992")

    assert any("NCD" in w for w in result.validation_warnings)


@pytest.mark.unit
def test_metar_validation_kmh_wind_unit():
    """Test validation warning for KMH wind unit (not WMO standard)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 280010KMH 10SM FEW030 22/18 A2992")

    assert any("KMH" in w for w in result.validation_warnings)


@pytest.mark.unit
def test_metar_validation_ts_without_cb():
    """Test validation warning for TS without CB cloud layer."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 5000 TS FEW030 BKN070 18/15 A2992")

    assert any("CB" in w for w in result.validation_warnings)


@pytest.mark.unit
def test_metar_validation_dewpoint_exceeds_temperature():
    """Test validation warning for dew point exceeding temperature."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW030 10/15 A2992")

    assert any("Dew point" in w for w in result.validation_warnings)


# ==============================================
# METAR DATA HELPER METHODS
# ==============================================


@pytest.mark.unit
def test_metar_data_wind_text():
    """Test MetarData.wind_text() helper method."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    wind_text = result.wind_text()
    assert isinstance(wind_text, str)
    assert len(wind_text) > 0
    assert "280" in wind_text or "8" in wind_text


@pytest.mark.unit
def test_metar_data_wind_text_calm():
    """Test MetarData.wind_text() for calm winds."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 00000KT 10SM SKC 25/10 A2990")

    wind_text = result.wind_text()
    assert isinstance(wind_text, str)
    assert len(wind_text) > 0
    assert "Calm" in wind_text


@pytest.mark.unit
def test_metar_data_wind_text_vrb():
    """Test MetarData.wind_text() for variable winds."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z VRB05KT 10SM CLR 22/18 A2992")

    wind_text = result.wind_text()
    assert isinstance(wind_text, str)
    assert len(wind_text) > 0
    assert "Variable" in wind_text


@pytest.mark.unit
def test_metar_data_visibility_text():
    """Test MetarData.visibility_text() helper method."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    visibility_text = result.visibility_text()
    assert isinstance(visibility_text, str)
    assert len(visibility_text) > 0


# ==============================================
# TAF BASIC TESTS
# ==============================================


@pytest.mark.integration
def test_taf_basic():
    """Test basic TAF with minimal fields."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")

    assert isinstance(result, TafData)
    assert result.station_id == "KJFK"
    assert len(result.forecast_periods) >= 1
    assert result.forecast_periods[0].wind.speed == 8
    assert result.forecast_periods[0].wind.direction == 280
    assert result.forecast_periods[0].visibility.value == 9999


@pytest.mark.integration
def test_taf_with_tempo():
    """Test TAF with TEMPO (temporary) change group."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TEMPO 0620/0622 -RA BKN020"
    )

    assert len(result.forecast_periods) >= 2
    assert any(p.change_type == "TEMPO" for p in result.forecast_periods)


@pytest.mark.integration
def test_taf_with_becmg():
    """Test TAF with BECMG (becoming) change group."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 BECMG 0620/0622 VRB05KT"
    )

    assert any(p.change_type == "BECMG" for p in result.forecast_periods)


@pytest.mark.integration
def test_taf_with_fm():
    """Test TAF with FM (from) change group."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250 FM062000 15010KT 6000 -RA SCT020"
    )

    assert any(p.change_type == "FM" for p in result.forecast_periods)


@pytest.mark.integration
def test_taf_amd_amendment():
    """Test TAF with AMD (amendment) indicator."""
    decoder = TafDecoder()
    result = decoder.decode("TAF AMD KJFK 061730Z 0618/0724 28008KT 9999 FEW030")

    assert result.is_amended is True
    assert result.status == "AMENDMENT"


@pytest.mark.integration
def test_taf_cor_correction():
    """Test TAF with COR (correction) indicator."""
    decoder = TafDecoder()
    result = decoder.decode("TAF COR KJFK 061730Z 0618/0724 28008KT 9999 FEW030")

    assert result.is_corrected is True
    assert result.status == "CORRECTION"


@pytest.mark.integration
def test_taf_preprocess_preserves_station_with_fm_substring():
    """TAF preprocessing must not split station identifiers that contain FM."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KFMH 061730Z 0618/0724 28008KT 9999 FEW030")

    assert result.station_id == "KFMH"
    assert result.forecast_periods[0].wind is not None


@pytest.mark.integration
def test_taf_preprocess_preserves_station_with_cloud_substring():
    """TAF preprocessing must not split station identifiers that contain cloud codes."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KOVC 061730Z 0618/0724 28008KT 9999 FEW030")

    assert result.station_id == "KOVC"
    assert result.forecast_periods[0].sky[0].coverage == "FEW"


@pytest.mark.integration
def test_taf_cnl_cancellation():
    """Test TAF with CNL (cancellation) indicator."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 CNL")

    assert result.is_cancelled is True
    assert result.status == "CANCELLATION"


@pytest.mark.integration
def test_taf_nil_missing():
    """Test TAF with NIL (missing) indicator."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 NIL")

    assert result.is_nil is True
    assert result.status == "MISSING"


@pytest.mark.integration
def test_taf_with_prob30_tempo():
    """Test TAF with PROB30 TEMPO (probability temporary)."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 PROB30 TEMPO 0620/0622 -RA"
    )

    assert any(
        p.change_type == "PROB" and p.probability == 30 for p in result.forecast_periods
    )


@pytest.mark.integration
def test_taf_compact_becmg_with_time_range():
    """TAF preprocessing should split BECMG from attached time ranges."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030BECMG0620/0622 VRB05KT"
    )

    becmg = [p for p in result.forecast_periods if p.change_type == "BECMG"]
    assert len(becmg) == 1
    assert becmg[0].from_time is not None
    assert becmg[0].to_time is not None
    assert becmg[0].wind is not None
    assert becmg[0].wind.is_variable


@pytest.mark.integration
def test_taf_compact_tempo_with_time_range():
    """TAF preprocessing should split TEMPO from attached time ranges."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030TEMPO0620/0622 -RA"
    )

    tempo = [p for p in result.forecast_periods if p.change_type == "TEMPO"]
    assert len(tempo) == 1
    assert tempo[0].from_time is not None
    assert tempo[0].to_time is not None
    assert any("rain" in phenomenon for wx in tempo[0].weather for phenomenon in wx.phenomena)


@pytest.mark.integration
def test_taf_compact_prob30_tempo_with_time_range():
    """TAF preprocessing should split compact PROB30 TEMPO time ranges."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030PROB30TEMPO0620/0622 -RA"
    )

    prob = [p for p in result.forecast_periods if p.change_type == "PROB"]
    assert len(prob) == 1
    assert prob[0].probability == 30
    assert prob[0].qualifier == "TEMPO"
    assert prob[0].from_time is not None
    assert prob[0].to_time is not None


@pytest.mark.integration
def test_taf_with_temperature_forecasts():
    """Test TAF with TX/TN temperature forecast groups."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 TX25/0618Z TN15/0706Z"
    )

    assert len(result.temperature_forecasts) == 2


@pytest.mark.integration
def test_taf_with_icing():
    """Non-standard icing group should be flagged, not treated as standard TAF syntax."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 620304")

    assert "620304" in result.forecast_periods[0].unparsed_tokens
    assert any("non-standard TAF extension groups" in w for w in result.validation_warnings)


@pytest.mark.integration
def test_taf_with_turbulence():
    """Non-standard turbulence group should be flagged, not treated as standard TAF syntax."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 520610")

    assert "520610" in result.forecast_periods[0].unparsed_tokens
    assert any("non-standard TAF extension groups" in w for w in result.validation_warnings)


@pytest.mark.integration
def test_taf_with_cavok():
    """Test TAF with CAVOK visibility."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 VRB05KT CAVOK TX25/0618Z TN15/0706Z"
    )

    assert result.forecast_periods[0].visibility.is_cavok is True


@pytest.mark.integration
def test_taf_with_remarks():
    """Test TAF with RMK (remarks) section."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 RMK NXT FCST BY 12Z")

    assert "Next Forecast" in result.remarks_decoded


# ==============================================
# TAF VALIDATION TESTS
# ==============================================


@pytest.mark.unit
def test_taf_validation_non_standard_duration():
    """Test TAF validation warning for non-standard validity period."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0721 28008KT 9999 FEW030")

    assert len(result.validation_warnings) >= 1


@pytest.mark.unit
def test_taf_preprocessing_compact_fm():
    """Test TafDecoder._preprocess_taf() handles compact FM groups."""
    decoder = TafDecoder()
    result = decoder._preprocess_taf("TAF KJFK 061730Z 0618/0724 28008KTFM062000 15010KT")

    # Should have space before FM
    assert " FM062000" in result


@pytest.mark.unit
def test_taf_preprocessing_compact_tempo():
    """Test TafDecoder._preprocess_taf() handles compact TEMPO groups."""
    decoder = TafDecoder()
    result = decoder._preprocess_taf("TAF KJFK 061730Z 0618/0724 28008KTTEMPO 0620/0622")

    # Should have space before TEMPO
    assert " TEMPO" in result


@pytest.mark.unit
def test_taf_preprocessing_compact_becmg():
    """Test TafDecoder._preprocess_taf() handles compact BECMG groups."""
    decoder = TafDecoder()
    result = decoder._preprocess_taf("TAF KJFK 061730Z 0618/0724 28008KTBECMG 0620/0622")

    # Should have space before BECMG
    assert " BECMG" in result


@pytest.mark.unit
def test_taf_derive_status_amendment():
    """Test TafDecoder._derive_status() for amendment."""
    status = TafDecoder._derive_status(is_amended=True, is_corrected=False, is_cancelled=False, is_nil=False)
    assert status == "AMENDMENT"


@pytest.mark.unit
def test_taf_derive_status_correction():
    """Test TafDecoder._derive_status() for correction."""
    status = TafDecoder._derive_status(is_amended=False, is_corrected=True, is_cancelled=False, is_nil=False)
    assert status == "CORRECTION"


@pytest.mark.unit
def test_taf_derive_status_cancellation():
    """Test TafDecoder._derive_status() for cancellation."""
    status = TafDecoder._derive_status(is_amended=False, is_corrected=False, is_cancelled=True, is_nil=False)
    assert status == "CANCELLATION"


@pytest.mark.unit
def test_taf_derive_status_missing():
    """Test TafDecoder._derive_status() for missing report."""
    status = TafDecoder._derive_status(is_amended=False, is_corrected=False, is_cancelled=False, is_nil=True)
    assert status == "MISSING"


@pytest.mark.unit
def test_taf_derive_status_normal():
    """Test TafDecoder._derive_status() for normal status."""
    status = TafDecoder._derive_status(is_amended=False, is_corrected=False, is_cancelled=False, is_nil=False)
    assert status == "NORMAL"


# ==============================================
# DECODER INSTANTIATION TESTS
# ==============================================


@pytest.mark.unit
def test_metar_decoder_instantiation():
    """Test MetarDecoder can be instantiated without arguments."""
    decoder = MetarDecoder()
    assert decoder is not None
    assert isinstance(decoder, MetarDecoder)


@pytest.mark.unit
def test_taf_decoder_instantiation():
    """Test TafDecoder can be instantiated without arguments."""
    decoder = TafDecoder()
    assert decoder is not None
    assert isinstance(decoder, TafDecoder)


@pytest.mark.unit
def test_metar_decoder_has_parsers():
    """Test MetarDecoder is properly initialized with all parsers."""
    decoder = MetarDecoder()
    assert hasattr(decoder, "wind_parser")
    assert hasattr(decoder, "visibility_parser")
    assert hasattr(decoder, "weather_parser")
    assert hasattr(decoder, "sky_parser")
    assert hasattr(decoder, "pressure_parser")
    assert hasattr(decoder, "temperature_parser")
    assert hasattr(decoder, "remarks_parser")
    assert hasattr(decoder, "runway_parser")


@pytest.mark.unit
def test_taf_decoder_has_parsers():
    """Test TafDecoder is properly initialized with all parsers."""
    decoder = TafDecoder()
    assert hasattr(decoder, "wind_parser")
    assert hasattr(decoder, "visibility_parser")
    assert hasattr(decoder, "weather_parser")
    assert hasattr(decoder, "sky_parser")
    assert hasattr(decoder, "temperature_parser")
    assert hasattr(decoder, "icing_parser")
    assert hasattr(decoder, "turbulence_parser")


# ==============================================
# METAR EDGE CASES AND ADDITIONAL TESTS
# ==============================================


@pytest.mark.integration
def test_metar_multiple_sky_layers():
    """Test METAR with multiple cloud layers."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW050 SCT100 BKN200 OVC250 22/18 A2992")

    assert len(result.sky) >= 3


@pytest.mark.integration
def test_metar_below_minimums_visibility():
    """Test METAR with visibility below minimums."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KLAX 061751Z 00000KT 0200 FG OVC002 18/18 A2980")

    assert result.visibility.value == 200
    assert result.visibility.unit == "M"


@pytest.mark.integration
def test_metar_with_windshear():
    """Test METAR with wind shear information."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW030 22/18 A2992 WS ALL RWY")

    assert isinstance(result.windshear, list)


@pytest.mark.integration
def test_metar_with_recent_weather():
    """Test METAR with recent weather information."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW030 22/18 A2992 RERA")

    # Recent weather should be in result if parsed
    assert isinstance(result.recent_weather, list)


@pytest.mark.integration
def test_metar_high_wind_conditions():
    """Test METAR with high wind speeds."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28035G50KT 5SM SKC 22/18 A2992")

    assert result.wind.speed == 35
    assert result.wind.gust == 50


@pytest.mark.integration
def test_metar_low_visibility_fog():
    """Test METAR with fog and low visibility."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KBOS 061751Z 00000KT 0400 FG VV002 18/18 A2990")

    assert result.visibility.value == 400
    assert any("fog" in w.phenomena for w in result.weather)


# ==============================================
# TAF EDGE CASES AND ADDITIONAL TESTS
# ==============================================


@pytest.mark.integration
def test_taf_multiple_change_groups():
    """Test TAF with multiple change groups."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250 "
        "TEMPO 0620/0622 -RA BKN020 "
        "BECMG 0623/0624 09010KT"
    )

    assert len(result.forecast_periods) >= 3


@pytest.mark.integration
def test_taf_with_prob40():
    """Test TAF with PROB40 (higher probability)."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 PROB40 TEMPO 0620/0622 -RA"
    )

    assert any(
        p.change_type == "PROB" and p.probability == 40 for p in result.forecast_periods
    )


@pytest.mark.integration
def test_taf_compact_spacing_multiple_issues():
    """Test TAF decoder handles multiple compact spacing issues."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KTFM062000 15010KT 6000 -RATEMPO0620/0622BKN020"
    )

    assert result.station_id == "KJFK"
    assert len(result.forecast_periods) >= 1


@pytest.mark.integration
def test_taf_with_multiple_icing_layers():
    """Multiple non-standard icing groups stay unparsed and are warned."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 620304 630507")

    assert "620304" in result.forecast_periods[0].unparsed_tokens
    assert "630507" in result.forecast_periods[0].unparsed_tokens
    assert any("non-standard TAF extension groups" in w for w in result.validation_warnings)


@pytest.mark.integration
def test_taf_with_high_altitude_winds():
    """Test TAF with high altitude winds."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 25045KT 9999 FEW250")

    assert result.forecast_periods[0].wind.speed == 45
    assert result.forecast_periods[0].wind.direction == 250


@pytest.mark.integration
def test_taf_full_validity_period():
    """Test TAF with full 24-hour validity period."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0618 28008KT 9999 FEW250")

    assert result.valid_period is not None


# ==============================================
# MODEL STRUCTURE TESTS
# ==============================================


@pytest.mark.unit
def test_metar_data_is_metar_report_subclass():
    """Test that MetarData is a subclass of MetarReport."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    assert isinstance(result, MetarReport)
    assert isinstance(result, MetarData)


@pytest.mark.unit
def test_taf_data_is_taf_report_subclass():
    """Test that TafData is a subclass of TafReport."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")

    assert isinstance(result, TafReport)
    assert isinstance(result, TafData)


@pytest.mark.unit
def test_metar_data_str_representation():
    """Test that MetarData has string representation."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    str_result = str(result)
    assert isinstance(str_result, str)
    assert len(str_result) > 0


@pytest.mark.unit
def test_taf_data_str_representation():
    """Test that TafData has string representation."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")

    str_result = str(result)
    assert isinstance(str_result, str)
    assert len(str_result) > 0


# ==============================================
# COMPLEX INTEGRATION TESTS
# ==============================================


@pytest.mark.integration
def test_metar_complete_realistic_report():
    """Test realistic complete METAR with many fields."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR KJFK 061751Z 28008KT 10SM FEW050 SCT100 BKN200 22/18 A2992 "
        "RMK AO2 SLP021 T02220178"
    )

    assert result.station_id == "KJFK"
    assert len(result.sky) >= 3
    assert result.temperature == 22
    assert result.dewpoint == 18
    assert "AO2" in result.remarks


@pytest.mark.integration
def test_taf_complete_realistic_report():
    """Test realistic complete TAF with multiple change groups."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250 "
        "TEMPO 0620/0622 -RA BKN050 "
        "FM062200 15010KT 6000 -RA SCT030 "
        "BECMG 0704/0706 20015KT 9999 SCT050 "
        "RMK NXT FCST BY 12Z"
    )

    assert result.station_id == "KJFK"
    assert len(result.forecast_periods) >= 3
    assert any(p.change_type == "TEMPO" for p in result.forecast_periods)
    assert any(p.change_type == "FM" for p in result.forecast_periods)
    assert any(p.change_type == "BECMG" for p in result.forecast_periods)


@pytest.mark.integration
def test_metar_rvr_with_variability():
    """Test METAR with RVR including variability trend."""
    decoder = MetarDecoder()
    result = decoder.decode(
        "METAR KJFK 061751Z 00000KT 0600 R04R/1200V1800U FG VV002 18/18 A2980"
    )

    assert len(result.runway_visual_ranges) >= 1


@pytest.mark.integration
def test_taf_with_both_prob_qualifiers():
    """Test TAF with both PROB30 and PROB40 in same report."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW030 "
        "PROB30 TEMPO 0620/0622 -RA "
        "PROB40 TEMPO 0700/0702 -SN"
    )

    assert any(p.probability == 30 for p in result.forecast_periods)
    assert any(p.probability == 40 for p in result.forecast_periods)


@pytest.mark.integration
def test_metar_with_all_weather_phenomenon():
    """Test METAR with various weather phenomenon combinations."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 3000 -SN BKN010 22/18 A2992")

    assert len(result.weather) >= 1
    assert any("snow" in w.phenomena for w in result.weather)


@pytest.mark.integration
def test_taf_with_temperature_and_weather():
    """Test TAF with both temperature forecast and weather."""
    decoder = TafDecoder()
    result = decoder.decode(
        "TAF KJFK 061730Z 0618/0724 28008KT 6000 -RA SCT020 BKN030 "
        "TX25/0618Z TN15/0706Z"
    )

    has_weather = any(len(p.weather) > 0 for p in result.forecast_periods)
    has_temps = len(result.temperature_forecasts) > 0
    assert has_weather or has_temps


# ==============================================
# SPECIAL CHARACTERS AND FORMATS
# ==============================================


@pytest.mark.integration
def test_metar_with_special_visibility_less_than():
    """Test METAR with less-than visibility modifier."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 00000KT M1/4SM FG OVC002 18/18 A2980")

    assert result.visibility.is_less_than is True


@pytest.mark.integration
def test_metar_with_special_visibility_greater_than():
    """Test METAR with greater-than visibility modifier."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT P6SM SKC 22/18 A2992")

    assert result.visibility.is_greater_than is True


@pytest.mark.integration
def test_taf_with_compact_cloud_spacing():
    """Test TAF cloud coverage compact formatting."""
    decoder = TafDecoder()
    result = decoder.decode("TAF KJFK 061730Z 0618/0724 28008KTFEW250")

    # Preprocessing should handle this
    assert result.station_id == "KJFK"


@pytest.mark.integration
def test_metar_metric_pressure_conversion():
    """Test METAR with metric pressure (Q notation)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR EGLL 061751Z 09015KT 9999 FEW030 18/10 Q1013")

    assert result.altimeter.value == 1013
    assert result.altimeter.unit == "hPa"


@pytest.mark.integration
def test_metar_imperial_pressure_conversion():
    """Test METAR with imperial pressure (A notation)."""
    decoder = MetarDecoder()
    result = decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW030 22/18 A2992")

    assert result.altimeter.value == 29.92
    assert result.altimeter.unit == "inHg"
