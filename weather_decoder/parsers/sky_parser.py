"""Sky conditions parser."""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import SkyCondition
from ..utils.constants import SKY_CONDITIONS, TREND_TYPES
from ..utils.patterns import SKY_PATTERN
from .base_parser import BaseParser, StopConditionMixin
from .token_stream import TokenStream


class SkyParser(BaseParser[SkyCondition], StopConditionMixin):
    """Parser for sky conditions in METAR and TAF reports."""

    stop_tokens = TREND_TYPES

    def parse(self, token: str) -> Optional[SkyCondition]:
        if token in ["SKC", "CLR", "NSC", "NCD"]:
            return SkyCondition(coverage=token, height=None)

        match = re.match(SKY_PATTERN, token)
        if not match:
            return None

        coverage = match.group(1)
        height_str = match.group(2)
        cloud_type = match.group(3) or None

        if height_str == "///":
            height = None
            unknown_height = True
        else:
            height = int(height_str) * 100
            unknown_height = False

        return SkyCondition(
            coverage=coverage,
            height=height,
            unknown_height=unknown_height,
            cb=cloud_type == "CB",
            tcu=cloud_type == "TCU",
            unknown_type=cloud_type == "///",
        )

    def extract_all(self, stream: TokenStream) -> List[SkyCondition]:
        sky_conditions: List[SkyCondition] = []
        i = 0
        while i < len(stream.tokens):
            if self.should_stop(stream.tokens[i]):
                break

            sky = self.parse(stream.tokens[i])
            if sky is not None:
                sky_conditions.append(sky)
                stream.pop(i)
            else:
                i += 1

        return sky_conditions

    @staticmethod
    def get_sky_description(sky_type: str) -> str:
        return SKY_CONDITIONS.get(sky_type, sky_type)
