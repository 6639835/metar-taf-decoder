"""Public import surface."""

from weather_decoder import (
    MetarReport,
    TafForecastPeriod,
    TafReport,
    Visibility,
    Wind,
    decode_metar,
    decode_taf,
)
from weather_decoder.constants.common import WEATHER_PHENOMENA
from weather_decoder.formatters.common import format_wind
from weather_decoder.parsers.remarks import RemarksParser, parse_remarks


def test_package_root_exports_decode_entry_points_and_models():
    assert callable(decode_metar)
    assert callable(decode_taf)
    assert MetarReport.__name__ == "MetarReport"
    assert TafReport.__name__ == "TafReport"
    assert TafForecastPeriod.__name__ == "TafForecastPeriod"
    assert Wind.__name__ == "Wind"
    assert Visibility.__name__ == "Visibility"


def test_current_public_modules_import():
    assert WEATHER_PHENOMENA
    assert callable(format_wind)
    assert RemarksParser.__name__ == "RemarksParser"
    assert callable(parse_remarks)


def test_decode_helpers_return_report_data():
    metar = "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"
    taf = "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250"

    assert decode_metar(metar).station_id == "KJFK"
    assert decode_taf(taf).station_id == "KJFK"
