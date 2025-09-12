"""
Weather Decoder Package - A comprehensive METAR and TAF decoder

This package provides utilities for parsing and decoding aviation weather reports:
- METAR (Meteorological Terminal Air Reports)  
- TAF (Terminal Aerodrome Forecasts)
"""

from .core.metar_decoder import MetarDecoder
from .core.taf_decoder import TafDecoder
from .data.metar_data import MetarData
from .data.taf_data import TafData

__version__ = "1.0.5"
__author__ = "Justin"

__all__ = [
    "MetarDecoder",
    "TafDecoder", 
    "MetarData",
    "TafData"
]
