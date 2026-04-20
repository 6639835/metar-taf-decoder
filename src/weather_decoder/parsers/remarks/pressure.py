"""Pressure remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    PRESSURE_TENDENCY_CHARACTERISTICS,
    re,
)


class PressureRemarksMixin(RemarksCommon):
    def _parse_sea_level_pressure(self, remarks: str, decoded: Dict) -> None:
        """Parse sea level pressure (SLPxxx)"""
        slp_match = re.search(r"SLP(\d{3})", remarks)
        if slp_match:
            slp = int(slp_match.group(1))
            # North American format: add decimal point
            if slp < 500:
                pressure = 1000 + slp / 10
            else:
                pressure = 900 + slp / 10
            decoded["Sea Level Pressure"] = f"{pressure:.1f} hPa"

    def _parse_pressure_tendency(self, remarks: str, decoded: Dict) -> None:
        """Parse pressure tendency (5appp format)

        5 = group identifier
        a = pressure characteristic (0-8)
        ppp = pressure change in tenths of hPa
        """
        pressure_tendency_match = re.search(r"(?<!\d)5([0-8])(\d{3})(?!\d)", remarks)
        if pressure_tendency_match:
            characteristic = int(pressure_tendency_match.group(1))
            change_tenths = int(pressure_tendency_match.group(2))
            change_hpa = change_tenths / 10
            char_desc = PRESSURE_TENDENCY_CHARACTERISTICS.get(
                characteristic, f"Unknown ({characteristic})"
            )
            decoded["Pressure Tendency"] = f"{char_desc}; change: {change_hpa:.1f} hPa"

    def _parse_qfe(self, remarks: str, decoded: Dict) -> None:
        """Parse QFE (field elevation pressure) - Russian METAR format

        Russian METARs use the format QFEnnn/xxxx where:
        - nnn = pressure in mmHg (millimeters of mercury)
        - xxxx = pressure in hPa (hectopascals), with leading zero if < 1000

        Example: QFE728/0971 means 728 mmHg = 971 hPa
        Some reports may only include QFEnnn without the hPa value.
        """
        # Try to match QFE with both mmHg and hPa values
        qfe_match = re.search(r"QFE(\d{3,4})(?:/(\d{4}))?", remarks)
        if qfe_match:
            qfe_mmhg = int(qfe_match.group(1))
            qfe_hpa_str = qfe_match.group(2)

            if qfe_hpa_str:
                # Both values provided
                qfe_hpa = int(qfe_hpa_str)
                decoded["QFE"] = f"{qfe_mmhg} mmHg ({qfe_hpa} hPa)"
            else:
                # Only mmHg value provided, calculate approximate hPa
                # 1 mmHg ≈ 1.33322 hPa
                qfe_hpa_calc = int(qfe_mmhg * 1.33322)
                decoded["QFE"] = f"{qfe_mmhg} mmHg (~{qfe_hpa_calc} hPa)"

    def _parse_altimeter_remarks(self, remarks: str, decoded: Dict) -> None:
        """Parse altimeter setting in remarks (Axxxx format)"""
        altimeter_rmk_match = re.search(r"\bA(\d{4})\b", remarks)
        if altimeter_rmk_match:
            alt_value = int(altimeter_rmk_match.group(1))
            alt_inhg = alt_value / 100
            decoded["Altimeter (Remarks)"] = f"{alt_inhg:.2f} inHg"

    def _parse_pressure_change(self, remarks: str, decoded: Dict) -> None:
        """Parse rapid pressure change indicators (PRESFR/PRESRR)"""
        if "PRESFR" in remarks:
            decoded["Pressure Change"] = "Pressure falling rapidly"
        elif "PRESRR" in remarks:
            decoded["Pressure Change"] = "Pressure rising rapidly"

    # =========================================================================
    # Temperature Information
    # =========================================================================
    def _parse_p_fr_p_rr(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA local report rapid pressure change (P/FR, P/RR) — JMA Attachment 2

        P/FR = pressure falling rapidly (equivalent to PRESFR)
        P/RR = pressure rising rapidly (equivalent to PRESRR)
        Used in JMA local routine/special METAR-format reports.
        """
        if re.search(r"\bP/FR\b", remarks):
            decoded.setdefault("Pressure Change", "Pressure falling rapidly")
        elif re.search(r"\bP/RR\b", remarks):
            decoded.setdefault("Pressure Change", "Pressure rising rapidly")
