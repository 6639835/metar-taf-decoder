"""Formatting utilities for METAR reports."""

from __future__ import annotations

from typing import Dict, List

from .common import (
    format_pressure,
    format_sky_conditions_list,
    format_temperature,
    format_visibility,
    format_weather_groups_list,
    format_wind,
)
from ..models import MetarReport, RunwayState, RunwayVisualRange


class MetarFormatter:
    """Formatter for MetarReport objects."""

    @staticmethod
    def format(metar: MetarReport) -> str:
        formatter = MetarFormatter()
        return formatter._format_metar(metar)

    def _format_metar(self, metar: MetarReport) -> str:
        lines = [
            f"METAR for {metar.station_id} issued "
            f"{metar.observation_time.day:02d} "
            f"{metar.observation_time.hour:02d}:{metar.observation_time.minute:02d} UTC",
        ]

        if metar.is_nil:
            lines.append("Status: NIL (Missing report)")
            return "\n".join(lines)

        lines.extend(
            [
                f"Type: {'AUTO' if metar.is_automated else 'Manual'} {metar.report_type}",
                f"Wind: {format_wind(metar.wind)}",
                f"Visibility: {format_visibility(metar.visibility)}",
            ]
        )

        if metar.runway_visual_ranges:
            lines.extend(self._format_rvr(metar.runway_visual_ranges))

        if metar.runway_states:
            lines.extend(self._format_runway_states(metar.runway_states))

        if metar.weather:
            wx_lines = format_weather_groups_list(metar.weather)
            if wx_lines:
                lines.append("Weather Phenomena:")
                lines.extend([f"  {line}" for line in wx_lines])

        if metar.sky:
            sky_lines = format_sky_conditions_list(metar.sky)
            if sky_lines:
                lines.append("Sky Conditions:")
                lines.extend([f"  {line}" for line in sky_lines])

        if metar.windshear:
            descriptions = [ws.description for ws in metar.windshear]
            lines.append(f"Windshear: {', '.join(descriptions)}")

        lines.append(f"Temperature: {format_temperature(metar.temperature)}")
        lines.append(f"Dew Point: {format_temperature(metar.dewpoint)}")

        lines.append(f"Altimeter: {format_pressure(metar.altimeter)}")

        if metar.trends:
            for i, trend in enumerate(metar.trends):
                prefix = "Trend: " if i == 0 else "       "
                lines.append(f"{prefix}{trend.description}")

        if metar.military_color_codes:
            lines.append("Military Color Codes:")
            for code in metar.military_color_codes:
                lines.append(f"  {code.code}: {code.description}")

        if metar.remarks:
            lines.extend(self._format_remarks(metar.remarks, metar.remarks_decoded))

        return "\n".join(lines)

    def _format_rvr(self, rvr_list: List[RunwayVisualRange]) -> List[str]:
        lines = ["Runway Visual Range:"]

        for rvr in rvr_list:
            if rvr.variable_range is not None:
                min_prefix = "less than " if rvr.is_less_than else "more than " if rvr.is_more_than else ""
                max_prefix = (
                    "less than "
                    if rvr.variable_less_than
                    else "more than "
                    if rvr.variable_more_than
                    else ""
                )
                rvr_line = (
                    f"  Runway {rvr.runway}: "
                    f"{min_prefix}{rvr.visual_range} to {max_prefix}{rvr.variable_range} {rvr.unit}"
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

    def _format_runway_states(self, reports: List[RunwayState]) -> List[str]:
        lines = ["Runway State Reports:"]
        for report in reports:
            lines.append(
                f"  Runway {report.runway}: {report.deposit}, {report.contamination}, {report.depth}, {report.braking}"
            )
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
                lines.append(f"  {key}: {value}")
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
