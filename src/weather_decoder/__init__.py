"""Weather Decoder public package exports.

``MetarData`` and ``TafData`` are the convenience report objects returned by the
decoders. They subclass the canonical report models exported from
``weather_decoder.models``.
"""

from .core.metar_decoder import MetarDecoder
from .core.taf_decoder import TafDecoder
from .data.metar_data import MetarData
from .data.taf_data import TafData
from .models import (
    DirectionalVisibility,
    IcingForecast,
    MilitaryColorCode,
    MinimumVisibility,
    MetarReport,
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

__version__ = "1.1.7"
__author__ = "Justin"


def decode_metar(raw_metar: str) -> MetarData:
    """Decode a METAR report using the default decoder."""
    return MetarDecoder().decode(raw_metar)


def decode_taf(raw_taf: str) -> TafData:
    """Decode a TAF report using the default decoder."""
    return TafDecoder().decode(raw_taf)


__all__ = [
    "decode_metar",
    "decode_taf",
    "MetarDecoder",
    "TafDecoder",
    "MetarData",
    "TafData",
    "DirectionalVisibility",
    "IcingForecast",
    "MilitaryColorCode",
    "MinimumVisibility",
    "MetarReport",
    "Pressure",
    "RunwayState",
    "RunwayVisualRange",
    "SeaCondition",
    "SkyCondition",
    "TafForecastPeriod",
    "TafReport",
    "TemperatureForecast",
    "TimeRange",
    "Trend",
    "TrendTime",
    "TurbulenceForecast",
    "Visibility",
    "WeatherPhenomenon",
    "Wind",
    "WindShear",
]
