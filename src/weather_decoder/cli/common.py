"""Shared CLI helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple


def iter_report_lines(path: Path) -> Iterator[Tuple[int, str]]:
    """Yield non-empty, non-comment lines from a file."""
    with path.open("r", encoding="utf-8") as handle:
        for line_num, line in enumerate(handle, 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            yield line_num, text


def print_section_header(label: str, line_num: int) -> None:
    divider = "=" * 60
    print(f"\n{divider}")
    print(f"{label} #{line_num}")
    print(divider)
