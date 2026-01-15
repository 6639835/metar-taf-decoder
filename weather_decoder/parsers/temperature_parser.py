"""Temperature information parser."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..models import TemperatureForecast
from ..utils.patterns import TEMPERATURE_PATTERN


class TemperatureParser:
    """Parser for temperature information in METAR and TAF reports."""

    TX_PATTERN = re.compile(r"TX([M]?)(\d{2})/(\d{2})(\d{2})Z")
    TN_PATTERN = re.compile(r"TN([M]?)(\d{2})/(\d{2})(\d{2})Z")

    def parse(self, token: str) -> Optional[Tuple[float, Optional[float]]]:
        match = re.match(TEMPERATURE_PATTERN, token)
        if not match:
            return None

        temp_sign = -1 if match.group(1) == "M" else 1
        temperature = temp_sign * int(match.group(2))

        dewpoint: Optional[float] = None
        if match.group(4) is not None:
            dew_sign = -1 if match.group(3) == "M" else 1
            dewpoint = dew_sign * int(match.group(4))

        return (temperature, dewpoint)

    def extract_temperature_dewpoint(self, tokens: List[str]) -> Tuple[Optional[float], Optional[float]]:
        for i, token in enumerate(tokens):
            result = self.parse(token)
            if result is not None:
                tokens.pop(i)
                return result
        return (None, None)

    def extract_temperature_forecasts(self, tokens: List[str]) -> List[TemperatureForecast]:
        forecasts: List[TemperatureForecast] = []
        i = 0
        while i < len(tokens):
            tx_match = self.TX_PATTERN.match(tokens[i])
            if tx_match:
                forecasts.append(self._parse_taf_temp_match(tx_match, "max"))
                tokens.pop(i)
                continue

            tn_match = self.TN_PATTERN.match(tokens[i])
            if tn_match:
                forecasts.append(self._parse_taf_temp_match(tn_match, "min"))
                tokens.pop(i)
                continue

            i += 1

        return forecasts

    def _parse_taf_temp_match(self, match: re.Match, temp_type: str) -> TemperatureForecast:
        temp_sign = -1 if match.group(1) == "M" else 1
        temp_val = temp_sign * int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))

        temp_time = self._create_forecast_datetime(day, hour)
        return TemperatureForecast(kind=temp_type, value=temp_val, time=temp_time)

    @staticmethod
    def _create_forecast_datetime(day: int, hour: int) -> datetime:
        from ..parsers.time_parser import TimeParser

        current_date = datetime.now(timezone.utc)
        return TimeParser._build_datetime(current_date, day, hour, 0)
