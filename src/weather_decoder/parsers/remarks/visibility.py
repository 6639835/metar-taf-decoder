"""Visibility remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    re,
)


class VisibilityRemarksMixin(RemarksCommon):
    def _parse_variable_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse variable visibility (VIS minVmax)"""
        vis_match = re.search(
            rf"VIS\s+({self._VIS_VALUE_PATTERN})V({self._VIS_VALUE_PATTERN})",
            remarks,
        )
        if vis_match:
            min_vis_str = vis_match.group(1)
            max_vis_str = vis_match.group(2)

            min_vis = self._parse_visibility_fraction(min_vis_str)
            max_vis = self._parse_visibility_fraction(max_vis_str)

            min_vis_display = (
                str(int(min_vis)) if min_vis == int(min_vis) else min_vis_str
            )
            max_vis_display = (
                str(int(max_vis)) if max_vis == int(max_vis) else max_vis_str
            )

            decoded["Variable Visibility"] = (
                f"{min_vis_display} to {max_vis_display} statute miles"
            )

    def _parse_lower_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse VIS LWR directional lower-visibility remarks."""
        match = re.search(
            rf"\bVIS\s+LWR\s+({self._DIRECTION_PATTERN}(?:-{self._DIRECTION_PATTERN})*)\b",
            remarks,
        )
        if match:
            decoded["Visibility Lower"] = (
                f"Visibility lower to the {self._expand_direction_text(match.group(1), range_separator=' through ')}"
            )

    def _parse_jma_directional_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA directional visibility remarks such as 3500E-S."""
        matches = re.findall(
            rf"\b(\d{{4}})({self._DIRECTION_PATTERN}(?:-{self._DIRECTION_PATTERN})*)\b",
            remarks,
        )
        if not matches:
            return

        decoded["Directional Visibility (JMA)"] = [
            f"{int(value)} m to the {self._expand_direction_text(direction, range_separator=' through ')}"
            for value, direction in matches
        ]

    def _parse_surface_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse surface visibility (SFC VIS vv)"""
        sfc_vis_match = re.search(rf"SFC\s+VIS\s+({self._VIS_VALUE_PATTERN})", remarks)
        if sfc_vis_match:
            sfc_vis_str = sfc_vis_match.group(1)
            decoded["Surface Visibility"] = f"{sfc_vis_str} SM"

    def _parse_tower_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse tower visibility (TWR VIS vv)"""
        twr_vis_match = re.search(rf"TWR\s+VIS\s+({self._VIS_VALUE_PATTERN})", remarks)
        if twr_vis_match:
            twr_vis_str = twr_vis_match.group(1)
            decoded["Tower Visibility"] = f"{twr_vis_str} SM"

    def _parse_sector_visibility(self, remarks: str, decoded: Dict) -> None:
        """Parse sector visibility (VIS [DIR] vvvvv) — FMH-1 §12.7.1.h

        Reports visibility in a specific compass direction sector.
        Example: VIS NE 1 1/2 SM or VIS W 3SM
        """
        m = re.search(
            r"\bVIS\s+(N|NE|E|SE|S|SW|W|NW)\s+(\d+(?:\s+\d+/\d+)?(?:SM)?|\d/\d+\s*SM?|M?\d+(?:\s*SM)?)\b",
            remarks,
        )
        if m:
            direction = m.group(1)
            vis_raw = m.group(2).strip()
            decoded.setdefault("Sector Visibility", [])
            if isinstance(decoded["Sector Visibility"], list):
                decoded["Sector Visibility"].append(f"{vis_raw} to the {direction}")
            if len(decoded["Sector Visibility"]) == 1:
                decoded["Sector Visibility"] = decoded["Sector Visibility"][0]

    def _parse_visibility_second_location(self, remarks: str, decoded: Dict) -> None:
        """Parse visibility at a second location (VIS vvvvv LOC) — FMH-1 §12.7.1.i

        Example: VIS 3 RWY11 — visibility at runway 11 threshold
        Must not overlap with variable-visibility (minVmax) or sector-visibility (VIS DIR ...) patterns.
        """
        m = re.search(
            r"\bVIS\s+(\d+(?:\s+\d+/\d+)?(?:SM)?|\d/\d+\s*SM?)\s+(RWY\w+|TWR|SFC)\b",
            remarks,
        )
        if m:
            vis_raw = m.group(1).strip()
            location = m.group(2)
            decoded["Visibility (2nd Location)"] = f"{vis_raw} at {location}"
