"""Regular expression patterns for weather parsing"""

import re

# Station and time patterns
STATION_ID_PATTERN = r'^([A-Z][A-Z0-9]{3})'
DATETIME_PATTERN = r'(\d{2})(\d{2})(\d{2})Z'
VALID_PERIOD_PATTERN = r'(\d{2})(\d{2})/(\d{2})(\d{2})'

# METAR type patterns  
METAR_TYPE_PATTERN = r'^(METAR|SPECI)'
AUTO_PATTERN = r'\bAUTO\b'

# Wind patterns
# Supports normal format and extreme wind speeds (P99KT, ABV49MPS, ABV99KT)
WIND_PATTERN = r'(P)?(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?(?:KT|MPS|KMH)'
WIND_EXTREME_PATTERN = r'ABV(\d{2,3})(KT|MPS)'
WIND_VAR_PATTERN = r'(\d{3})V(\d{3})'

# Visibility patterns
VISIBILITY_PATTERN = r'(?:^|\s)(?:(?:P?(\d{1,4})(?:/(\d))?(SM|KM|M)|(\d{4})(NDV)?|CAVOK|CLR))'

# Runway visual range patterns
# Format: R{runway}/{M|P}{value}{V{M|P}{value}}{FT}{trend}
# M = less than (Minus), P = more than (Plus)
# Trend: U = improving (Up), D = deteriorating (Down), N = no change
# Note: Pattern ends with $ to avoid matching runway state reports (6 digits)
RVR_PATTERN = r'R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$'

# Runway state report pattern (MOTNE format)
# Format: R{runway}/{deposit}{extent}{depth}{braking}
# - deposit: 1 digit (0-9, / for not reported)
# - extent: 1 digit (1=<10%, 2=11-25%, 5=26-50%, 9=>51%, / for not reported)
# - depth: 2 digits (00-90 in mm, 92=10cm, 99=runway not operational, // not reported)
# - braking: 2 digits (coefficient, 91=poor, 92=medium/poor, 93=medium, 94=medium/good, 95=good, 99=unreliable)
RUNWAY_STATE_PATTERN = r'R(\d{2}[LCR]?)/(\d|/)(\d|/)(\d{2}|//)(\d{2}|//)$'

# Sky condition patterns
# Height can be 3 digits or /// when height cannot be determined by auto system
SKY_PATTERN = r'(SKC|CLR|FEW|SCT|BKN|OVC|VV|///)(\d{3}|///)(CB|TCU|///)?'

# Temperature patterns
# Dewpoint is optional (e.g., 17/ when dewpoint not available)
TEMPERATURE_PATTERN = r'(M)?(\d{2})/(?:(M)?(\d{2}))?'
TAF_TEMPERATURE_PATTERN = r'T([MX])([M]?)(\d{2})/(\d{2})(\d{2})Z'

# Pressure patterns
ALTIMETER_PATTERN = r'(A|Q)(\d{4})'
QNH_PATTERN = r'Q(\d{4})'
ALT_QNH_PATTERN = r'QNH(\d{4})(?:INS|HPa)?'
ALT_PATTERN = r'A(\d{4})'

# Change group patterns  
CHANGE_GROUP_PATTERN = r'(BECMG|TEMPO|FM|PROB|TAF AMD)'
FM_PATTERN = r'FM(\d{2})(\d{2})(\d{2})'

# Remarks pattern
REMARKS_PATTERN = r'RMK\s+(.+)$'

# Time range pattern (for TAF TEMPO/BECMG)
TIME_RANGE_PATTERN = r'(\d{4})/(\d{4})'

# Compiled patterns for better performance
COMPILED_PATTERNS = {
    'station_id': re.compile(STATION_ID_PATTERN),
    'datetime': re.compile(DATETIME_PATTERN),
    'valid_period': re.compile(VALID_PERIOD_PATTERN),
    'metar_type': re.compile(METAR_TYPE_PATTERN),
    'auto': re.compile(AUTO_PATTERN),
    'wind': re.compile(WIND_PATTERN),
    'wind_extreme': re.compile(WIND_EXTREME_PATTERN),
    'wind_var': re.compile(WIND_VAR_PATTERN),
    'visibility': re.compile(VISIBILITY_PATTERN),
    'rvr': re.compile(RVR_PATTERN),
    'runway_state': re.compile(RUNWAY_STATE_PATTERN),
    'sky': re.compile(SKY_PATTERN),
    'temperature': re.compile(TEMPERATURE_PATTERN),
    'taf_temperature': re.compile(TAF_TEMPERATURE_PATTERN),
    'altimeter': re.compile(ALTIMETER_PATTERN),
    'qnh': re.compile(QNH_PATTERN),
    'alt_qnh': re.compile(ALT_QNH_PATTERN),
    'alt': re.compile(ALT_PATTERN),
    'change_group': re.compile(CHANGE_GROUP_PATTERN),
    'fm': re.compile(FM_PATTERN),
    'remarks': re.compile(REMARKS_PATTERN),
    'time_range': re.compile(TIME_RANGE_PATTERN)
}
