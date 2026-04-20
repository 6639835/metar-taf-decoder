"""Automation remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    MAINTENANCE_INDICATOR,
    SENSOR_STATUS,
    STATION_TYPES,
    re,
)


class AutomationRemarksMixin(RemarksCommon):
    def _parse_station_type(self, remarks: str, decoded: Dict, positions: Dict) -> None:
        """Parse station type (AO1/AO2)"""
        for code in ["AO2", "AO1"]:
            pos = remarks.find(code)
            if pos >= 0:
                decoded["Station Type"] = STATION_TYPES.get(code, code)
                positions["Station Type"] = pos
                return

    # =========================================================================
    # Wind Information
    # =========================================================================
    def _parse_slp_status(self, remarks: str, decoded: Dict) -> None:
        """Parse SLP status (SLPNO)"""
        if "SLPNO" in remarks:
            decoded["SLP Status"] = "Sea level pressure not available"

    def _parse_rvr_status(self, remarks: str, decoded: Dict) -> None:
        """Parse RVR status (RVRNO)"""
        if "RVRNO" in remarks:
            decoded["RVR Status"] = "Runway visual range not available"

    def _parse_sensor_status(self, remarks: str, decoded: Dict) -> None:
        """Parse sensor status indicators"""
        sensor_status = []
        visno_match = re.search(r"\bVISNO(?:\s+(RWY\w+|TWR|SFC))?\b", remarks)
        if visno_match:
            location = visno_match.group(1)
            sensor_status.append(
                f"Visibility at secondary location not available{f' ({location})' if location else ''}"
            )

        chino_match = re.search(r"\bCHINO(?:\s+(RWY\w+|TWR|SFC))?\b", remarks)
        if chino_match:
            location = chino_match.group(1)
            sensor_status.append(
                f"Sky condition at secondary location not available{f' ({location})' if location else ''}"
            )

        for code, description in SENSOR_STATUS.items():
            if code in {"VISNO", "CHINO"}:
                continue
            if code in remarks:
                sensor_status.append(description)

        if sensor_status:
            decoded["Sensor Status"] = "; ".join(sensor_status)

    def _parse_maintenance_indicator(
        self, remarks: str, decoded: Dict, positions: Dict
    ) -> None:
        """Parse maintenance indicator ($)"""
        if MAINTENANCE_INDICATOR in remarks:
            decoded["Maintenance Indicator"] = "Station requires maintenance"
            positions["Maintenance Indicator"] = remarks.find(MAINTENANCE_INDICATOR)

    # =========================================================================
    # Utility Methods
    # =========================================================================
    def _parse_acft_mshp(self, remarks: str, decoded: Dict) -> None:
        """Parse aircraft mishap report indicator — FMH-1 §12.7.1.x."""
        if re.search(r"\bACFT\s+MSHP\b", remarks, re.IGNORECASE):
            decoded["ACFT MSHP"] = "Aircraft mishap report"

    def _parse_nospeci(self, remarks: str, decoded: Dict) -> None:
        """Parse NOSPECI indicator — FMH-1 §12.7.1.y.

        Indicates this station does not issue SPECI (special) reports.
        """
        if re.search(r"\bNOSPECI\b", remarks, re.IGNORECASE):
            decoded["NOSPECI"] = "No SPECI reports issued at this station"
