"""Pressure/altimeter information parser"""

import re
from typing import Dict, List, Optional, Union

from ..utils.patterns import ALT_PATTERN, ALT_QNH_PATTERN, ALTIMETER_PATTERN, QNH_PATTERN
from .base_parser import TokenParser


class PressureParser(TokenParser):
    """Parser for pressure/altimeter information in METAR and TAF reports
    
    Handles various pressure formats:
    - US altimeter: Axxxx (e.g., A2992 = 29.92 inHg)
    - ICAO QNH: Qxxxx (e.g., Q1013 = 1013 hPa)
    - Alternative: QNHxxxxINS/HPa
    """

    def parse(self, token: str) -> Optional[Dict]:
        """Parse a pressure/altimeter token into structured data
        
        Args:
            token: A single token that may contain pressure information
            
        Returns:
            Dictionary with pressure data if token matches, None otherwise
        """
        # Standard A/Q format
        match = re.match(ALTIMETER_PATTERN, token)
        if match:
            prefix = match.group(1)
            value = int(match.group(2))

            if prefix == "A":
                return {"value": value / 100.0, "unit": "inHg"}
            else:  # Q prefix
                return {"value": value, "unit": "hPa"}

        return None

    def parse_qnh(self, token: str) -> Optional[Dict]:
        """Parse a QNH pressure token
        
        QNH can appear in multiple formats in TAF reports.
        
        Args:
            token: A single token that may contain QNH information
            
        Returns:
            Dictionary with QNH data if token matches, None otherwise
        """
        # Primary QNH pattern (Q followed by 4 digits)
        match = re.match(QNH_PATTERN, token)
        if match:
            qnh_value: Union[int, float] = int(match.group(1))

            # Determine unit based on value range
            if 900 <= qnh_value <= 1050:
                return {"value": qnh_value, "unit": "hPa"}
            else:
                return {"value": qnh_value / 100.0, "unit": "inHg"}

        # Alternative QNH format (QNHxxxxINS/HPa)
        match = re.match(ALT_QNH_PATTERN, token)
        if match:
            qnh_value = int(match.group(1))
            unit = "hPa" if "HPa" in token else "inHg"

            if unit == "inHg":
                return {"value": qnh_value / 100.0, "unit": unit}
            return {"value": qnh_value, "unit": unit}

        # US-style altimeter format (A prefix)
        match = re.match(ALT_PATTERN, token)
        if match:
            return {"value": int(match.group(1)) / 100.0, "unit": "inHg"}

        return None

    def extract_altimeter(self, parts: List[str]) -> Optional[Dict]:
        """Extract altimeter information from METAR parts
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            Dictionary with altimeter data if found, None otherwise
        """
        for i, part in enumerate(parts):
            result = self.parse(part)
            if result is not None:
                parts.pop(i)
                return result
        return None

    def extract_qnh(self, parts: List[str]) -> Optional[Dict]:
        """Extract QNH (pressure setting) information from TAF parts
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            Dictionary with QNH data if found, None otherwise
        """
        for i, part in enumerate(parts):
            result = self.parse_qnh(part)
            if result is not None:
                parts.pop(i)
                return result
        return None

    # Backwards compatibility aliases
    def parse_altimeter_string(self, alt_str: str) -> Optional[Dict]:
        """Parse an altimeter string directly (alias for parse())"""
        return self.parse(alt_str)

    def parse_qnh_string(self, qnh_str: str) -> Optional[Dict]:
        """Parse a QNH string directly (alias for parse_qnh())"""
        return self.parse_qnh(qnh_str)
