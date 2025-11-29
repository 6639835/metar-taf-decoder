"""Weather phenomena parser"""

from typing import Dict, List

from ..utils.constants import TREND_TYPES, WEATHER_DESCRIPTORS, WEATHER_INTENSITY, WEATHER_PHENOMENA


class WeatherParser:
    """Parser for weather phenomena in METAR and TAF reports"""

    @staticmethod
    def extract_weather(parts: List[str]) -> List[Dict]:
        """Extract weather phenomena from weather report parts"""
        weather_groups = []

        i = 0
        while i < len(parts):
            part = parts[i]

            # Stop if we encounter a trend indicator (TEMPO, BECMG, NOSIG)
            # These and their associated conditions should be handled by the trend parser
            if part in TREND_TYPES:
                break

            # Check for NSW (No Significant Weather)
            if part == "NSW":
                weather_groups.append({"intensity": "", "descriptor": "", "phenomena": ["no significant weather"]})
                parts.pop(i)
                continue

            # Process weather groups
            has_weather = False
            intensity = ""
            descriptor = ""
            phenomena = []

            # Check for intensity prefix
            if part.startswith("+") or part.startswith("-"):
                if part.startswith("+"):
                    intensity = "heavy"
                    part = part[1:]
                elif part.startswith("-"):
                    intensity = "light"
                    part = part[1:]
                has_weather = True

            # Check for vicinity (VC)
            elif part.startswith("VC"):
                intensity = "vicinity"
                part = part[2:]
                has_weather = True

            # Check for descriptor
            for desc_code, desc_value in WEATHER_DESCRIPTORS.items():
                if part.startswith(desc_code):
                    descriptor = desc_value
                    part = part[len(desc_code) :]
                    has_weather = True
                    break

            # Handle the case where the part is just 'TS' (thunderstorm without precipitation)
            if part == "TS":
                descriptor = "thunderstorm"
                has_weather = True
                part = ""

            # Check for weather phenomena
            remaining = part
            while remaining and len(remaining) >= 2:
                code = remaining[:2]
                if code in WEATHER_PHENOMENA:
                    phenomena.append(WEATHER_PHENOMENA[code])
                    remaining = remaining[2:]
                    has_weather = True
                else:
                    break

            if has_weather:
                weather_groups.append({"intensity": intensity, "descriptor": descriptor, "phenomena": phenomena})
                parts.pop(i)
            else:
                i += 1

        return weather_groups

    @staticmethod
    def parse_weather_string(weather_str: str) -> Dict:
        """Parse a single weather string"""
        # Check for NSW
        if weather_str == "NSW":
            return {"intensity": "", "descriptor": "", "phenomena": ["no significant weather"]}

        intensity = ""
        descriptor = ""
        phenomena = []
        part = weather_str

        # Check for intensity prefix
        if part.startswith("+"):
            intensity = "heavy"
            part = part[1:]
        elif part.startswith("-"):
            intensity = "light"
            part = part[1:]
        elif part.startswith("VC"):
            intensity = "vicinity"
            part = part[2:]

        # Check for descriptor
        for desc_code, desc_value in WEATHER_DESCRIPTORS.items():
            if part.startswith(desc_code):
                descriptor = desc_value
                part = part[len(desc_code) :]
                break

        # Handle standalone thunderstorm
        if part == "TS":
            descriptor = "thunderstorm"
            part = ""

        # Check for weather phenomena
        remaining = part
        while remaining and len(remaining) >= 2:
            code = remaining[:2]
            if code in WEATHER_PHENOMENA:
                phenomena.append(WEATHER_PHENOMENA[code])
                remaining = remaining[2:]
            else:
                break

        return {"intensity": intensity, "descriptor": descriptor, "phenomena": phenomena}
