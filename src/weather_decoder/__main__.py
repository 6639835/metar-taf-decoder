"""Package entry point for running the decoders via ``python -m weather_decoder``."""

from __future__ import annotations

import sys

from .cli.metar_cli import MetarCLI
from .cli.taf_cli import TafCLI


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"metar", "taf"}:
        print("Usage: python -m weather_decoder [metar|taf] <report or options>")
        raise SystemExit(2)

    command, *args = sys.argv[1:]
    if command == "metar":
        MetarCLI().run(args)
        return

    TafCLI().run(args)


if __name__ == "__main__":
    main()
