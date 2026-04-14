from weather_decoder import MetarData, MetarDecoder, TafData, TafDecoder


def test_metar_decoder_returns_public_wrapper() -> None:
    report = MetarDecoder().decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")

    assert isinstance(report, MetarData)
    assert report.station_id == "KJFK"
    assert report.wind is not None
    assert report.wind.speed == 8
    assert report.wind.unit == "KT"
    assert report.visibility is not None
    assert report.visibility.value == 10.0
    assert "Wind:" in str(report)


def test_taf_decoder_returns_public_wrapper() -> None:
    report = TafDecoder().decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")

    assert isinstance(report, TafData)
    assert report.station_id == "KJFK"
    assert report.forecast_periods
    assert report.forecast_periods[0].wind is not None
    assert report.forecast_periods[0].wind.speed == 8
    assert "Initial Forecast:" in str(report)
