"""Windshear information parser."""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import WindShear
from .token_stream import TokenStream


class WindShearParser:
    """Parser for windshear information in METAR reports."""

    def extract_all(self, stream: TokenStream) -> List[WindShear]:
        windshear_list: List[WindShear] = []
        i = 0

        while i < len(stream.tokens):
            token = stream.tokens[i]

            if token == "WS":
                ws_parts = [stream.pop(i)]

                while (
                    i < len(stream.tokens)
                    and (
                        stream.tokens[i] in ["RWY", "ALL", "TKOF", "LDG"]
                        or re.fullmatch(r"\d{2}[LCR]?", stream.tokens[i])
                    )
                ):
                    ws_parts.append(stream.pop(i))

                ws_info = self._parse_windshear_group(ws_parts)
                windshear_list.append(ws_info)
                continue

            if token.startswith("WS") and len(token) > 2:
                raw = stream.pop(i)
                windshear_list.append(self._parse_compact_windshear(raw))
                continue

            i += 1

        return windshear_list

    def _parse_windshear_group(self, ws_parts: List[str]) -> WindShear:
        ws_str = " ".join(ws_parts)

        if "ALL" in ws_parts:
            return WindShear(kind="all_runways", description="Wind shear on all runways", raw=ws_str)

        if "TKOF" in ws_parts:
            runway = self._find_runway(ws_parts)
            return WindShear(
                kind="takeoff",
                description=f"Wind shear during takeoff on runway {runway or 'unknown'}",
                runway=runway,
                raw=ws_str,
            )

        if "LDG" in ws_parts:
            runway = self._find_runway(ws_parts)
            return WindShear(
                kind="landing",
                description=f"Wind shear during landing on runway {runway or 'unknown'}",
                runway=runway,
                raw=ws_str,
            )

        runway = self._find_runway(ws_parts)
        return WindShear(
            kind="runway",
            description=f"Wind shear on runway {runway or 'unknown'}",
            runway=runway,
            raw=ws_str,
        )

    def _parse_compact_windshear(self, raw: str) -> WindShear:
        match = re.search(r"(\d{2}[LCR]?)", raw)
        runway = match.group(1) if match else None
        description = f"Wind shear on runway {runway}" if runway else "Wind shear reported"
        return WindShear(kind="runway", description=description, runway=runway, raw=raw)

    @staticmethod
    def _find_runway(parts: List[str]) -> Optional[str]:
        for part in parts:
            if re.match(r"\d{2}[LCR]?", part):
                return part
        return None
