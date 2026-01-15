"""Main TAF decoder that orchestrates parsing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..data.taf_data import TafData
from ..models import TafForecastPeriod, TafReport, TimeRange
from ..parsers.pressure_parser import PressureParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.token_stream import TokenStream
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..utils.constants import CHANGE_INDICATORS
from ..utils.patterns import COMPILED_PATTERNS, FM_PATTERN


class TafDecoder:
    """TAF decoder class that parses raw TAF strings."""

    def __init__(self):
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.pressure_parser = PressureParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()

    def decode(self, raw_taf: str) -> TafData:
        taf = self._preprocess_taf(raw_taf.strip())

        remarks, remarks_decoded = self._decode_remarks(taf)
        main_taf = taf.split("RMK", 1)[0].strip() if "RMK" in taf else taf

        tokens = main_taf.split()
        station_id, issue_time, valid_period = self._extract_header(tokens)

        forecast_periods = self._decode_forecast_periods(tokens)

        report = TafReport(
            raw_taf=raw_taf,
            station_id=station_id,
            issue_time=issue_time,
            valid_period=valid_period,
            forecast_periods=forecast_periods,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
        )

        return TafData(**report.__dict__)

    def _preprocess_taf(self, taf: str) -> str:
        taf = re.sub(r"(\S)FM(\d{6})", r"\1 FM\2", taf)
        taf = re.sub(r"FM(\d{6})(\S)", r"FM\1 \2", taf)

        for indicator in CHANGE_INDICATORS:
            pattern = r"(\S)(" + indicator + r")"
            taf = re.sub(pattern, r"\1 \2", taf)

        for cloud_type in ["FEW", "SCT", "BKN", "OVC"]:
            pattern = r"(\S)(" + cloud_type + r")"
            taf = re.sub(pattern, r"\1 \2", taf)

        taf = re.sub(r"PROB(\d{2})(\S)", r"PROB\1 \2", taf)

        return taf

    def _extract_header(self, parts: List[str]) -> Tuple[str, datetime, TimeRange]:
        if parts and parts[0] == "TAF":
            parts.pop(0)
            if parts and parts[0] == "AMD":
                parts.pop(0)

        station_id = ""
        if parts and COMPILED_PATTERNS["station_id"].match(parts[0]):
            station_id = parts.pop(0)

        issue_time = datetime.now(timezone.utc)
        if parts and re.match(r"\d{6}Z", parts[0]):
            time_str = parts.pop(0)
            issue_time = self.time_parser.parse_observation_time(time_str) or issue_time

        valid_period = self.time_parser.parse_valid_period(parts[0]) if parts else None
        if parts and valid_period:
            parts.pop(0)
        if valid_period is None:
            now = datetime.now(timezone.utc)
            valid_period = self.time_parser.parse_valid_period("0100/0100")
            if valid_period is None:
                from ..models import TimeRange

                valid_period = TimeRange(start=now, end=now)

        return station_id, issue_time, valid_period

    def _decode_forecast_periods(self, parts: List[str]) -> List[TafForecastPeriod]:
        change_indices = self._find_change_indices(parts)
        change_indices.append(len(parts))

        forecast_periods: List[TafForecastPeriod] = []

        if change_indices and 0 < change_indices[0]:
            initial_tokens = parts[: change_indices[0]]
            period = self._parse_forecast_period("MAIN", initial_tokens)
            forecast_periods.append(period)

        for i in range(len(change_indices) - 1):
            start_idx = change_indices[i]
            end_idx = change_indices[i + 1]
            change_tokens = parts[start_idx:end_idx]
            period = self._parse_change_group(change_tokens)
            if period:
                forecast_periods.append(period)

        return forecast_periods

    def _find_change_indices(self, parts: List[str]) -> List[int]:
        change_indices = []
        for i in range(len(parts)):
            token = parts[i]
            if token in ["TEMPO", "BECMG"] or token.startswith("PROB") or re.match(FM_PATTERN, token):
                change_indices.append(i)
        return change_indices

    def _parse_change_group(self, tokens: List[str]) -> Optional[TafForecastPeriod]:
        if not tokens:
            return None

        change_indicator = tokens[0]

        if change_indicator in ["TEMPO", "BECMG"]:
            return self._parse_time_range_group(change_indicator, tokens[1:])

        if change_indicator.startswith("PROB"):
            probability = int(change_indicator[4:]) if change_indicator[4:].isdigit() else None
            period = self._parse_time_range_group("PROB", tokens[1:])
            period.probability = probability
            period.change_type = "PROB"
            return period

        if re.match(FM_PATTERN, change_indicator):
            from_time = self.time_parser.parse_fm_time(change_indicator)
            period = self._parse_forecast_period("FM", tokens[1:])
            period.from_time = from_time
            return period

        return None

    def _parse_time_range_group(self, change_type: str, tokens: List[str]) -> TafForecastPeriod:
        if tokens and re.match(r"\d{4}/\d{4}", tokens[0]):
            from_time, to_time = self.time_parser.parse_time_range(tokens[0])
            period = self._parse_forecast_period(change_type, tokens[1:])
            period.from_time = from_time
            period.to_time = to_time
            return period

        return self._parse_forecast_period(change_type, tokens)

    def _parse_forecast_period(self, change_type: str, tokens: List[str]) -> TafForecastPeriod:
        working_tokens = list(tokens)
        stream = TokenStream(working_tokens)

        wind = self.wind_parser.extract(stream)
        visibility = self.visibility_parser.extract(stream)
        weather = self.weather_parser.extract_all(stream)
        sky = self.sky_parser.extract_all(stream)
        qnh = self.pressure_parser.extract_qnh(stream)
        temperatures = self.temperature_parser.extract_temperature_forecasts(stream.tokens)

        period = TafForecastPeriod(
            change_type=change_type,
            wind=wind,
            visibility=visibility,
            weather=weather,
            sky=sky,
            qnh=qnh,
            temperatures=temperatures,
            unparsed_tokens=stream.remaining(),
        )

        return period

    def _decode_remarks(self, taf: str) -> Tuple[str, dict]:
        match = re.search(r"RMK\s+(.+)$", taf)
        if match:
            remarks = match.group(1)
            decoded = {}

            nxt_fcst_match = re.search(r"NXT\s+FCST\s+BY\s+(\d{2})Z", remarks)
            if nxt_fcst_match:
                decoded["Next Forecast"] = f"Next forecast will be issued by {nxt_fcst_match.group(1)}:00 UTC"

            if "LTG OBS" in remarks:
                decoded["Lightning"] = "Lightning observed in vicinity"

            remark_codes = remarks.split()
            for code in remark_codes:
                if code.startswith("WS"):
                    decoded["Wind Shear"] = "Wind shear reported"
                elif code in ["CNF", "CNF+", "CNF-"]:
                    confidence = {"CNF": "normal", "CNF+": "high", "CNF-": "low"}
                    decoded["Forecast Confidence"] = confidence[code]
                elif code == "AMD":
                    decoded["Amendment"] = "Forecast has been amended"
                elif code == "COR":
                    decoded["Correction"] = "Correction to previously issued forecast"

            return remarks, decoded

        return "", {}
