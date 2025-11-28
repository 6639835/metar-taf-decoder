"""Temperature information parser"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..utils.patterns import TAF_TEMPERATURE_PATTERN, TEMPERATURE_PATTERN


class TemperatureParser:
    """Parser for temperature information in METAR and TAF reports"""

    @staticmethod
    def extract_temperature_dewpoint(parts: List[str]) -> Tuple[Optional[float], Optional[float]]:
        """Extract temperature and dewpoint from METAR parts

        Handles:
        - Standard format: 17/15 (temp 17°C, dewpoint 15°C)
        - Negative values: M03/M05 (temp -3°C, dewpoint -5°C)
        - Missing dewpoint: 17/ (temp 17°C, dewpoint not available)
        """
        for i, part in enumerate(parts):
            match = re.match(TEMPERATURE_PATTERN, part)
            if match:
                temp_sign = -1 if match.group(1) == "M" else 1
                temp_value = int(match.group(2))
                temperature = temp_sign * temp_value

                # Dewpoint is optional (group 3 is sign, group 4 is value)
                if match.group(4) is not None:
                    dew_sign = -1 if match.group(3) == "M" else 1
                    dew_value = int(match.group(4))
                    dewpoint = dew_sign * dew_value
                else:
                    dewpoint = None

                parts.pop(i)
                return temperature, dewpoint

        return None, None

    @staticmethod
    def extract_temperature_forecasts(parts: List[str], period: Dict) -> None:
        """Extract temperature forecasts from TAF period"""
        i = 0
        while i < len(parts):
            # Check for temperature pattern TXM05/0612Z TNM10/0709Z
            tx_match = re.match(r"TX([M]?)(\d{2})/(\d{2})(\d{2})Z", parts[i])
            if tx_match:
                temp_sign = -1 if tx_match.group(1) == "M" else 1
                temp_val = int(tx_match.group(2))
                day = int(tx_match.group(3))
                hour = int(tx_match.group(4))

                # Create datetime
                current_date = datetime.now(timezone.utc)
                year, month = current_date.year, current_date.month
                temp_time = datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

                # Handle month rollover
                if day > current_date.day:
                    if month == 1:
                        temp_time = datetime(year - 1, 12, day, hour, 0, tzinfo=timezone.utc)
                    else:
                        temp_time = datetime(year, month - 1, day, hour, 0, tzinfo=timezone.utc)

                # Initialize temperature_max_list if it doesn't exist
                if "temperature_max_list" not in period:
                    period["temperature_max_list"] = []

                # Add this temperature to the list
                period["temperature_max_list"].append({"value": temp_sign * temp_val, "time": temp_time})

                # Also set temperature_max for backward compatibility
                period["temperature_max"] = temp_sign * temp_val
                period["temperature_max_time"] = temp_time

                parts.pop(i)
                continue

            tn_match = re.match(r"TN([M]?)(\d{2})/(\d{2})(\d{2})Z", parts[i])
            if tn_match:
                temp_sign = -1 if tn_match.group(1) == "M" else 1
                temp_val = int(tn_match.group(2))
                day = int(tn_match.group(3))
                hour = int(tn_match.group(4))

                # Create datetime
                current_date = datetime.now(timezone.utc)
                year, month = current_date.year, current_date.month
                temp_time = datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

                # Handle month rollover
                if day > current_date.day:
                    if month == 1:
                        temp_time = datetime(year - 1, 12, day, hour, 0, tzinfo=timezone.utc)
                    else:
                        temp_time = datetime(year, month - 1, day, hour, 0, tzinfo=timezone.utc)

                # Initialize temperature_min_list if it doesn't exist
                if "temperature_min_list" not in period:
                    period["temperature_min_list"] = []

                # Add this temperature to the list
                period["temperature_min_list"].append({"value": temp_sign * temp_val, "time": temp_time})

                # Also set temperature_min for backward compatibility
                period["temperature_min"] = temp_sign * temp_val
                period["temperature_min_time"] = temp_time

                parts.pop(i)
                continue

            i += 1

    @staticmethod
    def parse_temperature_string(temp_str: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse a temperature/dewpoint string directly"""
        match = re.match(TEMPERATURE_PATTERN, temp_str)
        if match:
            temp_sign = -1 if match.group(1) == "M" else 1
            temp_value = int(match.group(2))
            temperature = temp_sign * temp_value

            # Dewpoint is optional
            if match.group(4) is not None:
                dew_sign = -1 if match.group(3) == "M" else 1
                dew_value = int(match.group(4))
                dewpoint = dew_sign * dew_value
            else:
                dewpoint = None

            return temperature, dewpoint

        return None, None

    @staticmethod
    def parse_taf_temperature_string(temp_str: str) -> Optional[Dict]:
        """Parse a TAF temperature forecast string"""
        tx_match = re.match(r"TX([M]?)(\d{2})/(\d{2})(\d{2})Z", temp_str)
        if tx_match:
            temp_sign = -1 if tx_match.group(1) == "M" else 1
            temp_val = int(tx_match.group(2))
            day = int(tx_match.group(3))
            hour = int(tx_match.group(4))

            current_date = datetime.now(timezone.utc)
            year, month = current_date.year, current_date.month
            temp_time = datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

            # Handle month rollover
            if day > current_date.day:
                if month == 1:
                    temp_time = datetime(year - 1, 12, day, hour, 0, tzinfo=timezone.utc)
                else:
                    temp_time = datetime(year, month - 1, day, hour, 0, tzinfo=timezone.utc)

            return {"type": "max", "value": temp_sign * temp_val, "time": temp_time}

        tn_match = re.match(r"TN([M]?)(\d{2})/(\d{2})(\d{2})Z", temp_str)
        if tn_match:
            temp_sign = -1 if tn_match.group(1) == "M" else 1
            temp_val = int(tn_match.group(2))
            day = int(tn_match.group(3))
            hour = int(tn_match.group(4))

            current_date = datetime.now(timezone.utc)
            year, month = current_date.year, current_date.month
            temp_time = datetime(year, month, day, hour, 0, tzinfo=timezone.utc)

            # Handle month rollover
            if day > current_date.day:
                if month == 1:
                    temp_time = datetime(year - 1, 12, day, hour, 0, tzinfo=timezone.utc)
                else:
                    temp_time = datetime(year, month - 1, day, hour, 0, tzinfo=timezone.utc)

            return {"type": "min", "value": temp_sign * temp_val, "time": temp_time}

        return None
