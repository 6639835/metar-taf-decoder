"""Station / sensor related codes used in METAR remarks."""

# Automated station type identifiers (AO1/AO2) commonly found in RMK.
STATION_TYPES = {
    "AO1": "Automated station without precipitation discriminator",
    "AO2": "Automated station with precipitation discriminator",
    # Common remarks variants (often used outside the U.S. METAR body header)
    "A01": "Automated observation equipment cannot distinguish between rain and snow",
    "A02": "Automated observation equipment can distinguish between rain and snow",
    "A02A": "Automated observation augmented by a human observer",
}

# Sensor/status indicators used in U.S. METAR remarks (RMK).
#
# NOTE: Some tokens end with "NO" and mean "not available".
SENSOR_STATUS = {
    "PWINO": "Precipitation identifier sensor not available",
    "TSNO": "Thunderstorm information not available",
    "FZRANO": "Freezing rain information not available",
    "PNO": "Precipitation amount not available",
    "VISNO": "Visibility at secondary location not available",
    "CHINO": "Sky condition at secondary location not available",
    "RVRNO": "RVR system values not available",
}

# Maintenance indicator (not a code group; a literal symbol)
MAINTENANCE_INDICATOR = "$"
