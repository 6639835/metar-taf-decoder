"""Sky conditions parser"""

import re
from typing import Dict, List, Optional

from ..utils.constants import SKY_CONDITIONS, TREND_TYPES
from ..utils.patterns import SKY_PATTERN
from .base_parser import StopConditionMixin, TokenParser


class SkyParser(TokenParser, StopConditionMixin):
    """Parser for sky conditions in METAR and TAF reports
    
    Handles various sky condition formats:
    - Clear sky codes: SKC, CLR, NSC, NCD
    - Cloud layers: FEW, SCT, BKN, OVC with height
    - Vertical visibility: VV with height
    - Unknown values: /// for height or cloud type
    - Significant clouds: CB (cumulonimbus), TCU (towering cumulus)
    """

    # Stop parsing when we encounter trend indicators
    stop_tokens = TREND_TYPES

    def parse(self, token: str) -> Optional[Dict]:
        """Parse a sky condition token into structured data
        
        Args:
            token: A single token that may contain sky condition
            
        Returns:
            Dictionary with sky data if token matches, None otherwise
        """
        # Check for no cloud codes first
        if token in ["SKC", "CLR", "NSC", "NCD"]:
            return {"type": token, "height": None}

        # Check for sky condition pattern
        match = re.match(SKY_PATTERN, token)
        if not match:
            return None

        sky_type = match.group(1)
        height_str = match.group(2)
        cloud_type = match.group(3) or None

        # Parse height - can be /// when unknown, or 3 digits
        if height_str == "///":
            height = None
            unknown_height = True
        else:
            height = int(height_str) * 100  # Convert to feet
            unknown_height = False

        # Build sky dictionary
        sky: Dict = {"type": sky_type, "height": height}

        if unknown_height:
            sky["unknown_height"] = True

        # Handle cloud type modifiers
        if cloud_type == "CB":
            sky["cb"] = True
        elif cloud_type == "TCU":
            sky["tcu"] = True
        elif cloud_type == "///":
            sky["unknown_type"] = True

        return sky

    def extract_sky_conditions(self, parts: List[str]) -> List[Dict]:
        """Extract all sky conditions from weather report parts
        
        This method extracts all sky condition tokens until a stop
        token (trend indicator) is encountered.
        
        Args:
            parts: List of tokens from the weather report (modified in place)
            
        Returns:
            List of sky condition dictionaries
        """
        sky_conditions: List[Dict] = []

        i = 0
        while i < len(parts):
            # Stop if we encounter a trend indicator
            if self.should_stop(parts[i]):
                break

            # Try to parse the token
            sky = self.parse(parts[i])
            if sky is not None:
                sky_conditions.append(sky)
                parts.pop(i)
                # Don't increment i since we removed the current element
            else:
                i += 1

        return sky_conditions

    # Backwards compatibility alias
    def parse_sky_string(self, sky_str: str) -> Optional[Dict]:
        """Parse a single sky condition string (alias for parse())"""
        return self.parse(sky_str)

    @staticmethod
    def get_sky_description(sky_type: str) -> str:
        """Get human-readable description for sky condition type
        
        Args:
            sky_type: Sky condition code (e.g., 'SKC', 'FEW', 'SCT')
            
        Returns:
            Human-readable description
        """
        return SKY_CONDITIONS.get(sky_type, sky_type)
