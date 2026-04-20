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
    is_calm: bool = False
    gust_is_above: bool = False


@dataclass(frozen=True)
class DirectionalVisibility:
    value: int
    direction: str


@dataclass(frozen=True)
class MinimumVisibility:
    value: int
    direction: Optional[str] = None


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
    unavailable: bool = False  # AUTO station: //// sentinel (vis not observable)


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
    variable_range_is_less_than: bool = False  # P/M on the variable upper bound
    variable_range_is_more_than: bool = False
    trend: Optional[str] = None


@dataclass(frozen=True)
class RunwayState:
    runway: Optional[str]
    deposit: str
    contamination: str
    depth: str
    braking: str
    raw: str
    all_runways: bool = False
    from_previous_report: bool = False
    cleared: bool = False
    aerodrome_closed: bool = False  # R/SNOCLO: aerodrome closed due to snow


@dataclass(frozen=True)
class WeatherPhenomenon:
    intensity: Optional[str] = None
    descriptor: Optional[str] = None
    phenomena: Tuple[str, ...] = field(default_factory=tuple)
    unavailable: bool = False  # AUTO station: // sentinel (weather not observable)


@dataclass(frozen=True)
class SkyCondition:
    coverage: str
    height: Optional[int]
    unknown_height: bool = False
    cb: bool = False
    tcu: bool = False
    unknown_type: bool = False
    system_unavailable: bool = False  # ////// sentinel: AUTO cloud system not operating


@dataclass(frozen=True)
class Pressure:
    value: float
    unit: str


@dataclass(frozen=True)
class SeaCondition:
    sea_surface_temperature: Optional[int]
    state_of_sea: Optional[str] = None
    significant_wave_height_m: Optional[float] = None
    temperature_missing: bool = False
    state_missing: bool = False
    wave_height_missing: bool = False
    raw: str = ""


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


@dataclass(frozen=True)
class IcingForecast:
    """TAF icing forecast group.

    Supports two encoding formats:

    1. ICAO Annex 3 / WMO FM 51 Appendix 5 numeric group (6ICEHHHH):
       digit 1  = 6 (icing group indicator)
       digit 2  = icing intensity (0=none, 1=light, 2=moderate in cloud,
                                   3=moderate in precipitation, 4=moderate freezing,
                                   5=severe in cloud, 6=severe in precipitation,
                                   7=severe freezing, 8=extreme)
       digit 3  = icing type (0=none/not reported, 1=rime in cloud, 2=mixed in cloud,
                              3=freezing precipitation, 4=clear ice)
       digits 4-5 = base in hundreds of feet
       digit 6  = depth in thousands of feet (1–9 → 1000–9000 ft)

       Example: 620304  — moderate icing, mixed, base 3000 ft, depth 4000 ft → top 7000 ft

    2. Plain-text TAF group (e.g. +ICGHH, -ICGHH):
       intensity prefix: + = heavy/severe, - = light, none = moderate
       ICG = icing indicator
       HH  = height in hundreds of feet
    """

    intensity: str  # "none", "light", "moderate", "severe", "extreme"
    base_ft: int  # base altitude in feet
    top_ft: Optional[int]  # top altitude in feet (base + depth), None if not specified
    icing_type: str  # "none", "rime", "mixed", "freezing precipitation", "clear ice"
    raw: str


@dataclass(frozen=True)
class TurbulenceForecast:
    """TAF turbulence forecast group.

    Supports two encoding formats:

    1. ICAO Annex 3 / WMO FM 51 Appendix 5 numeric group (5BHHHHH):
       digit 1  = 5 (turbulence group indicator)
       digit 2  = turbulence intensity/type (0=none, 1=light, 2=moderate in cloud,
                                             3=moderate in clear air, 4=moderate drz,
                                             5=severe in cloud, 6=severe in clear air,
                                             7=severe freezing, 8=extreme)
       digits 3-4 = base in hundreds of feet
       digits 5-6 = depth in hundreds of feet

       Example: 520610  — moderate turbulence, base 6000 ft, depth 1000 ft → top 7000 ft

    2. Plain-text TAF group (e.g. +TURB/20 /050, -TURB/10):
       intensity prefix: + = severe, - = light, none = moderate
       TURB = turbulence indicator
       /HH  = base in hundreds of feet
       [/HHH] = optional top in hundreds of feet
    """

    intensity: str  # "none", "light", "moderate", "severe", "extreme"
    base_ft: int  # base altitude in feet
    top_ft: Optional[int]  # top altitude in feet (base + depth), None if not specified
    in_cloud: bool  # True when turbulence is in-cloud (not CAT)
    raw: str


@dataclass
class TafForecastPeriod:
    change_type: str
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    wind: Optional[Wind] = None
    visibility: Optional[Visibility] = None
    weather: List[WeatherPhenomenon] = field(default_factory=list)
    sky: List[SkyCondition] = field(default_factory=list)
    temperatures: List[TemperatureForecast] = field(default_factory=list)
    nsw: bool = False
    windshear: List[WindShear] = field(default_factory=list)
    icing: List[IcingForecast] = field(default_factory=list)
    turbulence: List[TurbulenceForecast] = field(default_factory=list)
    unparsed_tokens: List[str] = field(default_factory=list)
    probability: Optional[int] = None
    qualifier: Optional[str] = None


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
    recent_weather: List[WeatherPhenomenon] = field(default_factory=list)
    sky: List[SkyCondition] = field(default_factory=list)
    temperature: Optional[float] = None
    dewpoint: Optional[float] = None
    altimeter: Optional[Pressure] = None
    sea_conditions: List[SeaCondition] = field(default_factory=list)
    windshear: List[WindShear] = field(default_factory=list)
    trends: List[Trend] = field(default_factory=list)
    is_corrected: bool = False
    remarks: str = ""
    remarks_decoded: Dict[str, object] = field(default_factory=dict)
    military_color_codes: List[MilitaryColorCode] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


@dataclass
class TafReport:
    raw_taf: str
    station_id: str
    issue_time: datetime
    valid_period: TimeRange
    forecast_periods: List[TafForecastPeriod]
    report_type: str = "TAF"
    status: str = "NORMAL"
    is_amended: bool = False
    is_corrected: bool = False
    is_cancelled: bool = False
    is_nil: bool = False
    remarks: str = ""
    remarks_decoded: Dict[str, object] = field(default_factory=dict)
    temperature_forecasts: List[TemperatureForecast] = field(default_factory=list)
    previous_valid_period: Optional[TimeRange] = (
        None  # for AMD/COR: stores replaced period
    )
    validation_warnings: List[str] = field(default_factory=list)
