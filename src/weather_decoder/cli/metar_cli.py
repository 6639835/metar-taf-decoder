"""Command line interface for METAR decoder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .. import __version__
from ..core.metar_decoder import MetarDecoder
from .common import iter_report_lines, print_section_header


class MetarCLI:
    """Command line interface for METAR decoding."""

    def __init__(self, decoder: Optional[MetarDecoder] = None):
        self.decoder = decoder or MetarDecoder()

    def run(self, args=None) -> None:
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        if parsed_args.file:
            self._process_file(Path(parsed_args.file))
            return

        if parsed_args.metar:
            self._process_single_metar(parsed_args.metar)
            return

        self._interactive_mode()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="METAR Decoder - Parse and decode METAR weather reports",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
  %(prog)s -f metars.txt
  %(prog)s  # Interactive mode
            """,
        )

        parser.add_argument("metar", nargs="?", help="Raw METAR string to decode")
        parser.add_argument("-f", "--file", help="File containing METAR strings (one per line)")
        parser.add_argument("--version", action="version", version=f"METAR Decoder {__version__}")

        return parser

    def _process_single_metar(self, metar_string: str) -> None:
        try:
            decoded = self.decoder.decode(metar_string)
            print(decoded)
        except Exception as exc:
            print(f"Error decoding METAR: {exc}", file=sys.stderr)
            sys.exit(1)

    def _process_file(self, filename: Path) -> None:
        try:
            for line_num, metar in iter_report_lines(filename):
                try:
                    decoded = self.decoder.decode(metar)
                    print_section_header("METAR", line_num)
                    print(decoded)
                except Exception as exc:
                    print(f"Error decoding METAR on line {line_num}: {exc}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"Error reading file '{filename}': {exc}", file=sys.stderr)
            sys.exit(1)

    def _interactive_mode(self) -> None:
        print(f"METAR Decoder {__version__} - Interactive Mode")
        print("Enter METAR strings to decode (press Ctrl+C to exit):")
        print("Example: METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        print()

        try:
            while True:
                try:
                    metar = input("> ").strip()
                    if not metar:
                        continue
                    if metar.lower() in ["quit", "exit", "q"]:
                        break
                    decoded = self.decoder.decode(metar)
                    print(decoded)
                    print()
                except Exception as exc:
                    print(f"Error: {exc}")
                    print("Please try again with a valid METAR string.")
                    print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")


def main() -> None:
    cli = MetarCLI()
    cli.run()
