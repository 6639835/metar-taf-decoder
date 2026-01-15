"""TAF report data container and formatting helpers."""

from __future__ import annotations

from ..formatters.taf_formatter import TafFormatter
from ..models import TafReport


class TafData(TafReport):
    """Decoded TAF report with convenience formatting helpers."""

    def __str__(self) -> str:  # pragma: no cover - formatting wrapper
        return TafFormatter.format(self)
