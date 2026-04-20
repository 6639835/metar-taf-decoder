"""Validation rules for decoded TAF reports."""

from __future__ import annotations

from typing import List, Optional

from ..models import TafForecastPeriod, TemperatureForecast, TimeRange
from ..parsers.icing_parser import IcingParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.turbulence_parser import TurbulenceParser

# Validation limits (WMO FM 51 / ICAO Annex 3 best practice)
_MAX_CHANGE_GROUPS = 5
_MAX_WEATHER_CODES_PER_PERIOD = 3
_MAX_TEMP_GROUPS = 4


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

        # Tier 3: TAF validity duration check — ICAO Annex 3 §6.2.6 allows 6–30 hours
        duration_hours = (valid_period.end - valid_period.start).total_seconds() / 3600
        if not is_cancelled and not is_nil:
            if not (6 <= duration_hours <= 30):
                warnings.append(f"TAF validity period of {duration_hours:.0f}h is outside the ICAO range of 6–30 hours")
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
            if self.temperature_parser.TX_PATTERN.match(token) or self.temperature_parser.TN_PATTERN.match(token)
        ]
        if misplaced:
            warnings.append(
                "TAF temperature groups (TX/TN) must appear at report level after the forecast groups, "
                f"not in self-contained periods: {' '.join(misplaced)}"
            )

        if len(temperature_forecasts) > _MAX_TEMP_GROUPS:
            warnings.append(
                f"TAF contains {len(temperature_forecasts)} temperature groups; maximum permitted is {_MAX_TEMP_GROUPS}"
            )

        max_count = sum(1 for temp in temperature_forecasts if temp.kind == "max")
        min_count = sum(1 for temp in temperature_forecasts if temp.kind == "min")
        if max_count > 2 or min_count > 2:
            warnings.append("TAF allows at most two TX groups and two TN groups at report level")

        return warnings

    @staticmethod
    def validate_probability(probability: Optional[int]) -> List[str]:
        # Tier 4: PROB must be 30 or 40 (WMO FM 51 Reg. 51.9.1, EU Appendix 3)
        if probability is not None and probability not in (30, 40):
            return [f"PROB{probability} is invalid — only PROB30 and PROB40 are permitted"]
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
                warnings.append("NOSIG is not valid in a TAF body — it is only for METAR TREND forecasts")
                break

        # Per-period validations
        for period in forecast_periods:
            period_label = period.from_time.strftime("%d/%HZ") if period.from_time else period.change_type

            if period.change_type in ("MAIN", "FM"):
                if period.wind is None:
                    warnings.append(f"Period {period_label}: wind is required in a complete TAF forecast section")
                if period.visibility is None:
                    warnings.append(f"Period {period_label}: visibility is required in a complete TAF forecast section")
                if period.visibility is None or not period.visibility.is_cavok:
                    if not period.sky:
                        warnings.append(
                            f"Period {period_label}: cloud, vertical visibility, NSC, or CAVOK is required "
                            "in a complete TAF forecast section"
                        )

            if period.change_type == "BECMG" and period.from_time and period.to_time:
                duration_hours = (period.to_time - period.from_time).total_seconds() / 3600
                if duration_hours > 4:
                    warnings.append(f"Period {period_label}: BECMG period of {duration_hours:.0f}h exceeds the FM 51 maximum of 4h")
                elif duration_hours > 2:
                    warnings.append(f"Period {period_label}: BECMG period of {duration_hours:.0f}h exceeds the usual FM 51 limit of 2h")

            if len(period.weather) > _MAX_WEATHER_CODES_PER_PERIOD:
                warnings.append(
                    f"Period {period_label}: {len(period.weather)} weather codes exceed the maximum "
                    f"of {_MAX_WEATHER_CODES_PER_PERIOD} per forecast period (WMO IWXXM 3.0)"
                )

            if period.visibility and period.visibility.is_cavok and (period.weather or period.sky or period.nsw):
                warnings.append(
                    f"Period {period_label}: CAVOK replaces visibility, weather, and cloud groups and cannot be combined with them"
                )

            if period.nsw and period.weather:
                warnings.append(f"Period {period_label}: NSW replaces the weather group and cannot appear with explicit weather phenomena")

            if "NSW" in period.unparsed_tokens and period.change_type in ("MAIN", "FM"):
                warnings.append(f"Period {period_label}: NSW is only valid after change groups, not in complete TAF forecast sections")

            extension_tokens = self._find_nonstandard_extension_tokens(period.unparsed_tokens)
            if extension_tokens:
                warnings.append(f"Period {period_label}: non-standard TAF extension groups present: {' '.join(extension_tokens)}")

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

            plain_turb = self.turbulence_parser.parse_plain(token, tokens[i + 1] if i + 1 < len(tokens) else None)
            if plain_turb is not None:
                _, consumed_next = plain_turb
                matches.append(token if not consumed_next else f"{token} {tokens[i + 1]}")
                i += 2 if consumed_next else 1
                continue

            i += 1

        return matches
