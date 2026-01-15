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
from ..parsers.sky_parser import SkyParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..parsers.trend_parser import TrendParser
from ..parsers.token_stream import TokenStream
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..parsers.windshear_parser import WindShearParser
from ..utils.constants import MILITARY_COLOR_CODES
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

        report_type, station_id, observation_time, is_automated = self._extract_header(stream)

        wind = self.wind_parser.extract(stream)
        visibility = self.visibility_parser.extract(stream)
        runway_states = self.runway_parser.extract_runway_state(stream)
        runway_visual_ranges = self.runway_parser.extract_rvr(stream)
        weather_groups = self.weather_parser.extract_all(stream)
        sky_conditions = self.sky_parser.extract_all(stream)
        temperature, dewpoint = self.temperature_parser.extract_temperature_dewpoint(stream.tokens)
        altimeter = self.pressure_parser.extract_altimeter(stream)
        windshear = self.windshear_parser.extract_all(stream)
        trends = self.trend_parser.extract_trends(stream)
        military_color_codes = self._extract_military_color_codes(stream)

        remarks, remarks_decoded = self.remarks_parser.parse(metar)

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
            sky=sky_conditions,
            temperature=temperature,
            dewpoint=dewpoint,
            altimeter=altimeter,
            windshear=windshear,
            trends=trends,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
            military_color_codes=military_color_codes,
        )

        return MetarData(**report.__dict__)

    def _extract_header(self, stream: TokenStream) -> Tuple[str, str, datetime, bool]:
        report_type = "METAR"
        station_id = ""
        observation_time = datetime.now(timezone.utc)
        is_automated = False

        if stream.peek() and COMPILED_PATTERNS["metar_type"].match(stream.peek()):
            report_type = stream.pop(0)

        if stream.peek() and COMPILED_PATTERNS["station_id"].match(stream.peek()):
            station_id = stream.pop(0)

        if stream.peek() and re.match(r"\d{6}Z", stream.peek()):
            time_str = stream.pop(0)
            observation_time = self.time_parser.parse_observation_time(time_str) or observation_time

        if stream.peek() == "AUTO":
            is_automated = True
            stream.pop(0)

        return report_type, station_id, observation_time, is_automated

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
