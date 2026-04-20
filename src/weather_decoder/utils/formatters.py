"""Deprecated compatibility shim for common formatting helpers.

Import from ``weather_decoder.formatters.common`` instead.
"""

from ..formatters.common import (
    format_pressure,
    format_sky_condition,
    format_temperature,
    format_visibility,
    format_weather_group,
    format_wind,
)

__all__ = [
    "format_wind",
    "format_visibility",
    "format_temperature",
    "format_pressure",
    "format_sky_condition",
    "format_weather_group",
]
