"""Command line interface for TAF decoder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .. import __version__
from ..core.taf_decoder import TafDecoder
from .common import iter_report_lines, print_section_header


class TafCLI:
    """Command line interface for TAF decoding."""

    def __init__(self, decoder: Optional[TafDecoder] = None):
        self.decoder = decoder or TafDecoder()

    def run(self, args=None) -> None:
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        if parsed_args.file:
            self._process_file(Path(parsed_args.file))
            return

        if parsed_args.taf:
            self._process_single_taf(parsed_args.taf)
            return

        self._interactive_mode()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="TAF Decoder - Parse and decode TAF weather reports",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"
  %(prog)s -f tafs.txt
  %(prog)s  # Interactive mode
            """,
        )

        parser.add_argument("taf", nargs="?", help="Raw TAF string to decode")
        parser.add_argument("-f", "--file", help="File containing TAF strings (one per line)")
        parser.add_argument("--version", action="version", version=f"TAF Decoder {__version__}")

        return parser

    def _process_single_taf(self, taf_string: str) -> None:
        try:
            decoded = self.decoder.decode(taf_string)
            print(decoded)
        except Exception as exc:
            print(f"Error decoding TAF: {exc}", file=sys.stderr)
            sys.exit(1)

    def _process_file(self, filename: Path) -> None:
        try:
            for line_num, taf in iter_report_lines(filename):
                try:
                    decoded = self.decoder.decode(taf)
                    print_section_header("TAF", line_num)
                    print(decoded)
                except Exception as exc:
                    print(f"Error decoding TAF on line {line_num}: {exc}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"Error reading file '{filename}': {exc}", file=sys.stderr)
            sys.exit(1)

    def _interactive_mode(self) -> None:
        print(f"TAF Decoder {__version__} - Interactive Mode")
        print("Enter TAF strings to decode (press Ctrl+C to exit):")
        print("Example: TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        print()

        try:
            while True:
                try:
                    taf = input("> ").strip()
                    if not taf:
                        continue
                    if taf.lower() in ["quit", "exit", "q"]:
                        break
                    decoded = self.decoder.decode(taf)
                    print(decoded)
                    print()
                except Exception as exc:
                    print(f"Error: {exc}")
                    print("Please try again with a valid TAF string.")
                    print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")


def main() -> None:
    cli = TafCLI()
    cli.run()
