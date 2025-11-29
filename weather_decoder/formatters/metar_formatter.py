"""METAR-specific formatting utilities

This module provides formatting functions for METAR data output.
"""

from typing import TYPE_CHECKING, Dict, List

from .common import (
    format_sky_conditions_list,
    format_visibility,
    format_weather_groups_list,
    format_wind,
)

if TYPE_CHECKING:
    from ..data.metar_data import MetarData


class MetarFormatter:
    """Formatter for METAR data output

    This class handles the conversion of MetarData objects into
    human-readable string representations.
    """

    @staticmethod
    def format(metar: "MetarData") -> str:
        """Format a MetarData object into a human-readable string

        Args:
            metar: The MetarData object to format

        Returns:
            Human-readable METAR string
        """
        formatter = MetarFormatter()
        return formatter._format_metar(metar)

    def _format_metar(self, metar: "MetarData") -> str:
        """Internal formatting method"""
        lines = [
            f"METAR for {metar.station_id} issued "
            f"{metar.observation_time.day:02d} "
            f"{metar.observation_time.hour:02d}:{metar.observation_time.minute:02d} UTC",
        ]

        # Handle NIL (missing) report
        if metar.is_nil:
            lines.append("Status: NIL (Missing report)")
            return "\n".join(lines)

        # Basic info
        lines.extend(
            [
                f"Type: {'AUTO' if metar.auto else 'Manual'} {metar.metar_type}",
                f"Wind: {format_wind(metar.wind)}",
                f"Visibility: {format_visibility(metar.visibility)}",
            ]
        )

        # RVR
        if metar.runway_visual_range:
            lines.extend(self._format_rvr(metar.runway_visual_range))

        # Runway conditions
        if metar.runway_conditions:
            lines.extend(self._format_runway_conditions(metar.runway_conditions))

        # Runway state reports
        if metar.runway_state_reports:
            lines.extend(self._format_runway_state_reports(metar.runway_state_reports))

        # Weather phenomena
        if metar.weather_groups:
            wx_lines = format_weather_groups_list(metar.weather_groups)
            if wx_lines:
                lines.append("Weather Phenomena:")
                lines.extend([f"  {line}" for line in wx_lines])

        # Sky conditions
        if metar.sky_conditions:
            sky_lines = format_sky_conditions_list(metar.sky_conditions)
            if sky_lines:
                lines.append("Sky Conditions:")
                lines.extend([f"  {line}" for line in sky_lines])

        # Windshear
        if metar.windshear:
            ws_descriptions = [ws.get("description", ws.get("raw", "Wind shear reported")) for ws in metar.windshear]
            lines.append(f"Windshear: {', '.join(ws_descriptions)}")

        # Temperature and dewpoint
        lines.append(f"Temperature: {metar.temperature}°C")
        if metar.dewpoint is not None:
            lines.append(f"Dew Point: {metar.dewpoint}°C")
        else:
            lines.append("Dew Point: Not available")

        # Altimeter
        lines.append(f"Altimeter: {metar.altimeter['value']} {metar.altimeter['unit']}")

        # Trends
        if metar.trends:
            for i, trend in enumerate(metar.trends):
                prefix = "Trend: " if i == 0 else "       "
                lines.append(f"{prefix}{trend['description']}")

        # Military color codes
        if metar.military_color_codes:
            lines.append("Military Color Codes:")
            for code in metar.military_color_codes:
                lines.append(f"  {code['code']}: {code['description']}")

        # Remarks
        if metar.remarks:
            lines.extend(self._format_remarks(metar))

        return "\n".join(lines)

    def _format_rvr(self, rvr_list: List[Dict]) -> List[str]:
        """Format runway visual range information"""
        lines = ["Runway Visual Range:"]

        for rvr in rvr_list:
            if rvr.get("variable_range"):
                # Variable RVR format
                min_prefix = ""
                max_prefix = ""

                if rvr.get("is_less_than"):
                    min_prefix = "less than "
                elif rvr.get("is_more_than"):
                    min_prefix = "more than "

                if rvr.get("variable_less_than"):
                    max_prefix = "less than "
                elif rvr.get("variable_more_than"):
                    max_prefix = "more than "

                rvr_line = (
                    f"  Runway {rvr['runway']}: "
                    f"{min_prefix}{rvr['visual_range']} to "
                    f"{max_prefix}{rvr['variable_range']} {rvr['unit']}"
                )
            else:
                # Regular RVR format
                if rvr.get("is_more_than"):
                    rvr_line = f"  Runway {rvr['runway']}: More than {rvr['visual_range']} {rvr['unit']}"
                elif rvr.get("is_less_than"):
                    rvr_line = f"  Runway {rvr['runway']}: Less than {rvr['visual_range']} {rvr['unit']}"
                else:
                    rvr_line = f"  Runway {rvr['runway']}: {rvr['visual_range']} {rvr['unit']}"

            if rvr.get("trend"):
                rvr_line += f" ({rvr['trend']})"

            lines.append(rvr_line)

        return lines

    def _format_runway_conditions(self, conditions: List[Dict]) -> List[str]:
        """Format runway conditions"""
        lines = ["Runway Conditions:"]
        for cond in conditions:
            lines.append(f"  Runway {cond['runway']}: {cond['description']}")
        return lines

    def _format_runway_state_reports(self, reports: List[Dict]) -> List[str]:
        """Format runway state reports"""
        lines = ["Runway State Reports:"]
        for report in reports:
            lines.append(
                f"  Runway {report['runway']}: {report['deposit']}, "
                f"{report['contamination']}, {report['depth']}, {report['braking']}"
            )
        return lines

    def _format_remarks(self, metar: "MetarData") -> List[str]:
        """Format remarks section"""
        lines = []

        # Add raw remarks
        if metar.remarks.strip():
            lines.append(f"Remarks: {metar.remarks}")

        # Add decoded remarks
        if metar.remarks_decoded:
            decoded_lines = self._format_decoded_remarks(metar.remarks_decoded)
            lines.extend(decoded_lines)

        return lines

    def _format_decoded_remarks(self, decoded: Dict) -> List[str]:
        """Format decoded remarks"""
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
                    lines.append(f"  {key}: {', '.join(value)}")
            else:
                lines.append(f"  {key}: {value}")

        return lines

    def _format_directional_info(self, info_list: List[Dict]) -> List[str]:
        """Format directional information"""
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
        """Format runway-specific winds"""
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
        """Format altitude-specific winds"""
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
        """Format location-specific winds"""
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
        """Format runway state reports in remarks"""
        lines = ["  Runway State Reports in Remarks:"]

        for report in reports:
            lines.append(
                f"    Runway {report['runway']}: {report['deposit']}, "
                f"{report['contamination']}, {report['depth']}, {report['braking']}"
            )

        return lines
