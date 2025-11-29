"""Sky condition and cloud type codes"""

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

# Cloud types requiring spacing fixes
CLOUD_TYPES = ["FEW", "SCT", "BKN", "OVC"]

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

