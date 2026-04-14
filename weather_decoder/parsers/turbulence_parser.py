"""TAF turbulence forecast parser.

Supports two formats:

1. ICAO Annex 3 / WMO FM 51 numeric format — 5BHHHHH
   Example tokens: ``520610``  (6 digits starting with '5')

2. Plain-English TAF format — [+|-]TURB/HH [/HHH]
   This format uses *two* tokens when the top altitude is present.
   Example token pairs: ``+TURB/20`` ``/050`` or standalone ``TURB/10``.

In both cases the parser removes the matched tokens from the stream and
returns a list of :class:`~weather_decoder.models.TurbulenceForecast` objects.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import TurbulenceForecast
from .token_stream import TokenStream

# ---------------------------------------------------------------------------
# Lookup tables (ICAO Annex 3, Appendix 5, Table A5-1)
# ---------------------------------------------------------------------------

_INTENSITY_MAP = {
    "0": "none",
    "1": "light",
    "2": "moderate",  # moderate in cloud
    "3": "moderate",  # moderate in clear air
    "4": "moderate",  # moderate — other
    "5": "severe",
    "6": "severe",  # severe in clear air
    "7": "severe",  # severe — other
    "8": "extreme",
}

# Codes 2,5 are in-cloud; 3,6 are clear-air (CAT)
_IN_CLOUD_MAP = {
    "0": False,
    "1": False,
    "2": True,
    "3": False,
    "4": False,
    "5": True,
    "6": False,
    "7": False,
    "8": False,
}

# Numeric turbulence group: 5 + type/intensity digit + 2-digit base (hundreds ft) + 2-digit depth (hundreds ft)
_NUMERIC_RE = re.compile(r"^5(\d)(\d{2})(\d{2})$")

# Plain-English turbulence group: optional intensity prefix, TURB, /HH
_PLAIN_RE = re.compile(r"^([+-])?TURB/(\d{2})$", re.IGNORECASE)

# Optional second token for plain-English top altitude: /HHH
_TOP_RE = re.compile(r"^/(\d{3})$")


class TurbulenceParser:
    """Parser for TAF turbulence forecast groups."""

    def parse_numeric(self, token: str) -> Optional[TurbulenceForecast]:
        """Try to parse *token* as a numeric turbulence group (5BHHHHH)."""
        m = _NUMERIC_RE.match(token)
        if not m:
            return None

        type_code = m.group(1)
        base_hundreds = int(m.group(2))
        depth_hundreds = int(m.group(3))

        intensity = _INTENSITY_MAP.get(type_code, "unknown")
        in_cloud = _IN_CLOUD_MAP.get(type_code, False)
        base_ft = base_hundreds * 100
        top_ft = base_ft + depth_hundreds * 100

        return TurbulenceForecast(
            intensity=intensity,
            base_ft=base_ft,
            top_ft=top_ft,
            in_cloud=in_cloud,
            raw=token,
        )

    @staticmethod
    def parse_plain(token: str, next_token: Optional[str] = None) -> Optional[tuple]:
        """Try to parse *token* (and optionally *next_token*) as a plain-text turbulence group.

        Returns a ``(TurbulenceForecast, consumed_next)`` tuple, or ``None`` if *token*
        does not match the plain format.  ``consumed_next`` is ``True`` when the second
        token was consumed for the top altitude.
        """
        m = _PLAIN_RE.match(token)
        if not m:
            return None

        prefix = m.group(1)
        base_hundreds = int(m.group(2))

        if prefix == "+":
            intensity = "severe"
        elif prefix == "-":
            intensity = "light"
        else:
            intensity = "moderate"

        base_ft = base_hundreds * 100
        top_ft: Optional[int] = None
        consumed_next = False

        if next_token is not None:
            top_m = _TOP_RE.match(next_token)
            if top_m:
                top_ft = int(top_m.group(1)) * 100
                consumed_next = True

        raw = token if not consumed_next else f"{token} {next_token}"

        return (
            TurbulenceForecast(
                intensity=intensity,
                base_ft=base_ft,
                top_ft=top_ft,
                in_cloud=False,
                raw=raw,
            ),
            consumed_next,
        )

    def extract_all(self, stream: TokenStream) -> List[TurbulenceForecast]:
        """Extract all turbulence groups from *stream*, consuming matched tokens."""
        turb_list: List[TurbulenceForecast] = []
        i = 0
        while i < len(stream.tokens):
            token = stream.tokens[i]

            # Try numeric format first
            result = self.parse_numeric(token)
            if result is not None:
                turb_list.append(result)
                stream.pop(i)
                continue

            # Try plain-English format (possibly two-token)
            next_token = stream.tokens[i + 1] if i + 1 < len(stream.tokens) else None
            plain = self.parse_plain(token, next_token)
            if plain is not None:
                forecast, consumed_next = plain
                turb_list.append(forecast)
                stream.pop(i)  # remove TURB/HH
                if consumed_next:
                    stream.pop(i)  # remove /HHH (now at position i after first pop)
                continue

            i += 1

        return turb_list
