"""Station / sensor related codes used in METAR remarks."""

# Automated station type identifiers (AO1/AO2) commonly found in RMK.
STATION_TYPES = {
    "AO1": "Automated station without precipitation discriminator",
    "AO2": "Automated station with precipitation discriminator",
}

# Sensor/status indicators used in U.S. METAR remarks (RMK).
#
# NOTE: Some tokens end with "NO" and mean "not available".
SENSOR_STATUS = {
    "PWINO": "Precipitation identifier sensor not available",
    "TSNO": "Thunderstorm information not available",
    "TSCBNO": "Thunderstorm and significant convective cloud information not available",
    "FZRANO": "Freezing rain sensor not available",
    "PNO": "Precipitation amount not available",
    "VISNO": "Visibility at secondary location not available",
    "CHINO": "Sky condition at secondary location not available",
    "RVRNO": "RVR system not available",
}

# Maintenance indicator (not a code group; a literal symbol)
MAINTENANCE_INDICATOR = "$"
