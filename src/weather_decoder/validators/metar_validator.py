"""Validation rules for decoded METAR reports."""

from __future__ import annotations

import re
from typing import List, Optional

from ..constants.weather_codes import WEATHER_PHENOMENA
from ..models import (
    RunwayState,
    RunwayVisualRange,
    SkyCondition,
    Trend,
    Visibility,
    WeatherPhenomenon,
    Wind,
)
from ..parsers.pressure_parser import PressureParser
from ..parsers.sea_parser import SeaParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.token_stream import TokenStream
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..utils.patterns import COMPILED_PATTERNS


class MetarValidator:
    """Cross-field and standards validation for parsed METAR data."""

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
        sky_conditions: List[SkyCondition],
        temperature: Optional[float],
        dewpoint: Optional[float],
        trends: List[Trend],
    ) -> List[str]:
        warnings: List[str] = []

        # Report type keyword validation (WMO Reg. 15.1.1)
        if not COMPILED_PATTERNS["metar_type"].match(
            validation_tokens[0] if validation_tokens else ""
        ):
            warnings.append(
                "METAR or SPECI keyword not found at start of report per WMO Reg. 15.1.1"
            )

        # Sky condition code warnings
        for sky in sky_conditions:
            if sky.coverage in ("SKC", "CLR"):
                warnings.append(
                    "SKC/CLR are US FAA codes; WMO METAR uses NSC (no significant cloud)"
                )
                break
        if not is_automated and any(s.coverage == "NCD" for s in sky_conditions):
            warnings.append(
                "NCD (No Cloud Detected) is only valid in AUTO (automated) METARs "
                "per ICAO Annex 3 §4.5.4.6"
            )

        # Wind unit warning (WMO Reg. 15.5.1 — only KT or MPS)
        if wind and wind.unit == "KMH":
            warnings.append(
                "KMH is not a valid WMO METAR wind speed unit (only KT or MPS per WMO Reg. 15.5.1)"
            )

        # Metric RVR warning (FMH-1 §12.6.7 — requires FT suffix)
        if self._is_us_station(station_id) and any(
            rvr.unit == "M" for rvr in runway_visual_ranges
        ):
            warnings.append(
                "Metric RVR (no FT suffix) — FMH-1 §12.6.7 requires FT for US METAR"
            )

        # UK stations do not use runway state groups since CAP 746 Issue 6
        if runway_states and station_id and station_id.upper().startswith("E"):
            warnings.append(
                "Runway state groups (MOTNE) are not used in UK METARs since CAP 746 Issue 6"
            )

        is_us_station = self._is_us_station(station_id)
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

        if len(weather_groups) > 3:
            warnings.append(
                f"More than 3 present weather groups ({len(weather_groups)}); "
                "ICAO/WMO specifications allow a maximum of 3"
            )

        self._validate_weather_groups(weather_groups, visibility, warnings)

        if len(runway_visual_ranges) > 4:
            warnings.append(
                f"More than 4 RVR groups ({len(runway_visual_ranges)}); "
                "ICAO/EU specifications allow a maximum of 4"
            )

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

        # CAVOK cross-field: weather/cloud groups must be absent when CAVOK is set
        if visibility and visibility.is_cavok:
            if weather_groups or any(s.height is not None for s in sky_conditions):
                warnings.append(
                    "CAVOK used but weather/cloud groups present — these are mutually exclusive"
                )

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

        warnings.extend(self._validate_body_order(validation_tokens))

        # Dew point cannot exceed temperature (physically impossible)
        if temperature is not None and dewpoint is not None and dewpoint > temperature:
            warnings.append(
                f"Dew point ({dewpoint}°C) exceeds temperature ({temperature}°C) — "
                "physically impossible"
            )

        # Descriptor + phenomenon constraint validation (WMO Code Table 4678 Notes 7–13)
        self._validate_descriptor_phenomena(weather_groups, warnings)

        return warnings

    @staticmethod
    def _validate_weather_groups(
        weather_groups: List[WeatherPhenomenon],
        visibility: Optional[Visibility],
        warnings: List[str],
    ) -> None:
        # Weather intensity and descriptor validation (WMO 306 Vol I.1, Reg. 15.8.4, 15.8.9, FMH-1 §12.6.8)
        for wx in weather_groups:
            # Intensity (-, +, VC) only valid for precipitation, FC, SS, DS
            # NOTE: "hail" (GR) is intentionally EXCLUDED — GR cannot take intensity per FMH-1 §12.6.8.a(1)
            valid_intensity_phenomena = {
                "drizzle",
                "rain",
                "snow",
                "snow grains",
                "ice pellets",
                "small hail",
                "unknown precipitation",
                "funnel cloud",
                "duststorm",
                "sandstorm",
                "shower",
                "thunderstorm",
            }
            if wx.intensity and wx.intensity != "recent":
                # GR (hail) cannot take intensity per FMH-1 §12.6.8.a(1)
                if "hail" in wx.phenomena:
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
                # GS (small hail) in body with intensity should be warned — spec says GS intensity in RMK only
                if "small hail" in wx.phenomena:
                    warnings.append(
                        "GS (small hail) intensity in the METAR body — "
                        "FMH-1 §12.6.8.a(1) specifies GS intensity in RMK section only (e.g. 'GS MOD')"
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
                # Speed must be ≥ 6 kt (FMH-1 §12.6.5.b) to report direction variation
                speed_kt = wind.speed if wind.unit == "KT" else wind.speed * 1.944
                if speed_kt < 6:
                    warnings.append(
                        "Wind direction variation (nnnVnnn) reported with speed < 6 kt — "
                        "report as VRBxxKT per FMH-1 §12.6.5.b"
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
            r"^R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(?:FT)?([UDN])?$", token
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
            "freezing": {"FG", "DZ", "RA", "UP"},
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
