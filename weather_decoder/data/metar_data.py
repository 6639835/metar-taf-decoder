"""METAR convenience wrapper returned by :class:`weather_decoder.MetarDecoder`."""

from __future__ import annotations

from ..formatters.common import format_visibility, format_wind
from ..formatters.metar_formatter import MetarFormatter
from ..models import MetarReport


class MetarData(MetarReport):
    """Public METAR report wrapper with formatting helpers.

    ``MetarData`` subclasses :class:`weather_decoder.models.MetarReport` so the
    structured model fields remain available while preserving the printable API
    used by the CLI and README examples.
    """

    def __str__(self) -> str:  # pragma: no cover - formatting wrapper
        return MetarFormatter.format(self)

    def wind_text(self) -> str:
        return format_wind(self.wind)

    def visibility_text(self) -> str:
        return format_visibility(self.visibility)
