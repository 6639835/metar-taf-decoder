"""Validation rules for decoded TAF reports."""

from __future__ import annotations

import re
from typing import List, Optional

from ..constants.weather_codes import WEATHER_PHENOMENA
from ..models import TafForecastPeriod, TemperatureForecast, TimeRange
from ..parsers.icing_parser import IcingParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.turbulence_parser import TurbulenceParser

# Validation limits (WMO FM 51 / ICAO Annex 3 best practice)
_MAX_CHANGE_GROUPS = 5
_MAX_WEATHER_CODES_PER_PERIOD = 3
_MAX_TEMP_GROUPS = 4


def _is_issue_time_token(token: str) -> bool:
    return bool(re.fullmatch(r"\d{6}Z", token))


def _is_valid_period_token(token: str) -> bool:
    return bool(re.fullmatch(r"\d{4}/\d{4}", token))


def _extract_station_token(tokens: List[str]) -> Optional[str]:
    index = 0
    if index < len(tokens) and tokens[index] == "TAF":
        index += 1
    while index < len(tokens) and tokens[index] in {"AMD", "COR"}:
        index += 1
    if index < len(tokens) and re.fullmatch(r"[A-Z][A-Z0-9]{3}", tokens[index]):
        return tokens[index]
    return None


class TafValidator:
    """Cross-field and standards validation for parsed TAF data."""

    def __init__(
        self,
        temperature_parser: TemperatureParser,
        icing_parser: IcingParser,
        turbulence_parser: TurbulenceParser,
    ):
        self.temperature_parser = temperature_parser
        self.icing_parser = icing_parser
        self.turbulence_parser = turbulence_parser

    @staticmethod
    def validate_report(
        *,
        validation_tokens: List[str],
        remarks: str,
        valid_period: TimeRange,
        is_cancelled: bool,
        is_nil: bool,
    ) -> List[str]:
        warnings: List[str] = []

        if remarks:
            warnings.append(
                "RMK section is not part of the Annex 3 / WMO FM 51 TAF template; parsed as a local extension"
            )

        if not validation_tokens or validation_tokens[0] != "TAF":
            warnings.append("Annex IV TAF requires the TAF forecast type indicator")
        header_search_tokens = (
            validation_tokens[1:4]
            if validation_tokens and validation_tokens[0] == "TAF"
            else validation_tokens[:3]
        )
        if not any(
            re.fullmatch(r"[A-Z][A-Z0-9]{3}", token)
            and token not in {"AMD", "COR", "NIL", "CNL"}
            for token in header_search_tokens
        ):
            warnings.append("Annex IV TAF requires an ICAO location indicator")
        station = _extract_station_token(validation_tokens)
        if station and not re.fullmatch(r"[A-Z]{4}", station):
            warnings.append(
                f"Station identifier '{station}' is not a WMO CCCC ICAO four-letter location indicator"
            )
        if not any(_is_issue_time_token(token) for token in validation_tokens):
            warnings.append("Annex IV TAF requires issue time as DDHHMMZ")
        if not any(_is_valid_period_token(token) for token in validation_tokens):
            warnings.append("Annex IV TAF requires a validity period as DDHH/DDHH")

        # Tier 3: TAF validity duration check — ICAO Annex 3 §6.2.6 allows 6–30 hours
        duration_hours = (valid_period.end - valid_period.start).total_seconds() / 3600
        if not is_cancelled and not is_nil:
            if not (6 <= duration_hours <= 30):
                warnings.append(
                    f"TAF validity period of {duration_hours:.0f}h is outside the ICAO range of 6–30 hours"
                )
            elif duration_hours not in (9, 24, 30):
                # Lower-priority note for non-standard but ICAO-compliant durations
                warnings.append(
                    f"TAF validity period of {duration_hours:.0f}h is non-standard "
                    "(expected 9, 24, or 30 hours by regional agreement)"
                )

        return warnings

    def validate_temperature_groups(
        self,
        working_tokens: List[str],
        temperature_forecasts: List[TemperatureForecast],
    ) -> List[str]:
        warnings: List[str] = []
        misplaced = [
            token
            for token in working_tokens
            if self.temperature_parser.TX_PATTERN.match(token)
            or self.temperature_parser.TN_PATTERN.match(token)
        ]
        if misplaced:
            warnings.append(
                "TAF temperature groups (TX/TN) must appear in the base forecast before "
                f"change groups, not in self-contained change periods: {' '.join(misplaced)}"
            )

        if len(temperature_forecasts) > _MAX_TEMP_GROUPS:
            warnings.append(
                f"TAF contains {len(temperature_forecasts)} temperature groups; maximum permitted is {_MAX_TEMP_GROUPS}"
            )

        max_count = sum(1 for temp in temperature_forecasts if temp.kind == "max")
        min_count = sum(1 for temp in temperature_forecasts if temp.kind == "min")
        if max_count > 2 or min_count > 2:
            warnings.append(
                "TAF allows at most two TX groups and two TN groups at report level"
            )

        return warnings

    @staticmethod
    def validate_probability(probability: Optional[int]) -> List[str]:
        # Tier 4: PROB must be 30 or 40 (WMO FM 51 Reg. 51.9.1, EU Appendix 3)
        if probability is not None and probability not in (30, 40):
            return [
                f"PROB{probability} is invalid — only PROB30 and PROB40 are permitted"
            ]
        return []

    @staticmethod
    def validate_probability_becmg() -> List[str]:
        # Tier 4: PROB combined with BECMG is prohibited (WMO FM 51 Reg. 51.9.3)
        return ["PROB combined with BECMG is not permitted per WMO FM 51 Reg. 51.9.3"]

    def validate_forecast_periods(
        self,
        *,
        parts: List[str],
        forecast_periods: List[TafForecastPeriod],
        valid_period: TimeRange,
    ) -> List[str]:
        warnings: List[str] = []

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
                warnings.append(
                    "NOSIG is not valid in a TAF body — it is only for METAR TREND forecasts"
                )
                break

        # Per-period validations
        for period in forecast_periods:
            period_label = (
                period.from_time.strftime("%d/%HZ")
                if period.from_time
                else period.change_type
            )

            warnings.extend(
                self._validate_period_times(
                    period=period,
                    period_label=period_label,
                    valid_period=valid_period,
                )
            )

            if period.change_type in ("MAIN", "FM"):
                if period.wind is None:
                    warnings.append(
                        f"Period {period_label}: wind is required in a complete TAF forecast section"
                    )
                if period.visibility is None:
                    warnings.append(
                        f"Period {period_label}: visibility is required in a complete TAF forecast section"
                    )
                if period.visibility is None or not period.visibility.is_cavok:
                    if not period.sky:
                        warnings.append(
                            f"Period {period_label}: cloud, vertical visibility, NSC, or CAVOK is required "
                            "in a complete TAF forecast section"
                        )

            if period.change_type == "BECMG" and period.from_time and period.to_time:
                duration_hours = (
                    period.to_time - period.from_time
                ).total_seconds() / 3600
                if duration_hours > 4:
                    warnings.append(
                        f"Period {period_label}: BECMG period of {duration_hours:.0f}h exceeds the FM 51 maximum of 4h"
                    )
                elif duration_hours > 2:
                    warnings.append(
                        f"Period {period_label}: BECMG period of {duration_hours:.0f}h exceeds the usual FM 51 limit of 2h"
                    )

            if period.change_type in ("BECMG", "TEMPO") and (
                period.from_time is None or period.to_time is None
            ):
                warnings.append(
                    f"Period {period_label}: {period.change_type} change groups require "
                    "a DDHH/DDHH time period in ICAO Annex 3 Table A5-1"
                )
            if period.change_type == "PROB" and (
                period.from_time is None or period.to_time is None
            ):
                warnings.append(
                    f"Period {period_label}: PROB groups require a DDHH/DDHH time period per WMO FM 51 Reg. 51.9.1"
                )

            if len(period.weather) > _MAX_WEATHER_CODES_PER_PERIOD:
                warnings.append(
                    f"Period {period_label}: {len(period.weather)} weather codes exceed the maximum "
                    f"of {_MAX_WEATHER_CODES_PER_PERIOD} per forecast period (WMO IWXXM 3.0)"
                )

            self._validate_annex_iv_period(period, period_label, warnings)

            if len(period.sky) > 4:
                warnings.append(
                    f"Period {period_label}: {len(period.sky)} cloud layers exceed the maximum "
                    "of 4 per forecast period (WMO IWXXM 3.0)"
                )

            non_annex_weather = {
                "ice crystals": "IC",
                "spray": "PY",
            }
            for wx in period.weather:
                for phenomenon, code in non_annex_weather.items():
                    if phenomenon in wx.phenomena:
                        warnings.append(
                            f"Period {period_label}: {code} ({phenomenon}) is not in "
                            "the ICAO Annex 3 TAF weather template"
                        )

            if (
                period.visibility
                and period.visibility.is_cavok
                and (period.weather or period.sky or period.nsw)
            ):
                warnings.append(
                    f"Period {period_label}: CAVOK replaces visibility, weather, and cloud groups and cannot be combined with them"
                )

            if period.nsw and period.weather:
                warnings.append(
                    f"Period {period_label}: NSW replaces the weather group and cannot appear with explicit weather phenomena"
                )

            if "NSW" in period.unparsed_tokens and period.change_type in ("MAIN", "FM"):
                warnings.append(
                    f"Period {period_label}: NSW is only valid after change groups, not in complete TAF forecast sections"
                )

            extension_tokens = self._find_nonstandard_extension_tokens(
                period.unparsed_tokens
            )
            if extension_tokens:
                warnings.append(
                    f"Period {period_label}: non-standard TAF extension groups present: {' '.join(extension_tokens)}"
                )

        return warnings

    def _validate_annex_iv_period(
        self, period: TafForecastPeriod, period_label: str, warnings: List[str]
    ) -> None:
        """Warn when a forecast period does not match EU Annex IV Appendix 3."""

        if period.wind is not None:
            if period.wind.unit != "KT":
                warnings.append(
                    f"Period {period_label}: Annex IV TAF wind speed unit must be KT, got {period.wind.unit}"
                )
            if period.wind.speed >= 100 and not period.wind.is_above:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF reports wind speed of 100 kt or more with P99"
                )
            if period.wind.is_above and period.wind.speed != 99:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF uses P99 as the fixed wind-speed value for 100 kt or more"
                )
            if (
                period.wind.gust is not None
                and period.wind.gust >= 100
                and not period.wind.gust_is_above
            ):
                warnings.append(
                    f"Period {period_label}: Annex IV TAF reports gusts of 100 kt or more with GP99"
                )
            if period.wind.gust_is_above and period.wind.gust != 99:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF uses GP99 as the fixed gust value for 100 kt or more"
                )

        if period.visibility is not None and not period.visibility.is_cavok:
            if period.visibility.unit != "M":
                warnings.append(
                    f"Period {period_label}: Annex IV TAF visibility must be reported in metres, got {period.visibility.unit}"
                )
            elif period.visibility.value > 9999:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF visibility of 10 km or more is encoded as 9999"
                )
            elif not self._is_valid_annex_visibility_value(
                int(period.visibility.value)
            ):
                warnings.append(
                    f"Period {period_label}: Annex IV TAF visibility does not match Appendix 3 ranges and resolutions"
                )

        if len(period.sky) > 4:
            warnings.append(
                f"Period {period_label}: Annex IV TAF allows up to four cloud layers"
            )

        for sky in period.sky:
            if sky.coverage in {"SKC", "CLR", "NCD"}:
                warnings.append(
                    f"Period {period_label}: {sky.coverage} is not in the Annex IV TAF cloud template; use NSC, VV, FEW, SCT, BKN, OVC, or CAVOK as applicable"
                )
            if sky.coverage == "VV" and sky.height is not None and sky.height > 2000:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF vertical visibility is outside the Appendix 3 range of 000-020 hundreds of feet"
                )
                continue
            if sky.coverage == "VV" or sky.height is None:
                continue
            if sky.height is not None and sky.height > 20000:
                warnings.append(
                    f"Period {period_label}: Annex IV TAF cloud-base height is outside the Appendix 3 range of 000-200 hundreds of feet"
                )
            elif sky.height is not None and not self._is_valid_annex_cloud_base(
                sky.height
            ):
                warnings.append(
                    f"Period {period_label}: Annex IV TAF cloud-base height does not match Appendix 3 resolution"
                )

        code_for = {v: k for k, v in WEATHER_PHENOMENA.items()}
        non_annex = {
            "hail": "GR",
            "snow pellets": "GS",
            "ice crystals": "IC",
            "spray": "PY",
            "unknown precipitation": "UP",
        }
        for wx in period.weather:
            for phenomenon, code in non_annex.items():
                if phenomenon in wx.phenomena:
                    warnings.append(
                        f"Period {period_label}: {code} ({phenomenon}) is not in the Annex IV TAF weather template"
                    )
            if wx.intensity == "vicinity":
                for phenomenon in wx.phenomena:
                    vicinity_code = code_for.get(phenomenon)
                    if vicinity_code and vicinity_code not in {
                        "TS",
                        "FG",
                        "FC",
                        "SH",
                        "PO",
                        "BLDU",
                        "BLSA",
                        "BLSN",
                    }:
                        warnings.append(
                            f"Period {period_label}: VC is not permitted with {vicinity_code} in the Annex IV TAF weather template"
                        )

    @staticmethod
    def _is_valid_annex_visibility_value(value: int) -> bool:
        if value == 9999:
            return True
        if 0 <= value <= 750:
            return value % 50 == 0
        if 800 <= value <= 4900:
            return value % 100 == 0
        if 5000 <= value <= 9000:
            return value % 1000 == 0
        return False

    @staticmethod
    def _is_valid_annex_cloud_base(height_ft: int) -> bool:
        if 0 <= height_ft <= 9900:
            return height_ft % 100 == 0
        if 10000 <= height_ft <= 20000:
            return height_ft % 1000 == 0
        return False

    @staticmethod
    def _validate_period_times(
        *,
        period: TafForecastPeriod,
        period_label: str,
        valid_period: TimeRange,
    ) -> List[str]:
        warnings: List[str] = []

        if period.from_time is not None and not (
            valid_period.start <= period.from_time < valid_period.end
        ):
            warnings.append(
                f"Period {period_label}: from time {period.from_time:%d%HZ} is outside "
                f"the TAF valid period {valid_period.start:%d%HZ}/{valid_period.end:%d%HZ}"
            )

        if period.to_time is not None and not (
            valid_period.start < period.to_time <= valid_period.end
        ):
            warnings.append(
                f"Period {period_label}: to time {period.to_time:%d%HZ} is outside "
                f"the TAF valid period {valid_period.start:%d%HZ}/{valid_period.end:%d%HZ}"
            )

        if (
            period.from_time is not None
            and period.to_time is not None
            and period.to_time <= period.from_time
        ):
            warnings.append(f"Period {period_label}: end time must be after start time")

        return warnings

    def _find_nonstandard_extension_tokens(self, tokens: List[str]) -> List[str]:
        matches: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token == "WS" or token.startswith("WS"):
                matches.append(token)
                i += 1
                continue

            if self.icing_parser.parse(token) is not None:
                matches.append(token)
                i += 1
                continue

            if self.turbulence_parser.parse_numeric(token) is not None:
                matches.append(token)
                i += 1
                continue

            plain_turb = self.turbulence_parser.parse_plain(
                token, tokens[i + 1] if i + 1 < len(tokens) else None
            )
            if plain_turb is not None:
                _, consumed_next = plain_turb
                matches.append(
                    token if not consumed_next else f"{token} {tokens[i + 1]}"
                )
                i += 2 if consumed_next else 1
                continue

            i += 1

        return matches
