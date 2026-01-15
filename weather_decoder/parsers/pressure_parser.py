"""Pressure/altimeter information parser."""

from __future__ import annotations

import re
from typing import Optional

from ..models import Pressure
from ..utils.patterns import ALT_PATTERN, ALT_QNH_PATTERN, ALTIMETER_PATTERN, QNH_PATTERN
from .base_parser import BaseParser
from .token_stream import TokenStream


class PressureParser(BaseParser[Pressure]):
    """Parser for pressure/altimeter information in METAR and TAF reports."""

    def parse(self, token: str) -> Optional[Pressure]:
        match = re.match(ALTIMETER_PATTERN, token)
        if match:
            prefix = match.group(1)
            value = int(match.group(2))
            if prefix == "A":
                return Pressure(value=value / 100.0, unit="inHg")
            return Pressure(value=value, unit="hPa")
        return None

    def parse_qnh(self, token: str) -> Optional[Pressure]:
        match = re.match(QNH_PATTERN, token)
        if match:
            qnh_value = int(match.group(1))
            if 900 <= qnh_value <= 1050:
                return Pressure(value=qnh_value, unit="hPa")
            return Pressure(value=qnh_value / 100.0, unit="inHg")

        match = re.match(ALT_QNH_PATTERN, token)
        if match:
            qnh_value = int(match.group(1))
            unit = "hPa" if "HPa" in token else "inHg"
            if unit == "inHg":
                return Pressure(value=qnh_value / 100.0, unit=unit)
            return Pressure(value=qnh_value, unit=unit)

        match = re.match(ALT_PATTERN, token)
        if match:
            return Pressure(value=int(match.group(1)) / 100.0, unit="inHg")

        return None

    def extract_altimeter(self, stream: TokenStream) -> Optional[Pressure]:
        return self.extract_first(stream)

    def extract_qnh(self, stream: TokenStream) -> Optional[Pressure]:
        for i, token in enumerate(stream.tokens):
            result = self.parse_qnh(token)
            if result is not None:
                stream.pop(i)
                return result
        return None
