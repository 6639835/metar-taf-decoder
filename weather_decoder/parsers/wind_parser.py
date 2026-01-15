"""Wind information parser."""

from __future__ import annotations

import re
from typing import Optional, Tuple

from ..models import Wind
from ..utils.patterns import WIND_EXTREME_PATTERN, WIND_PATTERN, WIND_VAR_PATTERN
from .base_parser import BaseParser
from .token_stream import TokenStream


class WindParser(BaseParser[Wind]):
    """Parser for wind information in METAR and TAF reports."""

    def parse(self, token: str) -> Optional[Wind]:
        extreme_match = re.match(WIND_EXTREME_PATTERN, token)
        if extreme_match:
            return Wind(
                direction=None,
                speed=int(extreme_match.group(1)),
                unit=extreme_match.group(2),
                is_variable=True,
                is_above=True,
            )

        match = re.match(WIND_PATTERN, token)
        if not match:
            return None

        is_above = match.group(1) == "P"
        direction_str = match.group(2)
        speed = int(match.group(3))
        gust = int(match.group(5)) if match.group(5) else None
        unit = self._determine_unit(token)

        direction = None if direction_str == "VRB" else int(direction_str)
        is_variable = direction_str == "VRB"

        return Wind(
            direction=direction,
            speed=speed,
            unit=unit,
            gust=gust,
            is_variable=is_variable,
            is_above=is_above,
        )

    def extract(self, stream: TokenStream) -> Optional[Wind]:
        for i, token in enumerate(stream.tokens):
            wind = self.parse(token)
            if wind is not None:
                stream.pop(i)
                var_range = self._parse_variable_direction(stream.peek(i))
                if var_range:
                    stream.pop(i)
                    wind = Wind(
                        direction=wind.direction,
                        speed=wind.speed,
                        unit=wind.unit,
                        gust=wind.gust,
                        is_variable=wind.is_variable,
                        variable_range=var_range,
                        is_above=wind.is_above,
                    )
                return wind
        return None

    @staticmethod
    def _determine_unit(token: str) -> str:
        if "KT" in token:
            return "KT"
        if "MPS" in token:
            return "MPS"
        if "KMH" in token:
            return "KMH"
        return "KT"

    @staticmethod
    def _parse_variable_direction(token: Optional[str]) -> Optional[Tuple[int, int]]:
        if not token:
            return None
        match = re.match(WIND_VAR_PATTERN, token)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None
