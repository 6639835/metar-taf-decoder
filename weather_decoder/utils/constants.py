"""Constants and lookup tables for weather decoding"""

# Weather intensity codes
WEATHER_INTENSITY = {"-": "light", "+": "heavy", "VC": "vicinity", "RE": "recent"}

# Weather descriptor codes
WEATHER_DESCRIPTORS = {
    "MI": "shallow",
    "PR": "partial",
    "BC": "patches",
    "DR": "low drifting",
    "BL": "blowing",
    "SH": "shower",
    "TS": "thunderstorm",
    "FZ": "freezing",
}

# Weather phenomena codes
WEATHER_PHENOMENA = {
    "DZ": "drizzle",
    "RA": "rain",
    "SN": "snow",
    "SG": "snow grains",
    "IC": "ice crystals",
    "PL": "ice pellets",
    "GR": "hail",
    "GS": "small hail",
    "UP": "unknown precipitation",
    "BR": "mist",
    "FG": "fog",
    "FU": "smoke",
    "VA": "volcanic ash",
    "DU": "dust",
    "SA": "sand",
    "HZ": "haze",
    "PY": "spray",
    "PO": "dust whirls",
    "SQ": "squalls",
    "FC": "funnel cloud",
    "+FC": "tornado/waterspout",
    "SS": "sandstorm",
    "DS": "duststorm",
}

# Sky condition codes
SKY_CONDITIONS = {
    "SKC": "clear",
    "CLR": "clear",
    "FEW": "few",
    "SCT": "scattered",
    "BKN": "broken",
    "OVC": "overcast",
    "VV": "vertical visibility",
    "NSC": "no significant cloud",
    "NCD": "no cloud detected",
    "///": "unknown",
}

# Trend types for METAR
TREND_TYPES = ["NOSIG", "BECMG", "TEMPO"]

# Change group indicators for TAF
CHANGE_INDICATORS = ["TEMPO", "BECMG", "PROB30", "PROB40", "FM"]

# Cloud types requiring spacing fixes
CLOUD_TYPES = ["FEW", "SCT", "BKN", "OVC"]

# RVR trend indicators
RVR_TRENDS = {"U": "improving", "D": "deteriorating", "N": "no change"}

# Military color codes
MILITARY_COLOR_CODES = {"BLU": "Blue", "WHT": "White", "GRN": "Green", "YLO": "Yellow", "AMB": "Amber", "RED": "Red"}

# Runway state report - deposit types
RUNWAY_DEPOSIT_TYPES = {
    "0": "clear and dry",
    "1": "damp",
    "2": "wet or water patches",
    "3": "rime or frost covered",
    "4": "dry snow",
    "5": "wet snow",
    "6": "slush",
    "7": "ice",
    "8": "compacted or rolled snow",
    "9": "frozen ruts or ridges",
    "/": "not reported",
}

# Runway state report - extent of contamination
RUNWAY_EXTENT = {
    "1": "10% or less",
    "2": "11% to 25%",
    "5": "26% to 50%",
    "9": "51% to 100%",
    "/": "not reported (e.g. due to rwy clearance in progress)",
}

# Runway state report - braking action/friction coefficient
RUNWAY_BRAKING = {
    "91": "poor",
    "92": "medium/poor",
    "93": "medium",
    "94": "medium/good",
    "95": "good",
    "99": "unreliable or unmeasurable",
    "//": "not reported",
}

# Pressure tendency characteristics (3-hour pressure tendency)
PRESSURE_TENDENCY_CHARACTERISTICS = {
    0: "Increasing, then decreasing",
    1: "Increasing, then steady; or increasing then increasing more slowly",
    2: "Increasing steadily or unsteadily",
    3: "Decreasing or steady, then increasing; or increasing then increasing more rapidly",
    4: "Steady",
    5: "Decreasing, then increasing",
    6: "Decreasing, then steady; or decreasing then decreasing more slowly",
    7: "Decreasing steadily or unsteadily",
    8: "Steady or increasing, then decreasing; or decreasing then decreasing more rapidly",
}

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

# Cloud type codes (ICAO/Canadian format)
CLOUD_TYPE_CODES = {
    "SC": "Stratocumulus",
    "ST": "Stratus",
    "CU": "Cumulus",
    "CB": "Cumulonimbus",
    "CI": "Cirrus",
    "CS": "Cirrostratus",
    "CC": "Cirrocumulus",
    "AC": "Altocumulus",
    "AS": "Altostratus",
    "NS": "Nimbostratus",
    "SN": "Nimbostratus",  # Canadian alternate for NS
    "TCU": "Towering Cumulus",
    "CF": "Cumulus Fractus",
    "SF": "Stratus Fractus",
}

# Runway state deposit types (8-group remarks format)
RUNWAY_STATE_DEPOSIT_TYPES_REMARKS = {
    "0": "Clear and dry",
    "1": "Damp",
    "2": "Wet or water patches",
    "3": "Rime or frost (normally less than 1mm deep)",
    "4": "Dry snow",
    "5": "Wet snow",
    "6": "Slush",
    "7": "Ice",
    "8": "Compacted or rolled snow",
    "9": "Frozen ruts or ridges",
    "/": "Not reported",
}

# Runway state extent types (8-group remarks format)
RUNWAY_STATE_EXTENT_REMARKS = {
    "1": "10% or less",
    "2": "11% to 25%",
    "5": "26% to 50%",
    "9": "51% to 100%",
    "/": "Not reported",
}

# Runway braking action (8-group remarks format)
RUNWAY_BRAKING_REMARKS = {
    91: "Poor",
    92: "Medium/Poor",
    93: "Medium",
    94: "Medium/Good",
    95: "Good",
    99: "Unreliable",
}
