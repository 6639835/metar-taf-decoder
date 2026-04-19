"""TAF convenience wrapper returned by :class:`weather_decoder.TafDecoder`."""

from __future__ import annotations

from ..formatters.taf_formatter import TafFormatter
from ..models import TafReport


class TafData(TafReport):
    """Public TAF report wrapper with formatting helpers.

    ``TafData`` subclasses :class:`weather_decoder.models.TafReport` so the
    decoded forecast model stays structured while keeping a friendly ``str()``
    representation for CLI and library use.
    """

    def __str__(self) -> str:  # pragma: no cover - formatting wrapper
        return TafFormatter.format(self)
