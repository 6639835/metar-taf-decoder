"""Remarks section parser for METAR reports

This module handles parsing of the RMK (remarks) section in METAR reports.
The remarks section contains supplementary information not included in the
main body of the report.
"""

import re
from typing import Dict, List, Optional, Tuple

from ..constants import (
    CLOUD_TYPE_CODES,
    DIRECTION_ABBREV,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    LOCATION_INDICATORS,
    MAINTENANCE_INDICATOR,
    PRESSURE_TENDENCY_CHARACTERISTICS,
    RUNWAY_BRAKING_REMARKS,
    RUNWAY_DEPTH_SPECIAL,
    RUNWAY_STATE_DEPOSIT_TYPES_REMARKS,
    RUNWAY_STATE_EXTENT_REMARKS,
    SENSOR_STATUS,
    STATION_TYPES,
    WEATHER_DESCRIPTORS,
    WEATHER_PHENOMENA,
)


class RemarksParser:
    """Parser for METAR remarks section

    The remarks section (RMK) contains supplementary weather information
    including precise temperature readings, pressure data, precipitation
    amounts, and various observational notes.
    """

    def __init__(self):
        """Initialize the remarks parser"""
        # Mapping of decoded keys to their search patterns for position tracking
        self._key_patterns = {
            # Prefer AO2 over AO1 when both appear
            "Station Type": ["A02A", "AO2", "AO1", "A02", "A01"],
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
            "Lightning": ["LTG"],
            "Virga": ["VIRGA"],
            "Thunderstorm Location": ["TS OHD", "TS DSNT", "TS VC", "TS ALQDS", "TS MOV"],
            "ACSL": ["ACSL"],
            "Cloud Types": ["SC", "AC", "ST", "CU", "CB", "CI", "AS", "NS", "SN", "TCU", "CC", "CS"],
            "Density Altitude": ["DENSITY ALT"],
            "Obscuration": ["OBSC"],
            "QBB": ["QBB"],
            "Ceiling": ["CIG"],
            "variable_ceiling": ["CIG"],
            "Pressure Change": ["PRESFR", "PRESRR"],
            "Frontal Passage": ["FROPA"],
            "Wind Shift": ["WSHFT"],
            "SLP Status": ["SLPNO"],
            "RVR Status": ["RVRNO"],
            "Runway State (Remarks)": [r"8\d{7}"],
            "Sensor Status": list(SENSOR_STATUS.keys()),
            "Maintenance Indicator": [MAINTENANCE_INDICATOR],
            "runway_winds": ["RWY", "WIND"],
        }

    _VIS_VALUE_PATTERN = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+)"
    _DIRECTION_PATTERN = r"(?:NE|NW|SE|SW|N|E|S|W)"

    def parse(self, metar: str) -> Tuple[str, Dict]:
        """Parse the remarks section from a METAR string

        Args:
            metar: The full METAR string

        Returns:
            Tuple of (raw_remarks_string, decoded_remarks_dict)
        """
        match = re.search(r"RMK\s+(.+)$", metar)
        if not match:
            return "", {}

        remarks = match.group(1)
        decoded = {}
        positions = {}  # Track position of each decoded key for sorting

        # Parse all remark types
        self._parse_station_type(remarks, decoded, positions)
        self._parse_runway_winds(remarks, decoded)
        self._parse_sea_level_pressure(remarks, decoded)
        self._parse_pressure_tendency(remarks, decoded)
        self._parse_temperature_tenths(remarks, decoded)
        self._parse_24hr_temperature_extremes(remarks, decoded)
        self._parse_6hr_temperatures(remarks, decoded)
        self._parse_6hr_precipitation(remarks, decoded)
        self._parse_24hr_precipitation(remarks, decoded)
        self._parse_snow_depth(remarks, decoded)
        self._parse_water_equivalent_snow(remarks, decoded)
        self._parse_sunshine_duration(remarks, decoded)
        self._parse_ice_accretion(remarks, decoded)
        self._parse_variable_visibility(remarks, decoded)
        self._parse_sector_visibility(remarks, decoded)
        self._parse_visibility_second_location(remarks, decoded)
        report_time = self._extract_report_time(metar)
        self._parse_thunderstorm_begin_end(remarks, decoded, report_time)
        self._parse_past_weather(remarks, decoded, report_time)
        self._parse_qfe(remarks, decoded)
        self._parse_altimeter_remarks(remarks, decoded)
        self._parse_precipitation_amount(remarks, decoded)
        self._parse_hailstone_size(remarks, decoded)
        self._parse_snow_pellet_intensity(remarks, decoded)
        self._parse_snincr(remarks, decoded)
        self._parse_peak_wind(remarks, decoded)
        self._parse_surface_visibility(remarks, decoded)
        self._parse_tower_visibility(remarks, decoded)
        self._parse_lightning(remarks, decoded)
        self._parse_virga(remarks, decoded)
        self._parse_thunderstorm_location(remarks, decoded)
        self._parse_acsl(remarks, decoded)
        self._parse_significant_cloud_remarks(remarks, decoded)
        self._parse_cloud_types(remarks, decoded)
        self._parse_cloud_type_8group(remarks, decoded)
        self._parse_variable_sky_condition(remarks, decoded)
        self._parse_ceiling(remarks, decoded)
        self._parse_ceiling_second_location(remarks, decoded)
        self._parse_density_altitude(remarks, decoded)
        self._parse_obscuration(remarks, decoded)
        self._parse_obscuration_coded(remarks, decoded)
        self._parse_qbb(remarks, decoded)
        self._parse_pressure_change(remarks, decoded)
        self._parse_p_fr_p_rr(remarks, decoded)
        self._parse_frontal_passage(remarks, decoded)
        self._parse_wind_shift(remarks, decoded)
        self._parse_slp_status(remarks, decoded)
        self._parse_rvr_status(remarks, decoded)
        self._parse_runway_state_remarks(remarks, decoded)
        self._parse_sensor_status(remarks, decoded)
        self._parse_ri_precip_intensity(remarks, decoded)
        self._parse_acft_mshp(remarks, decoded)
        self._parse_nospeci(remarks, decoded)
        self._parse_tornadic_activity(remarks, decoded)
        self._parse_volcanic_eruption(remarks, decoded)
        self._parse_maintenance_indicator(remarks, decoded, positions)

        # Sort decoded dict by position in original remarks string
        sorted_decoded = self._sort_by_position(remarks, decoded, positions)

        return remarks, sorted_decoded

    # =========================================================================
    # Station Information
    # =========================================================================

    def _parse_station_type(self, remarks: str, decoded: Dict, positions: Dict) -> None:
        """Parse station type (AO1/AO2)"""
        # Longest-first to avoid matching A02 within A02A
        for code in ["A02A", "AO2", "AO1", "A02", "A01"]:
            pos = remarks.find(code)
            if pos >= 0:
                decoded["Station Type"] = STATION_TYPES.get(code, code)
                positions["Station Type"] = pos
                return

    # =========================================================================
    # Wind Information
    # =========================================================================

    def _parse_runway_winds(self, remarks: str, decoded: Dict) -> None:
        """Parse runway-specific wind information

        Handles both US format (WIND location dddssKT) and
        ICAO/European format (RWYxx dddssKT [dddVddd])
        """
        # US format: WIND location dddss(G)KT
        wind_patterns = re.findall(r"WIND\s+(\w+)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", remarks)
        if wind_patterns:
            if "runway_winds" not in decoded:
                decoded["runway_winds"] = []
            for pattern in wind_patterns:
                location, direction, speed, gust = pattern
                wind_info = {
                    "runway": location,
                    "direction": int(direction),
                    "speed": int(speed),
                    "unit": "KT",
                }
                if gust:
                    wind_info["gust"] = int(gust)
                decoded["runway_winds"].append(wind_info)

        # ICAO/European format: RWYxx dddssKT [dddVddd]
        rwy_wind_patterns = re.findall(
            r"RWY(\d{2}[LCR]?)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT(?:\s+(\d{3})V(\d{3}))?",
            remarks,
        )
        if rwy_wind_patterns:
            if "runway_winds" not in decoded:
                decoded["runway_winds"] = []
            for pattern in rwy_wind_patterns:
                runway, direction, speed, gust, var_from, var_to = pattern
                wind_info = {
                    "runway": runway,
                    "direction": int(direction),
                    "speed": int(speed),
                    "unit": "KT",
                }
                if gust:
                    wind_info["gust"] = int(gust)
                if var_from and var_to:
                    wind_info["variable_direction"] = [int(var_from), int(var_to)]
                decoded["runway_winds"].append(wind_info)

    def _parse_peak_wind(self, remarks: str, decoded: Dict) -> None:
        """Parse peak wind information — FMH-1 §12.7.1.d.

        Format: PK WND dddff(f)/(hh)mm
        Time field may be 4 digits (HHMM) or 2 digits (MM of current hour).
        """
        pk_wnd_match = re.search(r"PK\s+WND\s+(\d{3})(\d{2,3})/(\d{2,4})", remarks)
        if pk_wnd_match:
            pk_direction = int(pk_wnd_match.group(1))
            pk_speed = int(pk_wnd_match.group(2))
            time_raw = pk_wnd_match.group(3)
            if len(time_raw) == 4:
                time_display = f"{time_raw[:2]}:{time_raw[2:]} UTC"
            else:
                time_display = f":{time_raw} UTC (current hour)"
            decoded["Peak Wind"] = f"{pk_direction}° at {pk_speed} KT at {time_display}"

    def _parse_wind_shift(self, remarks: str, decoded: Dict) -> None:
        """Parse wind shift information — FMH-1 §12.7.1.e.

        Format: WSHFT (hh)mm [FROPA]
        Time field may be 4 digits (HHMM) or 2 digits (MM of current hour).
        """
        wshft_match = re.search(r"WSHFT\s+(\d{2,4})(?:\s+(FROPA))?", remarks)
        if wshft_match:
            time_raw = wshft_match.group(1)
            fropa = wshft_match.group(2)
            if len(time_raw) == 4:
                time_display = f"{time_raw[:2]}:{time_raw[2:]} UTC"
            else:
                time_display = f":{time_raw} UTC (current hour)"
            value = f"at {time_display}"
            if fropa:
                value += " (frontal passage)"
            decoded["Wind Shift"] = value

    # =========================================================================
    # Pressure Information
    # =========================================================================

    def _parse_sea_level_pressure(self, remarks: str, decoded: Dict) -> None:
        """Parse sea level pressure (SLPxxx)"""
        slp_match = re.search(r"SLP(\d{3})", remarks)
        if slp_match:
            slp = int(slp_match.group(1))
            # North American format: add decimal point
            if slp < 500:
                pressure = 1000 + slp / 10
            else:
                pressure = 900 + slp / 10
            decoded["Sea Level Pressure"] = f"{pressure:.1f} hPa"

    def _parse_pressure_tendency(self, remarks: str, decoded: Dict) -> None:
        """Parse pressure tendency (5appp format)

        5 = group identifier
        a = pressure characteristic (0-8)
        ppp = pressure change in tenths of hPa
        """
        pressure_tendency_match = re.search(r"(?<!\d)5([0-8])(\d{3})(?!\d)", remarks)
        if pressure_tendency_match:
            characteristic = int(pressure_tendency_match.group(1))
            change_tenths = int(pressure_tendency_match.group(2))
            change_hpa = change_tenths / 10
            char_desc = PRESSURE_TENDENCY_CHARACTERISTICS.get(characteristic, f"Unknown ({characteristic})")
            decoded["Pressure Tendency"] = f"{char_desc}; change: {change_hpa:.1f} hPa"

    def _parse_qfe(self, remarks: str, decoded: Dict) -> None:
        """Parse QFE (field elevation pressure) - Russian METAR format

        Russian METARs use the format QFEnnn/xxxx where:
        - nnn = pressure in mmHg (millimeters of mercury)
        - xxxx = pressure in hPa (hectopascals), with leading zero if < 1000

        Example: QFE728/0971 means 728 mmHg = 971 hPa
        Some reports may only include QFEnnn without the hPa value.
        """
        # Try to match QFE with both mmHg and hPa values
        qfe_match = re.search(r"QFE(\d{3,4})(?:/(\d{4}))?", remarks)
        if qfe_match:
            qfe_mmhg = int(qfe_match.group(1))
            qfe_hpa_str = qfe_match.group(2)

            if qfe_hpa_str:
                # Both values provided
                qfe_hpa = int(qfe_hpa_str)
                decoded["QFE"] = f"{qfe_mmhg} mmHg ({qfe_hpa} hPa)"
            else:
                # Only mmHg value provided, calculate approximate hPa
                # 1 mmHg ≈ 1.33322 hPa
                qfe_hpa_calc = int(qfe_mmhg * 1.33322)
                decoded["QFE"] = f"{qfe_mmhg} mmHg (~{qfe_hpa_calc} hPa)"

    def _parse_altimeter_remarks(self, remarks: str, decoded: Dict) -> None:
        """Parse altimeter setting in remarks (Axxxx format)"""
        altimeter_rmk_match = re.search(r"\bA(\d{4})\b", remarks)
        if altimeter_rmk_match:
            alt_value = int(altimeter_rmk_match.group(1))
            alt_inhg = alt_value / 100
            decoded["Altimeter (Remarks)"] = f"{alt_inhg:.2f} inHg"

    def _parse_pressure_change(self, remarks: str, decoded: Dict) -> None:
        """Parse rapid pressure change indicators (PRESFR/PRESRR)"""
        if "PRESFR" in remarks:
            decoded["Pressure Change"] = "Pressure falling rapidly"
        elif "PRESRR" in remarks:
            decoded["Pressure Change"] = "Pressure rising rapidly"

    # =========================================================================
    # Temperature Information
    # =========================================================================

    def _parse_temperature_tenths(self, remarks: str, decoded: Dict) -> None:
        """Parse temperature/dewpoint to tenths (TsnTTTsnTTT format)"""
        temp_match = re.search(r"T([01])(\d{3})([01])(\d{3})", remarks)
        if temp_match:
            temp_sign = -1 if temp_match.group(1) == "1" else 1
            temp_tenths = int(temp_match.group(2))
            dew_sign = -1 if temp_match.group(3) == "1" else 1
            dew_tenths = int(temp_match.group(4))

            decoded["Temperature (tenths)"] = f"{temp_sign * temp_tenths / 10:.1f}°C"
            decoded["Dewpoint (tenths)"] = f"{dew_sign * dew_tenths / 10:.1f}°C"

    def _parse_24hr_temperature_extremes(self, remarks: str, decoded: Dict) -> None:
        """Parse 24-hour temperature extremes (4snTTTsnTTT format)"""
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

    def _parse_6hr_temperatures(self, remarks: str, decoded: Dict) -> None:
        """Parse 6-hour max/min temperatures (1snTTT and 2snTTT formats)"""
        # 6-hour maximum temperature
        max_temp_6hr_match = re.search(r"(?<!\d)1([01])(\d{3})(?!\d)", remarks)
        if max_temp_6hr_match:
            sign = -1 if max_temp_6hr_match.group(1) == "1" else 1
            temp_tenths = int(max_temp_6hr_match.group(2))
            temp_value = sign * temp_tenths / 10
            decoded["6-Hour Maximum Temperature"] = f"{temp_value:.1f}°C"

        # 6-hour minimum temperature
        min_temp_6hr_match = re.search(r"(?<!\d)2([01])(\d{3})(?!\d)", remarks)
        if min_temp_6hr_match:
            sign = -1 if min_temp_6hr_match.group(1) == "1" else 1
            temp_tenths = int(min_temp_6hr_match.group(2))
            temp_value = sign * temp_tenths / 10
            decoded["6-Hour Minimum Temperature"] = f"{temp_value:.1f}°C"

    # =========================================================================
    # Precipitation Information
    # =========================================================================

    def _parse_6hr_precipitation(self, remarks: str, decoded: Dict) -> None:
        """Parse 6-hour precipitation (6xxxx format)

        FMH-1 §12.7.2.a(3): 6R24R24R24R24
        - 6//// = indeterminate amount (e.g., gage frozen)
        - 60000 = trace or none
        - 6xxxx = amount in hundredths of inches
        """
        precip_6hr_match = re.search(r"(?<!\d)6(/{4}|\d{4})(?!\d)", remarks)
        if precip_6hr_match:
            raw = precip_6hr_match.group(1)
            if raw == "////":
                decoded["6-Hour Precipitation"] = "Indeterminate (gauge frozen or inaccessible)"
            else:
                precip_hundredths = int(raw)
                if precip_hundredths == 0:
                    decoded["6-Hour Precipitation"] = "Trace or none"
                else:
                    precip_inches = precip_hundredths / 100.0
                    decoded["6-Hour Precipitation"] = f"{precip_inches:.2f} inches"

    def _parse_precipitation_amount(self, remarks: str, decoded: Dict) -> None:
        """Parse precipitation amount (Pxxxx format)"""
        precip_match = re.search(r"P(\d{4})", remarks)
        if precip_match:
            precip_hundredths = int(precip_match.group(1))
            if precip_hundredths == 0:
                decoded["Precipitation Amount"] = "Less than 0.01 inches"
            else:
                precip_inches = precip_hundredths / 100.0
                decoded["Precipitation Amount"] = f"{precip_inches:.2f} inches"

    # =========================================================================
    # Visibility Information
    # =========================================================================

    def _parse_variable_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse variable visibility (VIS minVmax)"""
        vis_match = re.search(
            rf"VIS\s+({self._VIS_VALUE_PATTERN})V({self._VIS_VALUE_PATTERN})",
            remarks,
        )
        if vis_match:
            min_vis_str = vis_match.group(1)
            max_vis_str = vis_match.group(2)

            min_vis = self._parse_visibility_fraction(min_vis_str)
            max_vis = self._parse_visibility_fraction(max_vis_str)

            min_vis_display = str(int(min_vis)) if min_vis == int(min_vis) else min_vis_str
            max_vis_display = str(int(max_vis)) if max_vis == int(max_vis) else max_vis_str

            decoded["Variable Visibility"] = f"{min_vis_display} to {max_vis_display} statute miles"

    def _parse_surface_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse surface visibility (SFC VIS vv)"""
        sfc_vis_match = re.search(rf"SFC\s+VIS\s+({self._VIS_VALUE_PATTERN})", remarks)
        if sfc_vis_match:
            sfc_vis_str = sfc_vis_match.group(1)
            decoded["Surface Visibility"] = f"{sfc_vis_str} SM"

    def _parse_tower_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse tower visibility (TWR VIS vv)"""
        twr_vis_match = re.search(rf"TWR\s+VIS\s+({self._VIS_VALUE_PATTERN})", remarks)
        if twr_vis_match:
            twr_vis_str = twr_vis_match.group(1)
            decoded["Tower Visibility"] = f"{twr_vis_str} SM"

    @staticmethod
    def _parse_visibility_fraction(vis_str: str) -> float:
        """Parse a visibility string that may contain a fraction"""
        vis_str = vis_str.strip()
        if " " in vis_str:
            whole, fraction = vis_str.split()
            num, den = fraction.split("/")
            return float(whole) + (float(num) / float(den))
        if "/" in vis_str:
            num, den = vis_str.split("/")
            return float(num) / float(den)
        return float(vis_str)

    # =========================================================================
    # Weather Phenomena
    # =========================================================================

    def _parse_past_weather(self, remarks: str, decoded: Dict, report_time: Optional[Tuple[int, int, int]]) -> None:
        """Parse precipitation begin/end remarks (e.g., RAB11E24, FZRAB29E44, RAB0254E16B42)

        Format: [descriptor][phenomenon]B[time]E[time]...
        B = began, E = ended
        Time can be 2-digit (MM) or 4-digit (HHMM) format
        """
        past_weather_pattern = (
            r"(MI|PR|BC|DR|BL|SH|TS|FZ)?"
            r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)"
            r"(?:[BE]\d{2,4})+"
        )
        past_weather_matches = re.finditer(past_weather_pattern, remarks)

        timeline_events = []
        found_unknown_precipitation = False

        for match_index, match in enumerate(past_weather_matches):
            full_match = match.group(0)
            descriptor = match.group(1) or ""
            phenomenon = match.group(2)

            weather_type = self._build_weather_type(descriptor, phenomenon)
            found_unknown_precipitation = found_unknown_precipitation or phenomenon == "UP"

            # Extract all B/E events (supports both 2-digit MM and 4-digit HHMM formats)
            events_str = full_match[len(descriptor) + len(phenomenon) :]
            event_matches = re.findall(r"([BE])(\d{2,4})", events_str)

            for event_index, (action, time) in enumerate(event_matches):
                action_text = "began" if action == "B" else "ended"
                sort_key, display_time = self._resolve_event_time(time, report_time)
                timeline_events.append(
                    {
                        "sort_key": sort_key,
                        "match_index": match_index,
                        "event_index": event_index,
                        "display_time": display_time,
                        "description": f"{weather_type} {action_text}",
                    }
                )

        if timeline_events:
            timeline_events.sort(
                key=lambda event: (
                    event["sort_key"],
                    event["match_index"],
                    event["event_index"],
                )
            )

            timeline_parts: List[str] = []
            current_time = None
            current_descriptions: List[str] = []

            for event in timeline_events:
                if event["display_time"] != current_time:
                    if current_time is not None:
                        timeline_parts.append(f"{current_time}: {', '.join(current_descriptions)}")
                    current_time = event["display_time"]
                    current_descriptions = [event["description"]]
                else:
                    current_descriptions.append(event["description"])

            if current_time is not None:
                timeline_parts.append(f"{current_time}: {', '.join(current_descriptions)}")

            decoded["Precipitation Begin/End Times"] = "; ".join(timeline_parts)

        if found_unknown_precipitation:
            decoded["Unknown Precipitation"] = (
                "Automated station detected precipitation, but the precipitation discriminator could not identify the type"
            )

    def _parse_thunderstorm_begin_end(
        self,
        remarks: str,
        decoded: Dict,
        report_time: Optional[Tuple[int, int, int]],
    ) -> None:
        """Parse thunderstorm begin/end remarks (e.g. TSB0159E30)."""
        matches = re.finditer(r"\bTS(?:B(\d{2,4}))?(?:E(\d{2,4}))\b|\bTSB(\d{2,4})(?:E(\d{2,4}))?\b", remarks)
        events = []

        for match in matches:
            begin_token = match.group(1) or match.group(3)
            end_token = match.group(2) or match.group(4)

            if begin_token:
                sort_key, display_time = self._resolve_event_time(begin_token, report_time)
                events.append((sort_key, display_time, "thunderstorm began"))
            if end_token:
                sort_key, display_time = self._resolve_event_time(end_token, report_time)
                events.append((sort_key, display_time, "thunderstorm ended"))

        if not events:
            return

        events.sort(key=lambda item: item[0])
        parts = [f"{display_time}: {description}" for _, display_time, description in events]
        decoded["Thunderstorm Begin/End Times"] = "; ".join(parts)

    @staticmethod
    def _extract_report_time(metar: str) -> Optional[Tuple[int, int, int]]:
        """Extract the observation day/hour/minute from the METAR header."""
        match = re.search(r"\b(\d{2})(\d{2})(\d{2})Z\b", metar)
        if not match:
            return None

        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    @staticmethod
    def _build_weather_type(descriptor: str, phenomenon: str) -> str:
        """Build a human-readable precipitation type for precipitation timing remarks."""
        weather_parts = []
        if descriptor:
            weather_parts.append(WEATHER_DESCRIPTORS.get(descriptor, descriptor.lower()))

        if phenomenon == "UP":
            weather_parts.append("unknown precipitation")
        else:
            weather_parts.append(WEATHER_PHENOMENA.get(phenomenon, phenomenon.lower()))

        return " ".join(weather_parts)

    @staticmethod
    def _resolve_event_time(time_token: str, report_time: Optional[Tuple[int, int, int]]) -> Tuple[Tuple[int, int, int], str]:
        """Resolve a precipitation timing token to sortable UTC clock time."""
        if len(time_token) == 4:
            event_hour = int(time_token[:2])
            event_minute = int(time_token[2:])

            if report_time is None:
                return (0, event_hour, event_minute), f"{event_hour:02d}:{event_minute:02d} UTC"

            _, report_hour, report_minute = report_time
            day_offset = -1 if (event_hour, event_minute) > (report_hour, report_minute) else 0
            suffix = " (previous day)" if day_offset == -1 and report_hour == 0 else ""
            return (day_offset, event_hour, event_minute), f"{event_hour:02d}:{event_minute:02d} UTC{suffix}"

        event_minute = int(time_token)
        if report_time is None:
            return (0, 0, event_minute), f"minute {event_minute:02d}"

        _, report_hour, report_minute = report_time
        event_hour = report_hour
        day_offset = 0

        if event_minute > report_minute:
            event_hour = (report_hour - 1) % 24
            day_offset = -1 if report_hour == 0 else 0

        suffix = " (previous day)" if day_offset == -1 else ""
        return (day_offset, event_hour, event_minute), f"{event_hour:02d}:{event_minute:02d} UTC{suffix}"

    def _parse_lightning(self, remarks: str, decoded: Dict) -> None:
        """Parse lightning information

        Format: [FRQ|OCNL|CONS] LTG[IC|CC|CG|CA]* [DSNT|VC|OHD] [directions]
        """
        ltg_match = re.search(
            r"(FRQ|OCNL|CONS)?\s*LTG((?:IC|CC|CG|CA)+)?"
            r"(?:\s+(DSNT|VC|OHD))?"
            r"(?:\s+(ALQDS))?"
            r"(?:\s+((?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?"
            r"(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*))?",
            remarks,
        )
        if ltg_match:
            ltg_parts = []

            # Frequency
            freq = ltg_match.group(1)
            if freq:
                ltg_parts.append(LIGHTNING_FREQUENCY.get(freq, freq))

            # Lightning types
            ltg_types = ltg_match.group(2)
            if ltg_types:
                types = []
                for i in range(0, len(ltg_types), 2):
                    lt = ltg_types[i : i + 2]
                    types.append(LIGHTNING_TYPES.get(lt, lt))
                ltg_parts.append(" and ".join(types) + " lightning")
            else:
                ltg_parts.append("lightning")

            # Distance/location
            distance = ltg_match.group(3)
            if distance:
                ltg_parts.append(LOCATION_INDICATORS.get(distance, distance))

            # All quadrants
            alqds = ltg_match.group(4)
            if alqds:
                ltg_parts.append("all quadrants")

            # Direction
            direction = ltg_match.group(5)
            if direction:
                direction = direction.replace("AND", "and")
                for abbr, full in sorted(DIRECTION_ABBREV.items(), key=lambda item: -len(item[0])):
                    direction = direction.replace(abbr, full)
                direction = direction.replace("-", " to ")
                ltg_parts.append(f"to the {direction}")

            decoded["Lightning"] = " ".join(ltg_parts)

    def _parse_virga(self, remarks: str, decoded: Dict) -> None:
        """Parse virga information (precipitation not reaching ground)"""
        virga_match = re.search(
            r"VIRGA\s*(DSNT|VC)?\s*"
            r"((?:(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)"
            r"(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)?",
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
                dir_text = direction
                for abbr, full in DIRECTION_ABBREV.items():
                    dir_text = dir_text.replace(abbr, full)
                dir_text = dir_text.replace("-", " to ").replace("AND", "and")
                virga_parts.append(f"to the {dir_text}")

            decoded["Virga"] = " ".join(virga_parts)

    def _parse_thunderstorm_location(self, remarks: str, decoded: Dict) -> None:
        """Parse thunderstorm location and movement

        Format: TS [DSNT|VC|OHD|ALQDS] [AND] [directions] [MOV direction]
        Examples:
          - TS OHD MOV NE
          - TS DSNT NW
          - TS OHD AND NW -N-E MOV NE (overhead and northwest through north to east, moving northeast)
        """
        # Single direction: NE, NW, SE, SW, N, E, S, W
        single_dir = r"(?:NE|NW|SE|SW|N|E|S|W)"

        ts_match = re.search(
            r"\bTS\s+(DSNT|VC|OHD|ALQDS)?\s*"
            r"(?:AND\s+)?"  # Optional "AND" after location
            # Capture direction string: everything up to MOV or end, but be non-greedy
            rf"((?:{single_dir}(?:\s*-{single_dir})*(?:\s+AND\s+{single_dir}(?:\s*-{single_dir})*)*)?)?\s*"
            rf"(?:MOV\s+({single_dir}(?:-{single_dir})?))?",
            remarks,
        )
        if ts_match:
            ts_parts = ["Thunderstorm"]
            location = ts_match.group(1)
            direction = ts_match.group(2)
            movement = ts_match.group(3)

            if location:
                loc_map = {
                    "DSNT": "distant (10-30 NM)",
                    "VC": "in vicinity (5-10 NM)",
                    "OHD": "overhead",
                    "ALQDS": "all quadrants",
                }
                ts_parts.append(loc_map.get(location, location))

            if direction and direction.strip():
                dir_text = direction.strip()
                # Replace direction abbreviations with full names (longer first to avoid partial matches)
                for abbr, full in sorted(DIRECTION_ABBREV.items(), key=lambda x: -len(x[0])):
                    dir_text = re.sub(rf"\b{abbr}\b", full, dir_text)
                # Clean up: replace dashes with "through" and "AND" with "and"
                dir_text = re.sub(r"\s*-\s*", " through ", dir_text)
                dir_text = dir_text.replace(" AND ", " and ")
                ts_parts.append(f"to the {dir_text}")

            if movement:
                mov_text = movement
                for abbr, full in sorted(DIRECTION_ABBREV.items(), key=lambda x: -len(x[0])):
                    mov_text = re.sub(rf"\b{abbr}\b", full, mov_text)
                mov_text = mov_text.replace("-", " through ")
                ts_parts.append(f"moving {mov_text}")

            decoded["Thunderstorm Location"] = " ".join(ts_parts)

    # =========================================================================
    # Cloud Information
    # =========================================================================

    def _parse_acsl(self, remarks: str, decoded: Dict) -> None:
        """Parse ACSL (Altocumulus Standing Lenticular) clouds"""
        acsl_match = re.search(
            r"ACSL\s*(DSNT|VC|OHD)?\s*([NSEW]+(?:-[NSEW]+)?)?\s*" r"(?:MOV\s+([NSEW]+(?:-[NSEW]+)?))?",
            remarks,
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
                dir_text = direction
                for abbr, full in DIRECTION_ABBREV.items():
                    dir_text = dir_text.replace(abbr, full)
                dir_text = dir_text.replace("-", " to ")
                acsl_parts.append(f"to the {dir_text}")

            if movement:
                mov_text = movement
                for abbr, full in DIRECTION_ABBREV.items():
                    mov_text = mov_text.replace(abbr, full)
                mov_text = mov_text.replace("-", " to ")
                acsl_parts.append(f"moving {mov_text}")

            decoded["ACSL"] = " ".join(acsl_parts)

    def _parse_significant_cloud_remarks(self, remarks: str, decoded: Dict) -> None:
        """Parse FMH-1 significant cloud-type remarks written in plain language."""
        cloud_labels = {
            "CBMAM": "Cumulonimbus mammatus",
            "CB": "Cumulonimbus",
            "TCU": "Towering cumulus",
            "ACC": "Altocumulus castellanus",
            "SCSL": "Stratocumulus standing lenticular",
            "ACSL": "Altocumulus standing lenticular",
            "CCSL": "Cirrocumulus standing lenticular",
            "APRNT ROTOR CLD": "Apparent rotor cloud",
        }
        direction_pattern = r"(?:NE|NW|SE|SW|N|E|S|W)"
        pattern = (
            rf"\b(CBMAM|CB|TCU|ACC|SCSL|ACSL|CCSL|APRNT\s+ROTOR\s+CLD)"
            rf"(?:\s+(DSNT|VC|OHD))?"
            rf"(?:\s+({direction_pattern}(?:-{direction_pattern})?))?"
            rf"(?:\s+MOV\s+({direction_pattern}(?:-{direction_pattern})?))?"
        )

        cloud_descriptions: List[str] = []
        for match in re.finditer(pattern, remarks):
            cloud_code = match.group(1).replace("  ", " ")
            location = match.group(2)
            direction = match.group(3)
            movement = match.group(4)

            parts = [cloud_labels.get(cloud_code, cloud_code)]
            if location:
                parts.append(LOCATION_INDICATORS.get(location, location))
            if direction:
                parts.append(f"to the {self._expand_direction_text(direction)}")
            if movement:
                parts.append(f"moving {self._expand_direction_text(movement)}")
            cloud_descriptions.append(" ".join(parts))

        if cloud_descriptions:
            existing = decoded.get("Cloud Types")
            if existing:
                cloud_descriptions.insert(0, str(existing))
            decoded["Cloud Types"] = "; ".join(cloud_descriptions)

    def _parse_cloud_types(self, remarks: str, decoded: Dict) -> None:
        """Parse cloud type codes

        Handles:
        - Japanese/ICAO format: {oktas}{cloud_type}{height} e.g., 1CU007, 3SC015
        - Canadian format: {cloud_type}{oktas} e.g., SC6, AC3
        - Trace clouds: e.g., AC TR, CI TR
        """
        cloud_types_found = []

        # Japanese/ICAO format
        japan_cloud_matches = re.findall(r"\b(\d)(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d{3})\b", remarks)
        for oktas, cloud_code, height in japan_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            height_ft = int(height) * 100
            cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage at {height_ft} feet")

        # Canadian format (only if no Japanese format found)
        if not japan_cloud_matches:
            cloud_type_matches = re.findall(r"(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d)(?!\d{2})", remarks)
            for cloud_code, oktas in cloud_type_matches:
                cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
                cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage")

        # Trace cloud patterns
        trace_cloud_matches = re.findall(r"\b(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)\s+TR\b", remarks)
        for cloud_code in trace_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            cloud_types_found.append(f"{cloud_name} trace (less than 1/8 sky coverage)")

        if cloud_types_found:
            decoded["Cloud Types"] = "; ".join(cloud_types_found)

    def _parse_ceiling(self, remarks: str, decoded: Dict) -> None:
        """Parse ceiling information (CIGxxx or CIG xxxVxxx)"""
        cig_match = re.search(r"\bCIG\s*(\d{3})(?:\s*V\s*(\d{3}))?\b", remarks)
        if cig_match:
            cig_low = int(cig_match.group(1)) * 100
            if cig_match.group(2):
                cig_high = int(cig_match.group(2)) * 100
                decoded["variable_ceiling"] = f"{cig_low} to {cig_high} feet AGL"
            else:
                decoded["Ceiling"] = f"{cig_low} feet AGL"

    def _parse_obscuration(self, remarks: str, decoded: Dict) -> None:
        """Parse obscuration remarks"""
        if re.search(r"\bMT\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"
        elif re.search(r"\bMTN\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountain obscured"
        elif re.search(r"\bMTNS\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"

    def _parse_qbb(self, remarks: str, decoded: Dict) -> None:
        """Parse QBB (cloud base height in meters) - Russian METAR format

        QBB is used in Russian METARs to report the height of the lower
        boundary of clouds in meters above ground level.
        Format: QBBnnn where nnn is the height in meters
        Example: QBB220 = cloud base at 220 meters AGL
        """
        qbb_match = re.search(r"\bQBB(\d{2,4})\b", remarks)
        if qbb_match:
            height_meters = int(qbb_match.group(1))
            # Convert meters to feet for reference (1 meter ≈ 3.28084 feet)
            height_feet = int(height_meters * 3.28084)
            decoded["QBB"] = f"Cloud base at {height_meters} meters ({height_feet} feet) AGL"

    def _parse_density_altitude(self, remarks: str, decoded: Dict) -> None:
        """Parse density altitude (Canadian remarks)"""
        density_alt_match = re.search(r"DENSITY\s+ALT\s+(-?\d+)FT", remarks)
        if density_alt_match:
            density_alt = int(density_alt_match.group(1))
            decoded["Density Altitude"] = f"{density_alt} feet"

    # =========================================================================
    # Runway Information
    # =========================================================================

    def _parse_runway_state_remarks(self, remarks: str, decoded: Dict) -> None:
        """Parse runway state in remarks (8-group format: 8RDEddBB)

        8 = group identifier
        R = runway designator
        D = deposit type
        E = extent of contamination
        dd = depth of deposit
        BB = braking action/friction coefficient
        """
        runway_state_rmk_match = re.search(r"(?<!\d)8(\d)(\d)(\d)(\d{2})(\d{2})(?!\d)", remarks)
        if runway_state_rmk_match:
            runway_digit = runway_state_rmk_match.group(1)
            deposit = runway_state_rmk_match.group(2)
            extent = runway_state_rmk_match.group(3)
            depth_raw = runway_state_rmk_match.group(4)
            braking_raw = runway_state_rmk_match.group(5)

            # Decode runway
            runway_num = int(runway_digit)
            if runway_num <= 3:
                runway_desc = f"Runway {runway_num}{runway_num}"
            else:
                runway_desc = f"Runway {runway_num}x"

            # Deposit type
            deposit_desc = RUNWAY_STATE_DEPOSIT_TYPES_REMARKS.get(deposit, f"Unknown ({deposit})")

            # Extent of contamination
            extent_desc = RUNWAY_STATE_EXTENT_REMARKS.get(extent, f"Unknown ({extent})")

            # Depth of deposit
            depth_desc = self._decode_runway_depth(depth_raw)

            # Braking action
            braking_val = int(braking_raw)
            braking_desc = self._decode_braking_action(braking_val, braking_raw)

            decoded["Runway State (Remarks)"] = (
                f"{runway_desc}: {deposit_desc}, {extent_desc} coverage, " f"depth {depth_desc}, braking {braking_desc}"
            )

    @staticmethod
    def _decode_runway_depth(depth_raw: str) -> str:
        """Decode runway depth value"""
        special_desc = RUNWAY_DEPTH_SPECIAL.get(depth_raw)
        if special_desc:
            return special_desc[:1].upper() + special_desc[1:]

        depth_val = int(depth_raw)
        if depth_val <= 90:
            return f"{depth_val}mm"
        return f"{depth_val}mm"

    @staticmethod
    def _decode_braking_action(braking_val: int, braking_raw: str) -> str:
        """Decode braking action value"""
        if braking_val in RUNWAY_BRAKING_REMARKS:
            return RUNWAY_BRAKING_REMARKS[braking_val]
        elif braking_val == 99:
            return "Unreliable"
        return f"Friction coefficient 0.{braking_raw}"

    # =========================================================================
    # Status Indicators
    # =========================================================================

    def _parse_slp_status(self, remarks: str, decoded: Dict) -> None:
        """Parse SLP status (SLPNO)"""
        if "SLPNO" in remarks:
            decoded["SLP Status"] = "Sea level pressure not available"

    def _parse_rvr_status(self, remarks: str, decoded: Dict) -> None:
        """Parse RVR status (RVRNO)"""
        if "RVRNO" in remarks:
            decoded["RVR Status"] = "Runway visual range not available"

    def _parse_frontal_passage(self, remarks: str, decoded: Dict) -> None:
        """Parse frontal passage indicator (FROPA)"""
        if "FROPA" in remarks:
            decoded["Frontal Passage"] = "Frontal passage"

    def _parse_sensor_status(self, remarks: str, decoded: Dict) -> None:
        """Parse sensor status indicators"""
        sensor_status = []
        visno_match = re.search(r"\bVISNO(?:\s+(RWY\w+|TWR|SFC))?\b", remarks)
        if visno_match:
            location = visno_match.group(1)
            sensor_status.append(
                f"Visibility at secondary location not available{f' ({location})' if location else ''}"
            )

        chino_match = re.search(r"\bCHINO(?:\s+(RWY\w+|TWR|SFC))?\b", remarks)
        if chino_match:
            location = chino_match.group(1)
            sensor_status.append(
                f"Sky condition at secondary location not available{f' ({location})' if location else ''}"
            )

        for code, description in SENSOR_STATUS.items():
            if code in {"VISNO", "CHINO"}:
                continue
            if code in remarks:
                sensor_status.append(description)

        if sensor_status:
            decoded["Sensor Status"] = "; ".join(sensor_status)

    def _parse_maintenance_indicator(self, remarks: str, decoded: Dict, positions: Dict) -> None:
        """Parse maintenance indicator ($)"""
        if MAINTENANCE_INDICATOR in remarks:
            decoded["Maintenance Indicator"] = "Station requires maintenance"
            positions["Maintenance Indicator"] = remarks.find(MAINTENANCE_INDICATOR)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _parse_24hr_precipitation(self, remarks: str, decoded: Dict) -> None:
        """Parse 24-hour precipitation (7R24R24R24R24 format) — FMH-1 §12.7.2.a(3)(c)

        7xxxx = amount in hundredths of inches over previous 24 hours
        7//// = indeterminate amount
        """
        m = re.search(r"(?<!\d)7(/{4}|\d{4})(?!\d)", remarks)
        if m:
            raw = m.group(1)
            if raw == "////":
                decoded["24-Hour Precipitation"] = "Indeterminate (gauge frozen or inaccessible)"
            else:
                val = int(raw)
                decoded["24-Hour Precipitation"] = "Trace or none" if val == 0 else f"{val / 100.0:.2f} inches"

    def _parse_snow_depth(self, remarks: str, decoded: Dict) -> None:
        """Parse snow depth on ground — FMH-1 §12.7.2.a(4)

        Standard format: 4/sss  (4/ is group indicator, sss = depth in whole inches)
        ASOS variant:    /sss   (some older ASOS units omit the leading '4')

        4//// or //// = not measurable
        """
        m = re.search(r"(?<!\d)4(/(/{3}|\d{3}))(?!\d)", remarks)
        if not m:
            # Fallback: bare /sss without leading 4 (common in ASOS transmissions)
            m = re.search(r"(?<![4\d])(/)(/{3}|\d{3})(?!\d)", remarks)
        if m:
            raw = m.group(2) if m.lastindex >= 2 else m.group(1)
            if raw in ("///", "////"):
                decoded["Snow Depth"] = "Not measurable"
            else:
                depth = int(raw)
                decoded["Snow Depth"] = f"{depth} inch{'es' if depth != 1 else ''} on ground"

    def _parse_water_equivalent_snow(self, remarks: str, decoded: Dict) -> None:
        """Parse water equivalent of snow on ground (933RRR format) — FMH-1 §12.7.2.a(5)

        933RRR where RRR is tenths of inches (e.g., 933017 = 1.7 inches)
        """
        m = re.search(r"(?<!\d)933(\d{3})(?!\d)", remarks)
        if m:
            val_tenths = int(m.group(1))
            decoded["Water Equivalent of Snow"] = f"{val_tenths / 10.0:.1f} inches"

    def _parse_sunshine_duration(self, remarks: str, decoded: Dict) -> None:
        """Parse sunshine duration (98mmm format) — FMH-1 §12.7.2.c

        98mmm = minutes of sunshine in previous calendar day; 98/// = missing
        """
        m = re.search(r"(?<!\d)98(/{3}|\d{3})(?!\d)", remarks)
        if m:
            raw = m.group(1)
            if raw == "///":
                decoded["Sunshine Duration"] = "Missing"
            else:
                decoded["Sunshine Duration"] = f"{int(raw)} minutes"

    def _parse_ice_accretion(self, remarks: str, decoded: Dict) -> None:
        """Parse ice accretion on unshielded sensor (I1nnn/I3nnn/I6nnn) — FMH-1 §12.7.2.i

        I1nnn = 1-hour accretion; I3nnn = 3-hour; I6nnn = 6-hour
        nnn = hundredths of inch (e.g., I1015 = 0.15 inches in 1 hour)
        """
        ice_matches = re.findall(r"\bI([136])(\d{3})\b", remarks)
        if ice_matches:
            parts = []
            for period, raw in ice_matches:
                val_in = int(raw) / 100.0
                parts.append(f"{val_in:.2f} inches over {period} hour(s)")
            decoded["Ice Accretion"] = "; ".join(parts)

    def _parse_hailstone_size(self, remarks: str, decoded: Dict) -> None:
        """Parse hailstone size (GR [size]) — FMH-1 §12.7.1.n

        GR 3/4 = 3/4 inch; GR 1 1/2 = 1.5 inch; GR LESS THAN 1/4 = <1/4 inch
        """
        # GR LESS THAN fraction
        m = re.search(r"\bGR\s+LESS\s+THAN\s+(\d+/\d+|\d+)\b", remarks)
        if m:
            decoded["Hailstone Size"] = f"Less than {m.group(1)} inch in diameter"
            return
        # GR whole [fraction]
        m = re.search(r"\bGR\s+(\d+)(?:\s+(\d+/\d+))?\b", remarks)
        if m:
            if m.group(2):
                num, den = m.group(2).split("/")
                size = int(m.group(1)) + int(num) / int(den)
                decoded["Hailstone Size"] = f"{size:.2f} inches in diameter"
            else:
                decoded["Hailstone Size"] = f"{m.group(1)} inch(es) in diameter"
            return
        # GR fraction only
        m = re.search(r"\bGR\s+(\d+/\d+)\b", remarks)
        if m:
            decoded["Hailstone Size"] = f"{m.group(1)} inch in diameter"

    def _parse_snow_pellet_intensity(self, remarks: str, decoded: Dict) -> None:
        """Parse snow pellet/small hail intensity (GS LGT|MOD|HVY) — FMH-1 §12.7.1.o"""
        m = re.search(r"\bGS\s+(LGT|MOD|HVY)\b", remarks)
        if m:
            intensity_map = {"LGT": "light", "MOD": "moderate", "HVY": "heavy"}
            decoded["Snow Pellet Intensity"] = f"{intensity_map[m.group(1)]} snow pellets/small hail"

    def _parse_sector_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse sector visibility (VIS [DIR] vvvvv) — FMH-1 §12.7.1.h

        Reports visibility in a specific compass direction sector.
        Example: VIS NE 1 1/2 SM or VIS W 3SM
        """
        m = re.search(
            r"\bVIS\s+(N|NE|E|SE|S|SW|W|NW)\s+(\d+(?:\s+\d+/\d+)?(?:SM)?|\d/\d+\s*SM?|M?\d+(?:\s*SM)?)\b",
            remarks,
        )
        if m:
            direction = m.group(1)
            vis_raw = m.group(2).strip()
            decoded.setdefault("Sector Visibility", [])
            if isinstance(decoded["Sector Visibility"], list):
                decoded["Sector Visibility"].append(f"{vis_raw} to the {direction}")
            if len(decoded["Sector Visibility"]) == 1:
                decoded["Sector Visibility"] = decoded["Sector Visibility"][0]

    def _parse_visibility_second_location(self, remarks: str, decoded: Dict) -> None:
        """Parse visibility at a second location (VIS vvvvv LOC) — FMH-1 §12.7.1.i

        Example: VIS 3 RWY11 — visibility at runway 11 threshold
        Must not overlap with variable-visibility (minVmax) or sector-visibility (VIS DIR ...) patterns.
        """
        m = re.search(
            r"\bVIS\s+(\d+(?:\s+\d+/\d+)?(?:SM)?|\d/\d+\s*SM?)\s+(RWY\w+|TWR|SFC)\b",
            remarks,
        )
        if m:
            vis_raw = m.group(1).strip()
            location = m.group(2)
            decoded["Visibility (2nd Location)"] = f"{vis_raw} at {location}"

    def _parse_ceiling_second_location(self, remarks: str, decoded: Dict) -> None:
        """Parse ceiling at a second location (CIG hhh LOC) — FMH-1 §12.7.1.u

        Example: CIG 002 RWY11 — ceiling 200 ft at runway 11
        """
        m = re.search(r"\bCIG\s+(\d{3})\s+(RWY\w+|TWR|SFC)\b", remarks)
        if m:
            cig_ft = int(m.group(1)) * 100
            location = m.group(2)
            decoded["Ceiling (2nd Location)"] = f"{cig_ft} feet AGL at {location}"

    def _parse_variable_sky_condition(self, remarks: str, decoded: Dict) -> None:
        """Parse variable sky condition (NsNsNs hshshs V NsNsNs) — FMH-1 §12.7.1.s

        Example: SCT025 V BKN — ceiling variable between scattered and broken at 2500 ft
        """
        m = re.search(
            r"\b(FEW|SCT|BKN|OVC)(\d{3})\s+V\s+(FEW|SCT|BKN|OVC)\b",
            remarks,
        )
        if m:
            low_cov = m.group(1)
            height_ft = int(m.group(2)) * 100
            high_cov = m.group(3)
            decoded["Variable Sky"] = f"Variable between {low_cov} and {high_cov} at {height_ft} feet"

    def _parse_cloud_type_8group(self, remarks: str, decoded: Dict) -> None:
        """Parse cloud type additive data (8/CLCMCH format) — FMH-1 §12.7.2.b / WMO

        8/CL CM CH where each digit is a WMO cloud genus code:
        CL = 0-9 per Code Table 0513; CM = Code Table 0515; CH = Code Table 0521
        / = observation not made
        """
        # WMO Code Table 0513 (low clouds)
        cl_codes = {
            "0": "No low clouds",
            "1": "Cu (fair weather)",
            "2": "Cu (towering)",
            "3": "Cb (no top)",
            "4": "Sc (spread from Cu)",
            "5": "Sc (not from Cu)",
            "6": "St or Fs (not associated with fog)",
            "7": "Fs/St (associated with fog/precip)",
            "8": "Cu and Sc at different levels",
            "9": "Cb with anvil top",
            "/": "Not observed",
        }
        # WMO Code Table 0515 (middle clouds)
        cm_codes = {
            "0": "No middle clouds",
            "1": "As (thin)",
            "2": "As (thick) or Ns",
            "3": "Ac (thin at single level)",
            "4": "Ac patches (thin)",
            "5": "Ac (thin in bands)",
            "6": "Ac formed from Cu spreading",
            "7": "Ac (double layer or thick)",
            "8": "Ac with Cb",
            "9": "Ac (chaotic sky)",
            "/": "Not observed",
        }
        # WMO Code Table 0521 (high clouds)
        ch_codes = {
            "0": "No high clouds",
            "1": "Ci (filaments)",
            "2": "Ci (dense patch)",
            "3": "Ci (anvil from Cb)",
            "4": "Ci (thickening)",
            "5": "Ci and Cs (< 45° altitude)",
            "6": "Ci and Cs (> 45° altitude)",
            "7": "Cs covering sky",
            "8": "Cs not covering sky",
            "9": "Cc",
            "/": "Not observed",
        }
        m = re.search(r"(?<!\d)8/([0-9/])([0-9/])([0-9/])(?!\d)", remarks)
        if m:
            cl = cl_codes.get(m.group(1), f"Unknown ({m.group(1)})")
            cm = cm_codes.get(m.group(2), f"Unknown ({m.group(2)})")
            ch = ch_codes.get(m.group(3), f"Unknown ({m.group(3)})")
            decoded["Cloud Types (Additive)"] = f"Low: {cl}; Middle: {cm}; High: {ch}"

    def _parse_snincr(self, remarks: str, decoded: Dict) -> None:
        """Parse snow increasing rapidly (SNINCR nh/ns) — FMH-1 §12.7.1.z

        nh = inches of snow in past hour; ns = total snow depth on ground
        Example: SNINCR 2/8 — 2 inches of snow in past hour, 8 inches total
        """
        m = re.search(r"\bSNINCR\s+(\d+)/(\d+)\b", remarks)
        if m:
            hourly = m.group(1)
            total = m.group(2)
            decoded["Snow Increasing Rapidly"] = f"{hourly} inch(es) in past hour; {total} inch(es) total depth"

    def _parse_volcanic_eruption(self, remarks: str, decoded: Dict) -> None:
        """Parse volcanic eruption plain language — FMH-1 §12.7.1.a

        Captures 'VOLCANO ERUPTED' or 'ERUPTED' plain language blocks.
        """
        m = re.search(r"\b(VOLCANO|ERUPTION|ERUPTED)\b.*", remarks, re.IGNORECASE)
        if m:
            decoded["Volcanic Activity"] = m.group(0).strip()

    def _parse_ri_precip_intensity(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA precipitation intensity in RMK (RIxxx) — JMA Attachment 2

        RIxxx where xxx is precipitation intensity in tenths of mm/hr
        (e.g., RI035 = 3.5 mm/hr; RI300 = 30.0 mm/hr)
        Reported when intensity ≥ 3 mm/hr (RI030 and above).
        """
        m = re.search(r"\bRI(\d{3})\b", remarks)
        if m:
            val = int(m.group(1))
            decoded["Precipitation Intensity (JMA)"] = f"{val / 10.0:.1f} mm/hr"

    def _parse_p_fr_p_rr(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA local report rapid pressure change (P/FR, P/RR) — JMA Attachment 2

        P/FR = pressure falling rapidly (equivalent to PRESFR)
        P/RR = pressure rising rapidly (equivalent to PRESRR)
        Used in JMA local routine/special METAR-format reports.
        """
        if re.search(r"\bP/FR\b", remarks):
            decoded.setdefault("Pressure Change", "Pressure falling rapidly")
        elif re.search(r"\bP/RR\b", remarks):
            decoded.setdefault("Pressure Change", "Pressure rising rapidly")

    def _sort_by_position(self, remarks: str, decoded: Dict, positions: Dict) -> Dict:
        """Sort decoded dict by position in original remarks string"""
        regex_chars = set(r"\d[]{}+*?()|^$")

        # Find positions for keys not already tracked
        for key in decoded:
            if key not in positions:
                patterns = self._key_patterns.get(key, [])
                min_pos = len(remarks)  # Default to end
                for pattern in patterns:
                    is_regex = any(char in regex_chars for char in pattern)
                    if is_regex:
                        match = re.search(pattern, remarks)
                        if match:
                            min_pos = min(min_pos, match.start())
                    else:
                        pos = remarks.find(pattern)
                        if pos >= 0:
                            min_pos = min(min_pos, pos)
                positions[key] = min_pos

        # Sort decoded dict by position
        return dict(sorted(decoded.items(), key=lambda x: positions.get(x[0], len(remarks))))

    @staticmethod
    def _expand_direction_text(text: str) -> str:
        expanded = text
        for abbr, full in sorted(DIRECTION_ABBREV.items(), key=lambda item: -len(item[0])):
            expanded = re.sub(rf"\b{abbr}\b", full, expanded)
        return expanded.replace("-", " to ")

    # =========================================================================
    # New methods: Tornadic Activity, Coded Obscurations, ACFT MSHP, NOSPECI
    # =========================================================================

    def _parse_tornadic_activity(self, remarks: str, decoded: Dict) -> None:
        """Parse tornadic activity remarks — FMH-1 §12.7.1.b (highest priority in RMK section).

        Format: (TORNADO|FUNNEL CLOUD|WATERSPOUT) B(hh)(mm) [E(hh)(mm)] [dist] [dir] [MOV dir]
        Examples:
          TORNADO B13 6 NE
          FUNNEL CLOUD B1330 5 SW MOV NE
          WATERSPOUT B04E09
        """
        direction_pattern = r"(?:NE|NW|SE|SW|N|E|S|W)"
        pattern = (
            r"\b(TORNADO|FUNNEL\s+CLOUD|WATERSPOUT)"
            r"(?:\s+B(\d{2,4}))?"
            r"(?:\s+E(\d{2,4}))?"
            r"(?:\s+(\d+))?"
            rf"(?:\s+({direction_pattern}))?"
            rf"(?:\s+MOV\s+({direction_pattern}))?"
        )
        m = re.search(pattern, remarks, re.IGNORECASE)
        if not m:
            return

        phenomenon = m.group(1).replace("  ", " ")
        begin_raw = m.group(2)
        end_raw = m.group(3)
        distance = m.group(4)
        direction = m.group(5)
        mov_direction = m.group(6)

        def _fmt_time(t: str) -> str:
            return f"{t[:2]}:{t[2:]} UTC" if len(t) == 4 else f":{t} UTC (current hour)"

        parts_list = [phenomenon]
        if begin_raw:
            parts_list.append(f"began at {_fmt_time(begin_raw)}")
        if end_raw:
            parts_list.append(f"ended {_fmt_time(end_raw)}")
        if distance and direction:
            parts_list.append(f"{distance} SM to the {self._expand_direction_text(direction)}")
        elif direction:
            parts_list.append(f"to the {self._expand_direction_text(direction)}")
        if mov_direction:
            parts_list.append(f"moving {self._expand_direction_text(mov_direction)}")

        decoded["Tornadic Activity"] = "; ".join(parts_list)

    def _parse_obscuration_coded(self, remarks: str, decoded: Dict) -> None:
        """Parse FMH-1 §12.7.1.r coded obscuration remarks.

        Format: wx_code coverage hshshs
        Example: FG SCT000  FU BKN020  HZ FEW005
        """
        obs_wx = r"FG|FU|VA|DU|SA|HZ|PY|BR|BLSN|BLDU|BLSA|IC|GR|GS|SN|PL|RA|DZ|FZFG"
        coverage_levels = r"FEW|SCT|BKN|OVC"
        pattern = rf"\b({obs_wx})\s+({coverage_levels})(\d{{3}})\b"
        matches = re.findall(pattern, remarks)
        if not matches:
            return

        wx_labels = {
            "FG": "Fog",
            "FU": "Smoke",
            "VA": "Volcanic ash",
            "DU": "Widespread dust",
            "SA": "Sand",
            "HZ": "Haze",
            "PY": "Spray",
            "BR": "Mist",
            "BLSN": "Blowing snow",
            "BLDU": "Blowing dust",
            "BLSA": "Blowing sand",
            "IC": "Ice crystals",
            "GR": "Hail",
            "GS": "Snow pellets",
            "SN": "Snow",
            "PL": "Ice pellets",
            "RA": "Rain",
            "DZ": "Drizzle",
            "FZFG": "Freezing fog",
        }
        coverage_labels = {
            "FEW": "few",
            "SCT": "scattered",
            "BKN": "broken",
            "OVC": "overcast",
        }

        parts_list = []
        for wx, cov, hgt in matches:
            wx_label = wx_labels.get(wx, wx)
            cov_label = coverage_labels.get(cov, cov)
            height_ft = int(hgt) * 100
            parts_list.append(f"{wx_label} {cov_label} at {height_ft} feet")

        if parts_list:
            decoded.setdefault("Obscuration", "; ".join(parts_list))

    def _parse_acft_mshp(self, remarks: str, decoded: Dict) -> None:
        """Parse aircraft mishap report indicator — FMH-1 §12.7.1.x."""
        if re.search(r"\bACFT\s+MSHP\b", remarks, re.IGNORECASE):
            decoded["ACFT MSHP"] = "Aircraft mishap report"

    def _parse_nospeci(self, remarks: str, decoded: Dict) -> None:
        """Parse NOSPECI indicator — FMH-1 §12.7.1.y.

        Indicates this station does not issue SPECI (special) reports.
        """
        if re.search(r"\bNOSPECI\b", remarks, re.IGNORECASE):
            decoded["NOSPECI"] = "No SPECI reports issued at this station"
