"""Convenience report wrappers returned by the decoders.

These wrappers subclass the canonical report models in ``weather_decoder.models``
and add human-readable formatting helpers.
"""

from .metar_data import MetarData
from .taf_data import TafData

__all__ = ["MetarData", "TafData"]
