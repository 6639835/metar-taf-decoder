"""TAF Data class for holding decoded TAF information"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from ..utils.formatters import format_wind, format_visibility


@dataclass
class TafData:
    """Class to hold decoded TAF data"""
    raw_taf: str
    station_id: str
    issue_time: datetime
    valid_period: Dict
    forecast_periods: List[Dict]
    remarks: str
    remarks_decoded: Dict
    
    def __str__(self) -> str:
        """Return a human-readable string of the decoded TAF"""
        lines = [
            f"TAF for {self.station_id} issued {self.issue_time.day:02d} {self.issue_time.hour:02d}:{self.issue_time.minute:02d} UTC",
            f"Valid from {self.valid_period['from'].day:02d} {self.valid_period['from'].hour:02d}:{self.valid_period['from'].minute:02d} UTC",
            f"Valid to {self.valid_period['to'].day:02d} {self.valid_period['to'].hour:02d}:{self.valid_period['to'].minute:02d} UTC",
        ]
        
        # Add each forecast period
        for i, period in enumerate(self.forecast_periods):
            if i == 0:
                lines.append("\nInitial Forecast:")
            else:
                change_type = period.get('change_type', '')
                time_desc = ''
                
                if period.get('from_time') and period.get('to_time'):
                    from_time = period['from_time']
                    to_time = period['to_time']
                    time_desc = f" from {from_time.day:02d} {from_time.hour:02d}:{from_time.minute:02d} to {to_time.day:02d} {to_time.hour:02d}:{to_time.minute:02d} UTC"
                elif period.get('from_time'):
                    from_time = period['from_time']
                    time_desc = f" {from_time.day:02d} {from_time.hour:02d}:{from_time.minute:02d} UTC"
                
                prob = period.get('probability', 0)
                prob_text = f" (Probability {prob}%)" if prob > 0 else ""
                
                if change_type == 'TEMPO':
                    lines.append(f"\nTemporary conditions{time_desc}{prob_text}:")
                elif change_type == 'BECMG':
                    lines.append(f"\nConditions becoming{time_desc}{prob_text}:")
                elif change_type == 'FM':
                    lines.append(f"\nFrom {from_time.day:02d} {from_time.hour:02d}:{from_time.minute:02d} UTC{prob_text}:")
                elif change_type == 'PROB':
                    lines.append(f"\nProbability {prob}%{time_desc}:")
                else:
                    lines.append(f"\nChange group ({change_type}){time_desc}{prob_text}:")
            
            # Add wind information
            if period.get('wind'):
                lines.append(f"  Wind: {format_wind(period['wind'])}")
            
            # Add visibility information
            if period.get('visibility'):
                lines.append(f"  Visibility: {format_visibility(period['visibility'])}")
            
            # Add weather phenomena
            if period.get('weather_groups'):
                wx_lines = ["  Weather Phenomena:"]
                for wx in period['weather_groups']:
                    intensity = wx.get('intensity', '')
                    descriptor = wx.get('descriptor', '')
                    phenomena = wx.get('phenomena', [])
                    
                    if intensity or descriptor or phenomena:
                        wx_text = []
                        if intensity:
                            wx_text.append(intensity)
                        if descriptor:
                            wx_text.append(descriptor)
                        if phenomena:
                            wx_text.append(', '.join(phenomena))
                        
                        wx_lines.append(f"    {' '.join(wx_text)}")
                lines.extend(wx_lines)
            
            # Add sky conditions
            if period.get('sky_conditions'):
                sky_lines = ["  Sky Conditions:"]
                for sky in period['sky_conditions']:
                    if sky['type'] == 'CLR' or sky['type'] == 'SKC':
                        sky_lines.append(f"    Clear skies")
                    elif sky['type'] == 'NSC':
                        sky_lines.append(f"    No significant cloud")
                    elif sky['type'] == 'NCD':
                        sky_lines.append(f"    No cloud detected")
                    elif sky['type'] == 'VV':
                        if sky.get('unknown_height'):
                            sky_lines.append(f"    Vertical visibility (unknown height)")
                        else:
                            sky_lines.append(f"    Vertical visibility {sky['height']} feet")
                    elif sky['type'] == '///':
                        if sky.get('unknown_height'):
                            sky_lines.append(f"    Unknown cloud amount at unknown height")
                        else:
                            sky_lines.append(f"    Unknown cloud amount at {sky['height']} feet")
                    else:
                        # Handle unknown height
                        if sky.get('unknown_height'):
                            height_str = "unknown height"
                        else:
                            height_str = f"{sky['height']} feet"
                        sky_lines.append(f"    {sky['type']} clouds at {height_str}")
                        if sky.get('cb') or sky.get('tcu'):
                            cb_tcu = 'CB' if sky.get('cb') else 'TCU'
                            sky_lines[-1] += f" ({cb_tcu})"
                        elif sky.get('unknown_type'):
                            sky_lines[-1] += f" (unknown type)"
                lines.extend(sky_lines)
            
            # Add QNH information
            if period.get('qnh'):
                qnh = period['qnh']
                lines.append(f"  Pressure: {qnh['value']} {qnh['unit']}")
            
            # Add temperature information - improved to handle multiple forecasts
            if period.get('temperature_max_list') or period.get('temperature_min_list'):
                temp_line = "  Temperature:"
                
                # Handle max temperatures
                if period.get('temperature_max_list'):
                    max_temps = period['temperature_max_list']
                    for i, temp in enumerate(max_temps):
                        if i > 0:
                            temp_line += ","
                        temp_line += f" max {temp['value']}°C at {temp['time'].strftime('%d/%H:%M')} UTC"
                
                # Handle min temperatures
                if period.get('temperature_min_list'):
                    if period.get('temperature_max_list'):
                        temp_line += ","
                    min_temps = period['temperature_min_list']
                    for i, temp in enumerate(min_temps):
                        if i > 0:
                            temp_line += ","
                        temp_line += f" min {temp['value']}°C at {temp['time'].strftime('%d/%H:%M')} UTC"
                
                lines.append(temp_line)
            # Fallback for backward compatibility
            elif period.get('temperature_min') is not None or period.get('temperature_max') is not None:
                temp_line = "  Temperature:"
                if period.get('temperature_max') is not None:
                    temp_line += f" max {period['temperature_max']}°C at {period.get('temperature_max_time', '').strftime('%d/%H:%M')} UTC"
                if period.get('temperature_min') is not None:
                    if period.get('temperature_max') is not None:
                        temp_line += ","
                    temp_line += f" min {period['temperature_min']}°C at {period.get('temperature_min_time', '').strftime('%d/%H:%M')} UTC"
                lines.append(temp_line)
            
            # Add turbulence if present
            if period.get('turbulence'):
                lines.append(f"  Turbulence: {period['turbulence']}")
            
            # Add icing if present
            if period.get('icing'):
                lines.append(f"  Icing: {period['icing']}")
        
        # Add remarks if present
        if self.remarks:
            lines.append(f"\nRemarks: {self.remarks}")
            if self.remarks_decoded:
                for key, value in self.remarks_decoded.items():
                    if isinstance(value, dict):
                        lines.append(f"  {key}: {', '.join([f'{k}: {v}' for k, v in value.items()])}")
                    elif isinstance(value, list):
                        if value and isinstance(value[0], dict):
                            lines.append(f"  {key}:")
                            for item in value:
                                lines.append(f"    {', '.join([f'{k}: {v}' for k, v in item.items()])}")
                        else:
                            lines.append(f"  {key}: {', '.join(value)}")
                    else:
                        lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
