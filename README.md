# Weather Decoder

[![CI](https://github.com/6639835/metar-taf-decoder/actions/workflows/ci.yml/badge.svg)](https://github.com/6639835/metar-taf-decoder/actions/workflows/ci.yml)
[![Code Quality](https://github.com/6639835/metar-taf-decoder/actions/workflows/code-quality.yml/badge.svg)](https://github.com/6639835/metar-taf-decoder/actions/workflows/code-quality.yml)
[![Security](https://github.com/6639835/metar-taf-decoder/actions/workflows/security.yml/badge.svg)](https://github.com/6639835/metar-taf-decoder/actions/workflows/security.yml)
[![Python versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

A comprehensive, modular Python library for parsing and decoding aviation
weather reports (METAR and TAF).

## Features

- **METAR Decoder**: Parse Meteorological Terminal Air Reports
- **TAF Decoder**: Parse Terminal Aerodrome Forecasts
- **Modular Architecture**: Clean, maintainable code with specialized parsers
- **Command Line Interface**: Easy-to-use CLI tools
- **Comprehensive Parsing**: Handles wind, visibility, weather phenomena, sky conditions, and more
- **Remarks Decoding**: Family-based remarks parsers for automation, pressure, wind, visibility, lightning, precipitation, sky, temperature, and recent weather remarks
- **Multiple Formats**: Support for various international weather report formats
- **Standards Warnings**: Decodes regional formats while surfacing Annex IV,
  ICAO/WMO, FMH-1, CAP 746, and JMA validation warnings when a report uses
  non-template or locally extended syntax

## Installation

```bash
pip install -e .
```

Install the development toolchain:

```bash
pip install -r requirements-dev.txt
```

## Quick Start

### Python API

```python
from weather_decoder import MetarDecoder, TafDecoder, decode_metar, decode_taf

# Convenience functions
metar_report = decode_metar(
    "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
)
taf_report = decode_taf(
    "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"
)

# Reusable decoder instances
metar_decoder = MetarDecoder()
metar_report = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
print(metar_report)
print(metar_report.wind)

taf_decoder = TafDecoder()
taf_report = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
print(taf_report)
print(taf_report.forecast_periods)
```

### Command Line

```bash
# Decode METAR
decode-metar "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"

# Decode TAF
decode-taf "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"

# Process files
decode-metar -f metars.txt
decode-taf -f tafs.txt

# Interactive mode
decode-metar
decode-taf
```

For local development without installing the package, run the package module
with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python -m weather_decoder metar "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
PYTHONPATH=src python -m weather_decoder taf "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"
```

The Makefile provides short wrappers for the same development path:

```bash
make metar ARGS='"METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"'
make taf ARGS='"TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"'
```

## Architecture

The package keeps phase-based top-level boundaries with public entry points at
the package root and implementation details in focused subpackages.

```text
src/
└── weather_decoder/
    ├── __init__.py     # Public decode API and model exports
    ├── __main__.py     # python -m weather_decoder dispatch
    ├── core/           # Main decoder classes
    ├── models.py       # Canonical structured report/component models
    ├── data/           # Convenience wrappers returned by decoders
    ├── parsers/        # Specialized component parsers
    │   └── remarks/    # Ordered remarks dispatcher and family handlers
    ├── validators/     # Cross-field standards validation and warnings
    ├── formatters/     # Human-readable output helpers
    ├── constants/      # Organized code tables and lookup values
    └── cli/            # Command line interfaces
```

### Components

- **Core Decoders**: Orchestrate the parsing process
- **Specialized Parsers**: Handle specific weather components (wind, visibility, etc.)
- **Remarks Parsers**: Keep precedence-sensitive matching centralized in `parsers/remarks/registry.py`
- **Validators**: Apply cross-field standards checks and warning generation
- **Models**: Structured dataclasses for reports and report components
- **Convenience Wrappers**: Printable report objects returned by the decoders
- **Constants and Formatters**: Shared lookup tables, regex patterns, and output helpers
- **CLI**: User-friendly command line interfaces

## Supported Features

### METAR Features
- Station identification
- Observation time
- Wind information (including variable direction and gusts)
- Visibility (including RVR)
- Weather phenomena
- Sky conditions
- Temperature and dewpoint
- Altimeter settings
- Trends
- Comprehensive remarks parsing

### TAF Features
- Station identification and issue time
- Valid periods
- Wind forecasts
- Visibility forecasts
- Weather phenomena forecasts
- Sky condition forecasts
- Temperature forecasts (TX/TN)
- Change groups (TEMPO, BECMG, FM, PROB)
- Local remarks parsing with standards warnings when present

## Public API

The supported public API is exported from `weather_decoder`:

```python
from weather_decoder import MetarDecoder, TafDecoder, decode_metar, decode_taf

report = decode_metar("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
print(report.report_type, report.is_automated)
print(report.wind, report.visibility)
```

The decoder APIs return `MetarData` and `TafData`, convenience wrappers around
the strongly typed `MetarReport` and `TafReport` models. The model dataclasses
are also exported from the package root for consumers that need type annotations.

The parsers are intentionally permissive so regional formats such as FAA
statute-mile visibility and inHg altimeter groups can still be decoded. Check
`report.validation_warnings` when you need Annex IV / ICAO-template compliance.

Prefer the current paths in new code:

```python
from weather_decoder.parsers.remarks import RemarksParser, parse_remarks
from weather_decoder.constants.common import WEATHER_PHENOMENA
from weather_decoder.formatters.common import format_wind
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for
the development workflow, coding standards, and PR expectations. By
participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

The modular architecture makes it easy to:

1. Add new parsers for additional weather components
2. Improve existing parsers
3. Add support for new weather report formats
4. Enhance the CLI tools

To report a security vulnerability, please follow the process described in
[SECURITY.md](SECURITY.md). User-visible changes are tracked in
[CHANGELOG.md](CHANGELOG.md).

## Development

This project uses:

- `ruff` for linting, import sorting, and formatting
- `mypy` for type checking
- `pytest` for tests

Common commands:

```bash
ruff check .
ruff format .
mypy
pytest
```

The tests use a hybrid layout that mirrors major package boundaries:

```text
tests/
├── cli/
├── core/
├── formatters/
├── models/
├── parsers/
│   └── remarks/
├── public_api/
├── validators/
└── fixtures/
    ├── metar/
    └── taf/
```

## License

MIT License - see LICENSE file for details.
