"""Formatting utilities for TAF reports."""

from __future__ import annotations

from typing import Dict, List

from .common import format_pressure, format_sky_conditions_list, format_visibility, format_weather_groups_list, format_wind
from ..models import TafForecastPeriod, TafReport


class TafFormatter:
    """Formatter for TafReport objects."""

    @staticmethod
    def format(taf: TafReport) -> str:
        formatter = TafFormatter()
        return formatter._format_taf(taf)

    def _format_taf(self, taf: TafReport) -> str:
        lines = [
            f"TAF for {taf.station_id} issued "
            f"{taf.issue_time.day:02d} "
            f"{taf.issue_time.hour:02d}:{taf.issue_time.minute:02d} UTC",
            f"Valid from {taf.valid_period.start.day:02d} "
            f"{taf.valid_period.start.hour:02d}:{taf.valid_period.start.minute:02d} UTC",
            f"Valid to {taf.valid_period.end.day:02d} "
            f"{taf.valid_period.end.hour:02d}:{taf.valid_period.end.minute:02d} UTC",
        ]

        for i, period in enumerate(taf.forecast_periods):
            lines.extend(self._format_forecast_period(period, i))

        if taf.remarks:
            lines.extend(self._format_remarks(taf.remarks, taf.remarks_decoded))

        return "\n".join(lines)

    def _format_forecast_period(self, period: TafForecastPeriod, index: int) -> List[str]:
        lines: List[str] = []

        if index == 0:
            lines.append("\nInitial Forecast:")
        else:
            lines.append(f"\n{self._format_period_header(period)}")

        if period.wind:
            lines.append(f"  Wind: {format_wind(period.wind)}")

        if period.visibility:
            lines.append(f"  Visibility: {format_visibility(period.visibility)}")

        if period.weather:
            wx_lines = format_weather_groups_list(period.weather)
            if wx_lines:
                lines.append("  Weather Phenomena:")
                lines.extend([f"    {line}" for line in wx_lines])

        if period.sky:
            sky_lines = format_sky_conditions_list(period.sky)
            if sky_lines:
                lines.append("  Sky Conditions:")
                lines.extend([f"    {line}" for line in sky_lines])

        if period.qnh:
            lines.append(f"  Pressure: {format_pressure(period.qnh)}")

        temp_line = self._format_temperature(period)
        if temp_line:
            lines.append(temp_line)

        if period.unparsed_tokens:
            lines.append(f"  Unparsed tokens: {' '.join(period.unparsed_tokens)}")

        return lines

    def _format_period_header(self, period: TafForecastPeriod) -> str:
        change_type = period.change_type
        time_desc = self._format_time_description(period)
        prob_text = f" (Probability {period.probability}%)" if period.probability else ""

        if change_type == "TEMPO":
            return f"Temporary conditions{time_desc}{prob_text}:"
        if change_type == "BECMG":
            return f"Conditions becoming{time_desc}{prob_text}:"
        if change_type == "FM":
            if period.from_time:
                return (
                    f"From {period.from_time.day:02d} "
                    f"{period.from_time.hour:02d}:{period.from_time.minute:02d} UTC{prob_text}:"
                )
            return f"From (unknown time){prob_text}:"
        if change_type == "PROB":
            prob = period.probability or 0
            return f"Probability {prob}%{time_desc}:"

        return f"Change group ({change_type}){time_desc}{prob_text}:"

    def _format_time_description(self, period: TafForecastPeriod) -> str:
        if period.from_time and period.to_time:
            return (
                f" from {period.from_time.day:02d} "
                f"{period.from_time.hour:02d}:{period.from_time.minute:02d} to "
                f"{period.to_time.day:02d} {period.to_time.hour:02d}:{period.to_time.minute:02d} UTC"
            )
        if period.from_time:
            return f" {period.from_time.day:02d} {period.from_time.hour:02d}:{period.from_time.minute:02d} UTC"
        return ""

    def _format_temperature(self, period: TafForecastPeriod) -> str:
        if not period.temperatures:
            return ""

        parts: List[str] = []
        for temp in period.temperatures:
            parts.append(f" {temp.kind} {temp.value}°C at {temp.time.strftime('%d/%H:%M')} UTC")

        return f"  Temperature:{','.join(parts)}"

    def _format_remarks(self, remarks: str, decoded: Dict) -> List[str]:
        lines = [f"\nRemarks: {remarks}"]

        if decoded:
            for key, value in decoded.items():
                if isinstance(value, dict):
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
