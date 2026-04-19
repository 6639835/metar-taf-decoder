"""Runway information parser for METAR reports."""

from __future__ import annotations

import re
from typing import List

from ..constants.runway_codes import (
    RUNWAY_BRAKING,
    RUNWAY_BRAKING_RESERVED,
    RUNWAY_DEPOSIT_TYPES,
    RUNWAY_DEPTH_RESERVED,
    RUNWAY_EXTENT,
    RVR_TRENDS,
)
from ..models import RunwayState, RunwayVisualRange
from .token_stream import TokenStream

RVR_PATTERN = r"R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$"
RUNWAY_STATE_PATTERN = r"R(\d{2}[LCR]?)/(\d|/)(\d|/)(\d{2}|//)(\d{2}|//)$"
RUNWAY_STATE_CLRD_PATTERN = r"R(\d{2}[LCR]?)/CLRD//$"
SNOCLO_TOKEN = "R/SNOCLO"


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
            variable_range_is_less_than=modifier2 == "M" if modifier2 and variable_range else False,
            variable_range_is_more_than=modifier2 == "P" if modifier2 and variable_range else False,
            trend=RVR_TRENDS.get(trend, trend) if trend else None,
        )

    def extract_runway_state(self, stream: TokenStream) -> List[RunwayState]:
        state_list: List[RunwayState] = []
        i = 0
        while i < len(stream.tokens):
            # R/SNOCLO: aerodrome closed due to extreme snow (WMO FM 15 Reg. 15.13.6.1)
            if stream.tokens[i] == SNOCLO_TOKEN:
                state_list.append(
                    RunwayState(
                        runway=None,
                        deposit="aerodrome closed due to extreme snow deposit",
                        contamination="all runways",
                        depth="not applicable",
                        braking="not applicable",
                        raw=SNOCLO_TOKEN,
                        all_runways=True,
                        aerodrome_closed=True,
                    )
                )
                stream.pop(i)
                continue

            cleared_match = re.match(RUNWAY_STATE_CLRD_PATTERN, stream.tokens[i])
            if cleared_match:
                state_list.append(self._parse_runway_state_cleared(cleared_match, stream.tokens[i]))
                stream.pop(i)
                continue

            match = re.match(RUNWAY_STATE_PATTERN, stream.tokens[i])
            if match:
                state_list.append(self._parse_runway_state_match(match, stream.tokens[i]))
                stream.pop(i)
            else:
                i += 1

        return state_list

    def _parse_runway_state_match(self, match: re.Match, original: str) -> RunwayState:
        runway_code = match.group(1)
        deposit = match.group(2)
        extent = match.group(3)
        depth_raw = match.group(4)
        braking_raw = match.group(5)
        runway, all_runways, from_previous_report = self._decode_runway_reference(runway_code)

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
            all_runways=all_runways,
            from_previous_report=from_previous_report,
        )

    def _parse_runway_state_cleared(self, match: re.Match, original: str) -> RunwayState:
        runway, all_runways, from_previous_report = self._decode_runway_reference(match.group(1))
        return RunwayState(
            runway=runway,
            deposit="runway cleared",
            contamination="not reported",
            depth="not reported",
            braking="not reported",
            raw=original,
            all_runways=all_runways,
            from_previous_report=from_previous_report,
            cleared=True,
        )

    @staticmethod
    def _decode_depth(depth_raw: str) -> str:
        if depth_raw == "//":
            return "operationally not significant or not measurable"
        if depth_raw == "00":
            return "less than 1mm"

        try:
            depth_val = int(depth_raw)
        except ValueError:
            return f"unknown ({depth_raw})"

        # WMO Code Table 1079: code 91 is Reserved — must not be decoded as a valid value
        if depth_val in RUNWAY_DEPTH_RESERVED:
            return f"reserved value ({depth_val}) — invalid"

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
            99: "runway not operational due to snow, slush, ice, large drifts or runway clearance, but depth not reported",
        }
        return depth_codes.get(depth_val, f"unknown ({depth_raw})")

    @staticmethod
    def _decode_braking(braking_raw: str) -> str:
        if braking_raw == "//":
            return "not reported"
        if braking_raw in RUNWAY_BRAKING:
            return RUNWAY_BRAKING[braking_raw]

        try:
            braking_val = int(braking_raw)
        except ValueError:
            return f"unknown ({braking_raw})"

        # WMO Code Table 0366: codes 96-98 are Reserved — must not be decoded as coefficients
        if braking_val in RUNWAY_BRAKING_RESERVED:
            return f"reserved value ({braking_raw}) — invalid"

        coef = braking_val / 100
        return f"coefficient {coef:.2f}"

    @staticmethod
    def _decode_runway_reference(runway_code: str):
        if runway_code == "88":
            return None, True, False
        if runway_code == "99":
            return None, False, True
        return runway_code, False, False
