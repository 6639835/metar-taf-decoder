"""Runway state and RVR codes"""

# RVR trend indicators
RVR_TRENDS = {
    "U": "improving",
    "D": "deteriorating",
    "N": "no change",
}

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

# Runway braking action (8-group remarks format)
#
# NOTE: `RemarksParser` historically uses int keys for braking values (e.g. 91),
# while other parsers use string keys (e.g. "91"). Keep int-keyed mapping for
# backward compatibility.
RUNWAY_BRAKING_REMARKS = {
    91: "Poor",
    92: "Medium/Poor",
    93: "Medium",
    94: "Medium/Good",
    95: "Good",
    99: "Unreliable",
}

# Backward-compatible tables for remarks formatting.
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

RUNWAY_STATE_EXTENT_REMARKS = {
    "1": "10% or less",
    "2": "11% to 25%",
    "5": "26% to 50%",
    "9": "51% to 100%",
    "/": "Not reported",
}

# Runway depth special values used in runway state groups (e.g. 8-group remarks).
RUNWAY_DEPTH_SPECIAL = {
    "00": "less than 1mm",
    "92": "10cm",
    "93": "15cm",
    "94": "20cm",
    "95": "25cm",
    "96": "30cm",
    "97": "35cm",
    "98": "40cm or more",
    "99": "runway not operational",
    "//": "not reported or not measurable",
}
