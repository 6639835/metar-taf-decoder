"""High-level report modifiers / special tokens for METAR & TAF."""

# Report / message modifiers
REPORT_MODIFIERS = {
    "AUTO": "Automated observation (no human intervention)",
    "COR": "Correction to a previously disseminated observation",
    "AMD": "Amendment (TAF)",
    "RTD": "Routine delayed observation",
    "NOSPECI": "No SPECI reports are taken at the station",
    "NIL": "Missing report",
}

# Special conditions used in METAR/TAF bodies.
SPECIAL_CONDITIONS = {
    "NSW": "No significant weather",
    "CAVOK": (
        "Ceiling and visibility OK (visibility ≥10 km, no clouds below 5000 ft/1500 m, "
        "no CB/TCU, no significant weather)"
    ),
    "NOSIG": "No significant change expected (trend/TAF context)",
}

# Common "sentinel" / special values seen in reports (visibility, ceilings, etc.).
SPECIAL_VALUES = {
    "9999": "Visibility 10 km or more (meters-based reports)",
    "////": "Value not available / not reported (field unavailable)",
    "P6SM": "Visibility greater than 6 statute miles (US TAF)",
    "M1/4SM": "Visibility less than 1/4 statute mile (US format)",
}
