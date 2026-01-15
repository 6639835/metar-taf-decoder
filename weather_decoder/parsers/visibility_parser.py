"""Visibility information parser"""

import re
from typing import Dict, List, Optional, Union

from .base_parser import TokenParser


class VisibilityParser(TokenParser):
    """Parser for visibility information in METAR and TAF reports

    Handles various visibility formats:
    - CAVOK (Ceiling And Visibility OK)
    - 4-digit meter format (e.g., 1200, 9999, 0000)
    - SM format with fractions (e.g., 1/2SM, 3SM, P6SM, M1/4SM)
    - Mixed fractions (e.g., 1 1/2SM = 1.5 SM)
    - Directional visibility (e.g., 4000NE, 2000 1200NW)
    - NDV (No Directional Variation)
    """

    # Valid direction suffixes
    DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def parse(self, token: str) -> Optional[Dict]:
        """Parse a visibility token into structured data

        Args:
            token: A single token that may contain visibility information

        Returns:
            Dictionary with visibility data if token matches, None otherwise
        """
        # Check for CAVOK
        if token == "CAVOK":
            return {"value": 9999, "unit": "M", "is_cavok": True}

        # Check for visibility with directional suffix (e.g., 4000NE)
        dir_match = re.match(r"^(\d{4})(N|NE|E|SE|S|SW|W|NW)$", token)
        if dir_match:
            return {
                "value": int(dir_match.group(1)),
                "unit": "M",
                "is_cavok": False,
                "direction": dir_match.group(2),
            }

        # Check for standard 4-digit meter format
        if len(token) == 4 and token.isdigit():
            value = int(token)
            result: Dict[str, Union[int, str, bool]] = {"value": value, "unit": "M", "is_cavok": False}
            if value == 0:
                result["is_less_than"] = True
            return result

        # Check for NDV format (e.g., 9999NDV)
        if token.endswith("NDV"):
            numeric_part = token[:-3]
            if numeric_part.isdigit() and len(numeric_part) == 4:
                return {
                    "value": int(numeric_part),
                    "unit": "M",
                    "is_cavok": False,
                    "ndv": True,
                }

        # Check for SM format with optional M/P prefix
        sm_match = re.match(r"^([PM])?(\d+)(?:/(\d+))?SM$", token)
        if sm_match:
            return self._parse_sm_visibility(sm_match)

        return None

    def _parse_sm_visibility(self, match: re.Match) -> Dict:
        """Parse a statute miles visibility match

        Args:
            match: Regex match object from SM pattern

        Returns:
            Dictionary with visibility data
        """
        modifier = match.group(1)
        numerator = int(match.group(2))
        denominator = int(match.group(3)) if match.group(3) else 1

        result: Dict[str, Union[float, str, bool]] = {
            "value": numerator / denominator,
            "unit": "SM",
            "is_cavok": False,
        }

        if modifier == "P":
            result["is_greater_than"] = True
        elif modifier == "M":
            result["is_less_than"] = True

        return result

    def extract_visibility(self, parts: List[str]) -> Optional[Dict]:
        """Extract visibility information from weather report parts

        This method handles complex multi-token visibility formats like
        "1 1/2SM" (mixed fractions) and "2000 1200NW" (with directional).

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            Dictionary with visibility data if found, None otherwise
        """
        for i, part in enumerate(parts):
            # Try simple single-token parse first
            result = self.parse(part)

            if result is not None:
                parts.pop(i)

                # For 4-digit meter visibility, check for additional info
                if result.get("unit") == "M" and not result.get("is_cavok"):
                    self._check_additional_visibility(parts, i, result)

                return result

            # Check for mixed fraction SM visibility (e.g., "1 1/2SM")
            if part.isdigit() and i + 1 < len(parts):
                frac_match = re.match(r"^(\d+)/(\d+)SM$", parts[i + 1])
                if frac_match:
                    whole = int(part)
                    numerator = int(frac_match.group(1))
                    denominator = int(frac_match.group(2))

                    parts.pop(i)  # Remove whole number
                    parts.pop(i)  # Remove fraction (now at index i)
                    return {
                        "value": whole + (numerator / denominator),
                        "unit": "SM",
                        "is_cavok": False,
                    }

        return None

    def _check_additional_visibility(self, parts: List[str], i: int, result: Dict) -> None:
        """Check for additional visibility information after main value

        Handles:
        - Directional visibility (e.g., "2000 1200NW")
        - Minimum visibility (e.g., "4000 0600")

        Args:
            parts: List of remaining tokens (may be modified)
            i: Current index in parts list
            result: Visibility result dictionary (modified in place)
        """
        if i >= len(parts):
            return

        # Check for directional visibility
        next_dir_match = re.match(r"^(\d{4})(N|NE|E|SE|S|SW|W|NW)$", parts[i])
        if next_dir_match:
            result["directional_visibility"] = {
                "value": int(next_dir_match.group(1)),
                "direction": next_dir_match.group(2),
            }
            parts.pop(i)
        # Check for minimum visibility (4-digit without direction)
        elif len(parts[i]) == 4 and parts[i].isdigit():
            result["minimum_visibility"] = {"value": int(parts[i])}
            parts.pop(i)

    # Backwards compatibility alias
    def parse_visibility_string(self, vis_str: str) -> Optional[Dict]:
        """Parse a visibility string directly (alias for parse())"""
        return self.parse(vis_str)
