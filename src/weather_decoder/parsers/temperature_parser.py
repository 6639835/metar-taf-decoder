"""Temperature information parser."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..models import TemperatureForecast


class TemperatureParser:
    """Parser for temperature information in METAR and TAF reports."""

    METAR_TEMPERATURE_PATTERN = re.compile(r"^(M?\d{2}|//)/(M?\d{2}|//)?$")
    TX_PATTERN = re.compile(r"TX([M]?)(\d{2})/(\d{2})(\d{2})Z")
    TN_PATTERN = re.compile(r"TN([M]?)(\d{2})/(\d{2})(\d{2})Z")

    def parse(self, token: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
        match = self.METAR_TEMPERATURE_PATTERN.match(token)
        if not match:
            return None

        left = match.group(1)
        right = match.group(2)
        temperature = self._parse_temperature_component(left)
        dewpoint = self._parse_temperature_component(right)

        if temperature is None and dewpoint is None:
            return (None, None)

        return (temperature, dewpoint)

    def extract_temperature_dewpoint(self, tokens: List[str]) -> Tuple[Optional[float], Optional[float]]:
        for i, token in enumerate(tokens):
            result = self.parse(token)
            if result is not None:
                tokens.pop(i)
                return result
        return (None, None)

    def extract_temperature_forecasts(
        self,
        tokens: List[str],
        reference_time: Optional[datetime] = None,
    ) -> List[TemperatureForecast]:
        forecasts: List[TemperatureForecast] = []
        i = 0
        while i < len(tokens):
            tx_match = self.TX_PATTERN.match(tokens[i])
            if tx_match:
                forecasts.append(self._parse_taf_temp_match(tx_match, "max", reference_time))
                tokens.pop(i)
                continue

            tn_match = self.TN_PATTERN.match(tokens[i])
            if tn_match:
                forecasts.append(self._parse_taf_temp_match(tn_match, "min", reference_time))
                tokens.pop(i)
                continue

            i += 1

        return forecasts

    def _parse_taf_temp_match(
        self,
        match: re.Match,
        temp_type: str,
        reference_time: Optional[datetime] = None,
    ) -> TemperatureForecast:
        temp_sign = -1 if match.group(1) == "M" else 1
        temp_val = temp_sign * int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))

        temp_time = self._create_forecast_datetime(day, hour, reference_time)
        return TemperatureForecast(kind=temp_type, value=temp_val, time=temp_time)

    @staticmethod
    def _create_forecast_datetime(day: int, hour: int, reference_time: Optional[datetime] = None) -> datetime:
        from ..parsers.time_parser import TimeParser

        current_date = reference_time or datetime.now(timezone.utc)
        return TimeParser._build_datetime(current_date, day, hour, 0)

    @staticmethod
    def _parse_temperature_component(token: Optional[str]) -> Optional[float]:
        if token is None or token in {"", "//"}:
            return None
        if token.startswith("M") and token[1:].isdigit() and len(token) == 3:
            return -int(token[1:])
        if token.isdigit() and len(token) == 2:
            return int(token)
        return None
