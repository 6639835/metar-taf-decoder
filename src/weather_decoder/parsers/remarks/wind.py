"""Wind remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    List,
    re,
)


class WindRemarksMixin(RemarksCommon):
    def _parse_runway_winds(self, remarks: str, decoded: Dict) -> None:
        """Parse runway-specific wind information

        Handles both US format (WIND location dddssKT) and
        ICAO/European format (RWYxx dddssKT [dddVddd])
        """
        # US format: WIND location dddss(G)KT
        wind_patterns = re.findall(
            r"WIND\s+(\w+)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT", remarks
        )
        if wind_patterns:
            if "runway_winds" not in decoded:
                decoded["runway_winds"] = []
            for pattern in wind_patterns:
                location, direction, speed, gust = pattern
                wind_info = {
                    "runway": location,
                    "direction": int(direction),
                    "speed": int(speed),
                    "unit": "KT",
                }
                if gust:
                    wind_info["gust"] = int(gust)
                decoded["runway_winds"].append(wind_info)

        # ICAO/European format: RWYxx dddssKT [dddVddd]
        rwy_wind_patterns = re.findall(
            r"RWY(\d{2}[LCR]?)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT(?:\s+(\d{3})V(\d{3}))?",
            remarks,
        )
        if rwy_wind_patterns:
            if "runway_winds" not in decoded:
                decoded["runway_winds"] = []
            for pattern in rwy_wind_patterns:
                runway, direction, speed, gust, var_from, var_to = pattern
                wind_info = {
                    "runway": runway,
                    "direction": int(direction),
                    "speed": int(speed),
                    "unit": "KT",
                }
                if gust:
                    wind_info["gust"] = int(gust)
                if var_from and var_to:
                    wind_info["variable_direction"] = [int(var_from), int(var_to)]
                decoded["runway_winds"].append(wind_info)

    def _parse_location_winds(self, remarks: str, decoded: Dict) -> None:
        """Parse location-specific plain-language wind remarks.

        Examples:
          HARBOR WIND 10020G27KT
          ROOF WIND 13015G27KT
        """
        location_pattern = r"(?:HARBOR|ROOF|TOWER|TWR|SFC|RWY\d{2}[LCR]?)"
        matches = re.finditer(
            rf"\b({location_pattern})\s+WIND\s+"
            r"(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT\b",
            remarks,
        )
        winds: List[Dict[str, object]] = []
        for match in matches:
            location, direction, speed, gust = match.groups()
            if location in {"PK", "RWY"} or location.endswith("PK"):
                continue
            wind_info: Dict[str, object] = {
                "location": location.title(),
                "direction": int(direction),
                "speed": int(speed),
                "unit": "KT",
            }
            if gust:
                wind_info["gust"] = int(gust)
            winds.append(wind_info)

        if winds:
            decoded["location_winds"] = winds

    def _parse_peak_wind(self, remarks: str, decoded: Dict) -> None:
        """Parse peak wind information — FMH-1 §12.7.1.d.

        Format: PK WND dddff(f)/(hh)mm
        Time field may be 4 digits (HHMM) or 2 digits (MM of current hour).
        """
        pk_wnd_match = re.search(r"PK\s+WND\s+(\d{3})(\d{2,3})/(\d{2,4})", remarks)
        if pk_wnd_match:
            pk_direction = int(pk_wnd_match.group(1))
            pk_speed = int(pk_wnd_match.group(2))
            time_raw = pk_wnd_match.group(3)
            if len(time_raw) == 4:
                time_display = f"{time_raw[:2]}:{time_raw[2:]} UTC"
            else:
                time_display = f":{time_raw} UTC (current hour)"
            decoded["Peak Wind"] = f"{pk_direction}° at {pk_speed} KT at {time_display}"

    def _parse_wind_shift(self, remarks: str, decoded: Dict) -> None:
        """Parse wind shift information — FMH-1 §12.7.1.e.

        Format: WSHFT (hh)mm [FROPA]
        Time field may be 4 digits (HHMM) or 2 digits (MM of current hour).
        """
        wshft_match = re.search(r"WSHFT\s+(\d{2,4})(?:\s+(FROPA))?", remarks)
        if wshft_match:
            time_raw = wshft_match.group(1)
            fropa = wshft_match.group(2)
            if len(time_raw) == 4:
                time_display = f"{time_raw[:2]}:{time_raw[2:]} UTC"
            else:
                time_display = f":{time_raw} UTC (current hour)"
            value = f"at {time_display}"
            if fropa:
                value += " (frontal passage)"
            decoded["Wind Shift"] = value

    # =========================================================================
    # Pressure Information
    # =========================================================================
    def _parse_frontal_passage(self, remarks: str, decoded: Dict) -> None:
        """Parse frontal passage indicator (FROPA)"""
        if "FROPA" in remarks:
            decoded["Frontal Passage"] = "Frontal passage"
