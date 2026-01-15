"""Trend information parser for METAR reports."""

from __future__ import annotations

import re
from typing import List, Optional

from ..constants.change_codes import TREND_TYPES
from ..models import Trend, TrendTime
from .token_stream import TokenStream


class TrendParser:
    """Parser for trend information in METAR reports."""

    def __init__(self, wind_parser=None, sky_parser=None, weather_parser=None):
        self.wind_parser = wind_parser
        self.sky_parser = sky_parser
        self.weather_parser = weather_parser

    def extract_trends(self, stream: TokenStream) -> List[Trend]:
        trends: List[Trend] = []
        i = 0
        while i < len(stream.tokens):
            if stream.tokens[i] in TREND_TYPES:
                trend_type = stream.pop(i)
                trend = self._parse_trend_group(trend_type, stream, i)
                if trend:
                    trends.append(trend)
            else:
                i += 1
        return trends

    def _parse_trend_group(self, trend_type: str, stream: TokenStream, start_idx: int) -> Optional[Trend]:
        if trend_type == "NOSIG":
            return Trend(
                kind=trend_type,
                description="No significant change expected in next 2 hours",
                raw=trend_type,
            )

        trend_elements: List[str] = []
        time_info: dict = {}
        weather_changes: List[str] = []

        i = start_idx
        while i < len(stream.tokens) and stream.tokens[i] not in TREND_TYPES and not stream.tokens[i].startswith("RMK"):
            element = stream.pop(i)
            trend_elements.append(element)

            if self._parse_time_indicator(element, time_info):
                continue

            change = self._parse_weather_change(element)
            if change:
                weather_changes.append(change)

        description = self._build_trend_description(trend_type, time_info, weather_changes)

        time = TrendTime(
            from_time=time_info.get("from"),
            until_time=time_info.get("until"),
            at_time=time_info.get("at"),
        ) if time_info else None

        return Trend(
            kind=trend_type,
            raw=f"{trend_type} {' '.join(trend_elements)}" if trend_elements else trend_type,
            time=time,
            changes=tuple(weather_changes),
            description=description,
        )

    def _parse_time_indicator(self, element: str, time_info: dict) -> bool:
        if element.startswith("FM"):
            match = re.match(r"FM(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["from"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        elif element.startswith("TL"):
            match = re.match(r"TL(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["until"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        elif element.startswith("AT"):
            match = re.match(r"AT(\d{4})", element)
            if match:
                time_val = match.group(1)
                time_info["at"] = f"{time_val[:2]}:{time_val[2:]} UTC"
                return True
        return False

    def _parse_weather_change(self, element: str) -> Optional[str]:
        if element.isdigit() and len(element) == 4:
            vis_value = int(element)
            if vis_value == 9999:
                return "visibility 10km or more"
            if vis_value >= 1000:
                return f"visibility {vis_value/1000:.1f}km"
            return f"visibility {vis_value}m"

        wind_match = re.match(r"(\d{3}|VRB)\d{2,3}(G\d{2,3})?(KT|MPS|KMH)", element)
        if wind_match and self.wind_parser:
            wind_info = self.wind_parser.parse(element)
            if wind_info:
                return self._format_wind_change(wind_info)

        cloud_match = re.match(r"(SKC|CLR|NSC|NCD|FEW|SCT|BKN|OVC|VV)(\d{3}|///)?", element)
        if cloud_match and self.sky_parser:
            sky_info = self.sky_parser.parse(element)
            if sky_info:
                return self._format_sky_change(sky_info)

        wx_match = re.match(
            r"^[-+]?(VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?"
            r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+",
            element,
        )
        if wx_match and self.weather_parser:
            wx_info = self.weather_parser.parse(element)
            if wx_info:
                return self._format_weather_change(wx_info)

        if element == "NSW":
            return "no significant weather"

        if element == "CAVOK":
            return "CAVOK"

        return None

    @staticmethod
    def _format_wind_change(wind_info) -> str:
        dir_text = "variable" if wind_info.is_variable or wind_info.direction is None else f"{wind_info.direction}°"
        wind_desc = f"wind {dir_text} at {wind_info.speed} {wind_info.unit}"
        if wind_info.gust:
            wind_desc += f" gusting {wind_info.gust}"
        return wind_desc

    @staticmethod
    def _format_sky_change(sky_info) -> str:
        sky_type = sky_info.coverage

        if sky_type in ["SKC", "CLR"]:
            return "sky clear"
        if sky_type == "NSC":
            return "no significant cloud"
        if sky_type == "NCD":
            return "no cloud detected"
        if sky_type == "VV":
            if sky_info.unknown_height or sky_info.height is None:
                return "vertical visibility unknown"
            return f"vertical visibility {sky_info.height}ft"

        cloud_desc = f"{sky_type} at {sky_info.height}ft"
        if sky_info.cb:
            cloud_desc += " CB"
        elif sky_info.tcu:
            cloud_desc += " TCU"
        return cloud_desc

    @staticmethod
    def _format_weather_change(wx_info) -> str:
        wx_parts = []
        if wx_info.intensity:
            wx_parts.append(wx_info.intensity)
        if wx_info.descriptor:
            wx_parts.append(wx_info.descriptor)
        if wx_info.phenomena:
            wx_parts.extend(wx_info.phenomena)
        return " ".join(wx_parts) if wx_parts else ""

    @staticmethod
    def _build_trend_description(trend_type: str, time_info: dict, weather_changes: List[str]) -> str:
        parts = []

        if trend_type == "BECMG":
            parts.append("Becoming")
        elif trend_type == "TEMPO":
            parts.append("Temporary")

        if time_info.get("from") and time_info.get("until"):
            parts.append(f"from {time_info['from']} until {time_info['until']}:")
        elif time_info.get("from"):
            parts.append(f"from {time_info['from']}:")
        elif time_info.get("until"):
            parts.append(f"until {time_info['until']}:")
        elif time_info.get("at"):
            parts.append(f"at {time_info['at']}:")
        else:
            parts.append("-")

        if weather_changes:
            parts.append(", ".join(weather_changes))

        return " ".join(parts)
