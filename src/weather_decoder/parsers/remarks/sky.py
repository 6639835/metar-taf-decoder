"""Sky remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    CLOUD_TYPE_CODES,
    Dict,
    List,
    re,
)


class SkyRemarksMixin(RemarksCommon):
    def _parse_acsl(self, remarks: str, decoded: Dict) -> None:
        """Parse ACSL (Altocumulus Standing Lenticular) clouds"""
        acsl_match = re.search(
            r"ACSL\s*(DSNT|VC|OHD)?\s*([NSEW]+(?:-[NSEW]+)?)?\s*"
            r"(?:MOV\s+([NSEW]+(?:-[NSEW]+)?))?",
            remarks,
        )
        if acsl_match:
            acsl_parts = ["Altocumulus Standing Lenticular clouds"]
            location = acsl_match.group(1)
            direction = acsl_match.group(2)
            movement = acsl_match.group(3)

            if location:
                loc_map = {"DSNT": "distant", "VC": "in vicinity", "OHD": "overhead"}
                acsl_parts.append(loc_map.get(location, location))

            if direction:
                dir_text = self._expand_direction_text(
                    direction, range_separator=" through "
                )
                acsl_parts.append(f"to the {dir_text}")

            if movement:
                mov_text = self._expand_direction_text(
                    movement, range_separator=" through "
                )
                acsl_parts.append(f"moving {mov_text}")

            decoded["ACSL"] = " ".join(acsl_parts)

    def _parse_significant_cloud_remarks(self, remarks: str, decoded: Dict) -> None:
        """Parse FMH-1 significant cloud-type remarks written in plain language."""
        cloud_labels = {
            "CBMAM": "Cumulonimbus mammatus",
            "CB": "Cumulonimbus",
            "TCU": "Towering cumulus",
            "ACC": "Altocumulus castellanus",
            "SCSL": "Stratocumulus standing lenticular",
            "ACSL": "Altocumulus standing lenticular",
            "CCSL": "Cirrocumulus standing lenticular",
            "APRNT ROTOR CLD": "Apparent rotor cloud",
        }
        cloud_tokens = {key for key in cloud_labels if " " not in key}
        tokens = remarks.split()
        cloud_descriptions: List[str] = []
        i = 0
        while i < len(tokens):
            cloud_code = None
            if tokens[i : i + 3] == ["APRNT", "ROTOR", "CLD"]:
                cloud_code = "APRNT ROTOR CLD"
                j = i + 3
            elif tokens[i] in cloud_tokens:
                cloud_code = tokens[i]
                j = i + 1
            else:
                i += 1
                continue

            # JMA okta cloud groups such as 1CB035 are handled separately.
            if i > 0 and re.match(
                r"^\d(?:TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)\d{3}$", tokens[i]
            ):
                i += 1
                continue

            location_tokens: List[str] = []
            while j < len(tokens) and (
                self._is_location_token(tokens[j])
                or re.match(r"^\d+(?:KM|NM|SM)$", tokens[j])
                or tokens[j] in {"FM", "TO"}
            ):
                location_tokens.append(tokens[j])
                j += 1

            parts = [cloud_labels.get(cloud_code, cloud_code)]
            location_text = self._format_location_tokens(location_tokens)
            if location_text:
                parts.append(location_text)
            cloud_descriptions.append(" ".join(parts))
            i = j

        if cloud_descriptions:
            existing = decoded.get("Cloud Types")
            if existing:
                cloud_descriptions.insert(0, str(existing))
            decoded["Cloud Types"] = "; ".join(dict.fromkeys(cloud_descriptions))

    def _parse_cloud_types(self, remarks: str, decoded: Dict) -> None:
        """Parse cloud type codes

        Handles:
        - Japanese/ICAO format: {oktas}{cloud_type}{height} e.g., 1CU007, 3SC015
        - Canadian format: {cloud_type}{oktas} e.g., SC6, AC3
        - Trace clouds: e.g., AC TR, CI TR
        """
        cloud_types_found = []

        # Japanese/ICAO format
        japan_cloud_matches = re.findall(
            r"\b(\d)(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d{3})\b", remarks
        )
        for oktas, cloud_code, height in japan_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            height_ft = int(height) * 100
            cloud_types_found.append(
                f"{cloud_name} {oktas}/8 sky coverage at {height_ft} feet"
            )

        # Canadian format (only if no Japanese format found)
        if not japan_cloud_matches:
            cloud_type_matches = re.findall(
                r"(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)(\d)(?!\d{2})", remarks
            )
            for cloud_code, oktas in cloud_type_matches:
                cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
                cloud_types_found.append(f"{cloud_name} {oktas}/8 sky coverage")

        # Trace cloud patterns
        trace_cloud_matches = re.findall(
            r"\b(TCU|SN|SC|ST|CU|CB|CI|CS|CC|AC|AS|NS|CF|SF)\s+TR\b", remarks
        )
        for cloud_code in trace_cloud_matches:
            cloud_name = CLOUD_TYPE_CODES.get(cloud_code, cloud_code)
            cloud_types_found.append(f"{cloud_name} trace (less than 1/8 sky coverage)")

        if cloud_types_found:
            existing = decoded.get("Cloud Types")
            if existing:
                cloud_types_found.insert(0, str(existing))
            decoded["Cloud Types"] = "; ".join(dict.fromkeys(cloud_types_found))

    def _parse_ceiling(self, remarks: str, decoded: Dict) -> None:
        """Parse ceiling information (CIGxxx or CIG xxxVxxx)"""
        cig_match = re.search(r"\bCIG\s*(\d{3})(?:\s*V\s*(\d{3}))?\b", remarks)
        if cig_match:
            cig_low = int(cig_match.group(1)) * 100
            if cig_match.group(2):
                cig_high = int(cig_match.group(2)) * 100
                decoded["Variable Ceiling"] = f"{cig_low} to {cig_high} feet AGL"
            else:
                decoded["Ceiling"] = f"{cig_low} feet AGL"

    def _parse_obscuration(self, remarks: str, decoded: Dict) -> None:
        """Parse obscuration remarks"""
        if re.search(r"\bMT\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"
        elif re.search(r"\bMTN\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountain obscured"
        elif re.search(r"\bMTNS\s+OBSC\b", remarks):
            decoded["Obscuration"] = "Mountains obscured"

    def _parse_qbb(self, remarks: str, decoded: Dict) -> None:
        """Parse QBB (cloud base height in meters) - Russian METAR format

        QBB is used in Russian METARs to report the height of the lower
        boundary of clouds in meters above ground level.
        Format: QBBnnn where nnn is the height in meters
        Example: QBB220 = cloud base at 220 meters AGL
        """
        qbb_match = re.search(r"\bQBB(\d{2,4})\b", remarks)
        if qbb_match:
            height_meters = int(qbb_match.group(1))
            # Convert meters to feet for reference (1 meter ≈ 3.28084 feet)
            height_feet = int(height_meters * 3.28084)
            decoded["QBB"] = (
                f"Cloud base at {height_meters} meters ({height_feet} feet) AGL"
            )

    def _parse_density_altitude(self, remarks: str, decoded: Dict) -> None:
        """Parse density altitude (Canadian remarks)"""
        density_alt_match = re.search(r"DENSITY\s+ALT\s+(-?\d+)FT", remarks)
        if density_alt_match:
            density_alt = int(density_alt_match.group(1))
            decoded["Density Altitude"] = f"{density_alt} feet"

    # =========================================================================
    # Runway Information
    # =========================================================================
    def _parse_runway_state_remarks(self, remarks: str, decoded: Dict) -> None:
        """Do not decode bare 8-digit remark groups as METAR runway state.

        WMO FM 15 encodes METAR runway state as RDRDR/ERCReReRBRBR or R/SNOCLO,
        while FMH-1 uses 8/CLCMCH for additive cloud-type data. A bare group such
        as 83311195 is not a METAR runway-state group and should remain undecoded.
        """
        return None

    def _parse_ceiling_second_location(self, remarks: str, decoded: Dict) -> None:
        """Parse ceiling at a second location (CIG hhh LOC) — FMH-1 §12.7.1.u

        Example: CIG 002 RWY11 — ceiling 200 ft at runway 11
        """
        m = re.search(r"\bCIG\s+(\d{3})\s+(RWY\w+|TWR|SFC)\b", remarks)
        if m:
            cig_ft = int(m.group(1)) * 100
            location = m.group(2)
            decoded["Ceiling (2nd Location)"] = f"{cig_ft} feet AGL at {location}"

    def _parse_variable_sky_condition(self, remarks: str, decoded: Dict) -> None:
        """Parse variable sky condition (NsNsNs hshshs V NsNsNs) — FMH-1 §12.7.1.s

        Example: SCT025 V BKN — ceiling variable between scattered and broken at 2500 ft
        """
        m = re.search(
            r"\b(FEW|SCT|BKN|OVC)(\d{3})\s+V\s+(FEW|SCT|BKN|OVC)\b",
            remarks,
        )
        if m:
            low_cov = m.group(1)
            height_ft = int(m.group(2)) * 100
            high_cov = m.group(3)
            decoded["Variable Sky"] = (
                f"Variable between {low_cov} and {high_cov} at {height_ft} feet"
            )

    def _parse_cloud_type_8group(self, remarks: str, decoded: Dict) -> None:
        """Parse cloud type additive data (8/CLCMCH format) — FMH-1 §12.7.2.b / WMO

        8/CL CM CH where each digit is a WMO cloud genus code:
        CL = 0-9 per Code Table 0513; CM = Code Table 0515; CH = Code Table 0521
        / = observation not made
        """
        # WMO Code Table 0513 (low clouds)
        cl_codes = {
            "0": "No low clouds",
            "1": "Cu (fair weather)",
            "2": "Cu (towering)",
            "3": "Cb (no top)",
            "4": "Sc (spread from Cu)",
            "5": "Sc (not from Cu)",
            "6": "St or Fs (not associated with fog)",
            "7": "Fs/St (associated with fog/precip)",
            "8": "Cu and Sc at different levels",
            "9": "Cb with anvil top",
            "/": "Not observed",
        }
        # WMO Code Table 0515 (middle clouds)
        cm_codes = {
            "0": "No middle clouds",
            "1": "As (thin)",
            "2": "As (thick) or Ns",
            "3": "Ac (thin at single level)",
            "4": "Ac patches (thin)",
            "5": "Ac (thin in bands)",
            "6": "Ac formed from Cu spreading",
            "7": "Ac (double layer or thick)",
            "8": "Ac with Cb",
            "9": "Ac (chaotic sky)",
            "/": "Not observed",
        }
        # WMO Code Table 0521 (high clouds)
        ch_codes = {
            "0": "No high clouds",
            "1": "Ci (filaments)",
            "2": "Ci (dense patch)",
            "3": "Ci (anvil from Cb)",
            "4": "Ci (thickening)",
            "5": "Ci and Cs (< 45° altitude)",
            "6": "Ci and Cs (> 45° altitude)",
            "7": "Cs covering sky",
            "8": "Cs not covering sky",
            "9": "Cc",
            "/": "Not observed",
        }
        m = re.search(r"(?<!\d)8/([0-9/])([0-9/])([0-9/])(?!\d)", remarks)
        if m:
            cl = cl_codes.get(m.group(1), f"Unknown ({m.group(1)})")
            cm = cm_codes.get(m.group(2), f"Unknown ({m.group(2)})")
            ch = ch_codes.get(m.group(3), f"Unknown ({m.group(3)})")
            decoded["Cloud Types (Additive)"] = f"Low: {cl}; Middle: {cm}; High: {ch}"

    def _parse_obscuration_coded(self, remarks: str, decoded: Dict) -> None:
        """Parse FMH-1 §12.7.1.r coded obscuration remarks.

        Format: wx_code coverage hshshs
        Example: FG SCT000  FU BKN020  HZ FEW005
        """
        obs_wx = r"FG|FU|VA|DU|SA|HZ|PY|BR|BLSN|BLDU|BLSA|IC|GR|GS|SN|PL|RA|DZ|FZFG"
        coverage_levels = r"FEW|SCT|BKN|OVC"
        pattern = rf"\b({obs_wx})\s+({coverage_levels})(\d{{3}})\b"
        matches = re.findall(pattern, remarks)
        if not matches:
            return

        wx_labels = {
            "FG": "Fog",
            "FU": "Smoke",
            "VA": "Volcanic ash",
            "DU": "Widespread dust",
            "SA": "Sand",
            "HZ": "Haze",
            "PY": "Spray",
            "BR": "Mist",
            "BLSN": "Blowing snow",
            "BLDU": "Blowing dust",
            "BLSA": "Blowing sand",
            "IC": "Ice crystals",
            "GR": "Hail",
            "GS": "Snow pellets",
            "SN": "Snow",
            "PL": "Ice pellets",
            "RA": "Rain",
            "DZ": "Drizzle",
            "FZFG": "Freezing fog",
        }
        coverage_labels = {
            "FEW": "few",
            "SCT": "scattered",
            "BKN": "broken",
            "OVC": "overcast",
        }

        parts_list = []
        for wx, cov, hgt in matches:
            wx_label = wx_labels.get(wx, wx)
            cov_label = coverage_labels.get(cov, cov)
            height_ft = int(hgt) * 100
            parts_list.append(f"{wx_label} {cov_label} at {height_ft} feet")

        if parts_list:
            decoded.setdefault("Obscuration", "; ".join(parts_list))

    def _parse_pirep_cloud_layers(self, remarks: str, decoded: Dict) -> None:
        """Parse PIREP cloud-layer remarks."""
        if "PIREP" not in remarks or "CLD BASE" not in remarks:
            return

        context = ""
        context_match = re.search(r"\bPIREP\s+(ON\s+[A-Z]+)\b", remarks)
        if context_match:
            context = f"{context_match.group(1).lower()}: "

        layers: List[str] = []
        pattern = re.compile(
            r"\b(\d(?:ST|ND|RD|TH))\s+CLD\s+BASE\s+(\d{3}|///)\s+TOP\s+(\d{3}|///)\b"
        )
        for match in pattern.finditer(remarks):
            ordinal, base, top = match.groups()
            base_text = (
                "unknown base" if base == "///" else f"base {int(base) * 100} ft"
            )
            top_text = "unknown top" if top == "///" else f"top {int(top) * 100} ft"
            layers.append(
                f"{context}{ordinal.lower()} cloud layer {base_text}, {top_text}"
            )

        if layers:
            decoded["PIREP Clouds"] = layers
