"""Precipitation remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    re,
)


class PrecipitationRemarksMixin(RemarksCommon):
    def _parse_6hr_precipitation(self, remarks: str, decoded: Dict) -> None:
        """Parse 6-hour precipitation (6xxxx format)

        FMH-1 §12.7.2.a(3): 6R24R24R24R24
        - 6//// = indeterminate amount (e.g., gage frozen)
        - 60000 = trace or none
        - 6xxxx = amount in hundredths of inches
        """
        precip_6hr_match = re.search(r"(?<!\d)6(/{4}|\d{4})(?!\d)", remarks)
        if precip_6hr_match:
            raw = precip_6hr_match.group(1)
            if raw == "////":
                decoded["6-Hour Precipitation"] = (
                    "Indeterminate (gauge frozen or inaccessible)"
                )
            else:
                precip_hundredths = int(raw)
                if precip_hundredths == 0:
                    decoded["6-Hour Precipitation"] = "Trace or none"
                else:
                    precip_inches = precip_hundredths / 100.0
                    decoded["6-Hour Precipitation"] = f"{precip_inches:.2f} inches"

    def _parse_precipitation_amount(self, remarks: str, decoded: Dict) -> None:
        """Parse precipitation amount (Pxxxx format)"""
        precip_match = re.search(r"P(\d{4})", remarks)
        if precip_match:
            precip_hundredths = int(precip_match.group(1))
            if precip_hundredths == 0:
                decoded["Precipitation Amount"] = "Less than 0.01 inches"
            else:
                precip_inches = precip_hundredths / 100.0
                decoded["Precipitation Amount"] = f"{precip_inches:.2f} inches"

    # =========================================================================
    # Visibility Information
    # =========================================================================
    def _parse_24hr_precipitation(self, remarks: str, decoded: Dict) -> None:
        """Parse 24-hour precipitation (7R24R24R24R24 format) — FMH-1 §12.7.2.a(3)(c)

        7xxxx = amount in hundredths of inches over previous 24 hours
        7//// = indeterminate amount
        """
        m = re.search(r"(?<!\d)7(/{4}|\d{4})(?!\d)", remarks)
        if m:
            raw = m.group(1)
            if raw == "////":
                decoded["24-Hour Precipitation"] = (
                    "Indeterminate (gauge frozen or inaccessible)"
                )
            else:
                val = int(raw)
                decoded["24-Hour Precipitation"] = (
                    "Trace or none" if val == 0 else f"{val / 100.0:.2f} inches"
                )

    def _parse_snow_depth(self, remarks: str, decoded: Dict) -> None:
        """Parse snow depth on ground — FMH-1 §12.7.2.a(4)

        Standard format: 4/sss  (4/ is group indicator, sss = depth in whole inches)
        ASOS variant:    /sss   (some older ASOS units omit the leading '4')

        4//// or //// = not measurable
        """
        m = re.search(r"(?<!\d)4(/(/{3}|\d{3}))(?!\d)", remarks)
        if not m:
            # Fallback: bare /sss without leading 4 (common in ASOS transmissions)
            m = re.search(r"(?<![4\d])(/)(/{3}|\d{3})(?!\d)", remarks)
        if m:
            raw = m.group(2) if (m.lastindex or 0) >= 2 else m.group(1)
            if raw in ("///", "////"):
                decoded["Snow Depth"] = "Not measurable"
            else:
                depth = int(raw)
                decoded["Snow Depth"] = (
                    f"{depth} inch{'es' if depth != 1 else ''} on ground"
                )

    def _parse_water_equivalent_snow(self, remarks: str, decoded: Dict) -> None:
        """Parse water equivalent of snow on ground (933RRR format) — FMH-1 §12.7.2.a(5)

        933RRR where RRR is tenths of inches (e.g., 933017 = 1.7 inches)
        """
        m = re.search(r"(?<!\d)933(\d{3})(?!\d)", remarks)
        if m:
            val_tenths = int(m.group(1))
            decoded["Water Equivalent of Snow"] = f"{val_tenths / 10.0:.1f} inches"

    def _parse_sunshine_duration(self, remarks: str, decoded: Dict) -> None:
        """Parse sunshine duration (98mmm format) — FMH-1 §12.7.2.c

        98mmm = minutes of sunshine in previous calendar day; 98/// = missing
        """
        m = re.search(r"(?<!\d)98(/{3}|\d{3})(?!\d)", remarks)
        if m:
            raw = m.group(1)
            if raw == "///":
                decoded["Sunshine Duration"] = "Missing"
            else:
                decoded["Sunshine Duration"] = f"{int(raw)} minutes"

    def _parse_ice_accretion(self, remarks: str, decoded: Dict) -> None:
        """Parse ice accretion on unshielded sensor (I1nnn/I3nnn/I6nnn) — FMH-1 §12.7.2.i

        I1nnn = 1-hour accretion; I3nnn = 3-hour; I6nnn = 6-hour
        nnn = hundredths of inch (e.g., I1015 = 0.15 inches in 1 hour)
        """
        ice_matches = re.findall(r"\bI([136])(\d{3})\b", remarks)
        if ice_matches:
            parts = []
            for period, raw in ice_matches:
                val_in = int(raw) / 100.0
                parts.append(f"{val_in:.2f} inches over {period} hour(s)")
            decoded["Ice Accretion"] = "; ".join(parts)

    def _parse_snincr(self, remarks: str, decoded: Dict) -> None:
        """Parse snow increasing rapidly (SNINCR nh/ns) — FMH-1 §12.7.1.z

        nh = inches of snow in past hour; ns = total snow depth on ground
        Example: SNINCR 2/8 — 2 inches of snow in past hour, 8 inches total
        """
        m = re.search(r"\bSNINCR\s+(\d+)/(\d+)\b", remarks)
        if m:
            hourly = m.group(1)
            total = m.group(2)
            decoded["Snow Increasing Rapidly"] = (
                f"{hourly} inch(es) in past hour; {total} inch(es) total depth"
            )

    def _parse_ri_precip_intensity(self, remarks: str, decoded: Dict) -> None:
        """Parse JMA precipitation intensity in RMK (RIxxx) — JMA Attachment 2

        RIxxx where xxx is precipitation intensity in whole mm/h
        (e.g., RI035 = 35 mm/h).
        Reported when intensity is 3 mm/h or more.
        """
        m = re.search(r"\bRI(\d{3})\b", remarks)
        if m:
            val = int(m.group(1))
            decoded["Precipitation Intensity (JMA)"] = f"{val} mm/h"
