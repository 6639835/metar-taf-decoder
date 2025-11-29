"""Wind information parser"""

import re
from typing import Dict, List, Optional, Union

from ..utils.patterns import WIND_EXTREME_PATTERN, WIND_PATTERN, WIND_VAR_PATTERN
from .base_parser import TokenParser


class WindParser(TokenParser):
    """Parser for wind information in METAR and TAF reports

    Handles various wind formats:
    - Standard: dddssKT (e.g., 27015KT)
    - With gusts: dddssGggKT (e.g., 27015G25KT)
    - Variable direction: VRBssKT (e.g., VRB05KT)
    - Above limit: PddKT (e.g., P99KT)
    - Extreme: ABVssKT/MPS (e.g., ABV99KT)
    - Units: KT, MPS, KMH
    """

    def parse(self, token: str) -> Optional[Dict]:
        """Parse a wind token into structured data

        Args:
            token: A single token that may contain wind information

        Returns:
            Dictionary with wind data if token matches, None otherwise
        """
        # Check for extreme wind speed format (ABV49MPS, ABV99KT)
        extreme_match = re.match(WIND_EXTREME_PATTERN, token)
        if extreme_match:
            return {
                "direction": "VRB",
                "speed": int(extreme_match.group(1)),
                "unit": extreme_match.group(2),
                "above": True,
            }

        # Standard wind pattern
        match = re.match(WIND_PATTERN, token)
        if not match:
            return None

        # Check for P prefix (speed above limit)
        is_above = match.group(1) == "P"
        direction_str = match.group(2)
        speed = int(match.group(3))
        gust = int(match.group(5)) if match.group(5) else None

        # Determine unit
        unit = self._determine_unit(token)

        # Build wind dictionary
        wind: Dict[str, Union[str, int, bool, tuple]] = {
            "direction": "VRB" if direction_str == "VRB" else int(direction_str),
            "speed": speed,
            "unit": unit,
        }

        if is_above:
            wind["above"] = True

        if gust:
            wind["gust"] = gust

        return wind

    def extract_wind(self, parts: List[str]) -> Optional[Dict]:
        """Extract wind information from weather report parts

        This method extends the base extract() to also check for
        variable wind direction in the following token.

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            Dictionary with wind data if found, None otherwise
        """
        for i, part in enumerate(parts):
            wind = self.parse(part)
            if wind is not None:
                parts.pop(i)

                # Look for variable direction in the next part
                if i < len(parts):
                    var_dir = self.parse_variable_direction(parts[i])
                    if var_dir:
                        wind["variable_direction"] = var_dir
                        parts.pop(i)

                return wind

        return None

    @staticmethod
    def _determine_unit(token: str) -> str:
        """Determine the wind speed unit from the token"""
        if "KT" in token:
            return "KT"
        elif "MPS" in token:
            return "MPS"
        elif "KMH" in token:
            return "KMH"
        return "KT"  # Default

    @staticmethod
    def parse_variable_direction(var_str: str) -> Optional[tuple]:
        """Parse variable wind direction string (e.g., '240V340')

        Args:
            var_str: Token that may contain variable direction

        Returns:
            Tuple of (from_direction, to_direction) or None
        """
        match = re.match(WIND_VAR_PATTERN, var_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None

    # Backwards compatibility alias
    def parse_wind_string(self, wind_str: str) -> Optional[Dict]:
        """Parse a wind string directly (alias for parse())"""
        return self.parse(wind_str)
