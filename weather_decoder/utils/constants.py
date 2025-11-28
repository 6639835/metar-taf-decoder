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
    "1": "less than 10%",
    "2": "11% to 25%",
    "3": "26% to 50%",  # Not commonly used
    "4": "51% to 75%",  # Not commonly used
    "5": "26% to 50%",
    "6": "51% to 75%",  # Not commonly used
    "7": "76% to 90%",  # Not commonly used
    "8": "91% to 100%",  # Not commonly used
    "9": "more than 51%",
    "/": "not reported",
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
