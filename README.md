# Weather Decoder 1.0

A comprehensive, modular Python library for parsing and decoding aviation weather reports (METAR and TAF).

## Features

- **METAR Decoder**: Parse Meteorological Terminal Air Reports
- **TAF Decoder**: Parse Terminal Aerodrome Forecasts  
- **Modular Architecture**: Clean, maintainable code with specialized parsers
- **Command Line Interface**: Easy-to-use CLI tools
- **Comprehensive Parsing**: Handles wind, visibility, weather phenomena, sky conditions, and more
- **Remarks Decoding**: Intelligent parsing of remarks sections
- **Multiple Formats**: Support for various international weather report formats

## Installation

```bash
pip install -e .
```

## Quick Start

### Python API

```python
from weather_decoder import MetarDecoder, TafDecoder

# Decode METAR
metar_decoder = MetarDecoder()
metar_data = metar_decoder.decode("METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992")
print(metar_data)

# Decode TAF
taf_decoder = TafDecoder()
taf_data = taf_decoder.decode("TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250")
print(taf_data)
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

## Architecture

The Weather Decoder 1.0 features a clean, modular architecture:

```
weather_decoder/
├── core/           # Main decoder classes
├── data/           # Data classes for parsed reports
├── parsers/        # Specialized component parsers
├── utils/          # Constants, patterns, and formatters
└── cli/            # Command line interfaces
```

### Components

- **Core Decoders**: Orchestrate the parsing process
- **Specialized Parsers**: Handle specific weather components (wind, visibility, etc.)
- **Data Classes**: Structured representation of parsed data
- **Utilities**: Shared constants, patterns, and formatting functions
- **CLI**: User-friendly command line interfaces

## Benefits of the Modular Design

1. **Maintainability**: Each parser handles a specific component
2. **Testability**: Components can be tested in isolation
3. **Extensibility**: Easy to add new parsers or modify existing ones
4. **Reusability**: Parsers can be used independently
5. **Clarity**: Clear separation of concerns

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
- Pressure settings (QNH)
- Remarks parsing

## Migration from Version 1.x

The new modular structure maintains API compatibility while providing better organization:

```python
# Old way (still works)
from weather_decoder import MetarDecoder, TafDecoder

# New way (recommended for advanced usage)
from weather_decoder.core.metar_decoder import MetarDecoder
from weather_decoder.parsers.wind_parser import WindParser
```

## Contributing

Contributions are welcome! The modular architecture makes it easy to:

1. Add new parsers for additional weather components
2. Improve existing parsers
3. Add support for new weather report formats
4. Enhance the CLI tools

## License

MIT License - see LICENSE file for details.
