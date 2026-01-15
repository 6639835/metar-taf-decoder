"""Weather phenomena parser."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..models import WeatherPhenomenon
from ..utils.constants import TREND_TYPES, WEATHER_DESCRIPTORS, WEATHER_PHENOMENA
from .base_parser import BaseParser, StopConditionMixin
from .token_stream import TokenStream


class WeatherParser(BaseParser[WeatherPhenomenon], StopConditionMixin):
    """Parser for weather phenomena in METAR and TAF reports."""

    stop_tokens = TREND_TYPES

    def parse(self, token: str) -> Optional[WeatherPhenomenon]:
        if token == "NSW":
            return WeatherPhenomenon(phenomena=("no significant weather",))

        intensity = None
        descriptor = None
        phenomena: List[str] = []
        remaining = token
        has_weather = False

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

        for desc_code, desc_value in WEATHER_DESCRIPTORS.items():
            if remaining.startswith(desc_code):
                descriptor = desc_value
                remaining = remaining[len(desc_code) :]
                has_weather = True
                break

        if remaining == "TS":
            descriptor = "thunderstorm"
            remaining = ""
            has_weather = True

        while remaining and len(remaining) >= 2:
            code = remaining[:2]
            if code in WEATHER_PHENOMENA:
                phenomena.append(WEATHER_PHENOMENA[code])
                remaining = remaining[2:]
                has_weather = True
            else:
                break

        if has_weather:
            return WeatherPhenomenon(
                intensity=intensity,
                descriptor=descriptor,
                phenomena=tuple(phenomena),
            )

        return None

    def extract_all(self, stream: TokenStream) -> List[WeatherPhenomenon]:
        weather_groups: List[WeatherPhenomenon] = []

        i = 0
        while i < len(stream.tokens):
            if self.should_stop(stream.tokens[i]):
                break

            weather = self.parse(stream.tokens[i])
            if weather is not None:
                weather_groups.append(weather)
                stream.pop(i)
            else:
                i += 1

        return weather_groups
