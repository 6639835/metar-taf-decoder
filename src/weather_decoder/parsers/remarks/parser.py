"""Top-level remarks parser orchestration."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from .automation import AutomationRemarksMixin
from .common import MAINTENANCE_INDICATOR, SENSOR_STATUS, RemarksCommon
from .lightning import LightningRemarksMixin
from .precipitation import PrecipitationRemarksMixin
from .pressure import PressureRemarksMixin
from .recent_weather import RecentWeatherRemarksMixin
from .registry import iter_handlers
from .sky import SkyRemarksMixin
from .temperature import TemperatureRemarksMixin
from .visibility import VisibilityRemarksMixin
from .wind import WindRemarksMixin


class RemarksParser(
    AutomationRemarksMixin,
    WindRemarksMixin,
    PressureRemarksMixin,
    TemperatureRemarksMixin,
    PrecipitationRemarksMixin,
    VisibilityRemarksMixin,
    LightningRemarksMixin,
    SkyRemarksMixin,
    RecentWeatherRemarksMixin,
    RemarksCommon,
):
    """Parser for METAR remarks sections."""

    def __init__(self):
        """Initialize the remarks parser."""
        self._key_patterns = {
            # Prefer AO2 over AO1 when both appear
            "Station Type": ["AO2", "AO1"],
            "Sea Level Pressure": ["SLP"],
            "Pressure Tendency": [r"5[0-8]\d{3}"],
            "Temperature (tenths)": ["T0", "T1"],
            "Dewpoint (tenths)": ["T0", "T1"],
            "24-Hour Maximum Temperature": [r"4[01]\d{3}[01]\d{3}"],
            "24-Hour Minimum Temperature": [r"4[01]\d{3}[01]\d{3}"],
            "6-Hour Maximum Temperature": [r"1[01]\d{3}"],
            "6-Hour Minimum Temperature": [r"2[01]\d{3}"],
            "6-Hour Precipitation": [r"6\d{4}"],
            "Variable Visibility": ["VIS"],
            "Precipitation Begin/End Times": ["B", "E"],
            "Unknown Precipitation": ["UP"],
            "QFE": ["QFE"],
            "Precipitation Amount": [r"P\d{4}"],
            "Peak Wind": ["PK WND"],
            "Surface Visibility": ["SFC VIS"],
            "Tower Visibility": ["TWR VIS"],
            "Visibility Lower": ["VIS LWR"],
            "Directional Visibility (Remarks)": [],
            "Lightning": ["LTG"],
            "Virga": ["VIRGA"],
            "Thunderstorm Location": [
                "TS OHD",
                "TS DSNT",
                "TS VC",
                "TS ALQDS",
                "TS MOV",
            ],
            "Weather Location": ["SHRA", "VCSH"],
            "PIREP Turbulence": ["TURB OBS"],
            "PIREP Clouds": ["PIREP"],
            "Forecast Amendment": ["FCST AMD"],
            "Forecast Trends": ["FCST AMD", "TEMPO", "BECMG"],
            "ACSL": ["ACSL"],
            "Cloud Types": [
                "SC",
                "AC",
                "ST",
                "CU",
                "CB",
                "CI",
                "AS",
                "NS",
                "SN",
                "TCU",
                "CC",
                "CS",
            ],
            "Density Altitude": ["DENSITY ALT"],
            "Obscuration": ["OBSC"],
            "QBB": ["QBB"],
            "Ceiling": ["CIG"],
            "Variable Ceiling": ["CIG"],
            "Pressure Change": ["PRESFR", "PRESRR"],
            "Frontal Passage": ["FROPA"],
            "Wind Shift": ["WSHFT"],
            "SLP Status": ["SLPNO"],
            "RVR Status": ["RVRNO"],
            "Additive Data Warning": [],
            "Sensor Status": list(SENSOR_STATUS.keys()),
            "Maintenance Indicator": [MAINTENANCE_INDICATOR],
            "runway_winds": ["RWY", "WIND"],
            "location_winds": ["WIND"],
        }

    def parse(self, metar: str) -> Tuple[str, Dict[str, object]]:
        """Parse the remarks section from a METAR string."""
        match = re.search(r"RMK\s+(.+)$", metar)
        if not match:
            return "", {}

        remarks = match.group(1).rstrip("=").rstrip()
        decoded: Dict[str, object] = {}
        positions: Dict[str, int] = {}
        report_time = self._extract_report_time(metar)

        for handler in iter_handlers():
            handler.apply(self, remarks, decoded, positions, report_time)

        return remarks, self._sort_by_position(remarks, decoded, positions)


def parse_remarks(metar: str) -> Tuple[str, Dict[str, object]]:
    """Parse a METAR remarks section with the default parser."""
    return RemarksParser().parse(metar)
