"""Formatting utilities for METAR reports."""

from __future__ import annotations

import re
from typing import Dict, List

from .common import (
    format_pressure,
    format_sky_conditions_list,
    format_temperature,
    format_visibility,
    format_weather_groups_list,
    format_wind,
)
from ..constants.change_codes import TREND_TYPES
from ..models import MetarReport, RunwayState, RunwayVisualRange
from ..parsers.sky_parser import SkyParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.wind_parser import WindParser
from ..parsers.sea_parser import SeaParser
from ..utils.constants import MILITARY_COLOR_CODES
from ..utils.patterns import COMPILED_PATTERNS


class MetarFormatter:
    """Formatter for MetarReport objects."""

    @staticmethod
    def format(metar: MetarReport) -> str:
        formatter = MetarFormatter()
        return formatter._format_metar(metar)

    def _format_metar(self, metar: MetarReport) -> str:
        lines = [
            f"{metar.report_type} for {metar.station_id} issued "
            f"{metar.observation_time.day:02d} "
            f"{metar.observation_time.hour:02d}:{metar.observation_time.minute:02d} UTC",
        ]

        if metar.is_nil:
            lines.append("Status: NIL (Missing report)")
            return "\n".join(lines)

        report_suffix = " COR" if metar.is_corrected else ""
        lines.append(f"Type: {'AUTO' if metar.is_automated else 'Manual'} {metar.report_type}{report_suffix}")

        sections: Dict[str, List[str]] = {}
        sections["wind"] = [f"Wind: {format_wind(metar.wind)}"]
        sections["visibility"] = [f"Visibility: {format_visibility(metar.visibility)}"]

        if metar.runway_visual_ranges:
            sections["runway_visual_range"] = self._format_rvr(metar.runway_visual_ranges)

        if metar.runway_states:
            sections["runway_state"] = self._format_runway_states(metar.runway_states)

        if metar.weather:
            wx_lines = format_weather_groups_list(metar.weather)
            if wx_lines:
                sections["weather"] = ["Weather Phenomena:"] + [f"  {line}" for line in wx_lines]

        if metar.recent_weather:
            recent_lines = format_weather_groups_list(metar.recent_weather)
            if recent_lines:
                sections["recent_weather"] = ["Recent Weather:"] + [f"  {line}" for line in recent_lines]

        if metar.sky:
            sky_lines = format_sky_conditions_list(metar.sky)
            if sky_lines:
                sections["sky"] = ["Sky Conditions:"] + [f"  {line}" for line in sky_lines]

        if metar.windshear:
            descriptions = [ws.description for ws in metar.windshear]
            sections["windshear"] = [f"Windshear: {', '.join(descriptions)}"]

        sections["temperature"] = [
            f"Temperature: {format_temperature(metar.temperature)}",
            f"Dew Point: {format_temperature(metar.dewpoint)}",
        ]

        sections["altimeter"] = [f"Altimeter: {format_pressure(metar.altimeter)}"]

        if metar.sea_conditions:
            sections["sea_conditions"] = self._format_sea_conditions(metar.sea_conditions)

        if metar.trends:
            trend_lines: List[str] = []
            for i, trend in enumerate(metar.trends):
                prefix = "Trend: " if i == 0 else "       "
                trend_lines.append(f"{prefix}{trend.description}")
            sections["trends"] = trend_lines

        if metar.military_color_codes:
            code_lines = ["Military Color Codes:"]
            for code in metar.military_color_codes:
                code_lines.append(f"  {code.code}: {code.description}")
            sections["military_color_codes"] = code_lines

        ordered_sections = self._order_sections(metar, list(sections.keys()))
        for section in ordered_sections:
            lines.extend(sections[section])

        if metar.remarks:
            lines.extend(self._format_remarks(metar.remarks, metar.remarks_decoded))

        return "\n".join(lines)

    def _order_sections(self, metar: MetarReport, available_sections: List[str]) -> List[str]:
        tokens = metar.raw_metar.strip().split()
        if "RMK" in tokens:
            tokens = tokens[: tokens.index("RMK")]
        if "NIL" in tokens:
            tokens = tokens[: tokens.index("NIL")]

        wind_parser = WindParser()
        visibility_parser = VisibilityParser()
        weather_parser = WeatherParser()
        sky_parser = SkyParser()
        sea_parser = SeaParser()

        ordered: List[str] = []

        def add(section: str) -> None:
            if section in available_sections and section not in ordered:
                ordered.append(section)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if wind_parser.parse(token):
                add("wind")
                i += 1
                continue

            if visibility_parser.parse(token):
                add("visibility")
                i += 1
                continue

            if token.isdigit() and i + 1 < len(tokens) and re.match(r"^\d+/\d+SM$", tokens[i + 1]):
                add("visibility")
                i += 1
                continue

            if COMPILED_PATTERNS["rvr"].match(token):
                add("runway_visual_range")
                i += 1
                continue

            if COMPILED_PATTERNS["runway_state"].match(token):
                add("runway_state")
                i += 1
                continue

            if weather_parser.is_recent_weather_token(token):
                add("recent_weather")
                i += 1
                continue

            if weather_parser.parse(token):
                add("weather")
                i += 1
                continue

            if sky_parser.parse(token):
                add("sky")
                i += 1
                continue

            if COMPILED_PATTERNS["temperature"].match(token):
                add("temperature")
                i += 1
                continue

            if COMPILED_PATTERNS["altimeter"].match(token):
                add("altimeter")
                i += 1
                continue

            if sea_parser.parse(token):
                add("sea_conditions")
                i += 1
                continue

            if token == "WS" or token.startswith("WS"):
                add("windshear")
                i += 1
                continue

            if token in TREND_TYPES:
                add("trends")
                i += 1
                continue

            if token in MILITARY_COLOR_CODES:
                add("military_color_codes")
                i += 1
                continue

            i += 1

        default_order = [
            "wind",
            "visibility",
            "runway_visual_range",
            "runway_state",
            "weather",
            "recent_weather",
            "sky",
            "windshear",
            "temperature",
            "altimeter",
            "sea_conditions",
            "trends",
            "military_color_codes",
        ]

        for section in default_order:
            if section in available_sections and section not in ordered:
                ordered.append(section)

        return ordered

    def _format_rvr(self, rvr_list: List[RunwayVisualRange]) -> List[str]:
        lines = ["Runway Visual Range:"]

        for rvr in rvr_list:
            if rvr.variable_range is not None:
                min_prefix = "less than " if rvr.is_less_than else "more than " if rvr.is_more_than else ""
                max_prefix = "less than " if rvr.variable_less_than else "more than " if rvr.variable_more_than else ""
                rvr_line = (
                    f"  Runway {rvr.runway}: " f"{min_prefix}{rvr.visual_range} to {max_prefix}{rvr.variable_range} {rvr.unit}"
                )
            else:
                if rvr.is_more_than:
                    rvr_line = f"  Runway {rvr.runway}: More than {rvr.visual_range} {rvr.unit}"
                elif rvr.is_less_than:
                    rvr_line = f"  Runway {rvr.runway}: Less than {rvr.visual_range} {rvr.unit}"
                else:
                    rvr_line = f"  Runway {rvr.runway}: {rvr.visual_range} {rvr.unit}"

            if rvr.trend:
                rvr_line += f" ({rvr.trend})"

            lines.append(rvr_line)

        return lines

    def _format_sea_conditions(self, sea_conditions) -> List[str]:
        lines = ["Sea Conditions:"]
        for condition in sea_conditions:
            parts: List[str] = []

            if condition.temperature_missing:
                parts.append("sea-surface temperature not reported")
            elif condition.sea_surface_temperature is not None:
                parts.append(f"sea-surface temperature {condition.sea_surface_temperature}°C")

            if condition.state_missing:
                parts.append("state of sea not reported")
            elif condition.state_of_sea is not None:
                parts.append(f"state of sea {condition.state_of_sea}")

            if condition.wave_height_missing:
                parts.append("significant wave height not reported")
            elif condition.significant_wave_height_m is not None:
                parts.append(f"significant wave height {condition.significant_wave_height_m:.1f} m")

            lines.append(f"  {', '.join(parts) if parts else condition.raw}")

        return lines

    def _format_runway_states(self, reports: List[RunwayState]) -> List[str]:
        lines = ["Runway State Reports:"]
        for report in reports:
            if report.all_runways:
                runway_label = "All runways"
            elif report.from_previous_report:
                runway_label = "Previous report"
            else:
                runway_label = f"Runway {report.runway}"

            lines.append(f"  {runway_label}: {report.deposit}, {report.contamination}, {report.depth}, {report.braking}")
        return lines

    def _format_remarks(self, remarks: str, decoded: Dict) -> List[str]:
        lines = []

        if remarks.strip():
            lines.append(f"Remarks: {remarks}")

        if decoded:
            lines.extend(self._format_decoded_remarks(decoded))

        return lines

    def _format_decoded_remarks(self, decoded: Dict) -> List[str]:
        lines: List[str] = []

        for key, value in decoded.items():
            if key == "directional_info":
                lines.extend(self._format_directional_info(value))
            elif key == "variable_ceiling":
                lines.append(f"  Variable Ceiling: {value}")
            elif key == "runway_winds":
                lines.extend(self._format_runway_winds(value))
            elif key == "cloud_layers":
                lines.append("  Cloud layers:")
                for layer in value:
                    lines.append(f"    {layer}")
            elif key == "altitude_winds":
                lines.extend(self._format_altitude_winds(value))
            elif key == "location_winds":
                lines.extend(self._format_location_winds(value))
            elif key == "runway_state_reports_remarks":
                lines.extend(self._format_runway_state_remarks(value))
            elif isinstance(value, dict):
                lines.append(f"  {key}: {', '.join([f'{k}: {v}' for k, v in value.items()])}")
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    lines.append(f"  {key}:")
                    for item in value:
                        lines.append(f"    {', '.join([f'{k}: {v}' for k, v in item.items()])}")
                else:
                    lines.append(f"  {key}: {', '.join(str(item) for item in value)}")
            else:
                lines.append(f"  {key}: {value}")

        return lines

    def _format_directional_info(self, info_list: List[Dict]) -> List[str]:
        lines = ["  Directional information:"]

        for info in info_list:
            modifier = info.get("modifier", "")
            phenomenon = info.get("phenomenon", "")
            directions = info.get("directions", [])

            description = []
            if modifier:
                description.append(modifier)
            if phenomenon:
                description.append(phenomenon)
            if directions:
                if len(directions) == 1:
                    dir_text = directions[0]
                    if "from " in dir_text or "kilometers" in dir_text or "overhead" in dir_text:
                        description.append(dir_text)
                    else:
                        description.append(f"in the {dir_text}")
                else:
                    description.append(f"in the {', '.join(directions[:-1])} and {directions[-1]}")

            lines.append(f"    {' '.join(description)}")

        return lines

    def _format_runway_winds(self, winds: List[Dict]) -> List[str]:
        lines = ["  Runway-specific winds:"]

        for wind in winds:
            runway = wind.get("runway", "")
            direction = wind.get("direction", "")
            speed = wind.get("speed", "")
            unit = wind.get("unit", "KT")
            gust = wind.get("gust", "")
            var_dir = wind.get("variable_direction", [])

            wind_text = f"    Runway {runway}: {direction}° at {speed} {unit}"

            if gust:
                wind_text += f", gusting to {gust} {unit}"

            if var_dir and len(var_dir) == 2:
                wind_text += f" (varying between {var_dir[0]}° and {var_dir[1]}°)"

            lines.append(wind_text)

        return lines

    def _format_altitude_winds(self, winds: List[Dict]) -> List[str]:
        lines = ["  Altitude-specific winds:"]

        for wind in winds:
            altitude = wind.get("altitude", "")
            altitude_unit = wind.get("altitude_unit", "feet")
            direction = wind.get("direction", "")
            speed = wind.get("speed", "")
            unit = wind.get("unit", "KT")
            gust = wind.get("gust", "")

            wind_text = f"    At {altitude} {altitude_unit}: {direction}° at {speed} {unit}"

            if gust:
                wind_text += f", gusting to {gust} {unit}"

            lines.append(wind_text)

        return lines

    def _format_location_winds(self, winds: List[Dict]) -> List[str]:
        lines = ["  Location-specific winds:"]

        for wind in winds:
            location = wind.get("location", "")
            direction = wind.get("direction", "")
            speed = wind.get("speed", "")
            unit = wind.get("unit", "KT")
            gust = wind.get("gust", "")

            wind_text = f"    At {location}: {direction}° at {speed} {unit}"

            if gust:
                wind_text += f", gusting to {gust} {unit}"

            lines.append(wind_text)

        return lines

    def _format_runway_state_remarks(self, reports: List[Dict]) -> List[str]:
        lines = ["  Runway State Reports in Remarks:"]

        for report in reports:
            lines.append(
                f"    Runway {report['runway']}: {report['deposit']}, "
                f"{report['contamination']}, {report['depth']}, {report['braking']}"
            )

        return lines
