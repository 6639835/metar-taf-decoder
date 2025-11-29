"""Weather phenomena parser"""

from typing import Dict, List, Optional

from ..utils.constants import TREND_TYPES, WEATHER_DESCRIPTORS, WEATHER_PHENOMENA
from .base_parser import StopConditionMixin, TokenParser


class WeatherParser(TokenParser, StopConditionMixin):
    """Parser for weather phenomena in METAR and TAF reports

    Handles weather phenomena encoding:
    - Intensity: - (light), + (heavy), VC (vicinity)
    - Descriptors: MI, PR, BC, DR, BL, SH, TS, FZ
    - Phenomena: DZ, RA, SN, etc.
    - Special: NSW (No Significant Weather)
    """

    # Stop parsing when we encounter trend indicators
    stop_tokens = TREND_TYPES

    def parse(self, token: str) -> Optional[Dict]:
        """Parse a weather phenomena token into structured data

        Args:
            token: A single token that may contain weather phenomena

        Returns:
            Dictionary with weather data if token matches, None otherwise
        """
        # Check for NSW (No Significant Weather)
        if token == "NSW":
            return {
                "intensity": "",
                "descriptor": "",
                "phenomena": ["no significant weather"],
            }

        intensity = ""
        descriptor = ""
        phenomena: List[str] = []
        remaining = token
        has_weather = False

        # Check for intensity prefix
        if remaining.startswith("+"):
            intensity = "heavy"
            remaining = remaining[1:]
            has_weather = True
        elif remaining.startswith("-"):
            intensity = "light"
            remaining = remaining[1:]
            has_weather = True
        elif remaining.startswith("VC"):
            intensity = "vicinity"
            remaining = remaining[2:]
            has_weather = True

        # Check for descriptor
        for desc_code, desc_value in WEATHER_DESCRIPTORS.items():
            if remaining.startswith(desc_code):
                descriptor = desc_value
                remaining = remaining[len(desc_code) :]
                has_weather = True
                break

        # Handle standalone thunderstorm
        if remaining == "TS":
            descriptor = "thunderstorm"
            remaining = ""
            has_weather = True

        # Extract weather phenomena (2-character codes)
        while remaining and len(remaining) >= 2:
            code = remaining[:2]
            if code in WEATHER_PHENOMENA:
                phenomena.append(WEATHER_PHENOMENA[code])
                remaining = remaining[2:]
                has_weather = True
            else:
                break

        # Only return if we found some weather information
        if has_weather:
            return {
                "intensity": intensity,
                "descriptor": descriptor,
                "phenomena": phenomena,
            }

        return None

    def extract_weather(self, parts: List[str]) -> List[Dict]:
        """Extract all weather phenomena from weather report parts

        This method extracts all weather tokens until a stop
        token (trend indicator) is encountered.

        Args:
            parts: List of tokens from the weather report (modified in place)

        Returns:
            List of weather phenomena dictionaries
        """
        weather_groups: List[Dict] = []

        i = 0
        while i < len(parts):
            # Stop if we encounter a trend indicator
            if self.should_stop(parts[i]):
                break

            # Try to parse the token
            weather = self.parse(parts[i])
            if weather is not None:
                weather_groups.append(weather)
                parts.pop(i)
                # Don't increment i since we removed the current element
            else:
                i += 1

        return weather_groups

    # Backwards compatibility alias
    def parse_weather_string(self, weather_str: str) -> Optional[Dict]:
        """Parse a single weather string (alias for parse())"""
        return self.parse(weather_str)
