"""Constants and lookup tables for weather decoding"""

# Weather intensity codes
WEATHER_INTENSITY = {
    '-': 'light',
    '+': 'heavy',
    'VC': 'vicinity',
    'RE': 'recent'
}

# Weather descriptor codes
WEATHER_DESCRIPTORS = {
    'MI': 'shallow',
    'PR': 'partial',
    'BC': 'patches',
    'DR': 'low drifting',
    'BL': 'blowing',
    'SH': 'shower',
    'TS': 'thunderstorm',
    'FZ': 'freezing'
}

# Weather phenomena codes
WEATHER_PHENOMENA = {
    'DZ': 'drizzle',
    'RA': 'rain',
    'SN': 'snow',
    'SG': 'snow grains',
    'IC': 'ice crystals',
    'PL': 'ice pellets',
    'GR': 'hail',
    'GS': 'small hail',
    'UP': 'unknown precipitation',
    'BR': 'mist',
    'FG': 'fog',
    'FU': 'smoke',
    'VA': 'volcanic ash',
    'DU': 'dust',
    'SA': 'sand',
    'HZ': 'haze',
    'PY': 'spray',
    'PO': 'dust whirls',
    'SQ': 'squalls',
    'FC': 'funnel cloud',
    '+FC': 'tornado/waterspout',
    'SS': 'sandstorm',
    'DS': 'duststorm'
}

# Sky condition codes
SKY_CONDITIONS = {
    'SKC': 'clear',
    'CLR': 'clear',
    'FEW': 'few',
    'SCT': 'scattered',
    'BKN': 'broken',
    'OVC': 'overcast',
    'VV': 'vertical visibility',
    'NSC': 'no significant cloud',
    'NCD': 'no cloud detected',
    '///': 'unknown'
}

# Trend types for METAR
TREND_TYPES = ['NOSIG', 'BECMG', 'TEMPO']

# Change group indicators for TAF
CHANGE_INDICATORS = ['TEMPO', 'BECMG', 'PROB30', 'PROB40', 'FM']

# Cloud types requiring spacing fixes
CLOUD_TYPES = ['FEW', 'SCT', 'BKN', 'OVC']

# RVR trend indicators
RVR_TRENDS = {
    'U': 'improving',
    'D': 'deteriorating', 
    'N': 'no change'
}

# Military color codes
MILITARY_COLOR_CODES = {
    'BLU': 'Blue',
    'WHT': 'White', 
    'GRN': 'Green',
    'YLO': 'Yellow',
    'AMB': 'Amber',
    'RED': 'Red'
}
