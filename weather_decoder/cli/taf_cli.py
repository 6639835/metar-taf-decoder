"""Command line interface for TAF decoder"""

import argparse
import sys

from ..core.taf_decoder import TafDecoder


class TafCLI:
    """Command line interface for TAF decoding"""

    def __init__(self):
        self.decoder = TafDecoder()

    def run(self, args=None):
        """Run the TAF CLI"""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)

        if parsed_args.file:
            self._process_file(parsed_args.file)
        elif parsed_args.taf:
            self._process_single_taf(parsed_args.taf)
        else:
            self._interactive_mode()

    def _create_parser(self):
        """Create argument parser"""
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

        parser.add_argument("--version", action="version", version="TAF Decoder 1.1.0")

        return parser

    def _process_single_taf(self, taf_string):
        """Process a single TAF string"""
        try:
            decoded = self.decoder.decode(taf_string)
            print(decoded)
        except Exception as e:
            print(f"Error decoding TAF: {e}", file=sys.stderr)
            sys.exit(1)

    def _process_file(self, filename):
        """Process TAF strings from a file"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    taf = line.strip()
                    if taf and not taf.startswith("#"):  # Skip empty lines and comments
                        try:
                            decoded = self.decoder.decode(taf)
                            print(f"\n{'='*60}")
                            print(f"TAF #{line_num}")
                            print("=" * 60)
                            print(decoded)
                        except Exception as e:
                            print(f"Error decoding TAF on line {line_num}: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{filename}': {e}", file=sys.stderr)
            sys.exit(1)

    def _interactive_mode(self):
        """Run in interactive mode"""
        print("TAF Decoder 1.1.0 - Interactive Mode")
        print("Enter TAF strings to decode (press Ctrl+C to exit):")
        print("Example: TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
        print()

        try:
            while True:
                try:
                    taf = input("> ").strip()
                    if taf:
                        if taf.lower() in ["quit", "exit", "q"]:
                            break
                        decoded = self.decoder.decode(taf)
                        print(decoded)
                        print()
                except Exception as e:
                    print(f"Error: {e}")
                    print("Please try again with a valid TAF string.")
                    print()
        except KeyboardInterrupt:
            print("\nExiting...")
        except EOFError:
            print("\nExiting...")


def main():
    """Main entry point for TAF CLI"""
    cli = TafCLI()
    cli.run()
