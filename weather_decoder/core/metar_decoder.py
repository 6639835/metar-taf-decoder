"""Main METAR decoder that orchestrates parsing."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Tuple

from ..data.metar_data import MetarData
from ..models import MilitaryColorCode, MetarReport
from ..parsers.pressure_parser import PressureParser
from ..parsers.remarks_parser import RemarksParser
from ..parsers.runway_parser import RunwayParser
from ..parsers.sea_parser import SeaParser
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.trend_parser import TrendParser
from ..parsers.token_stream import TokenStream
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..parsers.windshear_parser import WindShearParser
from ..constants import MILITARY_COLOR_CODES
from ..utils.patterns import COMPILED_PATTERNS


class MetarDecoder:
    """METAR decoder class that parses raw METAR strings."""

    def __init__(self):
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.pressure_parser = PressureParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()
        self.remarks_parser = RemarksParser()
        self.runway_parser = RunwayParser()
        self.sea_parser = SeaParser()
        self.windshear_parser = WindShearParser()
        self.trend_parser = TrendParser(
            wind_parser=self.wind_parser,
            sky_parser=self.sky_parser,
            weather_parser=self.weather_parser,
        )

    def decode(self, raw_metar: str) -> MetarData:
        metar = raw_metar.strip()
        parts = metar.split()

        maintenance_needed = metar.rstrip().endswith("$") or "$" in parts

        if "RMK" in parts:
            rmk_index = parts.index("RMK")
            parts = parts[:rmk_index]

        is_nil = "NIL" in parts
        if is_nil:
            nil_index = parts.index("NIL")
            parts = parts[:nil_index]

        stream = TokenStream(parts)

        report_type, station_id, observation_time, is_automated, is_corrected = self._extract_header(stream)

        wind = self.wind_parser.extract(stream)
        visibility = self.visibility_parser.extract(stream)
        runway_states = self.runway_parser.extract_runway_state(stream)
        runway_visual_ranges = self.runway_parser.extract_rvr(stream)
        weather_groups = self.weather_parser.extract_all(stream)
        sky_conditions = self.sky_parser.extract_all(stream)
        temperature, dewpoint = self.temperature_parser.extract_temperature_dewpoint(stream.tokens)
        altimeter = self.pressure_parser.extract_altimeter(stream)
        recent_weather = self.weather_parser.extract_recent(stream)
        sea_conditions = self.sea_parser.extract_all(stream)
        windshear = self.windshear_parser.extract_all(stream)
        trends = self.trend_parser.extract_trends(stream)
        military_color_codes = self._extract_military_color_codes(stream)

        remarks, remarks_decoded = self.remarks_parser.parse(metar)

        # Tier 4: Cross-field and count validation warnings
        validation_warnings: List[str] = []

        # Report type keyword validation (WMO Reg. 15.1.1)
        if not COMPILED_PATTERNS["metar_type"].match(parts[0] if parts else ""):
            validation_warnings.append("METAR or SPECI keyword not found at start of report per WMO Reg. 15.1.1")

        # Sky condition code warnings
        for sky in sky_conditions:
            if sky.coverage in ("SKC", "CLR"):
                validation_warnings.append("SKC/CLR are US FAA codes; WMO METAR uses NSC (no significant cloud)")
                break
        if not is_automated and any(s.coverage == "NCD" for s in sky_conditions):
            validation_warnings.append(
                "NCD (No Cloud Detected) is only valid in AUTO (automated) METARs " "per ICAO Annex 3 §4.5.4.6"
            )

        # Wind unit warning (WMO Reg. 15.5.1 — only KT or MPS)
        if wind and wind.unit == "KMH":
            validation_warnings.append("KMH is not a valid WMO METAR wind speed unit (only KT or MPS per WMO Reg. 15.5.1)")

        # Metric RVR warning (FMH-1 §12.6.7 — requires FT suffix)
        if any(rvr.unit == "M" for rvr in runway_visual_ranges):
            validation_warnings.append("Metric RVR (no FT suffix) — FMH-1 §12.6.7 requires FT for US METAR")

        # UK stations do not use runway state groups since CAP 746 Issue 6
        if runway_states and station_id and station_id.upper().startswith("E"):
            validation_warnings.append("Runway state groups (MOTNE) are not used in UK METARs since CAP 746 Issue 6")

        if is_automated and visibility and visibility.is_cavok:
            validation_warnings.append("CAVOK should not appear in automated METAR/SPECI — use NSC or NCD instead")

        if len(sky_conditions) > 6:
            validation_warnings.append(
                f"More than 6 cloud layers reported ({len(sky_conditions)}); "
                "FMH-1 §9.5.2 allows a maximum of 6 (ICAO/WMO allow up to 4)"
            )
        elif len(sky_conditions) > 4:
            validation_warnings.append(
                f"More than 4 cloud layers reported ({len(sky_conditions)}); "
                "ICAO/WMO specifications allow a maximum of 4 "
                "(FMH-1 §9.5.2 allows up to 6 for US stations)"
            )

        if len(weather_groups) > 3:
            validation_warnings.append(
                f"More than 3 present weather groups ({len(weather_groups)}); " "ICAO/WMO specifications allow a maximum of 3"
            )

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
                    validation_warnings.append(
                        f"Intensity modifier '{wx.intensity}' is not valid for GR (hail) "
                        "per FMH-1 §12.6.8.a(1) — hail has no intensity qualifier"
                    )
                # -DS and -SS (light duststorm/sandstorm) are invalid — only moderate+ allowed
                if wx.intensity == "light" and any(p in ("duststorm", "sandstorm") for p in wx.phenomena):
                    phenom_names = ", ".join(p for p in wx.phenomena if p in ("duststorm", "sandstorm"))
                    validation_warnings.append(
                        f"Light intensity ('-') is not valid for {phenom_names} (DS/SS) — "
                        "only moderate or heavy (+) intensity is allowed"
                    )
                # GS (small hail) in body with intensity should be warned — spec says GS intensity in RMK only
                if "small hail" in wx.phenomena:
                    validation_warnings.append(
                        f"GS (small hail) intensity in the METAR body — "
                        "FMH-1 §12.6.8.a(1) specifies GS intensity in RMK section only (e.g. 'GS MOD')"
                    )
                # Check if any phenomenon justifies intensity
                has_valid_phenomena = any(p in valid_intensity_phenomena for p in wx.phenomena)
                if not has_valid_phenomena:
                    validation_warnings.append(
                        f"Intensity modifier '{wx.intensity}' not valid for weather phenomena: "
                        f"{', '.join(wx.phenomena)} (WMO 306 Reg. 15.8.4)"
                    )
            # Visibility-dependent phenomenon checks (WMO Reg. 15.8.12-15)
            if visibility and visibility.value < 10000:
                vis_m = visibility.value if visibility.unit == "M" else visibility.value * 1000
                # FG requires visibility < 1000m
                if "fog" in wx.phenomena and vis_m >= 1000:
                    validation_warnings.append(
                        f"FG (fog) reported with visibility {vis_m}m but requires < 1000m (WMO Reg. 15.8.14)"
                    )
                # BR requires 1000 ≤ visibility ≤ 5000m
                if "mist" in wx.phenomena and not (1000 <= vis_m <= 5000):
                    validation_warnings.append(
                        f"BR (mist) reported with visibility {vis_m}m but requires 1000-5000m (WMO Reg. 15.8.13)"
                    )
                # FU, HZ, DU, SA require visibility ≤ 5000m
                obscuration = {"smoke", "haze", "dust", "sand"}
                if any(p in obscuration for p in wx.phenomena) and vis_m > 5000:
                    px_list = ", ".join(p[:2].upper() for p in wx.phenomena if p in obscuration)
                    validation_warnings.append(
                        f"{px_list} reported with visibility {vis_m}m but requires ≤ 5000m (WMO Reg. 15.8.12)"
                    )

        if len(runway_visual_ranges) > 4:
            validation_warnings.append(
                f"More than 4 RVR groups ({len(runway_visual_ranges)}); " "ICAO/EU specifications allow a maximum of 4"
            )

        # TS in present weather but no CB in sky (CAP 746 §4.112)
        has_ts = any(
            (w.descriptor == "thunderstorm" or (w.phenomena and "thunderstorm" in w.phenomena)) for w in weather_groups
        )
        has_cb = any(s.cb for s in sky_conditions)
        if has_ts and not has_cb:
            validation_warnings.append("Thunderstorm (TS) present weather reported without a CB cloud layer (CAP 746 §4.112)")

        # Wind variation validation (ICAO Annex 3 §4.1.5.2, CAP 746 §4.11-4.13)
        if wind:
            if wind.variable_range and not wind.is_variable:
                var_lo, var_hi = wind.variable_range
                variation = (var_hi - var_lo) % 360
                # nnnVnnn only valid when variation is 60-179° (ICAO §4.1.5.2 b)
                if variation < 60:
                    validation_warnings.append(
                        f"Wind variable range {var_lo:03d}V{var_hi:03d} reported but variation "
                        f"({variation}°) is less than 60° — omit the variable range"
                    )
                elif variation >= 180:
                    validation_warnings.append(
                        f"Wind variable range {var_lo:03d}V{var_hi:03d} reported but variation "
                        f"({variation}°) is ≥180° — report as VRB instead"
                    )
                # Speed must be ≥ 6 kt (FMH-1 §12.6.5.b) to report direction variation
                speed_kt = wind.speed if wind.unit == "KT" else wind.speed * 1.944
                if speed_kt < 6:
                    validation_warnings.append(
                        "Wind direction variation (nnnVnnn) reported with speed < 6 kt — "
                        "report as VRBxxKT per FMH-1 §12.6.5.b"
                    )
            if wind.direction is not None and not wind.is_variable and not wind.is_calm:
                # Direction should be a multiple of 10° (CAP 746 §4.16)
                if wind.direction % 10 != 0:
                    validation_warnings.append(
                        f"Wind direction {wind.direction:03d}° is not rounded to the nearest 10° " "(CAP 746 §4.16)"
                    )
                # Direction must be 010-360°
                if not (10 <= wind.direction <= 360):
                    validation_warnings.append(f"Wind direction {wind.direction:03d}° is outside valid range 010-360°")

        # CAVOK cross-field: weather/cloud groups must be absent when CAVOK is set
        if visibility and visibility.is_cavok:
            if weather_groups or any(s.height is not None for s in sky_conditions):
                validation_warnings.append("CAVOK used but weather/cloud groups present — these are mutually exclusive")

        # NOSIG and BECMG/TEMPO are mutually exclusive (WMO Reg. 15.14.15)
        has_nosig = any(t.kind == "NOSIG" for t in trends)
        has_becmg_tempo = any(t.kind in ("BECMG", "TEMPO") for t in trends)
        if has_nosig and has_becmg_tempo:
            validation_warnings.append("NOSIG and BECMG/TEMPO are mutually exclusive per WMO Reg. 15.14.15")

        # NSW in METAR body (WMO Reg. 15.14.13) — NSW is TREND-only
        _trend_starts = {"BECMG", "TEMPO", "NOSIG"}
        _nsw_in_body = False
        for _tok in parts:
            if _tok in _trend_starts:
                break
            if _tok == "NSW":
                _nsw_in_body = True
                break
        if _nsw_in_body:
            validation_warnings.append(
                "NSW (no significant weather) is not valid in METAR body — " "only in TREND section per WMO Reg. 15.14.13"
            )

        # Dew point cannot exceed temperature (physically impossible)
        if temperature is not None and dewpoint is not None and dewpoint > temperature:
            validation_warnings.append(
                f"Dew point ({dewpoint}°C) exceeds temperature ({temperature}°C) — " "physically impossible"
            )

        # Descriptor + phenomenon constraint validation (WMO Code Table 4678 Notes 7–13)
        self._validate_descriptor_phenomena(weather_groups, validation_warnings)

        report = MetarReport(
            raw_metar=raw_metar,
            report_type=report_type,
            station_id=station_id,
            observation_time=observation_time,
            is_automated=is_automated,
            is_nil=is_nil,
            maintenance_needed=maintenance_needed,
            wind=wind,
            visibility=visibility,
            runway_visual_ranges=runway_visual_ranges,
            runway_states=runway_states,
            weather=weather_groups,
            recent_weather=recent_weather,
            sky=sky_conditions,
            temperature=temperature,
            dewpoint=dewpoint,
            altimeter=altimeter,
            sea_conditions=sea_conditions,
            windshear=windshear,
            trends=trends,
            is_corrected=is_corrected,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
            military_color_codes=military_color_codes,
            validation_warnings=validation_warnings,
        )

        return MetarData(**report.__dict__)

    def _extract_header(self, stream: TokenStream) -> Tuple[str, str, datetime, bool, bool]:
        report_type = "METAR"
        station_id = ""
        observation_time = datetime.now(timezone.utc)
        is_automated = False
        is_corrected = False

        if stream.peek() and COMPILED_PATTERNS["metar_type"].match(stream.peek()):
            report_type = stream.pop(0)

        if stream.peek() == "COR":
            is_corrected = True
            stream.pop(0)

        if stream.peek() and COMPILED_PATTERNS["station_id"].match(stream.peek()):
            station_id = stream.pop(0)

        if stream.peek() and re.match(r"\d{6}Z", stream.peek()):
            time_str = stream.pop(0)
            observation_time = self.time_parser.parse_observation_time(time_str) or observation_time

        if stream.peek() == "AUTO":
            is_automated = True
            stream.pop(0)

        return report_type, station_id, observation_time, is_automated, is_corrected

    def _extract_military_color_codes(self, stream: TokenStream) -> List[MilitaryColorCode]:
        codes: List[MilitaryColorCode] = []
        i = 0
        while i < len(stream.tokens):
            token = stream.tokens[i]
            if token in MILITARY_COLOR_CODES:
                stream.pop(i)
                codes.append(MilitaryColorCode(code=token, description=MILITARY_COLOR_CODES[token]))
            else:
                i += 1
        return codes

    @staticmethod
    def _validate_descriptor_phenomena(weather_groups, validation_warnings):
        """Validate descriptor+phenomenon combinations per WMO Code Table 4678 Notes 7–13."""
        from ..constants.weather_codes import WEATHER_PHENOMENA as _WP

        _code_for = {v: k for k, v in _WP.items()}

        # Descriptor → set of allowed phenomenon codes (WMO Code Table 4678 Notes 7–13)
        _desc_allowed = {
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
        _vc_allowed = {"TS", "DS", "SS", "FG", "FC", "SH", "PO", "BLDU", "BLSA", "BLSN", "VA"}

        for wx in weather_groups:
            if wx.intensity == "vicinity":
                for p in wx.phenomena:
                    code = _code_for.get(p)
                    if code and code not in _vc_allowed:
                        validation_warnings.append(
                            f"VC (vicinity) not valid with '{p}' ({code}); "
                            f"allowed: TS, DS, SS, FG, FC, SH, PO, BLDU, BLSA, BLSN, VA "
                            f"(WMO Code Table 4678 Note 13)"
                        )

            if wx.descriptor and wx.descriptor in _desc_allowed:
                allowed_codes = _desc_allowed[wx.descriptor]
                for p in wx.phenomena:
                    code = _code_for.get(p)
                    if code and code not in allowed_codes:
                        validation_warnings.append(
                            f"Descriptor '{wx.descriptor}' not valid with '{p}' ({code}); "
                            f"allowed phenomena: {', '.join(sorted(allowed_codes))} "
                            f"(WMO Code Table 4678 Notes 7–13)"
                        )
