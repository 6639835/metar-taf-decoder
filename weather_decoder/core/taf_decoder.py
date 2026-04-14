"""Main TAF decoder that orchestrates parsing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..data.taf_data import TafData
from ..models import TafForecastPeriod, TafReport, TimeRange
from ..parsers.icing_parser import IcingParser
from ..parsers.sea_parser import SeaParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.token_stream import TokenStream
from ..parsers.turbulence_parser import TurbulenceParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..parsers.windshear_parser import WindShearParser
from ..utils.constants import CHANGE_INDICATORS
from ..utils.patterns import COMPILED_PATTERNS, FM_PATTERN

# Validation limits (WMO FM 51 / ICAO Annex 3 best practice)
_MAX_CHANGE_GROUPS = 5
_MAX_WEATHER_CODES_PER_PERIOD = 3
_MAX_TEMP_GROUPS_PER_PERIOD = 2


class TafDecoder:
    """TAF decoder class that parses raw TAF strings."""

    def __init__(self):
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()
        self.windshear_parser = WindShearParser()
        self.sea_parser = SeaParser()
        self.icing_parser = IcingParser()
        self.turbulence_parser = TurbulenceParser()

    def decode(self, raw_taf: str) -> TafData:
        taf = self._preprocess_taf(raw_taf.strip())

        remarks, remarks_decoded = self._decode_remarks(taf)
        main_taf = taf.split("RMK", 1)[0].strip() if "RMK" in taf else taf

        tokens = main_taf.split()
        (
            station_id,
            issue_time,
            valid_period,
            is_amended,
            is_corrected,
            is_cancelled,
            is_nil,
        ) = self._extract_header(tokens)

        validation_warnings: List[str] = []

        # Tier 3: TAF validity duration check — ICAO Annex 3 §6.2.6 allows 6–30 hours
        duration_hours = (valid_period.end - valid_period.start).total_seconds() / 3600
        if not is_cancelled and not is_nil:
            if not (6 <= duration_hours <= 30):
                validation_warnings.append(
                    f"TAF validity period of {duration_hours:.0f}h is outside the ICAO range of 6–30 hours"
                )
            elif duration_hours not in (9, 24, 30):
                # Lower-priority note for non-standard but ICAO-compliant durations
                validation_warnings.append(
                    f"TAF validity period of {duration_hours:.0f}h is non-standard "
                    "(expected 9, 24, or 30 hours by regional agreement)"
                )

        forecast_periods = []
        period_warnings: List[str] = []
        if not is_cancelled and not is_nil:
            forecast_periods, period_warnings = self._decode_forecast_periods(tokens, valid_period.start)
        validation_warnings.extend(period_warnings)

        report = TafReport(
            raw_taf=raw_taf,
            station_id=station_id,
            issue_time=issue_time,
            valid_period=valid_period,
            forecast_periods=forecast_periods,
            status=self._derive_status(is_amended, is_corrected, is_cancelled, is_nil),
            is_amended=is_amended,
            is_corrected=is_corrected,
            is_cancelled=is_cancelled,
            is_nil=is_nil,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
            validation_warnings=validation_warnings,
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

    def _extract_header(self, parts: List[str]) -> Tuple[str, datetime, TimeRange, bool, bool, bool, bool]:
        if parts and parts[0] == "TAF":
            parts.pop(0)

        is_amended = False
        is_corrected = False
        while parts and parts[0] in {"AMD", "COR"}:
            modifier = parts.pop(0)
            if modifier == "AMD":
                is_amended = True
            elif modifier == "COR":
                is_corrected = True

        station_id = ""
        if parts and COMPILED_PATTERNS["station_id"].match(parts[0]):
            station_id = parts.pop(0)

        issue_time = datetime.now(timezone.utc)
        if parts and re.match(r"\d{6}Z", parts[0]):
            time_str = parts.pop(0)
            issue_time = self.time_parser.parse_observation_time(time_str) or issue_time

        valid_period = self.time_parser.parse_valid_period(parts[0], issue_time) if parts else None
        if parts and valid_period:
            parts.pop(0)
        if valid_period is None:
            valid_period = TimeRange(start=issue_time, end=issue_time)

        is_nil = bool(parts and parts[0] == "NIL")
        if is_nil:
            parts.pop(0)

        is_cancelled = bool(parts and parts[0] == "CNL")
        if is_cancelled:
            parts.pop(0)

        return station_id, issue_time, valid_period, is_amended, is_corrected, is_cancelled, is_nil

    def _decode_forecast_periods(
        self, parts: List[str], reference_time: datetime
    ) -> Tuple[List[TafForecastPeriod], List[str]]:
        if not parts:
            return [], []

        change_indices = self._find_change_indices(parts)
        change_indices.append(len(parts))

        forecast_periods: List[TafForecastPeriod] = []
        warnings: List[str] = []

        if not change_indices or 0 < change_indices[0]:
            initial_end = change_indices[0] if change_indices else len(parts)
            initial_tokens = parts[:initial_end]
            period = self._parse_forecast_period("MAIN", initial_tokens, reference_time)
            forecast_periods.append(period)

        for i in range(max(len(change_indices) - 1, 0)):
            start_idx = change_indices[i]
            end_idx = change_indices[i + 1]
            change_tokens = parts[start_idx:end_idx]
            period, period_warnings = self._parse_change_group(change_tokens, reference_time)
            warnings.extend(period_warnings)
            if period:
                forecast_periods.append(period)

        # Validation: maximum 5 non-MAIN change groups (WMO FM 51 / ICAO Annex 3 best practice)
        non_main_count = sum(1 for p in forecast_periods if p.change_type != "MAIN")
        if non_main_count > _MAX_CHANGE_GROUPS:
            warnings.append(
                f"TAF contains {non_main_count} change groups; maximum recommended is {_MAX_CHANGE_GROUPS} "
                "(WMO IWXXM 3.0 best practice)"
            )

        # NOSIG in TAF body — NOSIG is only valid in METAR TREND sections
        for tok in parts:
            if tok == "NOSIG":
                warnings.append("NOSIG is not valid in a TAF body — it is only for METAR TREND forecasts")
                break

        # Per-period validations
        for period in forecast_periods:
            period_label = period.from_time.strftime("%d/%HZ") if period.from_time else period.change_type

            if len(period.weather) > _MAX_WEATHER_CODES_PER_PERIOD:
                warnings.append(
                    f"Period {period_label}: {len(period.weather)} weather codes exceed the maximum "
                    f"of {_MAX_WEATHER_CODES_PER_PERIOD} per forecast period (WMO IWXXM 3.0)"
                )

            if len(period.temperatures) > _MAX_TEMP_GROUPS_PER_PERIOD:
                warnings.append(
                    f"Period {period_label}: {len(period.temperatures)} temperature groups exceed the "
                    f"maximum of {_MAX_TEMP_GROUPS_PER_PERIOD} per forecast period (WMO FM 51 Reg. 51.1.4)"
                )

        return forecast_periods, warnings

    def _find_change_indices(self, parts: List[str]) -> List[int]:
        change_indices = []
        for i in range(len(parts)):
            token = parts[i]
            if token == "TEMPO" and i > 0 and parts[i - 1].startswith("PROB"):
                continue
            if token in ["TEMPO", "BECMG"] or token.startswith("PROB") or re.match(FM_PATTERN, token):
                change_indices.append(i)
        return change_indices

    def _parse_change_group(
        self, tokens: List[str], reference_time: datetime
    ) -> Tuple[Optional[TafForecastPeriod], List[str]]:
        if not tokens:
            return None, []

        warnings: List[str] = []
        change_indicator = tokens[0]

        if change_indicator in ["TEMPO", "BECMG"]:
            return self._parse_time_range_group(change_indicator, tokens[1:], reference_time), warnings

        if change_indicator.startswith("PROB"):
            probability = int(change_indicator[4:]) if change_indicator[4:].isdigit() else None
            # Tier 4: PROB must be 30 or 40 (WMO FM 51 Reg. 51.9.1, EU Appendix 3)
            if probability is not None and probability not in (30, 40):
                warnings.append(f"PROB{probability} is invalid — only PROB30 and PROB40 are permitted")
            qualifier = None
            remainder = tokens[1:]
            if remainder and remainder[0] == "TEMPO":
                qualifier = "TEMPO"
                remainder = remainder[1:]
            elif remainder and remainder[0] == "BECMG":
                # Tier 4: PROB combined with BECMG is prohibited (WMO FM 51 Reg. 51.9.3)
                warnings.append("PROB combined with BECMG is not permitted per WMO FM 51 Reg. 51.9.3")
            period = self._parse_time_range_group("PROB", remainder, reference_time)
            period.probability = probability
            period.qualifier = qualifier
            return period, warnings

        if re.match(FM_PATTERN, change_indicator):
            from_time = self.time_parser.parse_fm_time(change_indicator, reference_time)
            period = self._parse_forecast_period("FM", tokens[1:], reference_time)
            period.from_time = from_time
            return period, warnings

        return None, warnings

    def _parse_time_range_group(
        self,
        change_type: str,
        tokens: List[str],
        reference_time: datetime,
    ) -> TafForecastPeriod:
        if tokens and re.match(r"\d{4}/\d{4}", tokens[0]):
            from_time, to_time = self.time_parser.parse_time_range(tokens[0], reference_time)
            period = self._parse_forecast_period(change_type, tokens[1:], reference_time)
            period.from_time = from_time
            period.to_time = to_time
            return period

        return self._parse_forecast_period(change_type, tokens, reference_time)

    def _parse_forecast_period(
        self,
        change_type: str,
        tokens: List[str],
        reference_time: datetime,
    ) -> TafForecastPeriod:
        working_tokens = list(tokens)
        stream = TokenStream(working_tokens)

        wind = self.wind_parser.extract(stream)
        visibility = self.visibility_parser.extract(stream)
        weather = self.weather_parser.extract_all(stream)
        windshear = self.windshear_parser.extract_all(stream)
        icing = self.icing_parser.extract_all(stream)
        turbulence = self.turbulence_parser.extract_all(stream)
        sky = self.sky_parser.extract_all(stream)
        # NOTE: QNH is NOT reported in TAF per ICAO Annex 3, Appendix 5, Table A5-1.
        # Do not parse pressure here.
        temperatures = []
        # TX/TN temperature groups belong to MAIN and FM self-contained periods (WMO FM 51 Reg. 51.1.4)
        if change_type in ("MAIN", "FM"):
            temperatures = self.temperature_parser.extract_temperature_forecasts(stream.tokens, reference_time)

        period = TafForecastPeriod(
            change_type=change_type,
            wind=wind,
            visibility=visibility,
            weather=weather,
            windshear=windshear,
            icing=icing,
            turbulence=turbulence,
            sky=sky,
            temperatures=temperatures,
            unparsed_tokens=stream.remaining(),
        )

        return period

    @staticmethod
    def _derive_status(is_amended: bool, is_corrected: bool, is_cancelled: bool, is_nil: bool) -> str:
        if is_nil:
            return "MISSING"
        if is_cancelled:
            return "CANCELLATION"
        if is_corrected:
            return "CORRECTION"
        if is_amended:
            return "AMENDMENT"
        return "NORMAL"

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
