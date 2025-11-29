"""Temperature information parser"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..utils.patterns import TEMPERATURE_PATTERN


class TemperatureParser:
    """Parser for temperature information in METAR and TAF reports

    Handles temperature formats:
    - METAR: TT/DD where TT is temperature, DD is dewpoint (e.g., 17/15, M03/M05)
    - TAF: TX/TN forecasts (e.g., TX25/1214Z, TNM02/1306Z)

    Note: This parser doesn't inherit from BaseParser because it returns
    a tuple (temperature, dewpoint) rather than a dictionary.
    """

    # Patterns for TAF temperature forecasts
    TX_PATTERN = re.compile(r"TX([M]?)(\d{2})/(\d{2})(\d{2})Z")
    TN_PATTERN = re.compile(r"TN([M]?)(\d{2})/(\d{2})(\d{2})Z")

    def parse(self, token: str) -> Optional[Tuple[float, Optional[float]]]:
        """Parse a temperature/dewpoint token

        Args:
            token: A single token that may contain temperature/dewpoint

        Returns:
            Tuple of (temperature, dewpoint) if token matches, None otherwise.
            Dewpoint may be None if not available in the token.
        """
        match = re.match(TEMPERATURE_PATTERN, token)
        if not match:
            return None

        # Parse temperature
        temp_sign = -1 if match.group(1) == "M" else 1
        temperature = temp_sign * int(match.group(2))

        # Parse dewpoint (optional)
        dewpoint: Optional[float] = None
        if match.group(4) is not None:
            dew_sign = -1 if match.group(3) == "M" else 1
            dewpoint = dew_sign * int(match.group(4))

        return (temperature, dewpoint)

    def extract_temperature_dewpoint(self, parts: List[str]) -> Tuple[Optional[float], Optional[float]]:
        """Extract temperature and dewpoint from METAR parts

        Handles:
        - Standard format: 17/15 (temp 17°C, dewpoint 15°C)
        - Negative values: M03/M05 (temp -3°C, dewpoint -5°C)
        - Missing dewpoint: 17/ (temp 17°C, dewpoint not available)

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            Tuple of (temperature, dewpoint), both may be None if not found
        """
        for i, part in enumerate(parts):
            result = self.parse(part)
            if result is not None:
                parts.pop(i)
                return result

        return (None, None)

    def extract_temperature_forecasts(self, parts: List[str], period: Dict) -> None:
        """Extract temperature forecasts from TAF period

        Extracts TX (maximum) and TN (minimum) temperature forecasts
        and adds them to the period dictionary.

        Args:
            parts: List of tokens from the weather report (modified in place)
            period: TAF period dictionary (modified in place with temperature data)
        """
        i = 0
        while i < len(parts):
            # Check for maximum temperature (TX)
            tx_match = self.TX_PATTERN.match(parts[i])
            if tx_match:
                temp_data = self._parse_taf_temp_match(tx_match, "max")
                self._add_temp_to_period(period, temp_data, "max")
                parts.pop(i)
                continue

            # Check for minimum temperature (TN)
            tn_match = self.TN_PATTERN.match(parts[i])
            if tn_match:
                temp_data = self._parse_taf_temp_match(tn_match, "min")
                self._add_temp_to_period(period, temp_data, "min")
                parts.pop(i)
                continue

            i += 1

    def _parse_taf_temp_match(self, match: re.Match, temp_type: str) -> Dict:
        """Parse a TAF temperature match into structured data

        Args:
            match: Regex match object from TX or TN pattern
            temp_type: Either "max" or "min"

        Returns:
            Dictionary with temperature value and forecast time
        """
        temp_sign = -1 if match.group(1) == "M" else 1
        temp_val = temp_sign * int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))

        temp_time = self._create_forecast_datetime(day, hour)

        return {
            "type": temp_type,
            "value": temp_val,
            "time": temp_time,
        }

    @staticmethod
    def _create_forecast_datetime(day: int, hour: int) -> datetime:
        """Create a datetime for a forecast time

        Args:
            day: Day of month
            hour: Hour (UTC)

        Returns:
            Datetime object for the forecast time
        """
        current_date = datetime.now(timezone.utc)
        year, month = current_date.year, current_date.month

        # Handle month rollover (forecast day > current day suggests previous month)
        if day > current_date.day:
            if month == 1:
                return datetime(year - 1, 12, day, hour, 0, tzinfo=timezone.utc)
            return datetime(year, month - 1, day, hour, 0, tzinfo=timezone.utc)

        return datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

    @staticmethod
    def _add_temp_to_period(period: Dict, temp_data: Dict, temp_type: str) -> None:
        """Add temperature data to a TAF period

        Args:
            period: TAF period dictionary (modified in place)
            temp_data: Parsed temperature data
            temp_type: Either "max" or "min"
        """
        list_key = f"temperature_{temp_type}_list"
        single_key = f"temperature_{temp_type}"
        time_key = f"temperature_{temp_type}_time"

        # Initialize list if needed
        if list_key not in period:
            period[list_key] = []

        # Add to list
        period[list_key].append(
            {
                "value": temp_data["value"],
                "time": temp_data["time"],
            }
        )

        # Set single values for backward compatibility
        period[single_key] = temp_data["value"]
        period[time_key] = temp_data["time"]

    # Backwards compatibility aliases
    def parse_temperature_string(self, temp_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse a temperature/dewpoint string directly"""
        result = self.parse(temp_str)
        return result if result else (None, None)

    def parse_taf_temperature_string(self, temp_str: str) -> Optional[Dict]:
        """Parse a TAF temperature forecast string"""
        tx_match = self.TX_PATTERN.match(temp_str)
        if tx_match:
            return self._parse_taf_temp_match(tx_match, "max")

        tn_match = self.TN_PATTERN.match(temp_str)
        if tn_match:
            return self._parse_taf_temp_match(tn_match, "min")

        return None
