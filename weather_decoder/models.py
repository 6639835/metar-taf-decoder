"""Data models for decoded METAR and TAF reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Wind:
    direction: Optional[int]
    speed: int
    unit: str
    gust: Optional[int] = None
    is_variable: bool = False
    variable_range: Optional[Tuple[int, int]] = None
    is_above: bool = False


@dataclass(frozen=True)
class DirectionalVisibility:
    value: int
    direction: str


@dataclass(frozen=True)
class MinimumVisibility:
    value: int


@dataclass(frozen=True)
class Visibility:
    value: float
    unit: str
    is_cavok: bool = False
    is_less_than: bool = False
    is_greater_than: bool = False
    direction: Optional[str] = None
    directional_visibility: Optional[DirectionalVisibility] = None
    minimum_visibility: Optional[MinimumVisibility] = None
    ndv: bool = False


@dataclass(frozen=True)
class RunwayVisualRange:
    runway: str
    visual_range: int
    unit: str
    is_less_than: bool = False
    is_more_than: bool = False
    variable_range: Optional[int] = None
    variable_less_than: bool = False
    variable_more_than: bool = False
    trend: Optional[str] = None


@dataclass(frozen=True)
class RunwayState:
    runway: str
    deposit: str
    contamination: str
    depth: str
    braking: str
    raw: str


@dataclass(frozen=True)
class WeatherPhenomenon:
    intensity: Optional[str] = None
    descriptor: Optional[str] = None
    phenomena: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SkyCondition:
    coverage: str
    height: Optional[int]
    unknown_height: bool = False
    cb: bool = False
    tcu: bool = False
    unknown_type: bool = False


@dataclass(frozen=True)
class Pressure:
    value: float
    unit: str


@dataclass(frozen=True)
class WindShear:
    kind: str
    description: str
    runway: Optional[str] = None
    raw: Optional[str] = None


@dataclass(frozen=True)
class TrendTime:
    from_time: Optional[str] = None
    until_time: Optional[str] = None
    at_time: Optional[str] = None


@dataclass(frozen=True)
class Trend:
    kind: str
    description: str
    raw: str
    time: Optional[TrendTime] = None
    changes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MilitaryColorCode:
    code: str
    description: str


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class TemperatureForecast:
    kind: str
    value: int
    time: datetime


@dataclass
class TafForecastPeriod:
    change_type: str
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    wind: Optional[Wind] = None
    visibility: Optional[Visibility] = None
    weather: List[WeatherPhenomenon] = field(default_factory=list)
    sky: List[SkyCondition] = field(default_factory=list)
    qnh: Optional[Pressure] = None
    temperatures: List[TemperatureForecast] = field(default_factory=list)
    unparsed_tokens: List[str] = field(default_factory=list)
    probability: Optional[int] = None


@dataclass
class MetarReport:
    raw_metar: str
    report_type: str
    station_id: str
    observation_time: datetime
    is_automated: bool
    is_nil: bool
    maintenance_needed: bool
    wind: Optional[Wind]
    visibility: Optional[Visibility]
    runway_visual_ranges: List[RunwayVisualRange] = field(default_factory=list)
    runway_states: List[RunwayState] = field(default_factory=list)
    weather: List[WeatherPhenomenon] = field(default_factory=list)
    sky: List[SkyCondition] = field(default_factory=list)
    temperature: Optional[float] = None
    dewpoint: Optional[float] = None
    altimeter: Optional[Pressure] = None
    windshear: List[WindShear] = field(default_factory=list)
    trends: List[Trend] = field(default_factory=list)
    remarks: str = ""
    remarks_decoded: Dict[str, object] = field(default_factory=dict)
    military_color_codes: List[MilitaryColorCode] = field(default_factory=list)


@dataclass
class TafReport:
    raw_taf: str
    station_id: str
    issue_time: datetime
    valid_period: TimeRange
    forecast_periods: List[TafForecastPeriod]
    remarks: str = ""
    remarks_decoded: Dict[str, object] = field(default_factory=dict)
