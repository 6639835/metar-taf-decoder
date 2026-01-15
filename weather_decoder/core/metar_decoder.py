"""Main METAR decoder that orchestrates parsing"""

import re
from datetime import datetime, timezone
from typing import Dict, List

from ..data.metar_data import MetarData
from ..parsers.pressure_parser import PressureParser
from ..parsers.remarks_parser import RemarksParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..utils.constants import (
    MILITARY_COLOR_CODES,
    RUNWAY_BRAKING,
    RUNWAY_DEPOSIT_TYPES,
    RUNWAY_EXTENT,
    RVR_TRENDS,
    TREND_TYPES,
)
from ..utils.patterns import COMPILED_PATTERNS, RUNWAY_STATE_PATTERN, RVR_PATTERN


class MetarDecoder:
    """METAR decoder class that parses raw METAR strings"""

    def __init__(self):
        """Initialize the METAR decoder"""
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.pressure_parser = PressureParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()
        self.remarks_parser = RemarksParser()

    def decode(self, raw_metar: str) -> MetarData:
        """
        Decode a raw METAR string into structured data

        Args:
            raw_metar: The raw METAR string to decode

        Returns:
            MetarData: A structured object containing all decoded METAR components
        """
        metar = raw_metar.strip()
        parts = metar.split()

        # Check for maintenance indicator ($) at end of METAR
        # The $ indicates the station needs maintenance
        maintenance_needed = metar.rstrip().endswith("$") or "$" in parts

        # Remove remarks section from parts to avoid processing remarks as main weather data
        if "RMK" in parts:
            rmk_index = parts.index("RMK")
            parts = parts[:rmk_index]

        # Check for NIL (missing) report
        is_nil = "NIL" in parts
        if is_nil:
            # NIL METAR indicates a missing report
            nil_index = parts.index("NIL")
            parts = parts[:nil_index]  # NIL ends the METAR

        # Extract header information
        metar_type, station_id, observation_time, auto = self._extract_header(parts)

        # Extract main elements
        wind = self._extract_wind(parts)
        visibility = self._extract_visibility(parts)
        # Extract runway state reports BEFORE RVR (they have similar R prefix but different format)
        runway_state_reports = self._extract_runway_state(parts)
        runway_visual_range = self._extract_rvr(parts)
        runway_conditions = []  # Placeholder for future implementation
        weather_groups = self._extract_weather(parts)
        sky_conditions = self._extract_sky_conditions(parts)
        temperature, dewpoint = self._extract_temperature_dewpoint(parts)
        altimeter = self._extract_altimeter(parts)
        windshear = self._extract_windshear(parts)
        trends = self._extract_trends(parts)
        military_color_codes = self._extract_military_color_codes(parts)

        # Extract remarks
        remarks, remarks_decoded = self._extract_remarks(metar)

        return MetarData(
            raw_metar=raw_metar,
            metar_type=metar_type,
            station_id=station_id,
            observation_time=observation_time,
            auto=auto,
            is_nil=is_nil,
            maintenance_needed=maintenance_needed,
            wind=wind or {"direction": 0, "speed": 0, "unit": "KT"},
            visibility=visibility or {"value": 9999, "unit": "M", "is_cavok": False},
            runway_visual_range=runway_visual_range,
            runway_conditions=runway_conditions,
            runway_state_reports=runway_state_reports,
            weather_groups=weather_groups,
            sky_conditions=sky_conditions,
            temperature=temperature or 0.0,
            dewpoint=dewpoint,
            altimeter=altimeter or {"value": 29.92, "unit": "inHg"},
            windshear=windshear,
            trends=trends,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
            military_color_codes=military_color_codes,
        )

    def _extract_header(self, parts: List[str]) -> tuple:
        """Extract METAR header information"""
        metar_type = "METAR"
        station_id = ""
        observation_time = datetime.now(timezone.utc)
        auto = False

        # Extract METAR type
        if parts and COMPILED_PATTERNS["metar_type"].match(parts[0]):
            metar_type = parts.pop(0)

        # Extract station ID
        if parts and COMPILED_PATTERNS["station_id"].match(parts[0]):
            station_id = parts.pop(0)

        # Extract observation time
        if parts and re.match(r"\d{6}Z", parts[0]):
            time_str = parts.pop(0)
            observation_time = self.time_parser.parse_observation_time(time_str) or observation_time

        # Check for AUTO
        if parts and parts[0] == "AUTO":
            auto = True
            parts.pop(0)

        return metar_type, station_id, observation_time, auto

    def _extract_wind(self, parts: List[str]) -> Dict:
        """Extract wind information"""
        return self.wind_parser.extract_wind(parts)

    def _extract_visibility(self, parts: List[str]) -> Dict:
        """Extract visibility information"""
        return self.visibility_parser.extract_visibility(parts)

    def _extract_rvr(self, parts: List[str]) -> List[Dict]:
        """Extract runway visual range information

        RVR format per ICAO: R{runway}/{M|P}{value}{V{M|P}{value}}{FT}{trend}
        - M = less than (Minus/below minimum)
        - P = more than (Plus/above maximum)
        - FT suffix indicates feet (US format), otherwise meters (ICAO default)
        - Trend: U = improving (Up), D = deteriorating (Down), N = no change
        """
        rvr_list = []

        i = 0
        while i < len(parts):
            match = re.match(RVR_PATTERN, parts[i])
            if match:
                runway = match.group(1)
                modifier1 = match.group(2)  # M or P for first value
                is_less_than = modifier1 == "M"
                is_more_than = modifier1 == "P"
                visual_range = int(match.group(3))
                modifier2 = match.group(4)  # M or P for variable value
                variable_less_than = modifier2 == "M" if modifier2 else False
                variable_more_than = modifier2 == "P" if modifier2 else False
                variable_range = int(match.group(5)) if match.group(5) else None
                trend = match.group(6)

                # Determine unit: FT if explicitly stated, otherwise meters (ICAO default)
                unit = "FT" if "FT" in parts[i] else "M"

                rvr = {
                    "runway": runway,
                    "visual_range": visual_range,
                    "unit": unit,
                    "is_less_than": is_less_than,
                    "is_more_than": is_more_than,
                }

                if variable_range:
                    rvr["variable_range"] = variable_range
                    rvr["variable_less_than"] = variable_less_than
                    rvr["variable_more_than"] = variable_more_than

                if trend:
                    rvr["trend"] = RVR_TRENDS.get(trend, trend)

                rvr_list.append(rvr)
                parts.pop(i)
            else:
                i += 1

        return rvr_list

    def _extract_runway_state(self, parts: List[str]) -> List[Dict]:
        """Extract runway state reports (MOTNE format)

        Format: R{runway}/{deposit}{extent}{depth}{braking}
        Example: R23/490156 = Runway 23, dry snow (4), >51% coverage (9), 01mm depth, braking 0.56
        """
        state_list = []

        i = 0
        while i < len(parts):
            match = re.match(RUNWAY_STATE_PATTERN, parts[i])
            if match:
                runway = match.group(1)
                deposit = match.group(2)
                extent = match.group(3)
                depth_raw = match.group(4)
                braking_raw = match.group(5)

                # Decode deposit type
                deposit_desc = RUNWAY_DEPOSIT_TYPES.get(deposit, f"unknown ({deposit})")

                # Decode extent
                extent_desc = RUNWAY_EXTENT.get(extent, f"unknown ({extent})")

                # Decode depth
                if depth_raw == "//":
                    depth_desc = "not reported"
                elif depth_raw == "00":
                    depth_desc = "less than 1mm"
                elif int(depth_raw) <= 90:
                    depth_desc = f"{int(depth_raw)}mm"
                elif depth_raw == "92":
                    depth_desc = "10cm"
                elif depth_raw == "93":
                    depth_desc = "15cm"
                elif depth_raw == "94":
                    depth_desc = "20cm"
                elif depth_raw == "95":
                    depth_desc = "25cm"
                elif depth_raw == "96":
                    depth_desc = "30cm"
                elif depth_raw == "97":
                    depth_desc = "35cm"
                elif depth_raw == "98":
                    depth_desc = "40cm or more"
                elif depth_raw == "99":
                    depth_desc = "runway not operational"
                else:
                    depth_desc = f"unknown ({depth_raw})"

                # Decode braking
                if braking_raw == "//":
                    braking_desc = "not reported"
                elif braking_raw in RUNWAY_BRAKING:
                    braking_desc = RUNWAY_BRAKING[braking_raw]
                else:
                    # Numeric braking coefficient (01-90 = 0.01 to 0.90)
                    try:
                        coef = int(braking_raw) / 100
                        braking_desc = f"coefficient {coef:.2f}"
                    except ValueError:
                        braking_desc = f"unknown ({braking_raw})"

                state_list.append(
                    {
                        "runway": runway,
                        "deposit": deposit_desc,
                        "contamination": extent_desc,
                        "depth": depth_desc,
                        "braking": braking_desc,
                        "raw": parts[i],
                    }
                )

                parts.pop(i)
            else:
                i += 1

        return state_list

    def _extract_weather(self, parts: List[str]) -> List[Dict]:
        """Extract weather phenomena"""
        return self.weather_parser.extract_weather(parts)

    def _extract_sky_conditions(self, parts: List[str]) -> List[Dict]:
        """Extract sky conditions"""
        return self.sky_parser.extract_sky_conditions(parts)

    def _extract_temperature_dewpoint(self, parts: List[str]) -> tuple:
        """Extract temperature and dewpoint"""
        return self.temperature_parser.extract_temperature_dewpoint(parts)

    def _extract_altimeter(self, parts: List[str]) -> Dict:
        """Extract altimeter setting"""
        return self.pressure_parser.extract_altimeter(parts)

    def _extract_windshear(self, parts: List[str]) -> List[Dict]:
        """Extract windshear information

        Formats per ICAO:
        - WS RWY xx: Wind shear on runway xx
        - WS ALL RWY: Wind shear on all runways
        - WS TKOF RWY xx: Wind shear during takeoff on runway xx
        - WS LDG RWY xx: Wind shear during landing on runway xx
        """
        windshear_list = []

        i = 0
        while i < len(parts):
            if parts[i] == "WS":
                ws_parts = [parts.pop(i)]

                # Collect all parts of the wind shear group
                while (
                    i < len(parts)
                    and (
                        parts[i] in ["RWY", "ALL", "TKOF", "LDG"]
                        or re.fullmatch(r"\d{2}[LCR]?", parts[i])
                    )
                ):
                    ws_parts.append(parts.pop(i))

                # Parse the wind shear group
                ws_str = " ".join(ws_parts)
                ws_info = {"raw": ws_str}

                if "ALL" in ws_parts:
                    ws_info["type"] = "all_runways"
                    ws_info["description"] = "Wind shear on all runways"
                elif "TKOF" in ws_parts:
                    ws_info["type"] = "takeoff"
                    # Find runway designator
                    for p in ws_parts:
                        if re.match(r"\d{2}[LCR]?", p):
                            ws_info["runway"] = p
                            break
                    ws_info["description"] = f"Wind shear during takeoff on runway {ws_info.get('runway', 'unknown')}"
                elif "LDG" in ws_parts:
                    ws_info["type"] = "landing"
                    # Find runway designator
                    for p in ws_parts:
                        if re.match(r"\d{2}[LCR]?", p):
                            ws_info["runway"] = p
                            break
                    ws_info["description"] = f"Wind shear during landing on runway {ws_info.get('runway', 'unknown')}"
                else:
                    ws_info["type"] = "runway"
                    # Find runway designator
                    for p in ws_parts:
                        if re.match(r"\d{2}[LCR]?", p):
                            ws_info["runway"] = p
                            break
                    ws_info["description"] = f"Wind shear on runway {ws_info.get('runway', 'unknown')}"

                windshear_list.append(ws_info)
            elif parts[i].startswith("WS") and len(parts[i]) > 2:
                # Handle combined format like "WSRWY26" (less common)
                raw = parts.pop(i)
                ws_info = {"raw": raw, "type": "runway"}

                rwy_match = re.search(r"(\d{2}[LCR]?)", raw)
                if rwy_match:
                    ws_info["runway"] = rwy_match.group(1)
                    ws_info["description"] = f"Wind shear on runway {ws_info['runway']}"
                else:
                    ws_info["description"] = "Wind shear reported"

                windshear_list.append(ws_info)
            else:
                i += 1

        return windshear_list

    def _extract_trends(self, parts: List[str]) -> List[Dict]:
        """Extract and decode trend information

        Trend types:
        - NOSIG: No significant changes expected in next 2 hours
        - BECMG: Becoming - gradual change expected
        - TEMPO: Temporary - fluctuations expected

        Time indicators:
        - FM (FroM): Changes starting from specified time
        - TL (TiLl/unTiL): Changes until specified time
        - AT: Changes at specified time
        """
        trends = []

        i = 0
        while i < len(parts):
            if parts[i] in TREND_TYPES:
                trend_type = parts.pop(i)

                # Handle NOSIG (no significant change)
                if trend_type == "NOSIG":
                    trends.append(
                        {
                            "type": trend_type,
                            "description": "No significant change expected in next 2 hours",
                            "raw": trend_type,
                        }
                    )
                    continue

                # Collect trend elements for BECMG and TEMPO
                trend_elements = []
                time_info = {}
                weather_changes = []

                while i < len(parts) and parts[i] not in TREND_TYPES and not parts[i].startswith("RMK"):
                    element = parts.pop(i)
                    trend_elements.append(element)

                    # Parse time indicators
                    if element.startswith("FM"):
                        time_match = re.match(r"FM(\d{4})", element)
                        if time_match:
                            time_val = time_match.group(1)
                            time_info["from"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                    elif element.startswith("TL"):
                        time_match = re.match(r"TL(\d{4})", element)
                        if time_match:
                            time_val = time_match.group(1)
                            time_info["until"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                    elif element.startswith("AT"):
                        time_match = re.match(r"AT(\d{4})", element)
                        if time_match:
                            time_val = time_match.group(1)
                            time_info["at"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                    # Parse visibility changes (4-digit number)
                    elif element.isdigit() and len(element) == 4:
                        vis_value = int(element)
                        if vis_value == 9999:
                            weather_changes.append("visibility 10km or more")
                        elif vis_value >= 1000:
                            weather_changes.append(f"visibility {vis_value/1000:.1f}km")
                        else:
                            weather_changes.append(f"visibility {vis_value}m")
                    # Parse wind changes
                    elif re.match(r"(\d{3}|VRB)\d{2,3}(G\d{2,3})?(KT|MPS|KMH)", element):
                        wind_info = self.wind_parser.parse_wind_string(element)
                        if wind_info:
                            dir_text = "variable" if wind_info["direction"] == "VRB" else f"{wind_info['direction']}°"
                            wind_desc = f"wind {dir_text} at {wind_info['speed']} {wind_info['unit']}"
                            if wind_info.get("gust"):
                                wind_desc += f" gusting {wind_info['gust']}"
                            weather_changes.append(wind_desc)
                    # Parse cloud changes
                    elif re.match(r"(SKC|CLR|NSC|NCD|FEW|SCT|BKN|OVC|VV)(\d{3}|///)?", element):
                        sky_info = self.sky_parser.parse_sky_string(element)
                        if sky_info:
                            if sky_info["type"] in ["SKC", "CLR"]:
                                weather_changes.append("sky clear")
                            elif sky_info["type"] == "NSC":
                                weather_changes.append("no significant cloud")
                            elif sky_info["type"] == "NCD":
                                weather_changes.append("no cloud detected")
                            elif sky_info["type"] == "VV":
                                if sky_info.get("unknown_height") or sky_info["height"] is None:
                                    weather_changes.append("vertical visibility unknown")
                                else:
                                    weather_changes.append(f"vertical visibility {sky_info['height']}ft")
                            else:
                                cloud_desc = f"{sky_info['type']} at {sky_info['height']}ft"
                                if sky_info.get("cb"):
                                    cloud_desc += " CB"
                                elif sky_info.get("tcu"):
                                    cloud_desc += " TCU"
                                weather_changes.append(cloud_desc)
                    # Parse weather phenomena
                    elif re.match(
                        r"^[-+]?(VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+",
                        element,
                    ):
                        wx_info = self.weather_parser.parse_weather_string(element)
                        if wx_info:
                            wx_parts = []
                            if wx_info.get("intensity"):
                                wx_parts.append(wx_info["intensity"])
                            if wx_info.get("descriptor"):
                                wx_parts.append(wx_info["descriptor"])
                            if wx_info.get("phenomena"):
                                wx_parts.extend(wx_info["phenomena"])
                            if wx_parts:
                                weather_changes.append(" ".join(wx_parts))
                    # NSW = No Significant Weather
                    elif element == "NSW":
                        weather_changes.append("no significant weather")
                    # CAVOK
                    elif element == "CAVOK":
                        weather_changes.append("CAVOK")

                # Build description
                description_parts = []

                if trend_type == "BECMG":
                    description_parts.append("Becoming")
                elif trend_type == "TEMPO":
                    description_parts.append("Temporary")

                # Add time info
                if time_info.get("from") and time_info.get("until"):
                    description_parts.append(f"from {time_info['from']} until {time_info['until']}:")
                elif time_info.get("from"):
                    description_parts.append(f"from {time_info['from']}:")
                elif time_info.get("until"):
                    description_parts.append(f"until {time_info['until']}:")
                elif time_info.get("at"):
                    description_parts.append(f"at {time_info['at']}:")
                else:
                    description_parts.append("-")

                # Add weather changes
                if weather_changes:
                    description_parts.append(", ".join(weather_changes))

                trends.append(
                    {
                        "type": trend_type,
                        "raw": f"{trend_type} {' '.join(trend_elements)}" if trend_elements else trend_type,
                        "time": time_info if time_info else None,
                        "changes": weather_changes if weather_changes else None,
                        "description": " ".join(description_parts),
                    }
                )
            else:
                i += 1

        return trends

    def _extract_military_color_codes(self, parts: List[str]) -> List[Dict]:
        """Extract military color codes"""
        color_codes = []

        i = 0
        while i < len(parts):
            if parts[i] in MILITARY_COLOR_CODES:
                code = parts.pop(i)
                color_codes.append({"code": code, "description": MILITARY_COLOR_CODES[code]})
            else:
                i += 1

        return color_codes

    def _extract_remarks(self, metar: str) -> tuple:
        """Extract and decode remarks section

        Delegates to RemarksParser for all remarks parsing logic.
        """
        return self.remarks_parser.parse(metar)
