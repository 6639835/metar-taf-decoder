"""Trend information parser for METAR reports

This module handles parsing of trend forecasts (NOSIG, BECMG, TEMPO)
that appear at the end of METAR reports.
"""

import re
from typing import Dict, List, Optional

from ..constants.change_codes import TREND_TYPES


class TrendParser:
    """Parser for trend information in METAR reports

    Trends indicate expected changes in weather conditions:
    - NOSIG: No significant changes expected in next 2 hours
    - BECMG: Becoming - gradual change expected
    - TEMPO: Temporary - fluctuations expected

    Time indicators:
    - FM (From): Changes starting from specified time
    - TL (Till): Changes until specified time
    - AT: Changes at specified time
    """

    def __init__(self, wind_parser=None, sky_parser=None, weather_parser=None):
        """Initialize the trend parser with optional dependent parsers

        Args:
            wind_parser: WindParser instance for parsing wind changes
            sky_parser: SkyParser instance for parsing sky changes
            weather_parser: WeatherParser instance for parsing weather changes
        """
        self.wind_parser = wind_parser
        self.sky_parser = sky_parser
        self.weather_parser = weather_parser

    def extract_trends(self, parts: List[str]) -> List[Dict]:
        """Extract and decode trend information from METAR parts

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            List of trend dictionaries
        """
        trends: List[Dict] = []

        i = 0
        while i < len(parts):
            if parts[i] in TREND_TYPES:
                trend_type = parts.pop(i)
                trend = self._parse_trend_group(trend_type, parts, i)
                if trend:
                    trends.append(trend)
            else:
                i += 1

        return trends

    def _parse_trend_group(self, trend_type: str, parts: List[str], start_idx: int) -> Dict:
        """Parse a single trend group

        Args:
            trend_type: The type of trend (NOSIG, BECMG, TEMPO)
            parts: Remaining parts list
            start_idx: Index to start parsing from

        Returns:
            Trend dictionary
        """
        # Handle NOSIG (no significant change)
        if trend_type == "NOSIG":
            return {
                "type": trend_type,
                "description": "No significant change expected in next 2 hours",
                "raw": trend_type,
            }

        # Collect trend elements for BECMG and TEMPO
        trend_elements: List[str] = []
        time_info: Dict[str, str] = {}
        weather_changes: List[str] = []

        i = start_idx
        while i < len(parts) and parts[i] not in TREND_TYPES and not parts[i].startswith("RMK"):
            element = parts.pop(i)
            trend_elements.append(element)

            # Parse time indicators
            time_parsed = self._parse_time_indicator(element, time_info)
            if time_parsed:
                continue

            # Parse weather changes
            change = self._parse_weather_change(element)
            if change:
                weather_changes.append(change)

        # Build description
        description = self._build_trend_description(trend_type, time_info, weather_changes)

        return {
            "type": trend_type,
            "raw": f"{trend_type} {' '.join(trend_elements)}" if trend_elements else trend_type,
            "time": time_info if time_info else None,
            "changes": weather_changes if weather_changes else None,
            "description": description,
        }

    def _parse_time_indicator(self, element: str, time_info: Dict) -> bool:
        """Parse time indicator from element

        Args:
            element: The element to parse
            time_info: Dictionary to store parsed time (modified in place)

        Returns:
            True if a time indicator was parsed, False otherwise
        """
        if element.startswith("FM"):
            match = re.match(r"FM(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["from"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        elif element.startswith("TL"):
            match = re.match(r"TL(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["until"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        elif element.startswith("AT"):
            match = re.match(r"AT(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["at"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        return False

    def _parse_weather_change(self, element: str) -> Optional[str]:
        """Parse a weather change element

        Args:
            element: The element to parse

        Returns:
            Description of the change, or None
        """
        # Visibility changes (4-digit number)
        if element.isdigit() and len(element) == 4:
            vis_value = int(element)
            if vis_value == 9999:
                return "visibility 10km or more"
            elif vis_value >= 1000:
                return f"visibility {vis_value/1000:.1f}km"
            else:
                return f"visibility {vis_value}m"

        # Wind changes
        wind_match = re.match(r"(\d{3}|VRB)\d{2,3}(G\d{2,3})?(KT|MPS|KMH)", element)
        if wind_match and self.wind_parser:
            wind_info = self.wind_parser.parse(element)
            if wind_info:
                return self._format_wind_change(wind_info)

        # Cloud changes
        cloud_match = re.match(r"(SKC|CLR|NSC|NCD|FEW|SCT|BKN|OVC|VV)(\d{3}|///)?", element)
        if cloud_match and self.sky_parser:
            sky_info = self.sky_parser.parse(element)
            if sky_info:
                return self._format_sky_change(sky_info)

        # Weather phenomena
        wx_match = re.match(
            r"^[-+]?(VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?" r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+",
            element,
        )
        if wx_match and self.weather_parser:
            wx_info = self.weather_parser.parse(element)
            if wx_info:
                return self._format_weather_change(wx_info)

        # NSW = No Significant Weather
        if element == "NSW":
            return "no significant weather"

        # CAVOK
        if element == "CAVOK":
            return "CAVOK"

        return None

    def _format_wind_change(self, wind_info: Dict) -> str:
        """Format wind change for trend description"""
        dir_text = "variable" if wind_info["direction"] == "VRB" else f"{wind_info['direction']}°"
        wind_desc = f"wind {dir_text} at {wind_info['speed']} {wind_info['unit']}"
        if wind_info.get("gust"):
            wind_desc += f" gusting {wind_info['gust']}"
        return wind_desc

    def _format_sky_change(self, sky_info: Dict) -> str:
        """Format sky condition change for trend description"""
        sky_type = sky_info["type"]

        if sky_type in ["SKC", "CLR"]:
            return "sky clear"
        elif sky_type == "NSC":
            return "no significant cloud"
        elif sky_type == "NCD":
            return "no cloud detected"
        elif sky_type == "VV":
            if sky_info.get("unknown_height") or sky_info["height"] is None:
                return "vertical visibility unknown"
            return f"vertical visibility {sky_info['height']}ft"
        else:
            cloud_desc = f"{sky_type} at {sky_info['height']}ft"
            if sky_info.get("cb"):
                cloud_desc += " CB"
            elif sky_info.get("tcu"):
                cloud_desc += " TCU"
            return cloud_desc

    def _format_weather_change(self, wx_info: Dict) -> str:
        """Format weather change for trend description"""
        wx_parts = []
        if wx_info.get("intensity"):
            wx_parts.append(wx_info["intensity"])
        if wx_info.get("descriptor"):
            wx_parts.append(wx_info["descriptor"])
        if wx_info.get("phenomena"):
            wx_parts.extend(wx_info["phenomena"])
        return " ".join(wx_parts) if wx_parts else ""

    def _build_trend_description(
        self,
        trend_type: str,
        time_info: Dict,
        weather_changes: List[str],
    ) -> str:
        """Build human-readable trend description

        Args:
            trend_type: BECMG or TEMPO
            time_info: Parsed time information
            weather_changes: List of weather change descriptions

        Returns:
            Human-readable description
        """
        parts = []

        if trend_type == "BECMG":
            parts.append("Becoming")
        elif trend_type == "TEMPO":
            parts.append("Temporary")

        # Add time info
        if time_info.get("from") and time_info.get("until"):
            parts.append(f"from {time_info['from']} until {time_info['until']}:")
        elif time_info.get("from"):
            parts.append(f"from {time_info['from']}:")
        elif time_info.get("until"):
            parts.append(f"until {time_info['until']}:")
        elif time_info.get("at"):
            parts.append(f"at {time_info['at']}:")
        else:
            parts.append("-")

        # Add weather changes
        if weather_changes:
            parts.append(", ".join(weather_changes))

        return " ".join(parts)
