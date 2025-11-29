"""Time and date parsing utilities"""

import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from ..utils.patterns import DATETIME_PATTERN, FM_PATTERN, VALID_PERIOD_PATTERN


class TimeParser:
    """Parser for time and date information in weather reports"""

    @staticmethod
    def parse_observation_time(time_str: str) -> Optional[datetime]:
        """Parse observation time from METAR/TAF (format: DDHHMMZ)"""
        match = re.match(DATETIME_PATTERN, time_str)
        if match:
            day, hour, minute = map(int, match.groups())

            # Create datetime object
            current_date = datetime.now(timezone.utc)
            year, month = current_date.year, current_date.month

            # Handle month rollover if needed
            if day > current_date.day:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1

            return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

        return None

    @staticmethod
    def parse_valid_period(period_str: str) -> Optional[Dict]:
        """Parse valid period from TAF (format: DDHH/DDHH)"""
        match = re.match(VALID_PERIOD_PATTERN, period_str)
        if match:
            from_day, from_hour, to_day, to_hour = map(int, match.groups())

            # Handle special case where hours are 24
            if from_hour == 24:
                from_hour = 0
                from_day += 1
            if to_hour == 24:
                to_hour = 0
                to_day += 1

            current_date = datetime.now(timezone.utc)
            year, month = current_date.year, current_date.month

            # Handle month rollover for from_time
            if from_day > current_date.day:
                if month == 1:
                    from_time = datetime(year - 1, 12, from_day, from_hour, 0, tzinfo=timezone.utc)
                else:
                    from_time = datetime(year, month - 1, from_day, from_hour, 0, tzinfo=timezone.utc)
            else:
                from_time = datetime(year, month, from_day, from_hour, 0, tzinfo=timezone.utc)

            # Handle month rollover for to_time
            if to_day < from_day:
                if month == 12:
                    to_time = datetime(year + 1, 1, to_day, to_hour, 0, tzinfo=timezone.utc)
                else:
                    to_time = datetime(year, month + 1, to_day, to_hour, 0, tzinfo=timezone.utc)
            else:
                to_time = datetime(year, month, to_day, to_hour, 0, tzinfo=timezone.utc)

            return {"from": from_time, "to": to_time}

        return None

    @staticmethod
    def parse_fm_time(fm_str: str) -> Optional[datetime]:
        """Parse FM (FROM) time from TAF (format: FM061200)"""
        match = re.match(FM_PATTERN, fm_str)
        if match:
            day, hour, minute = map(int, match.groups())

            current_date = datetime.now(timezone.utc)
            year, month = current_date.year, current_date.month

            # Handle month rollover
            if day > current_date.day:
                if month == 1:
                    from_time = datetime(year - 1, 12, day, hour, minute, tzinfo=timezone.utc)
                else:
                    from_time = datetime(year, month - 1, day, hour, minute, tzinfo=timezone.utc)
            else:
                from_time = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)

            return from_time

        return None

    @staticmethod
    def parse_time_range(time_group: str) -> Tuple[datetime, datetime]:
        """Parse a time range string (like '0609/0610') into datetime objects"""
        from_day = int(time_group[0:2])
        from_hour = int(time_group[2:4])
        to_day = int(time_group[5:7])
        to_hour = int(time_group[7:9])

        # Handle special case where hours are 24
        if from_hour == 24:
            from_hour = 0
            from_day += 1
        if to_hour == 24:
            to_hour = 0
            to_day += 1

        current_date = datetime.now(timezone.utc)
        year, month = current_date.year, current_date.month

        # Handle month rollover for from_time
        if from_day > current_date.day:
            if month == 1:
                from_time = datetime(year - 1, 12, from_day, from_hour, 0, tzinfo=timezone.utc)
            else:
                from_time = datetime(year, month - 1, from_day, from_hour, 0, tzinfo=timezone.utc)
        else:
            from_time = datetime(year, month, from_day, from_hour, 0, tzinfo=timezone.utc)

        # Handle month rollover for to_time
        if to_day < from_day:
            if month == 12:
                to_time = datetime(year + 1, 1, to_day, to_hour, 0, tzinfo=timezone.utc)
            else:
                to_time = datetime(year, month + 1, to_day, to_hour, 0, tzinfo=timezone.utc)
        else:
            to_time = datetime(year, month, to_day, to_hour, 0, tzinfo=timezone.utc)

        return from_time, to_time

    @staticmethod
    def get_current_utc_time() -> datetime:
        """Get current UTC time"""
        return datetime.now(timezone.utc)

    @staticmethod
    def format_time(dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%d %H:%M UTC")
