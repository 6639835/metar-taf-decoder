"""Deprecated compatibility shim for the remarks parser.

Import from ``weather_decoder.parsers.remarks`` instead.
"""

from .remarks import RemarksParser, parse_remarks

__all__ = ["RemarksParser", "parse_remarks"]
