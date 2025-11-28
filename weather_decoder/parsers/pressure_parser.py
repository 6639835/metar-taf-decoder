"""Pressure/altimeter information parser"""

import re
from typing import Dict, List, Optional

from ..utils.patterns import ALT_PATTERN, ALT_QNH_PATTERN, ALTIMETER_PATTERN, QNH_PATTERN


class PressureParser:
    """Parser for pressure/altimeter information in METAR and TAF reports"""

    @staticmethod
    def extract_altimeter(parts: List[str]) -> Optional[Dict]:
        """Extract altimeter information from METAR parts"""
        for i, part in enumerate(parts):
            match = re.match(ALTIMETER_PATTERN, part)
            if match:
                prefix = match.group(1)
                value = int(match.group(2))

                if prefix == "A":
                    # US format - inches of mercury in hundredths
                    altimeter = {"value": value / 100.0, "unit": "inHg"}
                else:  # Q prefix
                    # ICAO format - hectopascals
                    altimeter = {"value": value, "unit": "hPa"}

                parts.pop(i)
                return altimeter

        return None

    @staticmethod
    def extract_qnh(parts: List[str]) -> Optional[Dict]:
        """Extract QNH (pressure setting) information from TAF parts"""
        # Primary QNH pattern (Q followed by 4 digits)
        for i, part in enumerate(parts):
            match = re.match(QNH_PATTERN, part)
            if match:
                qnh_value = int(match.group(1))

                # For QNH in hPa, the value is typically between 900-1050
                if qnh_value >= 900 and qnh_value <= 1050:
                    unit = "hPa"
                else:
                    # For inches of mercury in hundredths (e.g., Q2992 = 29.92 inHg)
                    unit = "inHg"
                    qnh_value = qnh_value / 100.0  # Convert to decimal format

                qnh = {"value": qnh_value, "unit": unit}

                parts.pop(i)
                return qnh

        # Alternative QNH formats
        for i, part in enumerate(parts):
            match = re.match(ALT_QNH_PATTERN, part)
            if match:
                qnh_value = int(match.group(1))

                # Determine unit based on suffix
                unit = "inHg"
                if "HPa" in part:
                    unit = "hPa"

                # Format value based on unit
                formatted_value = qnh_value
                if unit == "inHg":
                    formatted_value = qnh_value / 100.0  # Convert to decimal format

                qnh = {"value": formatted_value, "unit": unit}

                parts.pop(i)
                return qnh

        # US-style altimeter format (A prefix)
        for i, part in enumerate(parts):
            match = re.match(ALT_PATTERN, part)
            if match:
                qnh_value = int(match.group(1))
                qnh_value = qnh_value / 100.0  # Convert to decimal format

                qnh = {"value": qnh_value, "unit": "inHg"}

                parts.pop(i)
                return qnh

        return None

    @staticmethod
    def parse_altimeter_string(alt_str: str) -> Optional[Dict]:
        """Parse an altimeter string directly"""
        match = re.match(ALTIMETER_PATTERN, alt_str)
        if match:
            prefix = match.group(1)
            value = int(match.group(2))

            if prefix == "A":
                # US format - inches of mercury in hundredths
                return {"value": value / 100.0, "unit": "inHg"}
            else:  # Q prefix
                # ICAO format - hectopascals
                return {"value": value, "unit": "hPa"}

        return None

    @staticmethod
    def parse_qnh_string(qnh_str: str) -> Optional[Dict]:
        """Parse a QNH string directly"""
        # Standard Q format
        match = re.match(QNH_PATTERN, qnh_str)
        if match:
            qnh_value = int(match.group(1))

            if qnh_value >= 900 and qnh_value <= 1050:
                unit = "hPa"
            else:
                unit = "inHg"
                qnh_value = qnh_value / 100.0

            return {"value": qnh_value, "unit": unit}

        # Alternative formats
        match = re.match(ALT_QNH_PATTERN, qnh_str)
        if match:
            qnh_value = int(match.group(1))
            unit = "hPa" if "HPa" in qnh_str else "inHg"

            if unit == "inHg":
                qnh_value = qnh_value / 100.0

            return {"value": qnh_value, "unit": unit}

        # A-prefix format
        match = re.match(ALT_PATTERN, qnh_str)
        if match:
            qnh_value = int(match.group(1)) / 100.0
            return {"value": qnh_value, "unit": "inHg"}

        return None
