"""Sea-surface temperature and sea-state parser."""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import SeaCondition
from .token_stream import TokenStream

SEA_STATE_DESCRIPTIONS = {
    "0": "calm (glassy)",
    "1": "calm (rippled)",
    "2": "smooth (wavelets)",
    "3": "slight",
    "4": "moderate",
    "5": "rough",
    "6": "very rough",
    "7": "high",
    "8": "very high",
    "9": "phenomenal",
}


class SeaParser:
    """Parser for METAR sea-surface temperature and sea-state groups."""

    SEA_PATTERN = re.compile(r"^W(M?\d{2}|//)/(S\d|S/|H\d{2,3}|H///)$")

    def parse(self, token: str) -> Optional[SeaCondition]:
        match = self.SEA_PATTERN.match(token)
        if not match:
            return None

        temperature_token = match.group(1)
        condition_token = match.group(2)

        sea_surface_temperature = None
        temperature_missing = temperature_token == "//"
        if not temperature_missing:
            sea_surface_temperature = (
                -int(temperature_token[1:])
                if temperature_token.startswith("M")
                else int(temperature_token)
            )

        state_of_sea = None
        significant_wave_height_m = None
        state_missing = False
        wave_height_missing = False

        if condition_token.startswith("S"):
            state_code = condition_token[1:]
            state_missing = state_code == "/"
            if not state_missing:
                state_of_sea = SEA_STATE_DESCRIPTIONS.get(state_code, state_code)
        else:
            height_code = condition_token[1:]
            wave_height_missing = height_code == "///"
            if not wave_height_missing:
                significant_wave_height_m = int(height_code) / 10.0

        return SeaCondition(
            sea_surface_temperature=sea_surface_temperature,
            state_of_sea=state_of_sea,
            significant_wave_height_m=significant_wave_height_m,
            temperature_missing=temperature_missing,
            state_missing=state_missing,
            wave_height_missing=wave_height_missing,
            raw=token,
        )

    def extract_all(self, stream: TokenStream) -> List[SeaCondition]:
        sea_conditions: List[SeaCondition] = []
        i = 0
        while i < len(stream.tokens):
            parsed = self.parse(stream.tokens[i])
            if parsed is not None:
                sea_conditions.append(parsed)
                stream.pop(i)
            else:
                i += 1
        return sea_conditions
