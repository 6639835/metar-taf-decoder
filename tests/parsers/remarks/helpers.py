"""Helpers for remarks parser tests."""

BASE = "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992"


def rmk(remark_text: str) -> str:
    """Return a full METAR string with the given RMK section appended."""
    return f"{BASE} RMK {remark_text}"
