"""Remarks section parser for METAR reports

This module handles parsing of the RMK (remarks) section in METAR reports.
The remarks section contains supplementary information not included in the
main body of the report.
"""

import re
from typing import Dict, Tuple

from ..utils.constants import (
    CLOUD_TYPE_CODES,
    DIRECTION_ABBREV,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    LOCATION_INDICATORS,
    PRESSURE_TENDENCY_CHARACTERISTICS,
    RUNWAY_BRAKING_REMARKS,
    RUNWAY_STATE_DEPOSIT_TYPES_REMARKS,
    RUNWAY_STATE_EXTENT_REMARKS,
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
            "Thunderstorm Location": ["TS OHD", "TS DSNT", "TS VC", "TS ALQDS", "TS MOV"],
            "ACSL": ["ACSL"],
            "Cloud Types": ["SC", "AC", "ST", "CU", "CB", "CI", "AS", "NS", "SN", "TCU", "CC", "CS"],
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
        self._parse_variable_visibility(remarks, decoded)
        self._parse_past_weather(remarks, decoded)
        self._parse_qfe(remarks, decoded)
        self._parse_altimeter_remarks(remarks, decoded)
        self._parse_precipitation_amount(remarks, decoded)
        self._parse_peak_wind(remarks, decoded)
        self._parse_surface_visibility(remarks, decoded)
        self._parse_tower_visibility(remarks, decoded)
        self._parse_lightning(remarks, decoded)
        self._parse_virga(remarks, decoded)
        self._parse_thunderstorm_location(remarks, decoded)
        self._parse_acsl(remarks, decoded)
        self._parse_cloud_types(remarks, decoded)
        self._parse_density_altitude(remarks, decoded)
        self._parse_obscuration(remarks, decoded)
        self._parse_ceiling(remarks, decoded)
        self._parse_pressure_change(remarks, decoded)
        self._parse_frontal_passage(remarks, decoded)
        self._parse_wind_shift(remarks, decoded)
        self._parse_slp_status(remarks, decoded)
        self._parse_rvr_status(remarks, decoded)
        self._parse_runway_state_remarks(remarks, decoded)
        self._parse_sensor_status(remarks, decoded)
        self._parse_maintenance_indicator(remarks, decoded, positions)

        # Sort decoded dict by position in original remarks string
        sorted_decoded = self._sort_by_position(remarks, decoded, positions)

        return remarks, sorted_decoded

    # =========================================================================
    # Station Information
    # =========================================================================

    def _parse_station_type(self, remarks: str, decoded: Dict, positions: Dict) -> None:
        """Parse station type (AO1/AO2)"""
        ao2_pos = remarks.find("AO2")
        ao1_pos = remarks.find("AO1")
        
        if ao2_pos >= 0:
            decoded["Station Type"] = "Automated station with precipitation discriminator"
            positions["Station Type"] = ao2_pos
        elif ao1_pos >= 0:
            decoded["Station Type"] = "Automated station without precipitation discriminator"
            positions["Station Type"] = ao1_pos

    # =========================================================================
    # Wind Information
    # =========================================================================

    def _parse_runway_winds(self, remarks: str, decoded: Dict) -> None:
        """Parse runway-specific wind information
        
        Handles both US format (WIND location dddssKT) and 
        ICAO/European format (RWYxx dddssKT [dddVddd])
        """
        # US format: WIND location dddss(G)KT
        wind_patterns = re.findall(
            r"WIND\s+(\w+)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", remarks
        )
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
        """Parse peak wind information (PK WND dddss/hhmm)"""
        pk_wnd_match = re.search(
            r"PK\s+WND\s+(\d{3})(\d{2,3})/(\d{2})(\d{2})", remarks
        )
        if pk_wnd_match:
            pk_direction = int(pk_wnd_match.group(1))
            pk_speed = int(pk_wnd_match.group(2))
            pk_hour = pk_wnd_match.group(3)
            pk_minute = pk_wnd_match.group(4)
            decoded["Peak Wind"] = f"{pk_direction}° at {pk_speed} KT at {pk_hour}:{pk_minute} UTC"

    def _parse_wind_shift(self, remarks: str, decoded: Dict) -> None:
        """Parse wind shift information (WSHFT hhmm)"""
        wshft_match = re.search(r"WSHFT\s+(\d{2})(\d{2})", remarks)
        if wshft_match:
            wshft_hour = wshft_match.group(1)
            wshft_min = wshft_match.group(2)
            decoded["wind_shift"] = {"time": f"{wshft_hour}:{wshft_min} UTC"}

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
            char_desc = PRESSURE_TENDENCY_CHARACTERISTICS.get(
                characteristic, f"Unknown ({characteristic})"
            )
            decoded["Pressure Tendency"] = f"{char_desc}; change: {change_hpa:.1f} hPa"

    def _parse_qfe(self, remarks: str, decoded: Dict) -> None:
        """Parse QFE (field elevation pressure)"""
        qfe_match = re.search(r"QFE(\d{3,4})", remarks)
        if qfe_match:
            qfe_value = int(qfe_match.group(1))
            decoded["QFE"] = f"{qfe_value} hPa"

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
        temp_extremes_match = re.search(
            r"(?<!\d)4([01])(\d{3})([01])(\d{3})(?!\d)", remarks
        )
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
        """Parse 6-hour precipitation (6xxxx format)"""
        precip_6hr_match = re.search(r"(?<!\d)6(\d{4})(?!\d)", remarks)
        if precip_6hr_match:
            precip_hundredths = int(precip_6hr_match.group(1))
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
        vis_match = re.search(r"VIS\s+(\d+(?:/\d+)?)V(\d+(?:/\d+)?)", remarks)
        if vis_match:
            min_vis_str = vis_match.group(1)
            max_vis_str = vis_match.group(2)

            min_vis = self._parse_visibility_fraction(min_vis_str)
            max_vis = self._parse_visibility_fraction(max_vis_str)

            min_vis_display = (
                str(int(min_vis)) if min_vis == int(min_vis) else min_vis_str
            )
            max_vis_display = (
                str(int(max_vis)) if max_vis == int(max_vis) else max_vis_str
            )

            decoded["Variable Visibility"] = (
                f"{min_vis_display} to {max_vis_display} statute miles"
            )

    def _parse_surface_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse surface visibility (SFC VIS vv)"""
        sfc_vis_match = re.search(r"SFC\s+VIS\s+(\d+(?:/\d+)?)", remarks)
        if sfc_vis_match:
            sfc_vis_str = sfc_vis_match.group(1)
            decoded["Surface Visibility"] = f"{sfc_vis_str} SM"

    def _parse_tower_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse tower visibility (TWR VIS vv)"""
        twr_vis_match = re.search(r"TWR\s+VIS\s+(\d+(?:/\d+)?)", remarks)
        if twr_vis_match:
            twr_vis_str = twr_vis_match.group(1)
            decoded["Tower Visibility"] = f"{twr_vis_str} SM"

    @staticmethod
    def _parse_visibility_fraction(vis_str: str) -> float:
        """Parse a visibility string that may contain a fraction"""
        if "/" in vis_str:
            num, den = vis_str.split("/")
            return float(num) / float(den)
        return float(vis_str)

    # =========================================================================
    # Weather Phenomena
    # =========================================================================

    def _parse_past_weather(self, remarks: str, decoded: Dict) -> None:
        """Parse past weather events (e.g., RAB11E24, FZRAB29E44)
        
        Format: [descriptor][phenomenon]B[time]E[time]...
        B = began, E = ended
        """
        past_weather_pattern = (
            r"(MI|PR|BC|DR|BL|SH|TS|FZ)?"
            r"(TS|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)"
            r"(?:[BE]\d{2})+"
        )
        past_weather_matches = re.finditer(past_weather_pattern, remarks)

        past_weather_events = []

        for match in past_weather_matches:
            full_match = match.group(0)
            descriptor = match.group(1) or ""
            phenomenon = match.group(2)

            # Build weather type string
            weather_parts = []
            if descriptor:
                weather_parts.append(
                    WEATHER_DESCRIPTORS.get(descriptor, descriptor.lower())
                )
            weather_parts.append(
                WEATHER_PHENOMENA.get(phenomenon, phenomenon.lower())
            )
            weather_type = " ".join(weather_parts)

            # Extract all B/E events
            events_str = full_match[len(descriptor) + len(phenomenon):]
            event_matches = re.findall(r"([BE])(\d{2})", events_str)

            # Build event descriptions
            event_descriptions = []
            for action, time in event_matches:
                action_text = "began" if action == "B" else "ended"
                event_descriptions.append(f"{action_text} at minute {time}")

            if event_descriptions:
                past_weather_events.append(
                    f"{weather_type} {', '.join(event_descriptions)}"
                )

        if past_weather_events:
            decoded["Past Weather"] = "; ".join(past_weather_events)

    def _parse_lightning(self, remarks: str, decoded: Dict) -> None:
        """Parse lightning information
        
        Format: [FRQ|OCNL|CONS] LTG[IC|CC|CG|CA]* [DSNT|VC|OHD] [directions]
        """
        ltg_match = re.search(
            r"(FRQ|OCNL|CONS)?\s*LTG((?:IC|CC|CG|CA)*)\s*"
            r"(?:(DSNT|VC|OHD)\s+)?"
            r"(?:(ALQDS)|"
            r"((?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?"
            r"(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)|"
            r"(DSNT|VC|OHD))(?=\s|$)",
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
                    lt = ltg_types[i:i + 2]
                    types.append(LIGHTNING_TYPES.get(lt, lt))
                ltg_parts.append(" and ".join(types) + " lightning")
            else:
                ltg_parts.append("lightning")

            # Distance/location
            distance = ltg_match.group(3) or ltg_match.group(6)
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
                for abbr, full in DIRECTION_ABBREV.items():
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
        
        Format: TS [DSNT|VC|OHD|ALQDS] [directions] [MOV direction]
        """
        ts_match = re.search(
            r"\bTS\s+(DSNT|VC|OHD|ALQDS)?\s*"
            r"((?:(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)"
            r"(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)?\s*"
            r"(?:MOV\s+((?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?))?",
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

            if direction:
                dir_text = direction
                for abbr, full in DIRECTION_ABBREV.items():
                    dir_text = dir_text.replace(abbr, full)
                dir_text = dir_text.replace("-", " to ").replace("AND", "and")
                ts_parts.append(f"to the {dir_text}")

            if movement:
                mov_text = movement
                for abbr, full in DIRECTION_ABBREV.items():
                    mov_text = mov_text.replace(abbr, full)
                mov_text = mov_text.replace("-", " to ")
                ts_parts.append(f"moving {mov_text}")

            decoded["Thunderstorm Location"] = " ".join(ts_parts)

    # =========================================================================
    # Cloud Information
    # =========================================================================

    def _parse_acsl(self, remarks: str, decoded: Dict) -> None:
        """Parse ACSL (Altocumulus Standing Lenticular) clouds"""
        acsl_match = re.search(
            r"ACSL\s*(DSNT|VC|OHD)?\s*([NSEW]+(?:-[NSEW]+)?)?\s*"
            r"(?:MOV\s+([NSEW]+(?:-[NSEW]+)?))?",
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

    def _parse_cloud_types(self, remarks: str, decoded: Dict) -> None:
        """Parse cloud type codes
        
        Handles:
        - Japanese/ICAO format: {oktas}{cloud_type}{height} e.g., 1CU007, 3SC015
        - Canadian format: {cloud_type}{oktas} e.g., SC6, AC3
        - Trace clouds: e.g., AC TR, CI TR
        """
        cloud_types_found = []

        # Japanese/ICAO format
        japan_cloud_matches = re.findall(
            r"\b(\d)(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d{3})\b", remarks
        )
        for oktas, cloud_code, height in japan_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            height_ft = int(height) * 100
            cloud_types_found.append(
                f"{cloud_name} {oktas}/8 sky coverage at {height_ft} feet"
            )

        # Canadian format (only if no Japanese format found)
        if not japan_cloud_matches:
            cloud_type_matches = re.findall(
                r"(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d)(?!\d{2})", remarks
            )
            for cloud_code, oktas in cloud_type_matches:
                cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
                cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage")

        # Trace cloud patterns
        trace_cloud_matches = re.findall(
            r"\b(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)\s+TR\b", remarks
        )
        for cloud_code in trace_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            cloud_types_found.append(
                f"{cloud_name} trace (less than 1/8 sky coverage)"
            )

        if cloud_types_found:
            decoded["Cloud Types"] = "; ".join(cloud_types_found)

    def _parse_ceiling(self, remarks: str, decoded: Dict) -> None:
        """Parse ceiling information (CIG xxx or CIG xxxVxxx)"""
        cig_match = re.search(r"\bCIG\s+(\d{3})(?:V(\d{3}))?", remarks)
        if cig_match:
            cig_low = int(cig_match.group(1)) * 100
            if cig_match.group(2):
                cig_high = int(cig_match.group(2)) * 100
                decoded["variable_ceiling"] = f"{cig_low} to {cig_high} feet"
            else:
                decoded["Ceiling"] = f"{cig_low} feet"

    def _parse_obscuration(self, remarks: str, decoded: Dict) -> None:
        """Parse obscuration remarks"""
        if re.search(r"\bMT\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"
        elif re.search(r"\bMTN\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountain obscured"
        elif re.search(r"\bMTNS\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"

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
        runway_state_rmk_match = re.search(
            r"(?<!\d)8(\d)(\d)(\d)(\d{2})(\d{2})(?!\d)", remarks
        )
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
            deposit_desc = RUNWAY_STATE_DEPOSIT_TYPES_REMARKS.get(
                deposit, f"Unknown ({deposit})"
            )

            # Extent of contamination
            extent_desc = RUNWAY_STATE_EXTENT_REMARKS.get(
                extent, f"Unknown ({extent})"
            )

            # Depth of deposit
            depth_val = int(depth_raw)
            depth_desc = self._decode_runway_depth(depth_val)

            # Braking action
            braking_val = int(braking_raw)
            braking_desc = self._decode_braking_action(braking_val, braking_raw)

            decoded["Runway State (Remarks)"] = (
                f"{runway_desc}: {deposit_desc}, {extent_desc} coverage, "
                f"depth {depth_desc}, braking {braking_desc}"
            )

    @staticmethod
    def _decode_runway_depth(depth_val: int) -> str:
        """Decode runway depth value"""
        if depth_val == 0:
            return "Less than 1mm"
        elif depth_val <= 90:
            return f"{depth_val}mm"
        elif depth_val == 92:
            return "10cm"
        elif depth_val == 93:
            return "15cm"
        elif depth_val == 94:
            return "20cm"
        elif depth_val == 95:
            return "25cm"
        elif depth_val == 96:
            return "30cm"
        elif depth_val == 97:
            return "35cm"
        elif depth_val == 98:
            return "40cm or more"
        elif depth_val == 99:
            return "Runway not operational"
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
        
        sensor_indicators = {
            "PWINO": "Present Weather Identifier not operational",
            "TSNO": "Thunderstorm sensor not operational",
            "FZRANO": "Freezing rain sensor not operational",
            "PNO": "Precipitation sensor not operational",
            "VISNO": "Visibility sensor not operational",
            "CHINO": "Ceiling height indicator not operational",
            "RVRNO": "RVR sensor not operational",
        }
        
        for code, description in sensor_indicators.items():
            if code in remarks:
                sensor_status.append(description)

        if sensor_status:
            decoded["Sensor Status"] = "; ".join(sensor_status)

    def _parse_maintenance_indicator(
        self, remarks: str, decoded: Dict, positions: Dict
    ) -> None:
        """Parse maintenance indicator ($)"""
        if "$" in remarks:
            decoded["Maintenance Indicator"] = "Station requires maintenance"
            positions["Maintenance Indicator"] = remarks.find("$")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _sort_by_position(
        self, remarks: str, decoded: Dict, positions: Dict
    ) -> Dict:
        """Sort decoded dict by position in original remarks string"""
        # Find positions for keys not already tracked
        for key in decoded:
            if key not in positions:
                patterns = self._key_patterns.get(key, [])
                min_pos = len(remarks)  # Default to end
                for pattern in patterns:
                    if pattern.startswith(r"") or any(
                        c in pattern for c in r"\d[]{}+*?"
                    ):
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
        return dict(
            sorted(decoded.items(), key=lambda x: positions.get(x[0], len(remarks)))
        )

