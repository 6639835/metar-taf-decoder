"""TAF-specific formatting utilities

This module provides formatting functions for TAF data output.
"""

from typing import TYPE_CHECKING, Dict, List

from .common import (
    format_sky_conditions_list,
    format_visibility,
    format_weather_groups_list,
    format_wind,
)

if TYPE_CHECKING:
    from ..data.taf_data import TafData


class TafFormatter:
    """Formatter for TAF data output

    This class handles the conversion of TafData objects into
    human-readable string representations.
    """

    @staticmethod
    def format(taf: "TafData") -> str:
        """Format a TafData object into a human-readable string

        Args:
            taf: The TafData object to format

        Returns:
            Human-readable TAF string
        """
        formatter = TafFormatter()
        return formatter._format_taf(taf)

    def _format_taf(self, taf: "TafData") -> str:
        """Internal formatting method"""
        lines = [
            f"TAF for {taf.station_id} issued "
            f"{taf.issue_time.day:02d} "
            f"{taf.issue_time.hour:02d}:{taf.issue_time.minute:02d} UTC",
            f"Valid from {taf.valid_period['from'].day:02d} "
            f"{taf.valid_period['from'].hour:02d}:{taf.valid_period['from'].minute:02d} UTC",
            f"Valid to {taf.valid_period['to'].day:02d} "
            f"{taf.valid_period['to'].hour:02d}:{taf.valid_period['to'].minute:02d} UTC",
        ]

        # Add each forecast period
        for i, period in enumerate(taf.forecast_periods):
            lines.extend(self._format_forecast_period(period, i))

        # Add remarks
        if taf.remarks:
            lines.extend(self._format_remarks(taf))

        return "\n".join(lines)

    def _format_forecast_period(self, period: Dict, index: int) -> List[str]:
        """Format a single forecast period"""
        lines: List[str] = []

        # Period header
        if index == 0:
            lines.append("\nInitial Forecast:")
        else:
            header = self._format_period_header(period)
            lines.append(f"\n{header}")

        # Wind
        if period.get("wind"):
            lines.append(f"  Wind: {format_wind(period['wind'])}")

        # Visibility
        if period.get("visibility"):
            lines.append(f"  Visibility: {format_visibility(period['visibility'])}")

        # Weather phenomena
        if period.get("weather_groups"):
            wx_lines = format_weather_groups_list(period["weather_groups"])
            if wx_lines:
                lines.append("  Weather Phenomena:")
                lines.extend([f"    {line}" for line in wx_lines])

        # Sky conditions
        if period.get("sky_conditions"):
            sky_lines = format_sky_conditions_list(period["sky_conditions"])
            if sky_lines:
                lines.append("  Sky Conditions:")
                lines.extend([f"    {line}" for line in sky_lines])

        # QNH
        if period.get("qnh"):
            qnh = period["qnh"]
            lines.append(f"  Pressure: {qnh['value']} {qnh['unit']}")

        # Temperature
        temp_line = self._format_temperature(period)
        if temp_line:
            lines.append(temp_line)

        # Turbulence
        if period.get("turbulence"):
            lines.append(f"  Turbulence: {period['turbulence']}")

        # Icing
        if period.get("icing"):
            lines.append(f"  Icing: {period['icing']}")

        return lines

    def _format_period_header(self, period: Dict) -> str:
        """Format the header for a forecast period"""
        change_type = period.get("change_type", "")
        time_desc = self._format_time_description(period)
        prob_text = self._format_probability(period)

        if change_type == "TEMPO":
            return f"Temporary conditions{time_desc}{prob_text}:"
        elif change_type == "BECMG":
            return f"Conditions becoming{time_desc}{prob_text}:"
        elif change_type == "FM":
            from_time = period.get("from_time")
            if from_time:
                return f"From {from_time.day:02d} " f"{from_time.hour:02d}:{from_time.minute:02d} UTC{prob_text}:"
            return f"From (unknown time){prob_text}:"
        elif change_type == "PROB":
            prob = period.get("probability", 0)
            return f"Probability {prob}%{time_desc}:"
        else:
            return f"Change group ({change_type}){time_desc}{prob_text}:"

    def _format_time_description(self, period: Dict) -> str:
        """Format time description for a period"""
        if period.get("from_time") and period.get("to_time"):
            from_time = period["from_time"]
            to_time = period["to_time"]
            return (
                f" from {from_time.day:02d} "
                f"{from_time.hour:02d}:{from_time.minute:02d} to "
                f"{to_time.day:02d} {to_time.hour:02d}:{to_time.minute:02d} UTC"
            )
        elif period.get("from_time"):
            from_time = period["from_time"]
            return f" {from_time.day:02d} " f"{from_time.hour:02d}:{from_time.minute:02d} UTC"
        return ""

    def _format_probability(self, period: Dict) -> str:
        """Format probability text"""
        prob = period.get("probability", 0)
        return f" (Probability {prob}%)" if prob > 0 else ""

    def _format_temperature(self, period: Dict) -> str:
        """Format temperature information for a period"""
        parts: List[str] = []

        # Handle new list-based format
        if period.get("temperature_max_list") or period.get("temperature_min_list"):
            if period.get("temperature_max_list"):
                for i, temp in enumerate(period["temperature_max_list"]):
                    prefix = "," if i > 0 else ""
                    parts.append(f"{prefix} max {temp['value']}°C at " f"{temp['time'].strftime('%d/%H:%M')} UTC")

            if period.get("temperature_min_list"):
                for i, temp in enumerate(period["temperature_min_list"]):
                    prefix = "," if parts or i > 0 else ""
                    parts.append(f"{prefix} min {temp['value']}°C at " f"{temp['time'].strftime('%d/%H:%M')} UTC")

        # Fallback for backward compatibility
        elif period.get("temperature_min") is not None or period.get("temperature_max") is not None:
            if period.get("temperature_max") is not None:
                max_time = period.get("temperature_max_time", "")
                time_str = max_time.strftime("%d/%H:%M") if max_time else "unknown"
                parts.append(f" max {period['temperature_max']}°C at {time_str} UTC")
            if period.get("temperature_min") is not None:
                prefix = "," if parts else ""
                min_time = period.get("temperature_min_time", "")
                time_str = min_time.strftime("%d/%H:%M") if min_time else "unknown"
                parts.append(f"{prefix} min {period['temperature_min']}°C at {time_str} UTC")

        if parts:
            return f"  Temperature:{''.join(parts)}"
        return ""

    def _format_remarks(self, taf: "TafData") -> List[str]:
        """Format remarks section"""
        lines = [f"\nRemarks: {taf.remarks}"]

        if taf.remarks_decoded:
            for key, value in taf.remarks_decoded.items():
                if isinstance(value, dict):
                    lines.append(f"  {key}: {', '.join([f'{k}: {v}' for k, v in value.items()])}")
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        lines.append(f"  {key}:")
                        for item in value:
                            lines.append(f"    {', '.join([f'{k}: {v}' for k, v in item.items()])}")
                    else:
                        lines.append(f"  {key}: {', '.join(value)}")
                else:
                    lines.append(f"  {key}: {value}")

        return lines
