"""METAR report data container and formatting helpers."""

from __future__ import annotations

from ..formatters.common import format_visibility, format_wind
from ..formatters.metar_formatter import MetarFormatter
from ..models import MetarReport


class MetarData(MetarReport):
    """Decoded METAR report with convenience formatting helpers."""

    def __str__(self) -> str:  # pragma: no cover - formatting wrapper
        return MetarFormatter.format(self)

    def wind_text(self) -> str:
        return format_wind(self.wind)

    def visibility_text(self) -> str:
        return format_visibility(self.visibility)
