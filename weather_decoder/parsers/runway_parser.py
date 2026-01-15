"""Runway information parser for METAR reports."""

from __future__ import annotations

import re
from typing import List

from ..constants.runway_codes import RUNWAY_BRAKING, RUNWAY_DEPOSIT_TYPES, RUNWAY_EXTENT, RVR_TRENDS
from ..models import RunwayState, RunwayVisualRange
from .token_stream import TokenStream

RVR_PATTERN = r"R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$"
RUNWAY_STATE_PATTERN = r"R(\d{2}[LCR]?)/(\d|/)(\d|/)(\d{2}|//)(\d{2}|//)$"


class RunwayParser:
    """Parser for runway information in METAR reports."""

    def extract_rvr(self, stream: TokenStream) -> List[RunwayVisualRange]:
        rvr_list: List[RunwayVisualRange] = []
        i = 0
        while i < len(stream.tokens):
            match = re.match(RVR_PATTERN, stream.tokens[i])
            if match:
                rvr_list.append(self._parse_rvr_match(match, stream.tokens[i]))
                stream.pop(i)
            else:
                i += 1

        return rvr_list

    def _parse_rvr_match(self, match: re.Match, original: str) -> RunwayVisualRange:
        runway = match.group(1)
        modifier1 = match.group(2)
        visual_range = int(match.group(3))
        modifier2 = match.group(4)
        variable_range = int(match.group(5)) if match.group(5) else None
        trend = match.group(6)

        unit = "FT" if "FT" in original else "M"

        return RunwayVisualRange(
            runway=runway,
            visual_range=visual_range,
            unit=unit,
            is_less_than=modifier1 == "M",
            is_more_than=modifier1 == "P",
            variable_range=variable_range,
            variable_less_than=modifier2 == "M" if modifier2 else False,
            variable_more_than=modifier2 == "P" if modifier2 else False,
            trend=RVR_TRENDS.get(trend, trend) if trend else None,
        )

    def extract_runway_state(self, stream: TokenStream) -> List[RunwayState]:
        state_list: List[RunwayState] = []
        i = 0
        while i < len(stream.tokens):
            match = re.match(RUNWAY_STATE_PATTERN, stream.tokens[i])
            if match:
                state_list.append(self._parse_runway_state_match(match, stream.tokens[i]))
                stream.pop(i)
            else:
                i += 1

        return state_list

    def _parse_runway_state_match(self, match: re.Match, original: str) -> RunwayState:
        runway = match.group(1)
        deposit = match.group(2)
        extent = match.group(3)
        depth_raw = match.group(4)
        braking_raw = match.group(5)

        deposit_desc = RUNWAY_DEPOSIT_TYPES.get(deposit, f"unknown ({deposit})")
        extent_desc = RUNWAY_EXTENT.get(extent, f"unknown ({extent})")
        depth_desc = self._decode_depth(depth_raw)
        braking_desc = self._decode_braking(braking_raw)

        return RunwayState(
            runway=runway,
            deposit=deposit_desc,
            contamination=extent_desc,
            depth=depth_desc,
            braking=braking_desc,
            raw=original,
        )

    @staticmethod
    def _decode_depth(depth_raw: str) -> str:
        if depth_raw == "//":
            return "not reported"
        if depth_raw == "00":
            return "less than 1mm"

        try:
            depth_val = int(depth_raw)
        except ValueError:
            return f"unknown ({depth_raw})"

        if depth_val <= 90:
            return f"{depth_val}mm"

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
        if braking_raw == "//":
            return "not reported"
        if braking_raw in RUNWAY_BRAKING:
            return RUNWAY_BRAKING[braking_raw]

        try:
            coef = int(braking_raw) / 100
            return f"coefficient {coef:.2f}"
        except ValueError:
            return f"unknown ({braking_raw})"
