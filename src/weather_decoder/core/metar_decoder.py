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
from ..validators import MetarValidator


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
        self.validator = MetarValidator(
            wind_parser=self.wind_parser,
            visibility_parser=self.visibility_parser,
            weather_parser=self.weather_parser,
            sky_parser=self.sky_parser,
            temperature_parser=self.temperature_parser,
            pressure_parser=self.pressure_parser,
            sea_parser=self.sea_parser,
        )

    def decode(self, raw_metar: str) -> MetarData:
        metar = raw_metar.strip()
        if metar.endswith("="):
            metar = metar[:-1].rstrip()
        parts = metar.split()

        maintenance_needed = metar.rstrip().endswith("$") or "$" in parts

        if "RMK" in parts:
            rmk_index = parts.index("RMK")
            parts = parts[:rmk_index]

        is_nil = "NIL" in parts
        if is_nil:
            nil_index = parts.index("NIL")
            parts = parts[:nil_index]

        validation_tokens = list(parts)
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

        validation_warnings = self.validator.validate(
            validation_tokens=validation_tokens,
            remaining_tokens=parts,
            station_id=station_id,
            is_automated=is_automated,
            wind=wind,
            visibility=visibility,
            runway_visual_ranges=runway_visual_ranges,
            runway_states=runway_states,
            weather_groups=weather_groups,
            sky_conditions=sky_conditions,
            temperature=temperature,
            dewpoint=dewpoint,
            trends=trends,
        )

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

        next_token = stream.peek()
        if next_token is not None and COMPILED_PATTERNS["metar_type"].match(next_token):
            report_type = stream.pop(0)

        if stream.peek() == "COR":
            is_corrected = True
            stream.pop(0)

        next_token = stream.peek()
        if next_token is not None and COMPILED_PATTERNS["station_id"].match(next_token):
            station_id = stream.pop(0)

        next_token = stream.peek()
        if next_token is not None and re.match(r"\d{6}Z", next_token):
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
