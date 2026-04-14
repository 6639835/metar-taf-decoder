"""Formatting utilities for TAF reports."""

from __future__ import annotations

from typing import Dict, List

from .common import format_sky_conditions_list, format_visibility, format_weather_groups_list, format_wind
from ..models import IcingForecast, TafForecastPeriod, TafReport, TurbulenceForecast, WindShear


class TafFormatter:
    """Formatter for TafReport objects."""

    @staticmethod
    def format(taf: TafReport) -> str:
        formatter = TafFormatter()
        return formatter._format_taf(taf)

    def _format_taf(self, taf: TafReport) -> str:
        status_parts = []
        if taf.is_amended:
            status_parts.append("AMD")
        if taf.is_corrected:
            status_parts.append("COR")
        if taf.is_cancelled:
            status_parts.append("CNL")
        if taf.is_nil:
            status_parts.append("NIL")

        header_suffix = f" ({' '.join(status_parts)})" if status_parts else ""
        lines = [
            f"{taf.report_type} for {taf.station_id} issued "
            f"{taf.issue_time.day:02d} "
            f"{taf.issue_time.hour:02d}:{taf.issue_time.minute:02d} UTC{header_suffix}",
            f"Valid from {taf.valid_period.start.day:02d} "
            f"{taf.valid_period.start.hour:02d}:{taf.valid_period.start.minute:02d} UTC",
            f"Valid to {taf.valid_period.end.day:02d} "
            f"{taf.valid_period.end.hour:02d}:{taf.valid_period.end.minute:02d} UTC",
        ]

        if taf.is_cancelled:
            lines.append("Status: Forecast cancelled")
        elif taf.is_nil:
            lines.append("Status: NIL (Missing forecast)")

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

        temp_line = self._format_temperature(period)
        if temp_line:
            lines.append(temp_line)

        # Wind shear
        if getattr(period, "windshear", None):
            lines.append("  Wind Shear:")
            for ws in period.windshear:
                lines.append(f"    {self._format_windshear(ws)}")

        # Icing
        if getattr(period, "icing", None):
            lines.append("  Icing:")
            for ice in period.icing:
                lines.append(f"    {self._format_icing(ice)}")

        # Turbulence
        if getattr(period, "turbulence", None):
            lines.append("  Turbulence:")
            for turb in period.turbulence:
                lines.append(f"    {self._format_turbulence(turb)}")

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
            if period.qualifier == "TEMPO":
                return f"Probability {prob}% temporary conditions{time_desc}:"
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

    @staticmethod
    def _format_windshear(ws: WindShear) -> str:
        """Format a WindShear model into a human-readable string."""
        if ws.description:
            return ws.description
        if ws.runway:
            return f"Wind shear on runway {ws.runway}"
        return "Wind shear"

    @staticmethod
    def _format_icing(ice: IcingForecast) -> str:
        """Format an IcingForecast model into a human-readable string."""
        parts = [f"{ice.intensity.capitalize()} icing"]
        if ice.icing_type and ice.icing_type not in ("none", "not specified"):
            parts.append(f"({ice.icing_type})")
        parts.append(f"from {ice.base_ft:,} ft")
        if ice.top_ft is not None:
            parts.append(f"to {ice.top_ft:,} ft")
        return " ".join(parts)

    @staticmethod
    def _format_turbulence(turb: TurbulenceForecast) -> str:
        """Format a TurbulenceForecast model into a human-readable string."""
        cloud_tag = " in cloud" if turb.in_cloud else ""
        parts = [f"{turb.intensity.capitalize()}{cloud_tag} turbulence"]
        parts.append(f"from {turb.base_ft:,} ft")
        if turb.top_ft is not None:
            parts.append(f"to {turb.top_ft:,} ft")
        return " ".join(parts)

    def _format_remarks(self, remarks: str, decoded: Dict) -> List[str]:
        lines = [f"\nRemarks: {remarks}"]

        if decoded:
            for key, value in decoded.items():
                if key == "variable_ceiling":
                    lines.append(f"  Variable Ceiling: {value}")
                    continue
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
