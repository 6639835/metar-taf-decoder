"""METAR Data class for holding decoded METAR information"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from ..formatters.common import format_visibility, format_wind
from ..formatters.metar_formatter import MetarFormatter


@dataclass
class MetarData:
    """Class to hold decoded METAR data
    
    This is a pure data container. Formatting logic is handled by MetarFormatter.
    """

    raw_metar: str
    metar_type: str
    station_id: str
    observation_time: datetime
    auto: bool
    is_nil: bool  # NIL indicates a missing report
    maintenance_needed: bool  # $ indicator - station needs maintenance
    wind: Dict
    visibility: Dict
    runway_visual_range: List[Dict]
    runway_conditions: List[Dict]
    runway_state_reports: List[Dict]  # MOTNE format runway reports from main body
    weather_groups: List[Dict]
    sky_conditions: List[Dict]
    temperature: float
    dewpoint: Optional[float]  # Can be None if not available
    altimeter: Dict
    windshear: List[Dict]  # Changed from List[str] to List[Dict] for structured data
    trends: List[Dict]
    remarks: str
    remarks_decoded: Dict
    military_color_codes: List[Dict]

    def __str__(self) -> str:
        """Return a human-readable string of the decoded METAR
        
        Delegates to MetarFormatter for the actual formatting.
        """
        return MetarFormatter.format(self)

    def wind_text(self) -> str:
        """Format wind information into a readable string"""
        return format_wind(self.wind)

    def visibility_text(self) -> str:
        """Format visibility information into a readable string"""
        return format_visibility(self.visibility)
