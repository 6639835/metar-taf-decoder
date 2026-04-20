"""Temperature remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    re,
)


class TemperatureRemarksMixin(RemarksCommon):
    def _parse_temperature_tenths(self, remarks: str, decoded: Dict) -> None:
        """Parse temperature/dewpoint to tenths (TsnTTTsnTTT format)"""
        temp_match = re.search(r"(?<!\S)T([01])(\d{3})([01])(\d{3})(?!\S)", remarks)
        if temp_match:
            temp_sign = -1 if temp_match.group(1) == "1" else 1
            temp_tenths = int(temp_match.group(2))
            dew_sign = -1 if temp_match.group(3) == "1" else 1
            dew_tenths = int(temp_match.group(4))

            decoded["Temperature (tenths)"] = f"{temp_sign * temp_tenths / 10:.1f}°C"
            decoded["Dewpoint (tenths)"] = f"{dew_sign * dew_tenths / 10:.1f}°C"

    def _parse_24hr_temperature_extremes(self, remarks: str, decoded: Dict) -> None:
        """Parse 24-hour temperature extremes (4snTTTsnTTT format)"""
        temp_extremes_match = re.search(
            r"(?<!\S)4([01])(\d{3})([01])(\d{3})(?!\S)", remarks
        )
        if temp_extremes_match:
            max_sign = -1 if temp_extremes_match.group(1) == "1" else 1
            max_temp_tenths = int(temp_extremes_match.group(2))
            min_sign = -1 if temp_extremes_match.group(3) == "1" else 1
            min_temp_tenths = int(temp_extremes_match.group(4))

            max_temp = max_sign * max_temp_tenths / 10
            min_temp = min_sign * min_temp_tenths / 10

            decoded["24-Hour Maximum Temperature"] = f"{max_temp:.1f}°C"
            decoded["24-Hour Minimum Temperature"] = f"{min_temp:.1f}°C"
            if max_temp < min_temp:
                self._add_warning(
                    decoded,
                    "24-hour maximum temperature is lower than 24-hour minimum temperature; source group may be malformed",
                )

    def _parse_6hr_temperatures(self, remarks: str, decoded: Dict) -> None:
        """Parse 6-hour max/min temperatures (1snTTT and 2snTTT formats)"""
        # 6-hour maximum temperature
        max_temp_6hr_match = re.search(r"(?<!\S)1([01])(\d{3})(?!\S)", remarks)
        if max_temp_6hr_match:
            sign = -1 if max_temp_6hr_match.group(1) == "1" else 1
            temp_tenths = int(max_temp_6hr_match.group(2))
            temp_value = sign * temp_tenths / 10
            decoded["6-Hour Maximum Temperature"] = f"{temp_value:.1f}°C"
            current_temp = self._decoded_celsius(decoded.get("Temperature (tenths)"))
            if current_temp is not None and temp_value < current_temp:
                self._add_warning(
                    decoded,
                    "6-hour maximum temperature is lower than current precise temperature; source group may be malformed",
                )

        # 6-hour minimum temperature
        min_temp_6hr_match = re.search(r"(?<!\S)2([01])(\d{3})(?!\S)", remarks)
        if min_temp_6hr_match:
            sign = -1 if min_temp_6hr_match.group(1) == "1" else 1
            temp_tenths = int(min_temp_6hr_match.group(2))
            temp_value = sign * temp_tenths / 10
            decoded["6-Hour Minimum Temperature"] = f"{temp_value:.1f}°C"
            current_temp = self._decoded_celsius(decoded.get("Temperature (tenths)"))
            if current_temp is not None and temp_value > current_temp:
                self._add_warning(
                    decoded,
                    "6-hour minimum temperature is higher than current precise temperature; source group may be malformed",
                )

    # =========================================================================
    # Precipitation Information
    # =========================================================================
