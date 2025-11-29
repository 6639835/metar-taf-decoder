"""Command line interface for METAR decoder"""

import argparse
import sys

from ..core.metar_decoder import MetarDecoder


class MetarCLI:
    """Command line interface for METAR decoding"""

    def __init__(self):
        self.decoder = MetarDecoder()

    def run(self, args=None):
        """Run the METAR CLI"""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        if parsed_args.file:
            self._process_file(parsed_args.file)
        elif parsed_args.metar:
            self._process_single_metar(parsed_args.metar)
        else:
            self._interactive_mode()

    def _create_parser(self):
        """Create argument parser"""
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

        parser.add_argument("--version", action="version", version="METAR Decoder 1.1.1")

        return parser

    def _process_single_metar(self, metar_string):
        """Process a single METAR string"""
        try:
            decoded = self.decoder.decode(metar_string)
            print(decoded)
        except Exception as e:
            print(f"Error decoding METAR: {e}", file=sys.stderr)
            sys.exit(1)

    def _process_file(self, filename):
        """Process METAR strings from a file"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    metar = line.strip()
                    if metar and not metar.startswith("#"):  # Skip empty lines and comments
                        try:
                            decoded = self.decoder.decode(metar)
                            print(f"\n{'='*60}")
                            print(f"METAR #{line_num}")
                            print("=" * 60)
                            print(decoded)
                        except Exception as e:
                            print(f"Error decoding METAR on line {line_num}: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{filename}': {e}", file=sys.stderr)
            sys.exit(1)

    def _interactive_mode(self):
        """Run in interactive mode"""
        print("METAR Decoder 1.1.1 - Interactive Mode")
        print("Enter METAR strings to decode (press Ctrl+C to exit):")
        print("Example: METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
        print()

        try:
            while True:
                try:
                    metar = input("> ").strip()
                    if metar:
                        if metar.lower() in ["quit", "exit", "q"]:
                            break
                        decoded = self.decoder.decode(metar)
                        print(decoded)
                        print()
                except Exception as e:
                    print(f"Error: {e}")
                    print("Please try again with a valid METAR string.")
                    print()
        except KeyboardInterrupt:
            print("\nExiting...")
        except EOFError:
            print("\nExiting...")


def main():
    """Main entry point for METAR CLI"""
    cli = MetarCLI()
    cli.run()
