"""Location, direction, and lightning codes"""

# Lightning frequency codes
LIGHTNING_FREQUENCY = {
    "FRQ": "frequent (more than 6 per minute)",
    "OCNL": "occasional (1-6 per minute)",
    "CONS": "continuous",
}

# Lightning type codes
LIGHTNING_TYPES = {
    "IC": "in-cloud",
    "CC": "cloud-to-cloud",
    "CG": "cloud-to-ground",
    "CA": "cloud-to-air",
}

# Location/Distance indicators
LOCATION_INDICATORS = {
    "DSNT": "distant (10-30 NM)",
    "VC": "in vicinity (5-10 NM)",
    "OHD": "overhead",
    "ALQDS": "all quadrants",
}

# Direction abbreviations
DIRECTION_ABBREV = {
    "NE": "northeast",
    "NW": "northwest",
    "SE": "southeast",
    "SW": "southwest",
    "N": "north",
    "E": "east",
    "S": "south",
    "W": "west",
}
