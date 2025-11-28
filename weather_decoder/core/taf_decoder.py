"""Main TAF decoder that orchestrates parsing"""

import re
from datetime import datetime, timezone
from typing import Dict, List

from ..data.taf_data import TafData
from ..parsers.pressure_parser import PressureParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..utils.constants import CHANGE_INDICATORS
from ..utils.patterns import COMPILED_PATTERNS, FM_PATTERN


class TafDecoder:
    """TAF decoder class that parses raw TAF strings"""

    def __init__(self):
        """Initialize the TAF decoder"""
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.pressure_parser = PressureParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()

    def decode(self, raw_taf: str) -> TafData:
        """
        Decode a raw TAF string into structured data

        Args:
            raw_taf: The raw TAF string to decode

        Returns:
            TafData: A structured object containing all decoded TAF components
        """
        taf = raw_taf.strip()

        # Preprocess: insert spaces between tokens that might be stuck together
        taf = self._preprocess_taf(taf)

        parts = taf.split()

        # Extract header elements
        station_id, issue_time, valid_period = self._extract_header(parts)

        # Extract forecast periods
        forecast_periods = self._decode_forecast_periods(taf)

        # Extract remarks section
        remarks, remarks_decoded = self._decode_remarks(taf)

        # Create and return the TafData object
        return TafData(
            raw_taf=raw_taf,
            station_id=station_id,
            issue_time=issue_time,
            valid_period=valid_period,
            forecast_periods=forecast_periods,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
        )

    def _preprocess_taf(self, taf: str) -> str:
        """Preprocess TAF string to insert spaces between tokens that might be stuck together"""
        # Handle FM format first (most common issue)
        taf = re.sub(r"(\S)FM(\d{6})", r"\1 FM\2", taf)
        taf = re.sub(r"FM(\d{6})(\S)", r"FM\1 \2", taf)

        # Insert space before change indicators
        for indicator in CHANGE_INDICATORS:
            pattern = r"(\S)(" + indicator + r")"
            taf = re.sub(pattern, r"\1 \2", taf)

        # Insert space before cloud cover indicators
        for cloud_type in ["FEW", "SCT", "BKN", "OVC"]:
            pattern = r"(\S)(" + cloud_type + r")"
            taf = re.sub(pattern, r"\1 \2", taf)

        # Fix PROB pattern
        taf = re.sub(r"PROB(\d{2})(\S)", r"PROB\1 \2", taf)

        return taf

    def _extract_header(self, parts: List[str]) -> tuple:
        """Extract TAF header information"""
        header_parts = []

        # Extract TAF indicator if present
        if parts and (parts[0] == "TAF" or parts[0] == "TAF AMD"):
            header_parts.append(parts.pop(0))
            if parts and parts[0] == "AMD":
                header_parts.append(parts.pop(0))

        # Extract station ID (ICAO code)
        station_id = ""
        if parts and COMPILED_PATTERNS["station_id"].match(parts[0]):
            station_id = parts.pop(0)
            header_parts.append(station_id)

        # Extract issue time
        issue_time = datetime.now(timezone.utc)
        if parts and re.match(r"\d{6}Z", parts[0]):
            time_str = parts.pop(0)
            header_parts.append(time_str)
            issue_time = self.time_parser.parse_observation_time(time_str) or issue_time

        # Extract valid period
        valid_period = {"from": datetime.now(timezone.utc), "to": datetime.now(timezone.utc)}
        if parts and COMPILED_PATTERNS["valid_period"].match(parts[0]):
            period_str = parts.pop(0)
            header_parts.append(period_str)
            valid_period = self.time_parser.parse_valid_period(period_str) or valid_period

        return station_id, issue_time, valid_period

    def _decode_forecast_periods(self, taf: str) -> List[Dict]:
        """Extract and decode each forecast period in the TAF"""
        # Remove remarks section first
        main_taf = taf
        if "RMK" in taf:
            main_taf = taf[: taf.index("RMK")]

        parts = main_taf.split()

        # Skip header information
        header_end = self._find_header_end(parts)

        # Find all change group indices
        change_indices = self._find_change_indices(parts, header_end)
        change_indices.append(len(parts))

        forecast_periods = []

        # Process initial forecast
        if header_end < change_indices[0]:
            initial_elements = parts[header_end : change_indices[0]]
            initial_forecast = {"change_type": "MAIN"}
            self._extract_forecast_elements(initial_elements, initial_forecast)
            forecast_periods.append(initial_forecast)

        # Process change groups
        for i in range(len(change_indices) - 1):
            start_idx = change_indices[i]
            end_idx = change_indices[i + 1]

            period = self._process_change_group(parts, start_idx, end_idx)
            if period:
                forecast_periods.append(period)

        return forecast_periods

    def _find_header_end(self, parts: List[str]) -> int:
        """Find where the header ends and forecast data begins"""
        header_end = 0
        for i, part in enumerate(parts):
            if (
                part == "TAF"
                or part == "TAF AMD"
                or COMPILED_PATTERNS["station_id"].match(part)
                or re.match(r"\d{6}Z", part)
                or COMPILED_PATTERNS["valid_period"].match(part)
            ):
                header_end = i + 1
            else:
                break
        return header_end

    def _find_change_indices(self, parts: List[str], header_end: int) -> List[int]:
        """Find indices where change groups start"""
        change_indices = []
        for i in range(header_end, len(parts)):
            if parts[i] in ["TEMPO", "BECMG"] or parts[i].startswith("PROB") or re.match(FM_PATTERN, parts[i]):
                change_indices.append(i)
        return change_indices

    def _process_change_group(self, parts: List[str], start_idx: int, end_idx: int) -> Dict:
        """Process a single change group"""
        change_indicator = parts[start_idx]
        period = {}

        if change_indicator == "TEMPO":
            period["change_type"] = "TEMPO"
            period = self._process_time_range_group(parts, start_idx, end_idx, period)
        elif change_indicator == "BECMG":
            period["change_type"] = "BECMG"
            period = self._process_time_range_group(parts, start_idx, end_idx, period)
        elif change_indicator.startswith("PROB"):
            period["change_type"] = "PROB"
            period["probability"] = int(change_indicator[4:])
            period = self._process_time_range_group(parts, start_idx, end_idx, period)
        elif re.match(FM_PATTERN, change_indicator):
            period["change_type"] = "FM"
            from_time = self.time_parser.parse_fm_time(change_indicator)
            if from_time:
                period["from_time"] = from_time
            self._extract_forecast_elements(parts[start_idx + 1 : end_idx], period)

        return period

    def _process_time_range_group(self, parts: List[str], start_idx: int, end_idx: int, period: Dict) -> Dict:
        """Process a change group that may have a time range"""
        # Check for time range
        if start_idx + 1 < len(parts) and re.match(r"\d{4}/\d{4}", parts[start_idx + 1]):
            time_group = parts[start_idx + 1]
            from_time, to_time = self.time_parser.parse_time_range(time_group)
            period["from_time"] = from_time
            period["to_time"] = to_time
            self._extract_forecast_elements(parts[start_idx + 2 : end_idx], period)
        else:
            self._extract_forecast_elements(parts[start_idx + 1 : end_idx], period)

        return period

    def _extract_forecast_elements(self, parts: List[str], period: Dict) -> None:
        """Extract all forecast elements from a section of parts"""
        working_parts = parts.copy()

        # Extract wind
        wind = self.wind_parser.extract_wind(working_parts)
        if wind:
            period["wind"] = wind

        # Extract visibility
        visibility = self.visibility_parser.extract_visibility(working_parts)
        if visibility:
            period["visibility"] = visibility

        # Extract weather phenomena
        weather_groups = self.weather_parser.extract_weather(working_parts)
        if weather_groups:
            period["weather_groups"] = weather_groups

        # Extract sky conditions
        sky_conditions = self.sky_parser.extract_sky_conditions(working_parts)
        if sky_conditions:
            period["sky_conditions"] = sky_conditions

        # Extract QNH (pressure setting)
        qnh = self.pressure_parser.extract_qnh(working_parts)
        if qnh:
            period["qnh"] = qnh

        # Extract temperature forecasts
        self.temperature_parser.extract_temperature_forecasts(working_parts, period)

        # Store any unprocessed parts for debugging
        if working_parts:
            if "debug_info" not in period:
                period["debug_info"] = {}
            period["debug_info"]["unprocessed_parts"] = working_parts.copy()

    def _decode_remarks(self, taf: str) -> tuple:
        """Extract and decode the remarks section"""
        match = re.search(r"RMK\s+(.+)$", taf)
        if match:
            remarks = match.group(1)

            # Decode common remarks patterns
            decoded = {}

            # Next forecast information
            nxt_fcst_match = re.search(r"NXT\s+FCST\s+BY\s+(\d{2})Z", remarks)
            if nxt_fcst_match:
                decoded["Next Forecast"] = f"Next forecast will be issued by {nxt_fcst_match.group(1)}:00 UTC"

            # Lightning observations
            if "LTG OBS" in remarks:
                decoded["Lightning"] = "Lightning observed in vicinity"

            # Process individual remark codes
            remark_codes = remarks.split()
            for code in remark_codes:
                if code.startswith("WS"):
                    decoded["Wind Shear"] = "Wind shear reported"
                elif code in ["CNF", "CNF+", "CNF-"]:
                    confidence = {"CNF": "normal", "CNF+": "high", "CNF-": "low"}
                    decoded["Forecast Confidence"] = confidence[code]
                elif code == "AMD":
                    decoded["Amendment"] = "Forecast has been amended"
                elif code == "COR":
                    decoded["Correction"] = "Correction to previously issued forecast"

            return remarks, decoded
        else:
            return "", {}
