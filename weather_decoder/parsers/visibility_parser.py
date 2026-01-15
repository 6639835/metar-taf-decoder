"""Visibility information parser."""

from __future__ import annotations

import re
from typing import Optional

from ..models import DirectionalVisibility, MinimumVisibility, Visibility
from .base_parser import BaseParser
from .token_stream import TokenStream


class VisibilityParser(BaseParser[Visibility]):
    """Parser for visibility information in METAR and TAF reports."""

    DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def parse(self, token: str) -> Optional[Visibility]:
        if token == "CAVOK":
            return Visibility(value=9999, unit="M", is_cavok=True)

        dir_match = re.match(r"^(\d{4})(N|NE|E|SE|S|SW|W|NW)$", token)
        if dir_match:
            return Visibility(
                value=int(dir_match.group(1)),
                unit="M",
                direction=dir_match.group(2),
            )

        if len(token) == 4 and token.isdigit():
            value = int(token)
            return Visibility(
                value=value,
                unit="M",
                is_less_than=value == 0,
            )

        if token.endswith("NDV"):
            numeric_part = token[:-3]
            if numeric_part.isdigit() and len(numeric_part) == 4:
                return Visibility(
                    value=int(numeric_part),
                    unit="M",
                    ndv=True,
                )

        sm_match = re.match(r"^([PM])?(\d+)(?:/(\d+))?SM$", token)
        if sm_match:
            return self._parse_sm_visibility(sm_match)

        return None

    def extract(self, stream: TokenStream) -> Optional[Visibility]:
        for i, token in enumerate(stream.tokens):
            result = self.parse(token)
            if result is not None:
                stream.pop(i)

                if result.unit == "M" and not result.is_cavok:
                    result = self._check_additional_visibility(stream, i, result)

                return result

            if token.isdigit() and i + 1 < len(stream.tokens):
                frac_match = re.match(r"^(\d+)/(\d+)SM$", stream.tokens[i + 1])
                if frac_match:
                    whole = int(token)
                    numerator = int(frac_match.group(1))
                    denominator = int(frac_match.group(2))
                    stream.pop(i)
                    stream.pop(i)
                    return Visibility(value=whole + (numerator / denominator), unit="SM")

        return None

    def _parse_sm_visibility(self, match: re.Match) -> Visibility:
        modifier = match.group(1)
        numerator = int(match.group(2))
        denominator = int(match.group(3)) if match.group(3) else 1

        return Visibility(
            value=numerator / denominator,
            unit="SM",
            is_greater_than=modifier == "P",
            is_less_than=modifier == "M",
        )

    def _check_additional_visibility(self, stream: TokenStream, index: int, result: Visibility) -> Visibility:
        if index >= len(stream.tokens):
            return result

        next_token = stream.tokens[index]
        next_dir_match = re.match(r"^(\d{4})(N|NE|E|SE|S|SW|W|NW)$", next_token)
        if next_dir_match:
            stream.pop(index)
            return Visibility(
                value=result.value,
                unit=result.unit,
                is_cavok=result.is_cavok,
                is_less_than=result.is_less_than,
                is_greater_than=result.is_greater_than,
                direction=result.direction,
                directional_visibility=DirectionalVisibility(
                    value=int(next_dir_match.group(1)),
                    direction=next_dir_match.group(2),
                ),
                minimum_visibility=result.minimum_visibility,
                ndv=result.ndv,
            )

        if len(next_token) == 4 and next_token.isdigit():
            stream.pop(index)
            return Visibility(
                value=result.value,
                unit=result.unit,
                is_cavok=result.is_cavok,
                is_less_than=result.is_less_than,
                is_greater_than=result.is_greater_than,
                direction=result.direction,
                directional_visibility=result.directional_visibility,
                minimum_visibility=MinimumVisibility(value=int(next_token)),
                ndv=result.ndv,
            )

        return result
