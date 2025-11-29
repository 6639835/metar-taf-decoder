"""TAF Data class for holding decoded TAF information"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from ..formatters.taf_formatter import TafFormatter


@dataclass
class TafData:
    """Class to hold decoded TAF data
    
    This is a pure data container. Formatting logic is handled by TafFormatter.
    """

    raw_taf: str
    station_id: str
    issue_time: datetime
    valid_period: Dict
    forecast_periods: List[Dict]
    remarks: str
    remarks_decoded: Dict

    def __str__(self) -> str:
        """Return a human-readable string of the decoded TAF
        
        Delegates to TafFormatter for the actual formatting.
        """
        return TafFormatter.format(self)
