"""Weather phenomena codes and descriptors"""

# Weather intensity codes
WEATHER_INTENSITY = {
    "-": "light",
    "+": "heavy",
    "VC": "vicinity",
    "RE": "recent",
}

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

# Weather phenomena codes (2-character base codes per WMO Code Table 4678 / ICAO)
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

# Compound phenomena — matched as complete tokens before 2-char decomposition.
# Covers: sleet (RASN/SNRA), EU/JMA auto-station combined codes, and common
# descriptor+phenomenon combinations that must be treated as atomic units.
# Per WMO 306 Vol I.1, Code Table 4678, and ICAO Annex 3
COMPOUND_WEATHER_PHENOMENA = {
    # Sleet / mixed precipitation (JMA, FMH-1)
    "RASN": "rain and snow mixed (sleet)",
    "SNRA": "snow and rain mixed (sleet)",
    # EU Regulation Annex IV / ICAO auto-station combined codes
    "FZUP": "freezing unknown precipitation",
    "SHUP": "shower of unknown precipitation",
    "TSUP": "thunderstorm with unknown precipitation",
    # Fog descriptors (WMO Reg 15.8.10)
    "FZFG": "freezing fog",
    "MIFG": "shallow fog",
    "VCFG": "fog in vicinity",
    "BCFG": "patchy fog",
    "PRFG": "partial fog",
    # Blowing phenomena variants (WMO Reg 15.8.9)
    "BLDU": "blowing dust",
    "BLSA": "blowing sand",
    "BLSN": "blowing snow",
    # Vicinity + phenomena combinations (WMO Reg 15.8.10, 15.8.11)
    "VCTS": "thunderstorm in vicinity",
    "VCDS": "duststorm in vicinity",
    "VCSS": "sandstorm in vicinity",
    "VCFC": "funnel cloud in vicinity",
    "VCSH": "showers in vicinity",
    "VCPO": "dust whirls in vicinity",
    "VCVA": "volcanic ash in vicinity",
    # Additional WMO-compliant compounds
    "SHSN": "snow shower",
    "SHGR": "hail shower",
    "SHGS": "small hail shower",
    "SHRA": "rain shower",
    "TSGR": "thunderstorm with hail",
    "TSGS": "thunderstorm with small hail",
    "TSRA": "thunderstorm with rain",
    "TSSN": "thunderstorm with snow",
}
