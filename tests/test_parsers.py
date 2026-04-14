from weather_decoder.parsers.visibility_parser import VisibilityParser
from weather_decoder.parsers.weather_parser import WeatherParser
from weather_decoder.parsers.wind_parser import WindParser


def test_wind_parser_returns_wind_model() -> None:
    wind = WindParser().parse("28045G65KT")

    assert wind is not None
    assert wind.direction == 280
    assert wind.speed == 45
    assert wind.gust == 65
    assert wind.unit == "KT"


def test_visibility_parser_returns_visibility_model() -> None:
    visibility = VisibilityParser().parse("P6SM")

    assert visibility is not None
    assert visibility.is_greater_than is True
    assert visibility.value == 6.0
    assert visibility.unit == "SM"


def test_weather_parser_returns_weather_model() -> None:
    weather = WeatherParser().parse("-RA")

    assert weather is not None
    assert weather.intensity == "light"
    assert "rain" in weather.phenomena
