"""Weather phenomena parser."""

from __future__ import annotations

import re
from typing import List, Optional

from ..constants import TREND_TYPES, WEATHER_DESCRIPTORS, WEATHER_PHENOMENA
from ..models import WeatherPhenomenon
from ..constants.weather_codes import COMPOUND_WEATHER_PHENOMENA
from .base_parser import BaseParser, StopConditionMixin
from .token_stream import TokenStream


class WeatherParser(BaseParser[WeatherPhenomenon], StopConditionMixin):
    """Parser for weather phenomena in METAR and TAF reports."""

    stop_tokens = TREND_TYPES
    RECENT_WEATHER_PATTERN = re.compile(
        r"^RE(?:RASN|SNRA|FZDZ|FZRA|FZUP|"
        r"REDZ|DZ|SHRA|RA|SHSN|SN|RESG|SG|SHGR|SHGS|SHUP|"
        r"GR|GS|BLSN|BLDU|BLSA|SS|DS|"
        r"TSRA|TSSN|TSGR|TSGS|TSUP|TS|"
        r"FC|VA|PL|UP|//)$"
    )

    def parse(self, token: str) -> Optional[WeatherPhenomenon]:
        # AUTO station: present weather not observable (// per ICAO/WMO Reg. 15.8.19, CAP 746 §4.154)
        if token == "//":
            return WeatherPhenomenon(unavailable=True)

        if token == "RE//":
            return WeatherPhenomenon(intensity="recent", phenomena=("not reported",))

        # NSW is only valid in METAR TREND sections (BECMG/TEMPO), not the METAR body.
        # Return None so extract_all() skips it; metar_decoder emits the validation warning.
        if token == "NSW":
            return None

        if token == "+FC":
            return WeatherPhenomenon(
                intensity="heavy", phenomena=("tornado/waterspout",)
            )

        if token.startswith("RE") and not self.RECENT_WEATHER_PATTERN.match(token):
            return None

        intensity = None
        descriptor = None
        phenomena: List[str] = []
        remaining = token
        has_weather = False

        # Check compound phenomena first (before prefix stripping) so that
        # 4-char atomic codes like VCTS, VCSH, FZFG, MIFG, BLSN etc. are
        # decoded correctly without being split by the VC/FZ/BL prefix logic.
        if len(remaining) >= 4 and remaining[:4] in COMPOUND_WEATHER_PHENOMENA:
            phenomena.append(COMPOUND_WEATHER_PHENOMENA[remaining[:4]])
            remaining = remaining[4:]
            has_weather = True
            # consume any further compound or 2-char codes in the same token
            while (
                remaining
                and len(remaining) >= 4
                and remaining[:4] in COMPOUND_WEATHER_PHENOMENA
            ):
                phenomena.append(COMPOUND_WEATHER_PHENOMENA[remaining[:4]])
                remaining = remaining[4:]
            while remaining and len(remaining) >= 2:
                code = remaining[:2]
                if code in WEATHER_PHENOMENA:
                    self._append_weather_phenomenon(phenomena, code)
                    remaining = remaining[2:]
                else:
                    break
            if has_weather and not remaining:
                return WeatherPhenomenon(
                    intensity=intensity,
                    descriptor=descriptor,
                    phenomena=tuple(phenomena),
                )

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
        elif remaining.startswith("RE"):
            intensity = "recent"
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

        # Match compound 4-char phenomena before falling back to 2-char loop.
        # This ensures RASN, SNRA, FZUP, SHUP, TSUP etc. are decoded atomically.
        while remaining and len(remaining) >= 4:
            code4 = remaining[:4]
            if code4 in COMPOUND_WEATHER_PHENOMENA:
                phenomena.append(COMPOUND_WEATHER_PHENOMENA[code4])
                remaining = remaining[4:]
                has_weather = True
            else:
                break

        while remaining and len(remaining) >= 2:
            code = remaining[:2]
            if code in WEATHER_PHENOMENA:
                self._append_weather_phenomenon(phenomena, code)
                remaining = remaining[2:]
                has_weather = True
            else:
                break

        if has_weather and not remaining:
            return WeatherPhenomenon(
                intensity=intensity,
                descriptor=descriptor,
                phenomena=tuple(phenomena),
            )

        return None

    @staticmethod
    def is_recent_weather_token(token: str) -> bool:
        return bool(WeatherParser.RECENT_WEATHER_PATTERN.match(token))

    @staticmethod
    def _append_weather_phenomenon(phenomena: List[str], code: str) -> None:
        if code == "GS":
            phenomena.append("snow pellets")
            return
        phenomena.append(WEATHER_PHENOMENA[code])

    def extract_all(self, stream: TokenStream) -> List[WeatherPhenomenon]:
        weather_groups: List[WeatherPhenomenon] = []

        i = 0
        while i < len(stream.tokens):
            if self.should_stop(stream.tokens[i]):
                break

            if self.is_recent_weather_token(stream.tokens[i]):
                i += 1
                continue

            weather = self.parse(stream.tokens[i])
            if weather is not None:
                weather_groups.append(weather)
                stream.pop(i)
            else:
                i += 1

        return weather_groups

    def extract_recent(self, stream: TokenStream) -> List[WeatherPhenomenon]:
        recent_weather: List[WeatherPhenomenon] = []

        i = 0
        while i < len(stream.tokens):
            token = stream.tokens[i]
            if self.should_stop(token):
                break

            if not self.is_recent_weather_token(token):
                i += 1
                continue

            weather = self.parse(token)
            if weather is not None:
                recent_weather.append(weather)
                stream.pop(i)
                if len(recent_weather) == 3:
                    break
            else:
                i += 1

        return recent_weather
