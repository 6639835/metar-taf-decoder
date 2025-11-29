"""Constants and lookup tables for weather decoding

This package provides organized constants for decoding METAR and TAF reports.
Constants are grouped by domain for easier maintenance.
"""

# Change indicators and trends
from .change_codes import (
    CHANGE_INDICATORS,
    TREND_TYPES,
)

# Location and direction codes
from .location_codes import (
    DIRECTION_ABBREV,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    LOCATION_INDICATORS,
)

# Military codes
from .military_codes import (
    MILITARY_COLOR_CODES,
)

# Pressure-related codes
from .pressure_codes import (
    PRESSURE_TENDENCY_CHARACTERISTICS,
)

# Runway-related codes
from .runway_codes import (
    RUNWAY_BRAKING,
    RUNWAY_BRAKING_REMARKS,
    RUNWAY_DEPOSIT_TYPES,
    RUNWAY_EXTENT,
    RUNWAY_STATE_DEPOSIT_TYPES_REMARKS,
    RUNWAY_STATE_EXTENT_REMARKS,
    RVR_TRENDS,
)

# Sky condition codes
from .sky_codes import (
    CLOUD_TYPE_CODES,
    CLOUD_TYPES,
    SKY_CONDITIONS,
)

# Weather-related codes
from .weather_codes import (
    WEATHER_DESCRIPTORS,
    WEATHER_INTENSITY,
    WEATHER_PHENOMENA,
)

__all__ = [
    # Weather
    "WEATHER_DESCRIPTORS",
    "WEATHER_INTENSITY",
    "WEATHER_PHENOMENA",
    # Sky
    "CLOUD_TYPE_CODES",
    "CLOUD_TYPES",
    "SKY_CONDITIONS",
    # Runway
    "RUNWAY_BRAKING",
    "RUNWAY_BRAKING_REMARKS",
    "RUNWAY_DEPOSIT_TYPES",
    "RUNWAY_EXTENT",
    "RUNWAY_STATE_DEPOSIT_TYPES_REMARKS",
    "RUNWAY_STATE_EXTENT_REMARKS",
    "RVR_TRENDS",
    # Pressure
    "PRESSURE_TENDENCY_CHARACTERISTICS",
    # Location
    "DIRECTION_ABBREV",
    "LIGHTNING_FREQUENCY",
    "LIGHTNING_TYPES",
    "LOCATION_INDICATORS",
    # Change codes
    "CHANGE_INDICATORS",
    "TREND_TYPES",
    # Military
    "MILITARY_COLOR_CODES",
]

