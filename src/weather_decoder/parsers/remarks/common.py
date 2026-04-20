"""Shared helpers for remarks parsing."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ...constants import (
    CLOUD_TYPE_CODES,
    DIRECTION_ABBREV,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    LOCATION_INDICATORS,
    MAINTENANCE_INDICATOR,
    PRESSURE_TENDENCY_CHARACTERISTICS,
    RUNWAY_BRAKING_REMARKS,
    RUNWAY_DEPTH_SPECIAL,
    SENSOR_STATUS,
    STATION_TYPES,
    WEATHER_DESCRIPTORS,
    WEATHER_PHENOMENA,
)

__all__ = [
    "CLOUD_TYPE_CODES",
    "DIRECTION_ABBREV",
    "Dict",
    "LIGHTNING_FREQUENCY",
    "LIGHTNING_TYPES",
    "List",
    "LOCATION_INDICATORS",
    "MAINTENANCE_INDICATOR",
    "Optional",
    "PRESSURE_TENDENCY_CHARACTERISTICS",
    "RUNWAY_BRAKING_REMARKS",
    "RUNWAY_DEPTH_SPECIAL",
    "RemarksCommon",
    "SENSOR_STATUS",
    "STATION_TYPES",
    "Tuple",
    "WEATHER_DESCRIPTORS",
    "WEATHER_PHENOMENA",
    "re",
]


class RemarksCommon:
    _key_patterns: Dict[str, List[str]] = {}
    _VIS_VALUE_PATTERN = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+)"
    _DIRECTION_PATTERN = r"(?:NE|NW|SE|SW|N|E|S|W)"

    @staticmethod
    def _parse_visibility_fraction(vis_str: str) -> float:
        """Parse a visibility string that may contain a fraction"""
        vis_str = vis_str.strip()
        if " " in vis_str:
            whole, fraction = vis_str.split()
            num, den = fraction.split("/")
            return float(whole) + (float(num) / float(den))
        if "/" in vis_str:
            num, den = vis_str.split("/")
            return float(num) / float(den)
        return float(vis_str)

    # =========================================================================
    # Weather Phenomena
    # =========================================================================
    @staticmethod
    def _extract_report_time(metar: str) -> Optional[Tuple[int, int, int]]:
        """Extract the observation day/hour/minute from the METAR header."""
        match = re.search(r"\b(\d{2})(\d{2})(\d{2})Z\b", metar)
        if not match:
            return None

        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    @staticmethod
    def _build_weather_type(descriptor: str, phenomenon: str) -> str:
        """Build a human-readable precipitation type for precipitation timing remarks."""
        weather_parts = []
        if descriptor:
            weather_parts.append(
                WEATHER_DESCRIPTORS.get(descriptor, descriptor.lower())
            )

        if phenomenon == "UP":
            weather_parts.append("unknown precipitation")
        else:
            weather_parts.append(WEATHER_PHENOMENA.get(phenomenon, phenomenon.lower()))

        return " ".join(weather_parts)

    @staticmethod
    def _resolve_event_time(
        time_token: str, report_time: Optional[Tuple[int, int, int]]
    ) -> Tuple[Tuple[int, int, int], str]:
        """Resolve a precipitation timing token to sortable UTC clock time."""
        if len(time_token) == 4:
            event_hour = int(time_token[:2])
            event_minute = int(time_token[2:])

            if report_time is None:
                return (
                    0,
                    event_hour,
                    event_minute,
                ), f"{event_hour:02d}:{event_minute:02d} UTC"

            _, report_hour, report_minute = report_time
            day_offset = (
                -1 if (event_hour, event_minute) > (report_hour, report_minute) else 0
            )
            suffix = " (previous day)" if day_offset == -1 and report_hour == 0 else ""
            return (
                day_offset,
                event_hour,
                event_minute,
            ), f"{event_hour:02d}:{event_minute:02d} UTC{suffix}"

        event_minute = int(time_token)
        if report_time is None:
            return (0, 0, event_minute), f"minute {event_minute:02d}"

        _, report_hour, report_minute = report_time
        event_hour = report_hour
        day_offset = 0

        if event_minute > report_minute:
            event_hour = (report_hour - 1) % 24
            day_offset = -1 if report_hour == 0 else 0

        suffix = " (previous day)" if day_offset == -1 else ""
        return (
            day_offset,
            event_hour,
            event_minute,
        ), f"{event_hour:02d}:{event_minute:02d} UTC{suffix}"

    @staticmethod
    def _decode_runway_depth(depth_raw: str) -> str:
        """Decode runway depth value"""
        special_desc = RUNWAY_DEPTH_SPECIAL.get(depth_raw)
        if special_desc:
            return special_desc[:1].upper() + special_desc[1:]

        depth_val = int(depth_raw)
        if depth_val <= 90:
            return f"{depth_val}mm"
        return f"{depth_val}mm"

    @staticmethod
    def _decode_braking_action(braking_val: int, braking_raw: str) -> str:
        """Decode braking action value"""
        if braking_val in RUNWAY_BRAKING_REMARKS:
            return RUNWAY_BRAKING_REMARKS[braking_val]
        elif braking_val == 99:
            return "Unreliable"
        return f"Friction coefficient 0.{braking_raw}"

    # =========================================================================
    # Status Indicators
    # =========================================================================
    def _sort_by_position(self, remarks: str, decoded: Dict, positions: Dict) -> Dict:
        """Sort decoded dict by position in original remarks string"""
        regex_chars = set(r"\d[]{}+*?()|^$")

        # Find positions for keys not already tracked
        for key in decoded:
            if key not in positions:
                patterns = self._key_patterns.get(key, [])
                min_pos = len(remarks)  # Default to end
                for pattern in patterns:
                    is_regex = any(char in regex_chars for char in pattern)
                    if is_regex:
                        match = re.search(pattern, remarks)
                        if match:
                            min_pos = min(min_pos, match.start())
                    else:
                        pos = remarks.find(pattern)
                        if pos >= 0:
                            min_pos = min(min_pos, pos)
                positions[key] = min_pos

        # Sort decoded dict by position
        return dict(
            sorted(decoded.items(), key=lambda x: positions.get(x[0], len(remarks)))
        )

    @classmethod
    def _is_location_token(cls, token: str) -> bool:
        return token in {
            "OHD",
            "VC",
            "DSNT",
            "ALQDS",
            "AND",
            "MOV",
            "STN",
            "STNRY",
        } or cls._is_direction_token(token)

    @classmethod
    def _is_direction_token(cls, token: str) -> bool:
        direction = cls._DIRECTION_PATTERN
        return bool(re.match(rf"^{direction}(?:-{direction})*$", token))

    @staticmethod
    def _format_distance(token: str) -> str:
        match = re.match(r"^(\d+)(KM|NM|SM)$", token)
        if not match:
            return token
        unit = {"KM": "km", "NM": "NM", "SM": "SM"}[match.group(2)]
        return f"{int(match.group(1))} {unit}"

    @classmethod
    def _format_location_tokens(cls, tokens: List[str]) -> str:
        location_parts: List[str] = []
        movement_parts: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token == "AND":
                i += 1
                continue

            if token == "MOV":
                if i + 1 < len(tokens):
                    movement = tokens[i + 1]
                    if movement in {"STN", "STNRY"}:
                        movement_parts.append("stationary")
                    elif cls._is_direction_token(movement):
                        movement_parts.append(
                            f"moving {cls._expand_direction_text(movement, range_separator=' through ')}"
                        )
                    else:
                        movement_parts.append(f"moving {movement.lower()}")
                    i += 2
                else:
                    i += 1
                continue

            if (
                token == "FM"
                and i + 3 < len(tokens)
                and re.match(r"^\d+(?:KM|NM|SM)$", tokens[i + 1])
            ):
                if tokens[i + 2] == "TO" and re.match(
                    r"^\d+(?:KM|NM|SM)$", tokens[i + 3]
                ):
                    text = f"from {cls._format_distance(tokens[i + 1])} to {cls._format_distance(tokens[i + 3])}"
                    if i + 4 < len(tokens) and cls._is_direction_token(tokens[i + 4]):
                        text += f" to the {cls._expand_direction_text(tokens[i + 4], range_separator=' through ')}"
                        i += 5
                    else:
                        i += 4
                    location_parts.append(text)
                    continue

            if re.match(r"^\d+(?:KM|NM|SM)$", token):
                text = cls._format_distance(token)
                if i + 1 < len(tokens) and cls._is_direction_token(tokens[i + 1]):
                    text += f" to the {cls._expand_direction_text(tokens[i + 1], range_separator=' through ')}"
                    i += 2
                else:
                    i += 1
                location_parts.append(text)
                continue

            if token == "DSNT":
                j = i + 1
                distant_locations: List[str] = []
                while j < len(tokens):
                    if tokens[j] == "AND":
                        j += 1
                        continue
                    if tokens[j] == "ALQDS":
                        distant_locations.append("all quadrants")
                        j += 1
                        continue
                    if cls._is_direction_token(tokens[j]):
                        distant_locations.append(
                            f"to the {cls._expand_direction_text(tokens[j], range_separator=' through ')}"
                        )
                        j += 1
                        continue
                    break

                if distant_locations:
                    location_parts.append(f"distant {' and '.join(distant_locations)}")
                    i = j
                else:
                    location_parts.append(LOCATION_INDICATORS.get(token, "distant"))
                    i += 1
                continue

            if token == "OHD":
                location_parts.append("overhead")
            elif token == "VC":
                location_parts.append("in vicinity (5-10 NM)")
            elif token == "ALQDS":
                location_parts.append("all quadrants")
            elif token in {"STN", "STNRY"}:
                movement_parts.append("stationary")
            elif cls._is_direction_token(token):
                location_parts.append(
                    f"to the {cls._expand_direction_text(token, range_separator=' through ')}"
                )

            i += 1

        parts = location_parts + movement_parts
        return " and ".join(parts)

    @staticmethod
    def _describe_weather_token(token: str) -> Optional[str]:
        intensity = ""
        raw = token
        if raw.startswith("+"):
            intensity = "heavy "
            raw = raw[1:]
        elif raw.startswith("-"):
            intensity = "light "
            raw = raw[1:]

        if raw == "VCSH":
            return "showers in vicinity"

        descriptor = ""
        for desc_code, desc_value in WEATHER_DESCRIPTORS.items():
            if raw.startswith(desc_code):
                descriptor = f"{desc_value} "
                raw = raw[len(desc_code) :]
                break

        phenomena = []
        while raw:
            code = raw[:2]
            if code not in WEATHER_PHENOMENA:
                return None
            phenomena.append(WEATHER_PHENOMENA[code])
            raw = raw[2:]

        if not phenomena:
            return None
        return f"{intensity}{descriptor}{' '.join(phenomena)}".strip()

    @staticmethod
    def _describe_forecast_amendment_token(token: str) -> Optional[str]:
        if token == "NSW":
            return "no significant weather"

        if token.isdigit() and len(token) == 4:
            visibility = int(token)
            if visibility == 9999:
                return "visibility 10km or more"
            if visibility >= 1000:
                return f"visibility {visibility / 1000:.1f}km"
            return f"visibility {visibility}m"

        cloud_match = re.match(r"^(FEW|SCT|BKN|OVC)(\d{3})([A-Z]{2,3})?$", token)
        if cloud_match:
            coverage, height, cloud_type = cloud_match.groups()
            description = f"{coverage} at {int(height) * 100}ft"
            if cloud_type:
                description += f" {cloud_type}"
            return description

        weather = RemarksCommon._describe_weather_token(token)
        if weather:
            return weather

        if re.match(r"^(\d{3}|VRB)\d{2,3}(?:G\d{2,3})?(?:KT|MPS|KMH)$", token):
            return f"wind {token}"

        return None

    @staticmethod
    def _expand_direction_text(text: str, range_separator: str = " to ") -> str:
        expanded = text
        for abbr, full in sorted(
            DIRECTION_ABBREV.items(), key=lambda item: -len(item[0])
        ):
            expanded = re.sub(rf"\b{abbr}\b", full, expanded)
        expanded = re.sub(r"\s+AND\s+", " and ", expanded)
        return re.sub(r"\s*-\s*", range_separator, expanded)

    @staticmethod
    def _decoded_celsius(value: object) -> Optional[float]:
        if not isinstance(value, str) or not value.endswith("°C"):
            return None
        try:
            return float(value[:-2])
        except ValueError:
            return None

    @staticmethod
    def _add_warning(decoded: Dict[str, object], message: str) -> None:
        existing = decoded.get("Additive Data Warning")
        if existing:
            decoded["Additive Data Warning"] = f"{existing}; {message}"
        else:
            decoded["Additive Data Warning"] = message

    # =========================================================================
    # New methods: Tornadic Activity, Coded Obscurations, ACFT MSHP, NOSPECI
    # =========================================================================
