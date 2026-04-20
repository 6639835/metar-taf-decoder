"""Lightning remarks handlers."""

from __future__ import annotations

from .common import (
    RemarksCommon,
    Dict,
    LIGHTNING_FREQUENCY,
    LIGHTNING_TYPES,
    List,
    re,
)


class LightningRemarksMixin(RemarksCommon):
    def _parse_lightning(self, remarks: str, decoded: Dict) -> None:
        """Parse lightning information

        Format: [FRQ|OCNL|CONS] LTG[IC|CC|CG|CA]* [DSNT|VC|OHD] [directions]
        """
        tokens = remarks.split()
        descriptions: List[str] = []
        i = 0
        while i < len(tokens):
            freq = None
            if (
                tokens[i] in LIGHTNING_FREQUENCY
                and i + 1 < len(tokens)
                and tokens[i + 1].startswith("LTG")
            ):
                freq = tokens[i]
                ltg_token = tokens[i + 1]
                j = i + 2
            elif tokens[i].startswith("LTG"):
                ltg_token = tokens[i]
                j = i + 1
            else:
                i += 1
                continue

            location_tokens: List[str] = []
            while j < len(tokens) and self._is_location_token(tokens[j]):
                location_tokens.append(tokens[j])
                j += 1

            ltg_parts = []
            if freq:
                ltg_parts.append(LIGHTNING_FREQUENCY.get(freq, freq))

            ltg_types = ltg_token[3:]
            if ltg_types:
                types = []
                idx = 0
                while idx + 1 < len(ltg_types):
                    lt = ltg_types[idx : idx + 2]
                    if lt in LIGHTNING_TYPES:
                        types.append(LIGHTNING_TYPES[lt])
                    idx += 2
                ltg_parts.append(
                    " and ".join(types) + " lightning" if types else "lightning"
                )
            else:
                ltg_parts.append("lightning")

            location_text = self._format_location_tokens(location_tokens)
            if location_text:
                ltg_parts.append(location_text)

            descriptions.append(" ".join(ltg_parts))
            i = j

        if descriptions:
            decoded["Lightning"] = "; ".join(descriptions)

    def _parse_thunderstorm_location(self, remarks: str, decoded: Dict) -> None:
        """Parse thunderstorm location and movement

        Format: TS [DSNT|VC|OHD|ALQDS] [AND] [directions] [MOV direction]
        Examples:
          - TS OHD MOV NE
          - TS DSNT NW
          - TS OHD AND NW -N-E MOV NE (overhead and northwest through north to east, moving northeast)
        """
        tokens = remarks.split()
        descriptions: List[str] = []
        i = 0
        while i < len(tokens):
            intensity = None
            if (
                tokens[i] in {"FBL", "MOD", "HVY"}
                and i + 1 < len(tokens)
                and tokens[i + 1] == "TS"
            ):
                intensity = tokens[i]
                j = i + 2
            elif tokens[i] == "TS":
                j = i + 1
            else:
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

            parts = ["Thunderstorm"]
            if intensity:
                parts.append(
                    {"FBL": "feeble", "MOD": "moderate", "HVY": "heavy"}[intensity]
                )

            location_text = self._format_location_tokens(location_tokens)
            if location_text:
                parts.append(location_text)

            descriptions.append(" ".join(parts))
            i = j

        if descriptions:
            decoded["Thunderstorm Location"] = "; ".join(dict.fromkeys(descriptions))
