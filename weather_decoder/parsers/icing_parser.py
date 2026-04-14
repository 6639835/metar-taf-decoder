"""TAF icing forecast parser.

Supports two formats:

1. ICAO Annex 3 / WMO FM 51 numeric format — 6ICEHHHH
   Example tokens: ``620304``  (6 digits starting with '6')

2. Plain-English TAF format — [+|-]ICG[H]HH
   Example tokens: ``+ICG30``, ``-ICG10``, ``ICGH20``

In both cases the parser removes the matched tokens from the stream and
returns a list of :class:`~weather_decoder.models.IcingForecast` objects.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import IcingForecast
from .token_stream import TokenStream

# ---------------------------------------------------------------------------
# Lookup tables (ICAO Annex 3, Appendix 5, Table A5-2)
# ---------------------------------------------------------------------------

_INTENSITY_MAP = {
    "0": "none",
    "1": "light",
    "2": "moderate",
    "3": "moderate",  # moderate in precipitation
    "4": "moderate",  # moderate freezing
    "5": "severe",
    "6": "severe",  # severe in precipitation
    "7": "severe",  # severe freezing
    "8": "extreme",
}

_TYPE_MAP = {
    "0": "none",
    "1": "rime",
    "2": "mixed",
    "3": "freezing precipitation",
    "4": "clear ice",
}

# Numeric icing group: 6 + intensity digit + type digit + 2-digit base (hundreds ft) + 1-digit depth (thousands ft)
# The depth digit is optional in some variants, so we allow 5 or 6 digits total.
_NUMERIC_RE = re.compile(r"^6(\d)(\d)(\d{2})(\d)?$")

# Plain-English icing group: optional intensity prefix, ICG or ICGH, 2-digit height
_PLAIN_RE = re.compile(r"^([+-])?ICG[H]?(\d{2})$", re.IGNORECASE)


class IcingParser:
    """Parser for TAF icing forecast groups."""

    def parse(self, token: str) -> Optional[IcingForecast]:
        """Try to parse *token* as an icing group; return ``None`` if not matched."""
        result = self._parse_numeric(token)
        if result is not None:
            return result
        return self._parse_plain(token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_numeric(token: str) -> Optional[IcingForecast]:
        m = _NUMERIC_RE.match(token)
        if not m:
            return None

        intensity_code = m.group(1)
        type_code = m.group(2)
        base_hundreds = int(m.group(3))
        depth_thousands = m.group(4)  # may be None

        intensity = _INTENSITY_MAP.get(intensity_code, "unknown")
        icing_type = _TYPE_MAP.get(type_code, "unknown")
        base_ft = base_hundreds * 100

        top_ft: Optional[int] = None
        if depth_thousands is not None:
            top_ft = base_ft + int(depth_thousands) * 1000

        return IcingForecast(
            intensity=intensity,
            base_ft=base_ft,
            top_ft=top_ft,
            icing_type=icing_type,
            raw=token,
        )

    @staticmethod
    def _parse_plain(token: str) -> Optional[IcingForecast]:
        m = _PLAIN_RE.match(token)
        if not m:
            return None

        prefix = m.group(1)
        height_hundreds = int(m.group(2))

        if prefix == "+":
            intensity = "severe"
        elif prefix == "-":
            intensity = "light"
        else:
            intensity = "moderate"

        base_ft = height_hundreds * 100

        return IcingForecast(
            intensity=intensity,
            base_ft=base_ft,
            top_ft=None,
            icing_type="icing",
            raw=token,
        )

    def extract_all(self, stream: TokenStream) -> List[IcingForecast]:
        """Extract all icing groups from *stream*, consuming matched tokens."""
        icing_list: List[IcingForecast] = []
        i = 0
        while i < len(stream.tokens):
            result = self.parse(stream.tokens[i])
            if result is not None:
                icing_list.append(result)
                stream.pop(i)
            else:
                i += 1
        return icing_list
