#!/usr/bin/env python3
"""
METAR Decoder Entry Point - Modern modular version
"""

from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parent / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from weather_decoder.cli.metar_cli import main

if __name__ == "__main__":
    main()
