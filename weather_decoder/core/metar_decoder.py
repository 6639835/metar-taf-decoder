"""Main METAR decoder that orchestrates parsing"""

import re
from datetime import datetime, timezone
from typing import Dict, List

from ..data.metar_data import MetarData
from ..parsers.pressure_parser import PressureParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..utils.constants import MILITARY_COLOR_CODES, RUNWAY_BRAKING, RUNWAY_DEPOSIT_TYPES, RUNWAY_EXTENT, TREND_TYPES
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
                    trend_map = {"U": "improving", "D": "deteriorating", "N": "no change"}
                    rvr["trend"] = trend_map.get(trend, trend)

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
                    and parts[i] in ["RWY", "ALL", "TKOF", "LDG"]
                    or (i < len(parts) and re.match(r"\d{2}[LCR]?", parts[i]))
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
                    elif re.match(r"(SKC|CLR|NSC|NCD|FEW|SCT|BKN|OVC|VV)\d{0,3}", element):
                        sky_info = self.sky_parser.parse_sky_string(element)
                        if sky_info:
                            if sky_info["type"] in ["SKC", "CLR"]:
                                weather_changes.append("sky clear")
                            elif sky_info["type"] == "NSC":
                                weather_changes.append("no significant cloud")
                            elif sky_info["type"] == "NCD":
                                weather_changes.append("no cloud detected")
                            elif sky_info["type"] == "VV":
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
                        r"^[-+]?VC?(MI|PR|BC|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+",
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
        """Extract and decode remarks section"""
        match = re.search(r"RMK\s+(.+)$", metar)
        if match:
            remarks = match.group(1)

            # Track positions for each decoded key to sort by original order
            # Format: {key: position_in_remarks}
            positions = {}

            # Basic remarks decoding
            decoded = {}

            # Check for common patterns
            ao2_pos = remarks.find("AO2")
            ao1_pos = remarks.find("AO1")
            if ao2_pos >= 0:
                decoded["Station Type"] = "Automated station with precipitation discriminator"
                positions["Station Type"] = ao2_pos
            elif ao1_pos >= 0:
                decoded["Station Type"] = "Automated station without precipitation discriminator"
                positions["Station Type"] = ao1_pos

            # Wind information in remarks (US format: WIND location dddssKT)
            wind_patterns = re.findall(r"WIND\s+(\w+)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", remarks)
            if wind_patterns:
                decoded["runway_winds"] = []
                for pattern in wind_patterns:
                    location, direction, speed, gust = pattern
                    wind_info = {"runway": location, "direction": int(direction), "speed": int(speed), "unit": "KT"}
                    if gust:
                        wind_info["gust"] = int(gust)
                    decoded["runway_winds"].append(wind_info)

            # Runway-specific winds (ICAO/European format: RWYxx dddssKT [dddVddd])
            # e.g., RWY17L 23006KT, RWY05 24005KT 210V270
            rwy_wind_patterns = re.findall(
                r"RWY(\d{2}[LCR]?)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT(?:\s+(\d{3})V(\d{3}))?", remarks
            )
            if rwy_wind_patterns:
                if "runway_winds" not in decoded:
                    decoded["runway_winds"] = []
                for pattern in rwy_wind_patterns:
                    runway, direction, speed, gust, var_from, var_to = pattern
                    wind_info = {"runway": runway, "direction": int(direction), "speed": int(speed), "unit": "KT"}
                    if gust:
                        wind_info["gust"] = int(gust)
                    if var_from and var_to:
                        wind_info["variable_direction"] = [int(var_from), int(var_to)]
                    decoded["runway_winds"].append(wind_info)

            # Sea Level Pressure (SLP)
            slp_match = re.search(r"SLP(\d{3})", remarks)
            if slp_match:
                slp = int(slp_match.group(1))
                # North American format: add decimal point (e.g., 095 -> 1009.5, 200 -> 1020.0)
                if slp < 500:
                    pressure = 1000 + slp / 10
                else:
                    pressure = 900 + slp / 10

                decoded["Sea Level Pressure"] = f"{pressure:.1f} hPa"

            # Pressure tendency (5appp format)
            # 5 = group identifier
            # a = pressure characteristic (0-8)
            # ppp = pressure change in tenths of hPa
            pressure_tendency_match = re.search(r"(?<!\d)5([0-8])(\d{3})(?!\d)", remarks)
            if pressure_tendency_match:
                characteristic = int(pressure_tendency_match.group(1))
                change_tenths = int(pressure_tendency_match.group(2))
                change_hpa = change_tenths / 10

                char_descriptions = {
                    0: "Increasing, then decreasing",
                    1: "Increasing, then steady; or increasing then increasing more slowly",
                    2: "Increasing steadily or unsteadily",
                    3: "Decreasing or steady, then increasing; or increasing then increasing more rapidly",
                    4: "Steady",
                    5: "Decreasing, then increasing",
                    6: "Decreasing, then steady; or decreasing then decreasing more slowly",
                    7: "Decreasing steadily or unsteadily",
                    8: "Steady or increasing, then decreasing; or decreasing then decreasing more rapidly",
                }

                char_desc = char_descriptions.get(characteristic, f"Unknown ({characteristic})")
                decoded["Pressure Tendency"] = f"{char_desc}; change: {change_hpa:.1f} hPa"

            # Temperature/dewpoint to tenths
            temp_match = re.search(r"T([01])(\d{3})([01])(\d{3})", remarks)
            if temp_match:
                temp_sign = -1 if temp_match.group(1) == "1" else 1
                temp_tenths = int(temp_match.group(2))
                dew_sign = -1 if temp_match.group(3) == "1" else 1
                dew_tenths = int(temp_match.group(4))

                decoded["Temperature (tenths)"] = f"{temp_sign * temp_tenths / 10:.1f}°C"
                decoded["Dewpoint (tenths)"] = f"{dew_sign * dew_tenths / 10:.1f}°C"

            # 24-hour temperature extremes (4snTTTsnTTT format)
            # Must be a standalone 9-digit code starting with 4, with word boundaries
            temp_extremes_match = re.search(r"(?<!\d)4([01])(\d{3})([01])(\d{3})(?!\d)", remarks)
            if temp_extremes_match:
                max_sign = -1 if temp_extremes_match.group(1) == "1" else 1
                max_temp_tenths = int(temp_extremes_match.group(2))
                min_sign = -1 if temp_extremes_match.group(3) == "1" else 1
                min_temp_tenths = int(temp_extremes_match.group(4))

                max_temp = max_sign * max_temp_tenths / 10
                min_temp = min_sign * min_temp_tenths / 10

                decoded["24-Hour Maximum Temperature"] = f"{max_temp:.1f}°C"
                decoded["24-Hour Minimum Temperature"] = f"{min_temp:.1f}°C"

            # 6-hour maximum temperature (1snTTT format)
            # e.g., 10161 = +16.1°C max temp
            max_temp_6hr_match = re.search(r"(?<!\d)1([01])(\d{3})(?!\d)", remarks)
            if max_temp_6hr_match:
                sign = -1 if max_temp_6hr_match.group(1) == "1" else 1
                temp_tenths = int(max_temp_6hr_match.group(2))
                temp_value = sign * temp_tenths / 10
                decoded["6-Hour Maximum Temperature"] = f"{temp_value:.1f}°C"

            # 6-hour minimum temperature (2snTTT format)
            # e.g., 20056 = +5.6°C min temp
            min_temp_6hr_match = re.search(r"(?<!\d)2([01])(\d{3})(?!\d)", remarks)
            if min_temp_6hr_match:
                sign = -1 if min_temp_6hr_match.group(1) == "1" else 1
                temp_tenths = int(min_temp_6hr_match.group(2))
                temp_value = sign * temp_tenths / 10
                decoded["6-Hour Minimum Temperature"] = f"{temp_value:.1f}°C"

            # 6-hour precipitation (6xxxx format)
            # e.g., 60000 = trace or no precipitation, 60015 = 0.15 inches
            precip_6hr_match = re.search(r"(?<!\d)6(\d{4})(?!\d)", remarks)
            if precip_6hr_match:
                precip_hundredths = int(precip_6hr_match.group(1))
                if precip_hundredths == 0:
                    decoded["6-Hour Precipitation"] = "Trace or none"
                else:
                    precip_inches = precip_hundredths / 100.0
                    decoded["6-Hour Precipitation"] = f"{precip_inches:.2f} inches"

            # Variable visibility (VIS)
            vis_match = re.search(r"VIS\s+(\d+(?:/\d+)?)V(\d+(?:/\d+)?)", remarks)
            if vis_match:
                min_vis_str = vis_match.group(1)
                max_vis_str = vis_match.group(2)

                # Parse fractions
                def parse_visibility_fraction(vis_str):
                    if "/" in vis_str:
                        num, den = vis_str.split("/")
                        return float(num) / float(den)
                    else:
                        return float(vis_str)

                min_vis = parse_visibility_fraction(min_vis_str)
                max_vis = parse_visibility_fraction(max_vis_str)

                if min_vis == int(min_vis):
                    min_vis_display = str(int(min_vis))
                else:
                    min_vis_display = min_vis_str

                if max_vis == int(max_vis):
                    max_vis_display = str(int(max_vis))
                else:
                    max_vis_display = max_vis_str

                decoded["Variable Visibility"] = f"{min_vis_display} to {max_vis_display} statute miles"

            # Past weather (RAB11E24, SNB05E15, etc.)
            # Handle combined begin/end patterns like RAB11E24
            # Valid weather codes for past weather: RA, SN, DZ, TS, PL, GR, GS, UP, FG, BR, etc.
            VALID_PAST_WEATHER_CODES = {
                "RA",
                "SN",
                "DZ",
                "TS",
                "PL",
                "GR",
                "GS",
                "UP",
                "FG",
                "BR",
                "FU",
                "VA",
                "DU",
                "SA",
                "HZ",
                "SQ",
                "FC",
                "SS",
                "DS",
            }

            combined_weather_matches = re.findall(r"([A-Z]{2})B(\d{2})E(\d{2})", remarks)
            individual_weather_matches = re.findall(r"([A-Z]{2})([BE])(\d{2})(?![BE\d])", remarks)

            past_weather_events = []

            # Process combined begin/end patterns (e.g., RAB11E24)
            for weather_code, begin_time, end_time in combined_weather_matches:
                # Only process valid weather codes (exclude QFE, QNH, etc.)
                if weather_code not in VALID_PAST_WEATHER_CODES:
                    continue

                if weather_code == "RA":
                    weather_type = "rain"
                elif weather_code == "SN":
                    weather_type = "snow"
                elif weather_code == "DZ":
                    weather_type = "drizzle"
                elif weather_code == "TS":
                    weather_type = "thunderstorm"
                else:
                    weather_type = weather_code.lower()

                past_weather_events.append(f"{weather_type} began at minute {begin_time}, ended at minute {end_time}")

            # Process individual begin/end patterns (e.g., RAB15, RAE20)
            for weather_code, begin_end, time_minutes in individual_weather_matches:
                # Only process valid weather codes (exclude QFE, QNH, etc.)
                if weather_code not in VALID_PAST_WEATHER_CODES:
                    continue

                if weather_code == "RA":
                    weather_type = "rain"
                elif weather_code == "SN":
                    weather_type = "snow"
                elif weather_code == "DZ":
                    weather_type = "drizzle"
                elif weather_code == "TS":
                    weather_type = "thunderstorm"
                else:
                    weather_type = weather_code.lower()

                action = "began" if begin_end == "B" else "ended"
                past_weather_events.append(f"{weather_type} {action} at minute {time_minutes}")

            if past_weather_events:
                decoded["Past Weather"] = ", ".join(past_weather_events)

            # QFE (field elevation pressure) in remarks
            qfe_match = re.search(r"QFE(\d{3,4})", remarks)
            if qfe_match:
                qfe_value = int(qfe_match.group(1))
                decoded["QFE"] = f"{qfe_value} hPa"

            # Altimeter setting in remarks (US format: A followed by 4 digits)
            # e.g., A3001 = 30.01 inHg, A2992 = 29.92 inHg
            # This is often included in Japanese METARs alongside Q (hPa) setting
            altimeter_rmk_match = re.search(r"\bA(\d{4})\b", remarks)
            if altimeter_rmk_match:
                alt_value = int(altimeter_rmk_match.group(1))
                alt_inhg = alt_value / 100
                decoded["Altimeter (Remarks)"] = f"{alt_inhg:.2f} inHg"

            # Precipitation amount (P0000, P0001, etc.)
            precip_match = re.search(r"P(\d{4})", remarks)
            if precip_match:
                precip_hundredths = int(precip_match.group(1))
                if precip_hundredths == 0:
                    decoded["Precipitation Amount"] = "Less than 0.01 inches"
                else:
                    precip_inches = precip_hundredths / 100.0
                    decoded["Precipitation Amount"] = f"{precip_inches:.2f} inches"

            # Peak Wind (PK WND dddss/hhmm or PK WND dddss(s)/hhmm)
            # e.g., PK WND 28032/1420 = peak wind 280° at 32 KT at 14:20 UTC
            pk_wnd_match = re.search(r"PK\s+WND\s+(\d{3})(\d{2,3})/(\d{2})(\d{2})", remarks)
            if pk_wnd_match:
                pk_direction = int(pk_wnd_match.group(1))
                pk_speed = int(pk_wnd_match.group(2))
                pk_hour = pk_wnd_match.group(3)
                pk_minute = pk_wnd_match.group(4)
                decoded["Peak Wind"] = f"{pk_direction}° at {pk_speed} KT at {pk_hour}:{pk_minute} UTC"

            # Surface Visibility (SFC VIS vv)
            # e.g., SFC VIS 10 = surface visibility 10 statute miles
            sfc_vis_match = re.search(r"SFC\s+VIS\s+(\d+(?:/\d+)?)", remarks)
            if sfc_vis_match:
                sfc_vis_str = sfc_vis_match.group(1)
                if "/" in sfc_vis_str:
                    # Fractional visibility
                    decoded["Surface Visibility"] = f"{sfc_vis_str} SM"
                else:
                    decoded["Surface Visibility"] = f"{sfc_vis_str} SM"

            # Tower Visibility (TWR VIS vv)
            twr_vis_match = re.search(r"TWR\s+VIS\s+(\d+(?:/\d+)?)", remarks)
            if twr_vis_match:
                twr_vis_str = twr_vis_match.group(1)
                decoded["Tower Visibility"] = f"{twr_vis_str} SM"

            # Lightning (LTG) information
            # Format: [FRQ|OCNL|CONS] LTG[IC|CC|CG|CA]+ [DSNT|VC|OHD]? [directions]
            # IC = in-cloud, CC = cloud-to-cloud, CG = cloud-to-ground, CA = cloud-to-air
            # FRQ = frequent (>6/min), OCNL = occasional (1-6/min), CONS = continuous
            # DSNT = distant (10-30 NM), VC = vicinity (5-10 NM), OHD = overhead
            # Direction patterns: N, NE, E, SE, S, SW, W, NW or ranges like E-SE
            ltg_match = re.search(
                r"(FRQ|OCNL|CONS)?\s*LTG((?:IC|CC|CG|CA)+)\s*(DSNT|VC|OHD|ALQDS)?\s*((?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)?(?=\s|$)",
                remarks,
            )
            if ltg_match:
                ltg_parts = []

                # Frequency
                freq = ltg_match.group(1)
                freq_map = {
                    "FRQ": "frequent (more than 6 per minute)",
                    "OCNL": "occasional (1-6 per minute)",
                    "CONS": "continuous",
                }
                if freq:
                    ltg_parts.append(freq_map.get(freq, freq))

                # Lightning types
                ltg_types = ltg_match.group(2)
                type_map = {"IC": "in-cloud", "CC": "cloud-to-cloud", "CG": "cloud-to-ground", "CA": "cloud-to-air"}
                types = []
                for i in range(0, len(ltg_types), 2):
                    lt = ltg_types[i : i + 2]
                    types.append(type_map.get(lt, lt))
                ltg_parts.append(" and ".join(types) + " lightning")

                # Location
                location = ltg_match.group(3)
                loc_map = {
                    "DSNT": "distant (10-30 NM)",
                    "VC": "in vicinity (5-10 NM)",
                    "OHD": "overhead",
                    "ALQDS": "all quadrants",
                }
                if location and location != "AND":
                    ltg_parts.append(loc_map.get(location, location))

                # Direction
                direction = ltg_match.group(4)
                if direction:
                    # Clean up direction string
                    direction = direction.replace("DSNT", "").strip()
                    direction = direction.replace("AND", "and")
                    dir_map = {
                        "NE": "northeast",
                        "NW": "northwest",
                        "SE": "southeast",
                        "SW": "southwest",
                        "N": "north",
                        "E": "east",
                        "S": "south",
                        "W": "west",
                    }
                    # Handle direction ranges like E-SE (east to southeast)
                    # Replace longer abbreviations first to avoid partial matches
                    for abbr, full in dir_map.items():
                        direction = direction.replace(abbr, full)
                    # Convert hyphen to "to" for ranges
                    direction = direction.replace("-", " to ")
                    ltg_parts.append(f"to the {direction}")

                decoded["Lightning"] = " ".join(ltg_parts)

            # VIRGA (precipitation not reaching ground)
            # Format: VIRGA [DSNT|VC] [directions]
            virga_match = re.search(
                r"VIRGA\s*(DSNT|VC)?\s*((?:(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)?",
                remarks,
            )
            if virga_match:
                virga_parts = ["Virga (precipitation not reaching ground)"]
                location = virga_match.group(1)
                direction = virga_match.group(2)

                if location:
                    loc_map = {"DSNT": "distant", "VC": "in vicinity"}
                    virga_parts.append(loc_map.get(location, location))

                if direction:
                    dir_map = {
                        "NE": "northeast",
                        "NW": "northwest",
                        "SE": "southeast",
                        "SW": "southwest",
                        "N": "north",
                        "E": "east",
                        "S": "south",
                        "W": "west",
                    }
                    dir_text = direction
                    for abbr, full in dir_map.items():
                        dir_text = dir_text.replace(abbr, full)
                    dir_text = dir_text.replace("-", " to ").replace("AND", "and")
                    virga_parts.append(f"to the {dir_text}")

                decoded["Virga"] = " ".join(virga_parts)

            # ACSL (Altocumulus Standing Lenticular) clouds
            # Format: ACSL [DSNT|VC|OHD] [direction] [MOV direction]
            acsl_match = re.search(
                r"ACSL\s*(DSNT|VC|OHD)?\s*([NSEW]+(?:-[NSEW]+)?)?\s*(?:MOV\s+([NSEW]+(?:-[NSEW]+)?))?", remarks
            )
            if acsl_match:
                acsl_parts = ["Altocumulus Standing Lenticular clouds"]
                location = acsl_match.group(1)
                direction = acsl_match.group(2)
                movement = acsl_match.group(3)

                if location:
                    loc_map = {"DSNT": "distant", "VC": "in vicinity", "OHD": "overhead"}
                    acsl_parts.append(loc_map.get(location, location))

                if direction:
                    dir_map = {
                        "NE": "northeast",
                        "NW": "northwest",
                        "SE": "southeast",
                        "SW": "southwest",
                        "N": "north",
                        "E": "east",
                        "S": "south",
                        "W": "west",
                    }
                    dir_text = direction
                    for abbr, full in dir_map.items():
                        dir_text = dir_text.replace(abbr, full)
                    dir_text = dir_text.replace("-", " to ")
                    acsl_parts.append(f"to the {dir_text}")

                if movement:
                    mov_text = movement
                    for abbr, full in dir_map.items():
                        mov_text = mov_text.replace(abbr, full)
                    mov_text = mov_text.replace("-", " to ")
                    acsl_parts.append(f"moving {mov_text}")

                decoded["ACSL"] = " ".join(acsl_parts)

            # Cloud type codes in remarks (Canadian/ICAO format)
            # Format: XX# where XX is cloud type abbreviation and # is oktas (1-8)
            # SC = Stratocumulus, ST = Stratus, CU = Cumulus, CB = Cumulonimbus
            # CI = Cirrus, CS = Cirrostratus, CC = Cirrocumulus
            # AC = Altocumulus, AS = Altostratus, NS = Nimbostratus, TCU = Towering Cumulus
            cloud_type_codes = {
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
                "TCU": "Towering Cumulus",
                "CF": "Cumulus Fractus",
                "SF": "Stratus Fractus",
            }

            cloud_types_found = []

            # Japanese/ICAO format: {oktas}{cloud_type}{height} e.g., 1CU007, 3SC015
            # oktas first, then cloud type, then height in hundreds of feet
            japan_cloud_matches = re.findall(r"\b(\d)(TCU|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d{3})\b", remarks)
            for oktas, cloud_code, height in japan_cloud_matches:
                cloud_name = cloud_type_codes.get(cloud_code, cloud_code)
                height_ft = int(height) * 100
                cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage at {height_ft} feet")

            # Canadian format: {cloud_type}{oktas} e.g., SC6, AC3, CB8, TCU4
            # Cloud codes can be concatenated without spaces (e.g., CU1AC1AC1CI1)
            # Use negative lookahead to ensure the digit is NOT followed by 2 more digits (which would be Japanese format)
            if not japan_cloud_matches:
                cloud_type_matches = re.findall(r"(TCU|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d)(?!\d{2})", remarks)
                for cloud_code, oktas in cloud_type_matches:
                    cloud_name = cloud_type_codes.get(cloud_code, cloud_code)
                    cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage")

            # Match trace cloud patterns like "AC TR", "CI TR", etc.
            # TR = trace amount (less than 1/8 sky coverage)
            trace_cloud_matches = re.findall(r"\b(TCU|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)\s+TR\b", remarks)
            for cloud_code in trace_cloud_matches:
                cloud_name = cloud_type_codes.get(cloud_code, cloud_code)
                cloud_types_found.append(f"{cloud_name} trace (less than 1/8 sky coverage)")

            if cloud_types_found:
                decoded["Cloud Types"] = "; ".join(cloud_types_found)

            # Density Altitude (Canadian remarks)
            # Format: DENSITY ALT -1792FT or DENSITY ALT 2500FT
            density_alt_match = re.search(r"DENSITY\s+ALT\s+(-?\d+)FT", remarks)
            if density_alt_match:
                density_alt = int(density_alt_match.group(1))
                decoded["Density Altitude"] = f"{density_alt} feet"

            # Obscuration remarks (MT OBSC, RWYXX OBSC, etc.)
            # MT OBSC = Mountains obscured
            if re.search(r"\bMT\s+OBSC\b", remarks):
                decoded["Obscuration"] = "Mountains obscured"
            elif re.search(r"\bMTN\s+OBSC\b", remarks):
                decoded["Obscuration"] = "Mountain obscured"
            elif re.search(r"\bMTNS\s+OBSC\b", remarks):
                decoded["Obscuration"] = "Mountains obscured"

            # CIG (ceiling) remarks
            # CIG xxx = Ceiling at xxx (variable ceiling)
            cig_match = re.search(r"\bCIG\s+(\d{3})(?:V(\d{3}))?", remarks)
            if cig_match:
                cig_low = int(cig_match.group(1)) * 100
                if cig_match.group(2):
                    cig_high = int(cig_match.group(2)) * 100
                    decoded["variable_ceiling"] = f"{cig_low} to {cig_high} feet"
                else:
                    decoded["Ceiling"] = f"{cig_low} feet"

            # PRESFR / PRESRR - Pressure falling/rising rapidly
            if "PRESFR" in remarks:
                decoded["Pressure Change"] = "Pressure falling rapidly"
            elif "PRESRR" in remarks:
                decoded["Pressure Change"] = "Pressure rising rapidly"

            # FROPA - Frontal passage
            if "FROPA" in remarks:
                decoded["Frontal Passage"] = "Frontal passage"

            # WSHFT - Wind shift
            wshft_match = re.search(r"WSHFT\s+(\d{2})(\d{2})", remarks)
            if wshft_match:
                wshft_hour = wshft_match.group(1)
                wshft_min = wshft_match.group(2)
                decoded["wind_shift"] = {"time": f"{wshft_hour}:{wshft_min} UTC"}

            # SLPNO - Sea level pressure not available
            if "SLPNO" in remarks:
                decoded["SLP Status"] = "Sea level pressure not available"

            # RVRNO - RVR not available
            if "RVRNO" in remarks:
                decoded["RVR Status"] = "Runway visual range not available"

            # Runway state in remarks (8-group format: 8RDEddBB)
            # 8 = group identifier
            # R = runway designator (0-9, where 5=left, 6-8 reserved, 9=right for parallel runways)
            # D = deposit type (0-9)
            # E = extent of contamination (1,2,5,9)
            # dd = depth of deposit (00-99)
            # BB = braking action/friction coefficient (00-99)
            runway_state_rmk_match = re.search(r"(?<!\d)8(\d)(\d)(\d)(\d{2})(\d{2})(?!\d)", remarks)
            if runway_state_rmk_match:
                runway_digit = runway_state_rmk_match.group(1)
                deposit = runway_state_rmk_match.group(2)
                extent = runway_state_rmk_match.group(3)
                depth_raw = runway_state_rmk_match.group(4)
                braking_raw = runway_state_rmk_match.group(5)

                # Decode runway - the digit after 8 represents the runway
                # Format varies: 83 could mean runway 33 (digit doubled) or runway 3x series
                # Using best interpretation based on context
                runway_num = int(runway_digit)
                if runway_num <= 3:
                    # For digits 0-3, likely runway XX where XX = digit * 11 (e.g., 3 -> 33)
                    runway_desc = f"Runway {runway_num}{runway_num}"
                else:
                    # For higher digits, show as tens digit
                    runway_desc = f"Runway {runway_num}x"

                # Deposit types
                deposit_types = {
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
                deposit_desc = deposit_types.get(deposit, f"Unknown ({deposit})")

                # Extent of contamination
                extent_types = {
                    "1": "10% or less",
                    "2": "11% to 25%",
                    "5": "26% to 50%",
                    "9": "51% to 100%",
                    "/": "Not reported",
                }
                extent_desc = extent_types.get(extent, f"Unknown ({extent})")

                # Depth of deposit
                depth_val = int(depth_raw)
                if depth_val == 0:
                    depth_desc = "Less than 1mm"
                elif depth_val <= 90:
                    depth_desc = f"{depth_val}mm"
                elif depth_val == 92:
                    depth_desc = "10cm"
                elif depth_val == 93:
                    depth_desc = "15cm"
                elif depth_val == 94:
                    depth_desc = "20cm"
                elif depth_val == 95:
                    depth_desc = "25cm"
                elif depth_val == 96:
                    depth_desc = "30cm"
                elif depth_val == 97:
                    depth_desc = "35cm"
                elif depth_val == 98:
                    depth_desc = "40cm or more"
                elif depth_val == 99:
                    depth_desc = "Runway not operational"
                else:
                    depth_desc = f"{depth_val}mm"

                # Braking action
                braking_val = int(braking_raw)
                if braking_val >= 91 and braking_val <= 95:
                    braking_map = {91: "Poor", 92: "Medium/Poor", 93: "Medium", 94: "Medium/Good", 95: "Good"}
                    braking_desc = braking_map.get(braking_val, f"Coefficient 0.{braking_raw}")
                elif braking_val == 99:
                    braking_desc = "Unreliable"
                else:
                    braking_desc = f"Friction coefficient 0.{braking_raw}"

                decoded[
                    "Runway State (Remarks)"
                ] = f"{runway_desc}: {deposit_desc}, {extent_desc} coverage, depth {depth_desc}, braking {braking_desc}"

            # Sensor status indicators
            sensor_status = []
            if "PWINO" in remarks:
                sensor_status.append("Present Weather Identifier not operational")
            if "TSNO" in remarks:
                sensor_status.append("Thunderstorm sensor not operational")
            if "FZRANO" in remarks:
                sensor_status.append("Freezing rain sensor not operational")
            if "PNO" in remarks:
                sensor_status.append("Precipitation sensor not operational")
            if "VISNO" in remarks:
                sensor_status.append("Visibility sensor not operational")
            if "CHINO" in remarks:
                sensor_status.append("Ceiling height indicator not operational")
            if "RVRNO" in remarks:
                sensor_status.append("RVR sensor not operational")

            if sensor_status:
                decoded["Sensor Status"] = "; ".join(sensor_status)

            # Check for maintenance indicator ($) in remarks - add at end
            if "$" in remarks:
                decoded["Maintenance Indicator"] = "Station requires maintenance"
                positions["Maintenance Indicator"] = remarks.find("$")

            # Sort decoded dictionary by position in original remarks string
            # Map keys to their search patterns for position finding
            key_patterns = {
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
                "Past Weather": ["B", "E"],
                "QFE": ["QFE"],
                "Precipitation Amount": [r"P\d{4}"],
                "Peak Wind": ["PK WND"],
                "Surface Visibility": ["SFC VIS"],
                "Tower Visibility": ["TWR VIS"],
                "Lightning": ["LTG"],
                "Virga": ["VIRGA"],
                "ACSL": ["ACSL"],
                "Cloud Types": ["SC", "AC", "ST", "CU", "CB", "CI", "AS", "NS", "TCU", "CC", "CS"],
                "Density Altitude": ["DENSITY ALT"],
                "Obscuration": ["OBSC"],
                "Ceiling": ["CIG"],
                "variable_ceiling": ["CIG"],
                "Pressure Change": ["PRESFR", "PRESRR"],
                "Frontal Passage": ["FROPA"],
                "wind_shift": ["WSHFT"],
                "SLP Status": ["SLPNO"],
                "RVR Status": ["RVRNO"],
                "Runway State (Remarks)": [r"8\d{7}"],
                "Sensor Status": ["PWINO", "TSNO", "FZRANO", "PNO", "VISNO", "CHINO", "RVRNO"],
                "Maintenance Indicator": ["$"],
                "runway_winds": ["RWY", "WIND"],
            }

            # Find positions for keys not already tracked
            for key in decoded:
                if key not in positions:
                    patterns = key_patterns.get(key, [])
                    min_pos = len(remarks)  # Default to end
                    for pattern in patterns:
                        if pattern.startswith(r"") or any(c in pattern for c in r"\d[]{}+*?"):
                            # It's a regex pattern
                            match = re.search(pattern, remarks)
                            if match:
                                min_pos = min(min_pos, match.start())
                        else:
                            # It's a literal string
                            pos = remarks.find(pattern)
                            if pos >= 0:
                                min_pos = min(min_pos, pos)
                    positions[key] = min_pos

            # Sort decoded dict by position
            sorted_decoded = dict(sorted(decoded.items(), key=lambda x: positions.get(x[0], len(remarks))))

            return remarks, sorted_decoded
        else:
            return "", {}
