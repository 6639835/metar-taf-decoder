"""Validation rules for decoded METAR reports."""

from __future__ import annotations

import re
from typing import List, Optional

from ..constants.weather_codes import WEATHER_PHENOMENA
from ..models import (
    Pressure,
    RunwayState,
    RunwayVisualRange,
    SkyCondition,
    Trend,
    Visibility,
    WeatherPhenomenon,
    Wind,
    WindShear,
)
from ..parsers.pressure_parser import PressureParser
from ..parsers.sea_parser import SeaParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.token_stream import TokenStream
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..constants.patterns import COMPILED_PATTERNS


class MetarValidator:
    """Cross-field and standards validation for parsed METAR data."""

    WMO_STATION_PATTERN = re.compile(r"^[A-Z]{4}$")

    def __init__(
        self,
        wind_parser: WindParser,
        visibility_parser: VisibilityParser,
        weather_parser: WeatherParser,
        sky_parser: SkyParser,
        temperature_parser: TemperatureParser,
        pressure_parser: PressureParser,
        sea_parser: SeaParser,
    ):
        self.wind_parser = wind_parser
        self.visibility_parser = visibility_parser
        self.weather_parser = weather_parser
        self.sky_parser = sky_parser
        self.temperature_parser = temperature_parser
        self.pressure_parser = pressure_parser
        self.sea_parser = sea_parser

    def validate(
        self,
        *,
        validation_tokens: List[str],
        remaining_tokens: List[str],
        station_id: str,
        is_automated: bool,
        wind: Optional[Wind],
        visibility: Optional[Visibility],
        runway_visual_ranges: List[RunwayVisualRange],
        runway_states: List[RunwayState],
        weather_groups: List[WeatherPhenomenon],
        recent_weather: List[WeatherPhenomenon],
        sky_conditions: List[SkyCondition],
        temperature: Optional[float],
        dewpoint: Optional[float],
        altimeter: Optional[Pressure],
        windshear: List[WindShear],
        trends: List[Trend],
        remarks: str = "",
        is_nil: bool = False,
        has_remarks: bool = False,
    ) -> List[str]:
        warnings: List[str] = []
        is_us_station = self._is_us_station(station_id)
        is_uk_station = self._is_uk_station(station_id)
        has_remarks = has_remarks or bool(remarks)

        # Report type keyword validation (WMO Reg. 15.1.1)
        if not COMPILED_PATTERNS["metar_type"].match(
            validation_tokens[0] if validation_tokens else ""
        ):
            warnings.append(
                "METAR or SPECI keyword not found at start of report per WMO Reg. 15.1.1"
            )

        self._validate_annex_iv_template(
            validation_tokens=validation_tokens,
            station_id=station_id,
            is_nil=is_nil,
            has_remarks=has_remarks,
            wind=wind,
            visibility=visibility,
            runway_visual_ranges=runway_visual_ranges,
            sky_conditions=sky_conditions,
            temperature=temperature,
            dewpoint=dewpoint,
            altimeter=altimeter,
            warnings=warnings,
        )

        self._validate_header_groups(validation_tokens, station_id, warnings)

        if station_id and not re.match(r"^[A-Z]{4}$", station_id):
            warnings.append(
                "Station identifier contains non-alpha characters; FMH-1 §12.6.2 "
                "requires four alphabetic characters for long-line METAR/SPECI"
            )

        if (
            is_us_station
            and len(validation_tokens) > 1
            and validation_tokens[1] == "COR"
        ):
            warnings.append(
                "COR report modifier appears before station identifier; FMH-1 §12.6.4 "
                "places COR after the date/time group, substituting for AUTO"
            )
        if is_uk_station and self._has_uk_misplaced_cor(validation_tokens):
            warnings.append(
                "UK corrected METARs shall use METAR COR before the ICAO location "
                "indicator (CAP 746 §4.4 variation 6)"
            )

        # Sky condition code warnings
        for sky in sky_conditions:
            if sky.coverage in ("SKC", "CLR"):
                if is_us_station:
                    if is_automated and sky.coverage == "SKC":
                        warnings.append(
                            "SKC reported by AUTO station; FMH-1 §12.6.9 requires CLR "
                            "for automated clear-sky reports"
                        )
                    elif not is_automated and sky.coverage == "CLR":
                        warnings.append(
                            "CLR reported by manual station; FMH-1 §12.6.9 requires SKC "
                            "for manual clear-sky reports"
                        )
                else:
                    warnings.append(
                        "SKC/CLR are US FAA codes; WMO METAR uses NSC (no significant cloud)"
                    )
                break
        if not is_automated and any(s.coverage == "NCD" for s in sky_conditions):
            warnings.append(
                "NCD (No Cloud Detected) is only valid in AUTO (automated) METARs "
                "per ICAO Annex 3 §4.5.4.6"
            )
        if not is_automated and any(
            s.system_unavailable or s.unknown_type for s in sky_conditions
        ):
            warnings.append(
                "Automated cloud limitation groups (////// or cloud type ///) "
                "are only valid in AUTO METARs (CAP 746 §4.146-4.147)"
            )
        if not is_automated and visibility and visibility.unavailable:
            warnings.append(
                "Visibility //// is an AUTO METAR sensor-unavailable group "
                "(CAP 746 §4.151)"
            )
        if not is_automated and any(w.unavailable for w in weather_groups):
            warnings.append(
                "Present weather // is an AUTO METAR sensor-unavailable group "
                "(CAP 746 §4.154)"
            )
        if is_us_station and any(s.coverage in {"NSC", "NCD"} for s in sky_conditions):
            warnings.append(
                "NSC/NCD are not FMH-1 sky-condition codes; FMH-1 §12.6.9 uses "
                "SKC, CLR, FEW, SCT, BKN, OVC, or VV"
            )

        # Wind unit warning (WMO Reg. 15.5.1 — only KT or MPS)
        if wind and wind.unit == "KMH":
            warnings.append(
                "KMH is not a valid WMO METAR wind speed unit (only KT or MPS per WMO Reg. 15.5.1)"
            )
        if is_uk_station and wind and wind.unit != "KT":
            warnings.append(
                "UK METAR surface wind speed shall be reported in knots (KT) "
                "per CAP 746 §4.5 and §4.8"
            )

        self._validate_non_wmo_regional_tokens(validation_tokens, warnings)
        if is_us_station and wind:
            if wind.unit != "KT":
                warnings.append(
                    f"{wind.unit} wind unit is not valid for FMH-1 METAR/SPECI; "
                    "FMH-1 §12.6.5 requires KT"
                )
            if wind.is_above or wind.gust_is_above:
                warnings.append(
                    "P-prefixed above-limit wind speeds are not part of FMH-1 §12.6.5 "
                    "wind coding"
                )

        # Metric RVR warning (FMH-1 §12.6.7 — requires FT suffix)
        if self._is_us_station(station_id) and any(
            rvr.unit == "M" for rvr in runway_visual_ranges
        ):
            warnings.append(
                "Metric RVR (no FT suffix) — FMH-1 §12.6.7 requires FT for US METAR"
            )

        # UK stations do not use runway state groups since CAP 746 Issue 6
        if runway_states and is_uk_station:
            warnings.append(
                "Runway state groups (MOTNE) are not used in UK METARs since CAP 746 Issue 6"
            )

        if len(sky_conditions) > 6:
            warnings.append(
                f"More than 6 cloud layers reported ({len(sky_conditions)}); "
                "FMH-1 §9.5.2 allows a maximum of 6 (ICAO/WMO allow up to 4)"
            )
        elif len(sky_conditions) > 4 and not is_us_station:
            warnings.append(
                f"More than 4 cloud layers reported ({len(sky_conditions)}); "
                "ICAO/WMO specifications allow a maximum of 4 "
                "(FMH-1 §9.5.2 allows up to 6 for US stations)"
            )
        if is_uk_station:
            self._validate_uk_cloud_layer_rules(sky_conditions, warnings)

        if len(weather_groups) > 3:
            warnings.append(
                f"More than 3 present weather groups ({len(weather_groups)}); "
                "ICAO/WMO specifications allow a maximum of 3"
            )

        self._validate_weather_groups(
            weather_groups, visibility, warnings, is_us_station=is_us_station
        )
        if is_us_station:
            self._validate_fmh1_visibility(visibility, warnings)
            self._validate_fmh1_pressure(validation_tokens, warnings)
            self._validate_fmh1_weather_groups(weather_groups, warnings)

        if len(runway_visual_ranges) > 4:
            warnings.append(
                f"More than 4 RVR groups ({len(runway_visual_ranges)}); "
                "ICAO/EU specifications allow a maximum of 4"
            )
        if any(rvr.unit == "FT" for rvr in runway_visual_ranges):
            warnings.append(
                "RVR with FT suffix is a local extension; ICAO Annex 3 METAR/SPECI "
                "Table A3-2 reports RVR in metres without a unit suffix"
            )
        if any(rvr.variable_range is not None for rvr in runway_visual_ranges):
            warnings.append(
                "Variable RVR range (Rxx/nnnnVnnnn) is not in the ICAO Annex 3 "
                "METAR/SPECI Table A3-2 RVR template"
            )
        if is_uk_station:
            self._validate_uk_rvr_groups(runway_visual_ranges, warnings)

        # TS in present weather but no CB in sky (CAP 746 §4.112)
        has_ts = any(
            (
                w.descriptor == "thunderstorm"
                or (w.phenomena and "thunderstorm" in w.phenomena)
            )
            for w in weather_groups
        )
        has_cb = any(s.cb for s in sky_conditions)
        if has_ts and not has_cb:
            warnings.append(
                "Thunderstorm (TS) present weather reported without a CB cloud layer (CAP 746 §4.112)"
            )

        self._validate_wind_variation(wind, warnings)
        if is_us_station:
            self._validate_fmh1_wind_variation(wind, warnings)

        # CAVOK cross-field: weather/cloud groups must be absent when CAVOK is set
        if visibility and visibility.is_cavok:
            if (
                weather_groups
                or sky_conditions
                or runway_visual_ranges
                or visibility.minimum_visibility is not None
            ):
                warnings.append(
                    "CAVOK used but RVR, minimum visibility, weather, or cloud groups "
                    "are present — these are mutually exclusive"
                )
            if is_us_station:
                warnings.append(
                    "CAVOK is not part of FMH-1 METAR/SPECI body coding; FMH-1 §12.6.6 "
                    "requires visibility in statute miles and §12.6.9 requires explicit sky coding"
                )
        if is_uk_station:
            self._validate_uk_visibility(visibility, warnings)

        # NOSIG and BECMG/TEMPO are mutually exclusive (WMO Reg. 15.14.15)
        has_nosig = any(t.kind == "NOSIG" for t in trends)
        has_becmg_tempo = any(t.kind in ("BECMG", "TEMPO") for t in trends)
        if has_nosig and has_becmg_tempo:
            warnings.append(
                "NOSIG and BECMG/TEMPO are mutually exclusive per WMO Reg. 15.14.15"
            )

        # NSW in METAR body (WMO Reg. 15.14.13) — NSW is TREND-only
        trend_starts = {"BECMG", "TEMPO", "NOSIG"}
        nsw_in_body = False
        for token in remaining_tokens:
            if token in trend_starts:
                break
            if token == "NSW":
                nsw_in_body = True
                break
        if nsw_in_body:
            warnings.append(
                "NSW (no significant weather) is not valid in METAR body — "
                "only in TREND section per WMO Reg. 15.14.13"
            )

        self._validate_jma_automated_report(
            validation_tokens, station_id, is_automated, warnings
        )

        warnings.extend(self._validate_body_order(validation_tokens))

        # Dew point cannot exceed temperature (physically impossible)
        if temperature is not None and dewpoint is not None and dewpoint > temperature:
            warnings.append(
                f"Dew point ({dewpoint}°C) exceeds temperature ({temperature}°C) — "
                "physically impossible"
            )
        if is_us_station and temperature is None and dewpoint is not None:
            warnings.append(
                "Dew point reported while temperature is missing; FMH-1 §12.6.10 says "
                "the entire temperature/dew point group is omitted when temperature is unavailable"
            )

        # Descriptor + phenomenon constraint validation (WMO Code Table 4678 Notes 7–13)
        self._validate_descriptor_phenomena(weather_groups, warnings)

        if is_uk_station:
            self._validate_uk_only_rules(
                validation_tokens=validation_tokens,
                is_automated=is_automated,
                altimeter=altimeter,
                wind=wind,
                windshear=windshear,
                remarks=remarks,
                recent_weather=recent_weather,
                warnings=warnings,
            )

        return warnings

    def _validate_header_groups(
        self,
        tokens: List[str],
        station_id: str,
        warnings: List[str],
    ) -> None:
        """Validate mandatory WMO FM 15/16 header groups without rejecting local input."""
        if station_id and not self.WMO_STATION_PATTERN.match(station_id):
            warnings.append(
                f"Station identifier '{station_id}' is not a WMO CCCC ICAO four-letter location indicator"
            )

        index = 0
        if index < len(tokens) and COMPILED_PATTERNS["metar_type"].match(tokens[index]):
            index += 1
        if index < len(tokens) and tokens[index] == "COR":
            index += 1

        if index >= len(tokens) or not COMPILED_PATTERNS["station_id"].match(
            tokens[index]
        ):
            warnings.append("WMO METAR/SPECI station group CCCC is missing")
            return

        index += 1
        if index < len(tokens) and tokens[index] == "COR":
            index += 1

        if index >= len(tokens) or not COMPILED_PATTERNS["datetime"].match(
            tokens[index]
        ):
            warnings.append("WMO METAR/SPECI observation time group YYGGggZ is missing")

    @staticmethod
    def _validate_non_wmo_regional_tokens(
        tokens: List[str], warnings: List[str]
    ) -> None:
        """Warn for accepted regional/local tokens that are outside WMO FM 15/16."""
        if MetarValidator._contains_statute_mile_visibility(tokens):
            warnings.append(
                "Statute-mile visibility is a regional extension; WMO FM 15/16 uses metric VVVV or CAVOK"
            )

        if any(re.fullmatch(r"\d{1,2}KM|\d{4}M", token) for token in tokens):
            warnings.append(
                "Visibility suffixes KM/M are regional extensions; WMO FM 15/16 uses unsuffixed VVVV"
            )

        if any(re.fullmatch(r"A\d{4}", token) for token in tokens):
            warnings.append(
                "Altimeter group A#### is a regional extension; WMO FM 15/16 uses Q#### for QNH"
            )

    @staticmethod
    def _contains_statute_mile_visibility(tokens: List[str]) -> bool:
        for index, token in enumerate(tokens):
            if re.fullmatch(r"[PM]?\d+(?:/\d+)?SM", token):
                return True
            if (
                token.isdigit()
                and index + 1 < len(tokens)
                and re.fullmatch(r"\d+/\d+SM", tokens[index + 1])
            ):
                return True
        return False

    @staticmethod
    def _validate_fmh1_visibility(
        visibility: Optional[Visibility], warnings: List[str]
    ) -> None:
        if visibility is None or visibility.unavailable:
            return

        if visibility.unit != "SM":
            if visibility.is_cavok:
                return
            warnings.append(
                f"{visibility.unit} visibility is not valid for FMH-1 METAR/SPECI; "
                "FMH-1 §12.6.6 requires statute miles ending with SM"
            )
            return

        if visibility.is_greater_than:
            warnings.append(
                "Greater-than visibility such as P6SM is not an FMH-1 METAR/SPECI "
                "visibility value; FMH-1 §12.6.6 uses the reportable SM table"
            )

        reportable_sm_values = {
            0,
            1 / 16,
            1 / 8,
            3 / 16,
            1 / 4,
            5 / 16,
            3 / 8,
            1 / 2,
            5 / 8,
            3 / 4,
            7 / 8,
            1,
            1 + 1 / 8,
            1 + 1 / 4,
            1 + 3 / 8,
            1 + 1 / 2,
            1 + 5 / 8,
            1 + 3 / 4,
            1 + 7 / 8,
            2,
            2 + 1 / 4,
            2 + 1 / 2,
            2 + 3 / 4,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            20,
            25,
            30,
            35,
        }
        value = float(visibility.value)
        if value > 35:
            valid = value.is_integer() and (int(value) - 35) % 5 == 0
        else:
            valid = any(abs(value - allowed) < 1e-9 for allowed in reportable_sm_values)
        if not valid:
            warnings.append(
                f"{visibility.value:g}SM is not a reportable FMH-1 visibility value "
                "per Table 12-1"
            )

    @staticmethod
    def _validate_fmh1_pressure(
        validation_tokens: List[str], warnings: List[str]
    ) -> None:
        for token in validation_tokens:
            if re.match(r"^Q\d{4}$", token) or re.match(r"^Q/{4}$", token):
                warnings.append(
                    "Q-coded pressure is not valid for FMH-1 METAR/SPECI altimeter; "
                    "FMH-1 §12.6.11 requires A followed by inches of mercury"
                )
                return

    @staticmethod
    def _validate_fmh1_weather_groups(
        weather_groups: List[WeatherPhenomenon], warnings: List[str]
    ) -> None:
        for wx in weather_groups:
            joined = " ".join(wx.phenomena)
            if "unknown precipitation" in joined and (
                wx.intensity in {"light", "heavy"}
                or wx.descriptor in {"freezing", "shower", "thunderstorm"}
                or joined != "unknown precipitation"
            ):
                warnings.append(
                    "UP (unknown precipitation) cannot carry intensity or FZ/SH/TS "
                    "descriptors in FMH-1 §12.6.8 body coding"
                )
            if any("volcanic ash in vicinity" == p for p in wx.phenomena):
                warnings.append(
                    "VCVA is not an FMH-1 vicinity weather body code; FMH-1 §12.6.8.a(2) "
                    "limits VC to TS, FG, SH, PO, BLDU, BLSA, BLSN, SS, and DS"
                )

    @staticmethod
    def _validate_fmh1_wind_variation(
        wind: Optional[Wind], warnings: List[str]
    ) -> None:
        if wind is None or wind.variable_range is None or wind.is_variable:
            return

        speed_kt = wind.speed if wind.unit == "KT" else wind.speed * 1.944
        if speed_kt < 6:
            warnings.append(
                "Wind direction variation (nnnVnnn) reported with speed < 6 kt — "
                "report as VRBxxKT per FMH-1 §12.6.5.b"
            )

    def _validate_annex_iv_template(
        self,
        *,
        validation_tokens: List[str],
        station_id: str,
        is_nil: bool,
        has_remarks: bool,
        wind: Optional[Wind],
        visibility: Optional[Visibility],
        runway_visual_ranges: List[RunwayVisualRange],
        sky_conditions: List[SkyCondition],
        temperature: Optional[float],
        dewpoint: Optional[float],
        altimeter: Optional[Pressure],
        warnings: List[str],
    ) -> None:
        """Warn when a decoded METAR/SPECI does not match EU Annex IV Appendix 1."""

        if not station_id:
            warnings.append("Annex IV METAR/SPECI requires an ICAO location indicator")

        if not any(re.fullmatch(r"\d{6}Z", token) for token in validation_tokens):
            warnings.append("Annex IV METAR/SPECI requires observation time as DDHHMMZ")

        if has_remarks:
            warnings.append(
                "RMK remarks are a local extension and are not part of the Annex IV METAR/SPECI template"
            )

        if is_nil:
            return

        if wind is None:
            warnings.append("Annex IV METAR/SPECI requires a surface wind group")
        else:
            if wind.unit != "KT":
                warnings.append(
                    f"Annex IV METAR/SPECI wind speed unit must be KT, got {wind.unit}"
                )
            if wind.speed >= 100 and not wind.is_above:
                warnings.append(
                    "Annex IV METAR/SPECI reports wind speed of 100 kt or more with P99, not a raw 3-digit speed"
                )
            if wind.is_above and wind.speed != 99:
                warnings.append(
                    "Annex IV METAR/SPECI uses P99 as the fixed wind-speed value for 100 kt or more"
                )
            if wind.gust is not None and wind.gust >= 100 and not wind.gust_is_above:
                warnings.append(
                    "Annex IV METAR/SPECI reports gusts of 100 kt or more with GP99, not a raw 3-digit gust"
                )
            if wind.gust_is_above and wind.gust != 99:
                warnings.append(
                    "Annex IV METAR/SPECI uses GP99 as the fixed gust value for 100 kt or more"
                )

        if visibility is None:
            warnings.append("Annex IV METAR/SPECI requires visibility or CAVOK")
        else:
            if not visibility.is_cavok and visibility.unit != "M":
                warnings.append(
                    f"Annex IV METAR/SPECI visibility must be reported in metres, got {visibility.unit}"
                )
            if visibility.unit == "M" and visibility.value > 9999:
                warnings.append(
                    "Annex IV METAR/SPECI visibility of 10 km or more is encoded as 9999"
                )
            if (
                not visibility.is_cavok
                and visibility.unit == "M"
                and not visibility.unavailable
                and not self._is_valid_annex_visibility_value(int(visibility.value))
            ):
                warnings.append(
                    "Annex IV METAR/SPECI visibility does not match Appendix 1 ranges and resolutions"
                )
            if (
                visibility.minimum_visibility is not None
                and not self._is_valid_annex_visibility_value(
                    visibility.minimum_visibility.value
                )
            ):
                warnings.append(
                    "Annex IV METAR/SPECI minimum visibility does not match Appendix 1 ranges and resolutions"
                )

        for rvr in runway_visual_ranges:
            if rvr.unit != "M":
                warnings.append(
                    f"Annex IV METAR/SPECI RVR is reported in metres, got {rvr.unit}"
                )
            if rvr.unavailable:
                continue
            if rvr.variable_range is not None:
                warnings.append(
                    "Annex IV METAR/SPECI RVR template does not include variable RVR ranges"
                )
            if rvr.visual_range > 2000 or (
                rvr.variable_range is not None and rvr.variable_range > 2000
            ):
                warnings.append(
                    "Annex IV METAR/SPECI RVR value is outside the Appendix 1 range of 0000-2000 m"
                )
            if not self._is_valid_annex_rvr_value(rvr.visual_range):
                warnings.append(
                    "Annex IV METAR/SPECI RVR does not match Appendix 1 ranges and resolutions"
                )
            if rvr.variable_range is not None and not self._is_valid_annex_rvr_value(
                rvr.variable_range
            ):
                warnings.append(
                    "Annex IV METAR/SPECI variable RVR does not match Appendix 1 ranges and resolutions"
                )

        if visibility is None or not visibility.is_cavok:
            if not sky_conditions:
                warnings.append(
                    "Annex IV METAR/SPECI requires cloud, vertical visibility, NSC, NCD, or CAVOK"
                )

        for sky in sky_conditions:
            if sky.coverage in {"SKC", "CLR"}:
                continue
            if sky.coverage == "VV" and sky.height is not None and sky.height > 2000:
                warnings.append(
                    "Annex IV METAR/SPECI vertical visibility is outside the Appendix 1 range of 000-020 hundreds of feet"
                )
                continue
            if sky.coverage == "VV" or sky.height is None:
                continue
            if sky.height is not None and sky.height > 20000:
                warnings.append(
                    "Annex IV METAR/SPECI cloud-base height is outside the Appendix 1 range of 000-200 hundreds of feet"
                )
            elif sky.height is not None and not self._is_valid_annex_cloud_base(
                sky.height
            ):
                warnings.append(
                    "Annex IV METAR/SPECI cloud-base height does not match Appendix 1 resolution"
                )

        has_temperature_group = any(
            self.temperature_parser.parse(token) is not None
            for token in validation_tokens
        )
        if not has_temperature_group:
            warnings.append(
                "Annex IV METAR/SPECI requires an air/dew-point temperature group"
            )
        else:
            for label, value in (
                ("air temperature", temperature),
                ("dew-point temperature", dewpoint),
            ):
                if value is not None and not (-80 <= value <= 60):
                    warnings.append(
                        f"Annex IV METAR/SPECI {label} {value:g}C is outside the Appendix 1 range -80 to +60C"
                    )

        has_qnh = any(
            re.fullmatch(r"Q(?:\d{4}|/{4})", token) for token in validation_tokens
        )
        has_altimeter = any(
            re.fullmatch(r"A\d{4}", token) for token in validation_tokens
        )
        if not has_qnh:
            warnings.append("Annex IV METAR/SPECI requires QNH as Qnnnn")
        if has_altimeter:
            warnings.append(
                "Annex IV METAR/SPECI includes QNH only; inHg altimeter groups such as Annnn are non-standard"
            )
        if (
            altimeter
            and altimeter.unit == "hPa"
            and not (850 <= altimeter.value <= 1100)
        ):
            warnings.append(
                "Annex IV METAR/SPECI QNH is outside the Appendix 1 range 0850-1100 hPa"
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
    def _is_valid_annex_rvr_value(value: int) -> bool:
        if 0 <= value <= 375:
            return value % 25 == 0
        if 400 <= value <= 750:
            return value % 50 == 0
        if 800 <= value <= 2000:
            return value % 100 == 0
        return False

    @staticmethod
    def _is_valid_annex_cloud_base(height_ft: int) -> bool:
        if 0 <= height_ft <= 9900:
            return height_ft % 100 == 0
        if 10000 <= height_ft <= 20000:
            return height_ft % 1000 == 0
        return False

    @staticmethod
    def _validate_weather_groups(
        weather_groups: List[WeatherPhenomenon],
        visibility: Optional[Visibility],
        warnings: List[str],
        *,
        is_us_station: bool,
    ) -> None:
        # Weather intensity and descriptor validation (WMO 306 Vol I.1, Reg. 15.8.4, 15.8.9, FMH-1 §12.6.8)
        for wx in weather_groups:
            # Intensity (-, +, VC) only valid for precipitation, FC, SS, DS
            valid_intensity_phenomena = {
                "drizzle",
                "rain",
                "snow",
                "snow grains",
                "ice pellets",
                "hail",
                "snow pellets",
                "unknown precipitation",
                "funnel cloud",
                "dust whirls",
                "duststorm",
                "sandstorm",
                "shower",
                "thunderstorm",
                "tornado/waterspout",
            }
            if wx.intensity and wx.intensity != "recent":
                # US FMH-1 differs from CAP 746/WMO practice for hail intensity.
                if is_us_station and "hail" in wx.phenomena:
                    warnings.append(
                        f"Intensity modifier '{wx.intensity}' is not valid for GR (hail) "
                        "per FMH-1 §12.6.8.a(1) — hail has no intensity qualifier"
                    )
                # -DS and -SS (light duststorm/sandstorm) are invalid — only moderate+ allowed
                if wx.intensity == "light" and any(
                    p in ("duststorm", "sandstorm") for p in wx.phenomena
                ):
                    phenom_names = ", ".join(
                        p for p in wx.phenomena if p in ("duststorm", "sandstorm")
                    )
                    warnings.append(
                        f"Light intensity ('-') is not valid for {phenom_names} (DS/SS) — "
                        "only moderate or heavy (+) intensity is allowed"
                    )
                # GS body intensity should be warned for US reports — FMH-1 keeps GS intensity in RMK.
                if is_us_station and any(p == "snow pellets" for p in wx.phenomena):
                    warnings.append(
                        "GS (snow pellets) intensity in the METAR body — "
                        "FMH-1 §12.6.8.a(1) specifies GS intensity in RMK section only (e.g. 'GS MOD')"
                    )
                if any(
                    p in ("hail", "snow pellets") for p in wx.phenomena
                ) and wx.descriptor not in {"shower", "thunderstorm"}:
                    warnings.append(
                        "GR/GS shall be used only with shower (SH) or thunderstorm (TS) "
                        "descriptors (CAP 746 §4.69)"
                    )
                # Check if any phenomenon justifies intensity
                has_valid_phenomena = any(
                    p in valid_intensity_phenomena for p in wx.phenomena
                )
                if not has_valid_phenomena:
                    warnings.append(
                        f"Intensity modifier '{wx.intensity}' not valid for weather phenomena: "
                        f"{', '.join(wx.phenomena)} (WMO 306 Reg. 15.8.4)"
                    )
            # Visibility-dependent phenomenon checks (WMO Reg. 15.8.12-15)
            non_annex_weather = {
                "ice crystals": "IC",
                "spray": "PY",
            }
            for phenomenon, code in non_annex_weather.items():
                if phenomenon in wx.phenomena:
                    warnings.append(
                        f"{code} ({phenomenon}) is not in the ICAO Annex 3 "
                        "METAR/SPECI present weather template"
                    )

            if visibility and visibility.value < 10000:
                vis_m = (
                    visibility.value
                    if visibility.unit == "M"
                    else visibility.value * 1000
                )
                # FG requires visibility < 1000m
                if "fog" in wx.phenomena and vis_m >= 1000:
                    warnings.append(
                        f"FG (fog) reported with visibility {vis_m}m but requires < 1000m (WMO Reg. 15.8.14)"
                    )
                # BR requires 1000 ≤ visibility ≤ 5000m
                if "mist" in wx.phenomena and not (1000 <= vis_m <= 5000):
                    warnings.append(
                        f"BR (mist) reported with visibility {vis_m}m but requires 1000-5000m (WMO Reg. 15.8.13)"
                    )
                # FU, HZ, DU, SA require visibility ≤ 5000m
                obscuration = {"smoke", "haze", "dust", "sand"}
                if any(p in obscuration for p in wx.phenomena) and vis_m > 5000:
                    px_list = ", ".join(
                        p[:2].upper() for p in wx.phenomena if p in obscuration
                    )
                    warnings.append(
                        f"{px_list} reported with visibility {vis_m}m but requires ≤ 5000m (WMO Reg. 15.8.12)"
                    )

    @staticmethod
    def _validate_wind_variation(wind: Optional[Wind], warnings: List[str]) -> None:
        # Wind variation validation (ICAO Annex 3 §4.1.5.2, CAP 746 §4.11-4.13)
        if wind:
            if wind.variable_range and not wind.is_variable:
                var_lo, var_hi = wind.variable_range
                variation = (var_hi - var_lo) % 360
                # nnnVnnn only valid when variation is 60-179° (ICAO §4.1.5.2 b)
                if variation < 60:
                    warnings.append(
                        f"Wind variable range {var_lo:03d}V{var_hi:03d} reported but variation "
                        f"({variation}°) is less than 60° — omit the variable range"
                    )
                elif variation >= 180:
                    warnings.append(
                        f"Wind variable range {var_lo:03d}V{var_hi:03d} reported but variation "
                        f"({variation}°) is ≥180° — report as VRB instead"
                    )
                # CAP 746 applies the variable-direction group at 3 kt or more.
                speed_kt = wind.speed if wind.unit == "KT" else wind.speed * 1.944
                if speed_kt < 3:
                    warnings.append(
                        "Wind direction variation (nnnVnnn) reported with speed < 3 kt — "
                        "report as VRBxxKT"
                    )
            if wind.direction is not None and not wind.is_variable and not wind.is_calm:
                # Direction should be a multiple of 10° (CAP 746 §4.16)
                if wind.direction % 10 != 0:
                    warnings.append(
                        f"Wind direction {wind.direction:03d}° is not rounded to the nearest 10° "
                        "(CAP 746 §4.16)"
                    )
                # Direction must be 010-360°
                if not (10 <= wind.direction <= 360):
                    warnings.append(
                        f"Wind direction {wind.direction:03d}° is outside valid range 010-360°"
                    )

    def _validate_body_order(self, tokens: List[str]) -> List[str]:
        body_tokens = list(tokens)
        stream = TokenStream(body_tokens)
        self._extract_header(stream)
        body_tokens = stream.remaining()

        order = {
            "wind": 1,
            "visibility": 2,
            "rvr": 3,
            "weather": 4,
            "sky": 5,
            "temperature": 6,
            "altimeter": 7,
            "recent_weather": 8,
            "windshear": 9,
            "sea": 10,
            "runway_state": 11,
            "trend": 12,
        }

        warnings: List[str] = []
        max_seen = 0
        i = 0
        while i < len(body_tokens):
            token = body_tokens[i]
            category = self._classify_metar_token(body_tokens, i)
            if category is None:
                i += 1
                continue

            # Trend forecast content is a self-contained trailing section. Once a
            # trend starts, changed elements such as wind/visibility/clouds no
            # longer participate in METAR body-order validation.
            if category == "trend":
                break

            if order[category] < max_seen:
                warnings.append(
                    f"METAR body elements are out of order near token '{token}' "
                    "(Annex 3 / WMO FM 15 ordering violation)"
                )
                break

            max_seen = max(max_seen, order[category])
            i += (
                2
                if category == "visibility"
                and token.isdigit()
                and i + 1 < len(body_tokens)
                and re.match(r"^\d+/\d+SM$", body_tokens[i + 1])
                else 1
            )

        return warnings

    def _classify_metar_token(self, tokens: List[str], index: int) -> str | None:
        token = tokens[index]

        if token in {"BECMG", "TEMPO", "NOSIG"}:
            return "trend"
        if self.wind_parser.parse(token) is not None or re.match(
            r"^\d{3}V\d{3}$", token
        ):
            return "wind"
        if self.weather_parser.is_recent_weather_token(token):
            return "recent_weather"
        if token == "WS" or token.startswith("WS"):
            return "windshear"
        if self.sea_parser.parse(token) is not None:
            return "sea"
        if (
            token == "R/SNOCLO"
            or re.match(r"^R(\d{2}[LCR]?)/(\d|/)(\d|/)(\d{2}|//)(\d{2}|//)$", token)
            or re.match(
                r"^R(\d{2}[LCR]?)/CLRD//$",
                token,
            )
        ):
            return "runway_state"
        if re.match(
            r"^R(\d{2}[LCR]?)/([PM])?(\d{4}|/{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$",
            token,
        ):
            return "rvr"
        if self.visibility_parser.parse(token) is not None:
            return "visibility"
        if (
            token.isdigit()
            and index + 1 < len(tokens)
            and re.match(r"^\d+/\d+SM$", tokens[index + 1])
        ):
            return "visibility"
        if self.weather_parser.parse(token) is not None:
            return "weather"
        if self.sky_parser.parse(token) is not None:
            return "sky"
        if self.temperature_parser.parse(token) is not None:
            return "temperature"
        if self.pressure_parser.parse(token) is not None:
            return "altimeter"
        return None

    @staticmethod
    def _extract_header(stream: TokenStream) -> None:
        next_token = stream.peek()
        if next_token is not None and COMPILED_PATTERNS["metar_type"].match(next_token):
            stream.pop(0)

        if stream.peek() == "COR":
            stream.pop(0)

        next_token = stream.peek()
        if next_token is not None and COMPILED_PATTERNS["station_id"].match(next_token):
            stream.pop(0)

        next_token = stream.peek()
        if next_token is not None and re.match(r"\d{6}Z", next_token):
            stream.pop(0)

        if stream.peek() == "COR":
            stream.pop(0)

        if stream.peek() == "AUTO":
            stream.pop(0)

    @staticmethod
    def _is_us_station(station_id: str) -> bool:
        station = station_id.upper()
        return station.startswith(("K", "PA", "PH", "PG", "TJ"))

    @staticmethod
    def _is_uk_station(station_id: str) -> bool:
        return station_id.upper().startswith("EG")

    @staticmethod
    def _has_uk_misplaced_cor(tokens: List[str]) -> bool:
        return "COR" in tokens and not (len(tokens) > 1 and tokens[1] == "COR")

    @staticmethod
    def _validate_uk_cloud_layer_rules(
        sky_conditions: List[SkyCondition], warnings: List[str]
    ) -> None:
        if len(sky_conditions) <= 3:
            return

        convective_layers = sum(1 for sky in sky_conditions if sky.cb or sky.tcu)
        if len(sky_conditions) > 3 + convective_layers:
            warnings.append(
                "UK METARs normally report up to three cloud layers; extra layers "
                "are only for omitted TCU/CB layers (CAP 746 §4.103)"
            )

    def _validate_uk_rvr_groups(
        self, runway_visual_ranges: List[RunwayVisualRange], warnings: List[str]
    ) -> None:
        for rvr in runway_visual_ranges:
            self._validate_uk_rvr_value(
                rvr.visual_range,
                is_less_than=rvr.is_less_than,
                is_more_than=rvr.is_more_than,
                warnings=warnings,
                label=f"RVR for runway {rvr.runway}",
            )
            if rvr.variable_range is not None:
                self._validate_uk_rvr_value(
                    rvr.variable_range,
                    is_less_than=rvr.variable_less_than
                    or rvr.variable_range_is_less_than,
                    is_more_than=rvr.variable_more_than
                    or rvr.variable_range_is_more_than,
                    warnings=warnings,
                    label=f"Variable RVR for runway {rvr.runway}",
                )

    @staticmethod
    def _validate_uk_rvr_value(
        value: int,
        *,
        is_less_than: bool,
        is_more_than: bool,
        warnings: List[str],
        label: str,
    ) -> None:
        if is_less_than and value != 50:
            warnings.append(
                f"{label} below-reportable value should be encoded as M0050"
            )
        if value < 50 and not is_less_than:
            warnings.append(f"{label} below 50 m should be encoded as M0050")
        if value > 2000:
            warnings.append(
                f"{label} exceeds the CAP 746 maximum reportable RVR value of 2000 m"
            )
        if is_more_than and value > 2000:
            warnings.append(f"{label} above-reportable value should not exceed P2000")

        if value < 400:
            step = 25
        elif value <= 800:
            step = 50
        else:
            step = 100
        if value % step != 0:
            warnings.append(
                f"{label} value {value:04d} is not on the CAP 746 RVR reporting "
                f"increment of {step} m"
            )

    def _validate_uk_visibility(
        self, visibility: Optional[Visibility], warnings: List[str]
    ) -> None:
        if visibility is None or visibility.is_cavok or visibility.unavailable:
            return
        if visibility.unit != "M":
            warnings.append("UK METAR visibility is reported in metres or as CAVOK")
            return

        self._validate_uk_visibility_value(
            int(visibility.value), warnings, "Visibility"
        )
        if visibility.minimum_visibility is not None:
            self._validate_uk_visibility_value(
                visibility.minimum_visibility.value, warnings, "Minimum visibility"
            )

    @staticmethod
    def _validate_uk_visibility_value(
        value: int, warnings: List[str], label: str
    ) -> None:
        if value == 9999 or value == 0:
            return
        if value < 50:
            warnings.append(f"{label} below 50 m should be encoded as 0000")
            return
        if value < 800:
            step = 50
        elif value < 5000:
            step = 100
        elif value < 10000:
            step = 1000
        else:
            warnings.append(f"{label} of 10 km or more should be encoded as 9999")
            return

        if value % step != 0:
            warnings.append(
                f"{label} value {value:04d} is not on the CAP 746 visibility "
                f"reporting increment of {step} m"
            )

    def _validate_uk_only_rules(
        self,
        *,
        validation_tokens: List[str],
        is_automated: bool,
        altimeter: Optional[Pressure],
        wind: Optional[Wind],
        windshear: List[WindShear],
        remarks: str,
        recent_weather: List[WeatherPhenomenon],
        warnings: List[str],
    ) -> None:
        if remarks:
            warnings.append(
                "RMK remarks are not used in UK civil METARs (CAP 746 §4.4 variation 5)"
            )

        if windshear:
            warnings.append(
                "Wind shear groups (WS...) are not reported in UK METARs "
                "(CAP 746 §4.4 variation 2)"
            )

        if altimeter and altimeter.unit != "hPa":
            warnings.append(
                "UK METAR pressure shall be QNH encoded as Qdddd in hectopascals "
                "(CAP 746 §4.120-4.126)"
            )
        if any(re.fullmatch(r"A(?:\d{4}|/{4})", token) for token in validation_tokens):
            warnings.append(
                "UK METARs use Qdddd QNH, not A#### altimeter groups "
                "(CAP 746 §4.120-4.126)"
            )

        if wind:
            if wind.speed >= 100 and not wind.is_above:
                warnings.append(
                    "UK METAR wind speeds of 100 kt or more should be encoded as P99 "
                    "(CAP 746 §4.19)"
                )
            if wind.gust is not None and wind.gust >= 100 and not wind.gust_is_above:
                warnings.append(
                    "UK METAR gusts of 100 kt or more should be encoded as GP99 "
                    "(CAP 746 §4.19)"
                )
            if wind.gust is not None and wind.gust - wind.speed < 10:
                warnings.append(
                    "UK METAR gusts are reported only when they exceed the mean wind "
                    "speed by 10 kt or more (CAP 746 §4.10)"
                )

        if len(recent_weather) > 3:
            warnings.append("Up to three recent weather groups may be reported")

        self._validate_uk_recent_weather_codes(validation_tokens, warnings)

        if not is_automated and "AUTO" in validation_tokens:
            warnings.append("AUTO marker and manual report state are inconsistent")

    @staticmethod
    def _validate_uk_recent_weather_codes(
        validation_tokens: List[str], warnings: List[str]
    ) -> None:
        allowed_recent_weather = {
            "RETS",
            "RETSRA",
            "RETSSN",
            "RETSGR",
            "RETSGS",
            "REFZRA",
            "REFZDZ",
            "RERA",
            "RESN",
            "REDZ",
            "REPL",
            "RESG",
            "RESHRA",
            "RESHSN",
            "RESHGS",
            "RESHGR",
            "REBLSN",
            "REUP",
            "RESHUP",
            "REFZUP",
            "RETSUP",
            "RESS",
            "REDS",
            "REFC",
            "REVA",
        }
        for token in MetarValidator._body_tokens_before_trend(validation_tokens):
            if token.startswith("RE") and token not in allowed_recent_weather:
                warnings.append(
                    f"{token} is not a permitted UK METAR recent weather code "
                    "(CAP 746 Table 4)"
                )

    @staticmethod
    def _is_japan_station(station_id: str) -> bool:
        return station_id.upper().startswith("RJ")

    def _validate_jma_automated_report(
        self,
        validation_tokens: List[str],
        station_id: str,
        is_automated: bool,
        warnings: List[str],
    ) -> None:
        """Validate JMA-specific automated METAR/SPECI body restrictions."""
        if not (is_automated and self._is_japan_station(station_id)):
            return

        body_tokens = self._body_tokens_before_trend(validation_tokens)

        if "CAVOK" in body_tokens:
            warnings.append(
                "JMA automated METAR/SPECI do not use CAVOK; report 9999 with NSC or NCD instead"
            )

        if any(token in {"SKC", "CLR"} for token in body_tokens):
            warnings.append(
                "JMA automated METAR/SPECI do not use SKC/CLR; use NSC or NCD when applicable"
            )

        invalid_weather = [
            token
            for token in body_tokens
            if self._is_jma_automated_invalid_weather_token(token)
        ]
        if invalid_weather:
            warnings.append(
                "JMA automated METAR/SPECI present weather is limited to RA, SN, "
                "RASN/SNRA, FG, BR, HZ, UP, SQ, and TS combinations; invalid token(s): "
                + ", ".join(invalid_weather)
            )

    @staticmethod
    def _body_tokens_before_trend(validation_tokens: List[str]) -> List[str]:
        stream = TokenStream(list(validation_tokens))
        MetarValidator._extract_header(stream)

        body_tokens: List[str] = []
        trend_starts = {"BECMG", "TEMPO", "NOSIG"}
        for token in stream.tokens:
            if token in trend_starts:
                break
            body_tokens.append(token)
        return body_tokens

    def _is_jma_automated_invalid_weather_token(self, token: str) -> bool:
        if token.startswith("RE") or self.weather_parser.parse(token) is None:
            return False

        normalized = token.lstrip("+-")
        allowed = {"RA", "SN", "RASN", "SNRA", "FG", "BR", "HZ", "UP", "SQ", "TS"}
        allowed_ts = {"TSRA", "TSSN", "TSRASN", "TSSNRA", "TSUP"}

        return normalized not in allowed and normalized not in allowed_ts

    @staticmethod
    def _validate_descriptor_phenomena(
        weather_groups: List[WeatherPhenomenon], warnings: List[str]
    ) -> None:
        """Validate descriptor+phenomenon combinations per WMO Code Table 4678 Notes 7–13."""
        code_for = {v: k for k, v in WEATHER_PHENOMENA.items()}

        # Descriptor → set of allowed phenomenon codes (WMO Code Table 4678 Notes 7–13)
        desc_allowed = {
            "shallow": {"FG"},
            "partial": {"FG"},
            "patches": {"FG"},
            "low drifting": {"DU", "SA", "SN"},
            "blowing": {"DU", "SA", "SN"},
            "shower": {"RA", "SN", "GS", "GR", "UP"},
            "thunderstorm": {"RA", "SN", "GS", "GR", "UP"},
            "freezing": {"FG", "DZ", "RA"},
        }
        # VC (vicinity) valid phenomena (Note 13)
        vc_allowed = {
            "TS",
            "DS",
            "SS",
            "FG",
            "FC",
            "SH",
            "PO",
            "BLDU",
            "BLSA",
            "BLSN",
            "VA",
        }

        for wx in weather_groups:
            if wx.intensity == "vicinity":
                for p in wx.phenomena:
                    code = code_for.get(p)
                    if code and code not in vc_allowed:
                        warnings.append(
                            f"VC (vicinity) not valid with '{p}' ({code}); "
                            f"allowed: TS, DS, SS, FG, FC, SH, PO, BLDU, BLSA, BLSN, VA "
                            f"(WMO Code Table 4678 Note 13)"
                        )

            if wx.descriptor and wx.descriptor in desc_allowed:
                allowed_codes = desc_allowed[wx.descriptor]
                for p in wx.phenomena:
                    code = code_for.get(p)
                    if code and code not in allowed_codes:
                        warnings.append(
                            f"Descriptor '{wx.descriptor}' not valid with '{p}' ({code}); "
                            f"allowed phenomena: {', '.join(sorted(allowed_codes))} "
                            f"(WMO Code Table 4678 Notes 7–13)"
                        )
