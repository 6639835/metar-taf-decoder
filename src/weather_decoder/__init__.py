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
    MetarReport,
    TafForecastPeriod,
    TafReport,
)

__version__ = "1.1.6"
__author__ = "Justin"

__all__ = [
    "MetarDecoder",
    "TafDecoder",
    "MetarData",
    "TafData",
    "MetarReport",
    "TafForecastPeriod",
    "TafReport",
]
