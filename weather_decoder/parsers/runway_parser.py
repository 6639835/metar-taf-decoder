"""Runway information parser

This module handles parsing of runway-related information in METAR reports:
- Runway Visual Range (RVR)
- Runway State Reports (MOTNE format)
"""

import re
from typing import Dict, List, Optional

from ..constants.runway_codes import (
    RUNWAY_BRAKING,
    RUNWAY_DEPOSIT_TYPES,
    RUNWAY_EXTENT,
    RVR_TRENDS,
)

# Regex patterns for runway parsing
RVR_PATTERN = r"R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$"
RUNWAY_STATE_PATTERN = r"R(\d{2}[LCR]?)/(\d|/)(\d|/)(\d{2}|//)(\d{2}|//)$"


class RunwayParser:
    """Parser for runway information in METAR reports

    Handles:
    - RVR (Runway Visual Range) reports
    - Runway state reports (MOTNE format)
    """

    def extract_rvr(self, parts: List[str]) -> List[Dict]:
        """Extract runway visual range information

        RVR format per ICAO: R{runway}/{M|P}{value}{V{M|P}{value}}{FT}{trend}
        - M = less than (Minus/below minimum)
        - P = more than (Plus/above maximum)
        - FT suffix indicates feet (US format), otherwise meters (ICAO default)
        - Trend: U = improving (Up), D = deteriorating (Down), N = no change

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            List of RVR dictionaries
        """
        rvr_list: List[Dict] = []

        i = 0
        while i < len(parts):
            match = re.match(RVR_PATTERN, parts[i])
            if match:
                rvr = self._parse_rvr_match(match, parts[i])
                rvr_list.append(rvr)
                parts.pop(i)
            else:
                i += 1

        return rvr_list

    def _parse_rvr_match(self, match: re.Match, original: str) -> Dict:
        """Parse an RVR regex match into structured data

        Args:
            match: Regex match object
            original: Original token string

        Returns:
            RVR dictionary
        """
        runway = match.group(1)
        modifier1 = match.group(2)  # M or P for first value
        visual_range = int(match.group(3))
        modifier2 = match.group(4)  # M or P for variable value
        variable_range = int(match.group(5)) if match.group(5) else None
        trend = match.group(6)

        # Determine unit: FT if explicitly stated, otherwise meters (ICAO default)
        unit = "FT" if "FT" in original else "M"

        rvr: Dict = {
            "runway": runway,
            "visual_range": visual_range,
            "unit": unit,
            "is_less_than": modifier1 == "M",
            "is_more_than": modifier1 == "P",
        }

        if variable_range:
            rvr["variable_range"] = variable_range
            rvr["variable_less_than"] = modifier2 == "M" if modifier2 else False
            rvr["variable_more_than"] = modifier2 == "P" if modifier2 else False

        if trend:
            rvr["trend"] = RVR_TRENDS.get(trend, trend)

        return rvr

    def extract_runway_state(self, parts: List[str]) -> List[Dict]:
        """Extract runway state reports (MOTNE format)

        Format: R{runway}/{deposit}{extent}{depth}{braking}
        Example: R23/490156 = Runway 23, dry snow (4), >51% coverage (9),
                             01mm depth, braking coefficient 0.56

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            List of runway state dictionaries
        """
        state_list: List[Dict] = []

        i = 0
        while i < len(parts):
            match = re.match(RUNWAY_STATE_PATTERN, parts[i])
            if match:
                state = self._parse_runway_state_match(match, parts[i])
                state_list.append(state)
                parts.pop(i)
            else:
                i += 1

        return state_list

    def _parse_runway_state_match(self, match: re.Match, original: str) -> Dict:
        """Parse a runway state regex match into structured data

        Args:
            match: Regex match object
            original: Original token string

        Returns:
            Runway state dictionary
        """
        runway = match.group(1)
        deposit = match.group(2)
        extent = match.group(3)
        depth_raw = match.group(4)
        braking_raw = match.group(5)

        # Decode components
        deposit_desc = RUNWAY_DEPOSIT_TYPES.get(deposit, f"unknown ({deposit})")
        extent_desc = RUNWAY_EXTENT.get(extent, f"unknown ({extent})")
        depth_desc = self._decode_depth(depth_raw)
        braking_desc = self._decode_braking(braking_raw)

        return {
            "runway": runway,
            "deposit": deposit_desc,
            "contamination": extent_desc,
            "depth": depth_desc,
            "braking": braking_desc,
            "raw": original,
        }

    @staticmethod
    def _decode_depth(depth_raw: str) -> str:
        """Decode runway depth value

        Args:
            depth_raw: Raw depth code (2 characters)

        Returns:
            Human-readable depth description
        """
        if depth_raw == "//":
            return "not reported"
        elif depth_raw == "00":
            return "less than 1mm"

        try:
            depth_val = int(depth_raw)
        except ValueError:
            return f"unknown ({depth_raw})"

        if depth_val <= 90:
            return f"{depth_val}mm"

        # Special codes for larger depths
        depth_codes = {
            92: "10cm",
            93: "15cm",
            94: "20cm",
            95: "25cm",
            96: "30cm",
            97: "35cm",
            98: "40cm or more",
            99: "runway not operational",
        }
        return depth_codes.get(depth_val, f"unknown ({depth_raw})")

    @staticmethod
    def _decode_braking(braking_raw: str) -> str:
        """Decode runway braking action/friction coefficient

        Args:
            braking_raw: Raw braking code (2 characters)

        Returns:
            Human-readable braking description
        """
        if braking_raw == "//":
            return "not reported"

        if braking_raw in RUNWAY_BRAKING:
            return RUNWAY_BRAKING[braking_raw]

        # Numeric braking coefficient (01-90 = 0.01 to 0.90)
        try:
            coef = int(braking_raw) / 100
            return f"coefficient {coef:.2f}"
        except ValueError:
            return f"unknown ({braking_raw})"

    def parse_rvr_string(self, rvr_str: str) -> Optional[Dict]:
        """Parse a single RVR string

        Args:
            rvr_str: RVR string to parse

        Returns:
            RVR dictionary or None if no match
        """
        match = re.match(RVR_PATTERN, rvr_str)
        if match:
            return self._parse_rvr_match(match, rvr_str)
        return None

    def parse_runway_state_string(self, state_str: str) -> Optional[Dict]:
        """Parse a single runway state string

        Args:
            state_str: Runway state string to parse

        Returns:
            Runway state dictionary or None if no match
        """
        match = re.match(RUNWAY_STATE_PATTERN, state_str)
        if match:
            return self._parse_runway_state_match(match, state_str)
        return None
