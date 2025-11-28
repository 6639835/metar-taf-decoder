"""METAR Data class for holding decoded METAR information"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from ..utils.formatters import format_visibility, format_wind


@dataclass
class MetarData:
    """Class to hold decoded METAR data"""

    raw_metar: str
    metar_type: str
    station_id: str
    observation_time: datetime
    auto: bool
    is_nil: bool  # NIL indicates a missing report
    maintenance_needed: bool  # $ indicator - station needs maintenance
    wind: Dict
    visibility: Dict
    runway_visual_range: List[Dict]
    runway_conditions: List[Dict]
    runway_state_reports: List[Dict]  # MOTNE format runway reports from main body
    weather_groups: List[Dict]
    sky_conditions: List[Dict]
    temperature: float
    dewpoint: float  # Can be None if not available
    altimeter: Dict
    windshear: List[Dict]  # Changed from List[str] to List[Dict] for structured data
    trends: List[Dict]
    remarks: str
    remarks_decoded: Dict
    military_color_codes: List[Dict]

    def __str__(self) -> str:
        """Return a human-readable string of the decoded METAR"""
        lines = [
            f"METAR for {self.station_id} issued {self.observation_time.day:02d} {self.observation_time.hour:02d}:{self.observation_time.minute:02d} UTC",
        ]

        # Handle NIL (missing) report
        if self.is_nil:
            lines.append("Status: NIL (Missing report)")
            return "\n".join(lines)

        lines.extend(
            [
                f"Type: {'AUTO' if self.auto else 'Manual'} {self.metar_type}",
                f"Wind: {self.wind_text()}",
                f"Visibility: {self.visibility_text()}",
            ]
        )

        if self.runway_visual_range:
            rvr_lines = [f"Runway Visual Range:"]
            for rvr in self.runway_visual_range:
                if rvr.get("variable_range"):
                    # Variable RVR format
                    min_range_prefix = ""
                    max_range_prefix = ""

                    if rvr.get("is_less_than"):
                        min_range_prefix = "less than "
                    elif rvr.get("is_more_than"):
                        min_range_prefix = "more than "

                    if rvr.get("variable_less_than"):
                        max_range_prefix = "less than "
                    elif rvr.get("variable_more_than"):
                        max_range_prefix = "more than "

                    rvr_line = f"  Runway {rvr['runway']}: {min_range_prefix}{rvr['visual_range']} to {max_range_prefix}{rvr['variable_range']} {rvr['unit']}"
                else:
                    # Regular RVR format
                    rvr_line = f"  Runway {rvr['runway']}: {rvr['visual_range']} {rvr['unit']}"
                    if rvr.get("is_more_than"):
                        rvr_line = f"  Runway {rvr['runway']}: More than {rvr['visual_range']} {rvr['unit']}"
                    if rvr.get("is_less_than"):
                        rvr_line = f"  Runway {rvr['runway']}: Less than {rvr['visual_range']} {rvr['unit']}"

                if rvr.get("trend"):
                    rvr_line += f" ({rvr['trend']})"
                rvr_lines.append(rvr_line)
            lines.extend(rvr_lines)

        if self.runway_conditions:
            rwy_cond_lines = [f"Runway Conditions:"]
            for rwy_cond in self.runway_conditions:
                rwy_line = f"  Runway {rwy_cond['runway']}: {rwy_cond['description']}"
                rwy_cond_lines.append(rwy_line)
            lines.extend(rwy_cond_lines)

        if self.runway_state_reports:
            state_lines = [f"Runway State Reports:"]
            for report in self.runway_state_reports:
                state_line = f"  Runway {report['runway']}: {report['deposit']}, {report['contamination']}, {report['depth']}, {report['braking']}"
                state_lines.append(state_line)
            lines.extend(state_lines)

        if self.weather_groups:
            wx_lines = [f"Weather Phenomena:"]
            for wx in self.weather_groups:
                intensity = wx.get("intensity", "")
                descriptor = wx.get("descriptor", "")
                phenomena = wx.get("phenomena", [])

                if intensity or descriptor or phenomena:
                    wx_text = []
                    if intensity:
                        wx_text.append(intensity)
                    if descriptor:
                        wx_text.append(descriptor)
                    if phenomena:
                        wx_text.append(", ".join(phenomena))

                    wx_lines.append(f"  {' '.join(wx_text)}")
            lines.extend(wx_lines)

        if self.sky_conditions:
            sky_lines = [f"Sky Conditions:"]
            for sky in self.sky_conditions:
                if sky["type"] == "CLR" or sky["type"] == "SKC":
                    sky_lines.append(f"  Clear skies")
                elif sky["type"] == "NSC":
                    sky_lines.append(f"  No significant cloud")
                elif sky["type"] == "NCD":
                    sky_lines.append(f"  No cloud detected")
                elif sky["type"] == "VV":
                    if sky.get("unknown_height"):
                        sky_lines.append(f"  Vertical visibility (unknown height)")
                    else:
                        sky_lines.append(f"  Vertical visibility {sky['height']} feet")
                elif sky["type"] == "///":
                    if sky.get("unknown_height"):
                        sky_lines.append(f"  Unknown cloud amount at unknown height (AUTO station)")
                    else:
                        sky_lines.append(f"  Unknown cloud amount at {sky['height']} feet (AUTO station)")
                elif sky["type"] == "AUTO" and sky.get("missing_data"):
                    sky_lines.append(f"  Cloud data missing (AUTO station)")
                elif sky["type"] == "unknown" and sky.get("missing_data"):
                    cloud_type_text = ""
                    if sky.get("cloud_type"):
                        cloud_type_text = f" ({sky['cloud_type']})"
                    elif sky.get("cb"):
                        cloud_type_text = " (CB)"
                    elif sky.get("tcu"):
                        cloud_type_text = " (TCU)"
                    sky_lines.append(f"  Unknown cloud height{cloud_type_text} (AUTO station)")
                else:
                    # Handle unknown height
                    if sky.get("unknown_height"):
                        height_str = "unknown height"
                    else:
                        height_str = f"{sky['height']} feet"
                    sky_lines.append(f"  {sky['type']} clouds at {height_str}")
                    if sky.get("cb") or sky.get("tcu"):
                        cb_tcu = "CB" if sky.get("cb") else "TCU"
                        sky_lines[-1] += f" ({cb_tcu})"
                    elif sky.get("unknown_type"):
                        sky_lines[-1] += f" (unknown type)"
            lines.extend(sky_lines)

        if self.windshear:
            ws_descriptions = [ws.get("description", ws.get("raw", "Wind shear reported")) for ws in self.windshear]
            lines.append(f"Windshear: {', '.join(ws_descriptions)}")

        lines.append(f"Temperature: {self.temperature}°C")
        if self.dewpoint is not None:
            lines.append(f"Dew Point: {self.dewpoint}°C")
        else:
            lines.append("Dew Point: Not available")
        lines.append(f"Altimeter: {self.altimeter['value']} {self.altimeter['unit']}")

        if self.trends:
            for i, trend in enumerate(self.trends):
                if i == 0:
                    trend_line = f"Trend: {trend['description']}"
                else:
                    trend_line = f"       {trend['description']}"
                lines.append(trend_line)

        if self.military_color_codes:
            mil_code_lines = [f"Military Color Codes:"]
            for code in self.military_color_codes:
                mil_code_lines.append(f"  {code['code']}: {code['description']}")
            lines.extend(mil_code_lines)

        if self.remarks:
            # Create a filtered version of the remarks text that removes information
            # which will be shown in structured format below
            filtered_remarks = self.remarks

            # Remove location-specific wind information if it's in the structured format
            if self.remarks_decoded and "location_winds" in self.remarks_decoded:
                for wind_info in self.remarks_decoded["location_winds"]:
                    location = wind_info.get("location", "")
                    direction = wind_info.get("direction", "")
                    speed = wind_info.get("speed", "")
                    unit = wind_info.get("unit", "KT")
                    gust = wind_info.get("gust", "")

                    # Create pattern to remove from remarks
                    pattern = f"WIND {location} {direction}{speed}"
                    if gust:
                        pattern += f"G{gust}"
                    pattern += f"{unit}"

                    # Remove this pattern from the remarks
                    filtered_remarks = filtered_remarks.replace(pattern, "").strip()

            # Process the remarks to convert cloud layer codes to readable format
            readable_remarks = filtered_remarks

            # Find and replace cloud layer patterns
            for match in re.finditer(r"(OVC|BKN|SCT|FEW)(\d{3})(?:///)?", filtered_remarks):
                cloud_type = match.group(1)
                height = int(match.group(2)) * 100

                # Get the full pattern that was matched
                original_pattern = match.group(0)

                # Determine if it has unknown type
                has_unknown_type = "///" in original_pattern

                # Create readable replacement
                if cloud_type == "OVC":
                    replacement = f"OVC clouds at {height} feet"
                elif cloud_type == "BKN":
                    replacement = f"BKN clouds at {height} feet"
                elif cloud_type == "SCT":
                    replacement = f"SCT clouds at {height} feet"
                else:  # FEW
                    replacement = f"FEW clouds at {height} feet"

                if has_unknown_type:
                    replacement += " (unknown type)"

                # Replace in the original remarks
                readable_remarks = readable_remarks.replace(original_pattern, replacement)

            # First add the raw remarks
            if self.remarks.strip():
                lines.append(f"Remarks: {self.remarks}")

            # Now build the decoded remarks
            decoded_remarks = []

            if self.remarks_decoded:
                for key, value in self.remarks_decoded.items():
                    if key == "directional_info":
                        decoded_remarks.append("  Directional information:")
                        for info in value:
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
                                    # Check if this is a range format (contains "from X to Y")
                                    if "from " in directions[0]:
                                        direction_text = directions[0]
                                    elif "kilometers" in directions[0] or "overhead" in directions[0]:
                                        # For distance patterns or overhead
                                        direction_text = directions[0]
                                    else:
                                        direction_text = f"in the {directions[0]}"
                                else:
                                    direction_text = f"in the {', '.join(directions[:-1])} and {directions[-1]}"
                                description.append(direction_text)

                            decoded_remarks.append(f"    {' '.join(description)}")
                    elif key == "variable_ceiling":
                        decoded_remarks.append(f"  {key}: {value}")
                    elif key == "runway_winds":
                        decoded_remarks.append("  Runway-specific winds:")
                        for wind in value:
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

                            decoded_remarks.append(wind_text)
                    elif key == "cloud_layers":
                        decoded_remarks.append("  Cloud layers:")
                        for layer in value:
                            decoded_remarks.append(f"    {layer}")
                    elif key == "altitude_winds":
                        decoded_remarks.append("  Altitude-specific winds:")
                        for wind in value:
                            altitude = wind.get("altitude", "")
                            altitude_unit = wind.get("altitude_unit", "feet")
                            direction = wind.get("direction", "")
                            speed = wind.get("speed", "")
                            unit = wind.get("unit", "KT")
                            gust = wind.get("gust", "")

                            wind_text = f"    At {altitude} {altitude_unit}: {direction}° at {speed} {unit}"

                            if gust:
                                wind_text += f", gusting to {gust} {unit}"

                            decoded_remarks.append(wind_text)
                    elif key == "location_winds":
                        decoded_remarks.append("  Location-specific winds:")
                        for wind in value:
                            location = wind.get("location", "")
                            direction = wind.get("direction", "")
                            speed = wind.get("speed", "")
                            unit = wind.get("unit", "KT")
                            gust = wind.get("gust", "")

                            wind_text = f"    At {location}: {direction}° at {speed} {unit}"

                            if gust:
                                wind_text += f", gusting to {gust} {unit}"

                            decoded_remarks.append(wind_text)
                    elif key == "wind_shift":
                        decoded_remarks.append(f"  wind_shift: at {value['time']}")
                    elif key == "runway_state_reports_remarks":
                        decoded_remarks.append("  Runway State Reports in Remarks:")
                        for report in value:
                            decoded_remarks.append(
                                f"    Runway {report['runway']}: {report['deposit']}, {report['contamination']}, {report['depth']}, {report['braking']}"
                            )
                    elif isinstance(value, dict):
                        decoded_remarks.append(f"  {key}: {', '.join([f'{k}: {v}' for k, v in value.items()])}")
                    elif isinstance(value, list):
                        # Check if the list contains dictionaries
                        if value and isinstance(value[0], dict):
                            # Handle lists of dictionaries in a generic way, other than the special cases above
                            decoded_remarks.append(f"  {key}:")
                            for item in value:
                                decoded_remarks.append(f"    {', '.join([f'{k}: {v}' for k, v in item.items()])}")
                        else:
                            # Regular list of strings
                            decoded_remarks.append(f"  {key}: {', '.join(value)}")
                    else:
                        decoded_remarks.append(f"  {key}: {value}")

            # Add the decoded remarks (without "Remarks:" prefix) to the output
            if decoded_remarks:
                lines.extend(decoded_remarks)

        return "\n".join(lines)

    def wind_text(self) -> str:
        """Format wind information into a readable string"""
        return format_wind(self.wind)

    def visibility_text(self) -> str:
        """Format visibility information into a readable string"""
        return format_visibility(self.visibility)
