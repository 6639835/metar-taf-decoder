"""RecentWeather remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    List,
    Optional,
    Tuple,
    re,
)


class RecentWeatherRemarksMixin(RemarksCommon):
    def _parse_past_weather(
        self, remarks: str, decoded: Dict, report_time: Optional[Tuple[int, int, int]]
    ) -> None:
        """Parse precipitation begin/end remarks (e.g., RAB11E24, FZRAB29E44, RAB0254E16B42)

        Format: [descriptor][phenomenon]B[time]E[time]...
        B = began, E = ended
        Time can be 2-digit (MM) or 4-digit (HHMM) format
        """
        past_weather_pattern = (
            r"(MI|PR|BC|DR|BL|SH|TS|FZ)?"
            r"(DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)"
            r"(?:[BE]\d{2,4})+"
        )
        past_weather_matches = re.finditer(past_weather_pattern, remarks)

        timeline_events = []
        found_unknown_precipitation = False

        for match_index, match in enumerate(past_weather_matches):
            full_match = match.group(0)
            descriptor = match.group(1) or ""
            phenomenon = match.group(2)

            weather_type = self._build_weather_type(descriptor, phenomenon)
            found_unknown_precipitation = (
                found_unknown_precipitation or phenomenon == "UP"
            )

            # Extract all B/E events (supports both 2-digit MM and 4-digit HHMM formats)
            events_str = full_match[len(descriptor) + len(phenomenon) :]
            event_matches = re.findall(r"([BE])(\d{2,4})", events_str)

            for event_index, (action, time) in enumerate(event_matches):
                action_text = "began" if action == "B" else "ended"
                sort_key, display_time = self._resolve_event_time(time, report_time)
                timeline_events.append(
                    {
                        "sort_key": sort_key,
                        "match_index": match_index,
                        "event_index": event_index,
                        "display_time": display_time,
                        "description": f"{weather_type} {action_text}",
                    }
                )

        if timeline_events:
            seen_events = set()
            unique_events = []
            for event in timeline_events:
                event_key = (event["display_time"], event["description"])
                if event_key in seen_events:
                    continue
                seen_events.add(event_key)
                unique_events.append(event)
            timeline_events = unique_events
            timeline_events.sort(
                key=lambda event: (
                    event["sort_key"],
                    event["match_index"],
                    event["event_index"],
                )
            )

            timeline_parts: List[str] = []
            current_time = None
            current_descriptions: List[str] = []

            for event in timeline_events:
                display_time = str(event["display_time"])
                description = str(event["description"])
                if display_time != current_time:
                    if current_time is not None:
                        timeline_parts.append(
                            f"{current_time}: {', '.join(current_descriptions)}"
                        )
                    current_time = display_time
                    current_descriptions = [description]
                else:
                    current_descriptions.append(description)

            if current_time is not None:
                timeline_parts.append(
                    f"{current_time}: {', '.join(current_descriptions)}"
                )

            decoded["Precipitation Begin/End Times"] = "; ".join(timeline_parts)

        if found_unknown_precipitation:
            decoded["Unknown Precipitation"] = (
                "Automated station detected precipitation, but the precipitation discriminator could not identify the type"
            )

    def _parse_thunderstorm_begin_end(
        self,
        remarks: str,
        decoded: Dict,
        report_time: Optional[Tuple[int, int, int]],
    ) -> None:
        """Parse thunderstorm begin/end remarks (e.g. TSB0159E30)."""
        events = []

        for match in re.finditer(r"\bTS((?:[BE]\d{2,4})+)\b", remarks):
            for action, time_token in re.findall(r"([BE])(\d{2,4})", match.group(1)):
                sort_key, display_time = self._resolve_event_time(
                    time_token, report_time
                )
                description = (
                    "thunderstorm began" if action == "B" else "thunderstorm ended"
                )
                events.append((sort_key, display_time, description))

        if not events:
            return

        events = list(dict.fromkeys(events))
        events.sort(key=lambda item: item[0])
        parts = [
            f"{display_time}: {description}" for _, display_time, description in events
        ]
        decoded["Thunderstorm Begin/End Times"] = "; ".join(parts)

    def _parse_virga(self, remarks: str, decoded: Dict) -> None:
        """Parse virga information (precipitation not reaching ground)"""
        virga_match = re.search(
            r"VIRGA\s*(DSNT|VC)?\s*"
            r"((?:(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)"
            r"(?:\s+AND\s+(?:NE|NW|SE|SW|N|E|S|W)(?:-(?:NE|NW|SE|SW|N|E|S|W))?)*)?",
            remarks,
        )
        if virga_match:
            virga_parts = ["Virga (precipitation not reaching ground)"]
            location = virga_match.group(1)
            direction = virga_match.group(2)

            if location:
                loc_map = {"DSNT": "distant", "VC": "in vicinity"}
                virga_parts.append(loc_map.get(location, location))

            if direction:
                dir_text = self._expand_direction_text(
                    direction, range_separator=" through "
                )
                virga_parts.append(f"to the {dir_text}")

            decoded["Virga"] = " ".join(virga_parts)

    def _parse_directional_weather(self, remarks: str, decoded: Dict) -> None:
        """Parse plain-language weather location remarks such as SHRA DSNT S-N."""
        tokens = remarks.split()
        descriptions: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            weather = self._describe_weather_token(token)
            if weather is None:
                i += 1
                continue

            j = i + 1
            location_tokens: List[str] = []
            while j < len(tokens) and self._is_location_token(tokens[j]):
                location_tokens.append(tokens[j])
                j += 1

            if location_tokens:
                descriptions.append(
                    f"{weather} {self._format_location_tokens(location_tokens)}"
                )
            i = j

        if descriptions:
            decoded["Weather Location"] = "; ".join(dict.fromkeys(descriptions))

    def _parse_jma_pirep_turbulence(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA PIREP turbulence remarks appended in RMK."""
        intensity_map = {
            "FBL": "Feeble",
            "LGT": "Light",
            "MOD": "Moderate",
            "SEV": "Severe",
            "HVY": "Heavy",
        }
        phase_map = {
            "CMB": "climb",
            "DES": "descent",
            "CRZ": "cruise",
        }
        pattern = re.compile(
            r"\b(FBL|LGT|MOD|SEV|HVY)\s+TURB\s+OBS\s+AT\s+(\d{4})Z\s+"
            r"(.+?)\s+BTN\s+(\d+FT)\s+AND\s+(\d+FT)\s+IN\s+"
            r"(CMB|DES|CRZ)(?:\s+(?:BY\s+)?([A-Z0-9]+))?"
        )
        reports: List[str] = []
        for match in pattern.finditer(remarks):
            intensity, hhmm, location, lower, upper, phase, aircraft = match.groups()
            time_text = f"{hhmm[:2]}:{hhmm[2:]} UTC"
            description = (
                f"{intensity_map[intensity]} turbulence observed at {time_text} "
                f"near {location.strip()} between {lower} and {upper} "
                f"in {phase_map.get(phase, phase.lower())}"
            )
            if aircraft:
                description += f" by {aircraft}"
            reports.append(description)

        if reports:
            decoded["PIREP Turbulence"] = reports

    def _parse_jma_forecast_amendment(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA FCST AMD trend blocks appended in RMK."""
        tokens = remarks.split()
        try:
            start = next(
                i
                for i in range(len(tokens) - 1)
                if tokens[i : i + 2] == ["FCST", "AMD"]
            )
        except StopIteration:
            return

        j = start + 2
        if j < len(tokens) and re.match(r"^\d{4}$", tokens[j]):
            issue_time = tokens[j]
            decoded["Forecast Amendment"] = (
                f"Amended forecast issued at {issue_time[:2]}:{issue_time[2:]} UTC"
            )
            j += 1
        else:
            decoded["Forecast Amendment"] = "Amended forecast"

        trends: List[str] = []
        while j < len(tokens):
            if tokens[j] not in {"TEMPO", "BECMG"}:
                j += 1
                continue

            trend_type = tokens[j]
            j += 1
            period = None
            if j < len(tokens) and re.match(r"^\d{4}$", tokens[j]):
                period = f"{tokens[j][:2]}:00-{tokens[j][2:]}:00 UTC"
                j += 1

            elements: List[str] = []
            while j < len(tokens) and tokens[j] not in {"TEMPO", "BECMG"}:
                change = self._describe_forecast_amendment_token(tokens[j])
                if change:
                    elements.append(change)
                j += 1

            label = "Temporary" if trend_type == "TEMPO" else "Becoming"
            description = label
            if period:
                description += f" {period}"
            if elements:
                description += f": {', '.join(elements)}"
            trends.append(description)

        if trends:
            decoded["Forecast Trends"] = trends

    # =========================================================================
    # Cloud Information
    # =========================================================================
    def _parse_hailstone_size(self, remarks: str, decoded: Dict) -> None:
        """Parse hailstone size (GR [size]) — FMH-1 §12.7.1.n

        GR 3/4 = 3/4 inch; GR 1 1/2 = 1.5 inch; GR LESS THAN 1/4 = <1/4 inch
        """
        # GR LESS THAN fraction
        m = re.search(r"\bGR\s+LESS\s+THAN\s+(\d+/\d+|\d+)\b", remarks)
        if m:
            decoded["Hailstone Size"] = f"Less than {m.group(1)} inch in diameter"
            return
        # GR whole [fraction]
        m = re.search(r"\bGR\s+(\d+)(?:\s+(\d+/\d+))?\b", remarks)
        if m:
            if m.group(2):
                num, den = m.group(2).split("/")
                size = int(m.group(1)) + int(num) / int(den)
                decoded["Hailstone Size"] = f"{size:.2f} inches in diameter"
            else:
                decoded["Hailstone Size"] = f"{m.group(1)} inch(es) in diameter"
            return
        # GR fraction only
        m = re.search(r"\bGR\s+(\d+/\d+)\b", remarks)
        if m:
            decoded["Hailstone Size"] = f"{m.group(1)} inch in diameter"

    def _parse_snow_pellet_intensity(self, remarks: str, decoded: Dict) -> None:
        """Parse snow pellet/small hail intensity (GS LGT|MOD|HVY) — FMH-1 §12.7.1.o"""
        m = re.search(r"\bGS\s+(LGT|MOD|HVY)\b", remarks)
        if m:
            intensity_map = {"LGT": "light", "MOD": "moderate", "HVY": "heavy"}
            decoded["Snow Pellet Intensity"] = (
                f"{intensity_map[m.group(1)]} snow pellets/small hail"
            )

    def _parse_volcanic_eruption(self, remarks: str, decoded: Dict) -> None:
        """Parse volcanic eruption plain language — FMH-1 §12.7.1.a

        Captures 'VOLCANO ERUPTED' or 'ERUPTED' plain language blocks.
        """
        m = re.search(r"\b(VOLCANO|ERUPTION|ERUPTED)\b.*", remarks, re.IGNORECASE)
        if m:
            decoded["Volcanic Activity"] = m.group(0).strip()

    def _parse_tornadic_activity(self, remarks: str, decoded: Dict) -> None:
        """Parse tornadic activity remarks — FMH-1 §12.7.1.b (highest priority in RMK section).

        Format: (TORNADO|FUNNEL CLOUD|WATERSPOUT) B(hh)(mm) [E(hh)(mm)] [dist] [dir] [MOV dir]
        Examples:
          TORNADO B13 6 NE
          FUNNEL CLOUD B1330 5 SW MOV NE
          WATERSPOUT B04E09
        """
        direction_pattern = r"(?:NE|NW|SE|SW|N|E|S|W)"
        pattern = (
            r"\b(TORNADO|FUNNEL\s+CLOUD|WATERSPOUT)"
            r"(?:\s+B(\d{2,4}))?"
            r"(?:\s+E(\d{2,4}))?"
            r"(?:\s+(\d+))?"
            rf"(?:\s+({direction_pattern}))?"
            rf"(?:\s+MOV\s+({direction_pattern}))?"
        )
        m = re.search(pattern, remarks, re.IGNORECASE)
        if not m:
            return

        phenomenon = m.group(1).replace("  ", " ")
        begin_raw = m.group(2)
        end_raw = m.group(3)
        distance = m.group(4)
        direction = m.group(5)
        mov_direction = m.group(6)

        def _fmt_time(t: str) -> str:
            return f"{t[:2]}:{t[2:]} UTC" if len(t) == 4 else f":{t} UTC (current hour)"

        parts_list = [phenomenon]
        if begin_raw:
            parts_list.append(f"began at {_fmt_time(begin_raw)}")
        if end_raw:
            parts_list.append(f"ended {_fmt_time(end_raw)}")
        if distance and direction:
            parts_list.append(
                f"{distance} SM to the {self._expand_direction_text(direction)}"
            )
        elif direction:
            parts_list.append(f"to the {self._expand_direction_text(direction)}")
        if mov_direction:
            parts_list.append(f"moving {self._expand_direction_text(mov_direction)}")

        decoded["Tornadic Activity"] = "; ".join(parts_list)
