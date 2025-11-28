"""Wind information parser"""

import re
from typing import Dict, List, Optional
from ..utils.patterns import WIND_PATTERN, WIND_VAR_PATTERN, WIND_EXTREME_PATTERN


class WindParser:
    """Parser for wind information in METAR and TAF reports"""
    
    @staticmethod
    def extract_wind(parts: List[str]) -> Optional[Dict]:
        """Extract wind information from weather report parts"""
        for i, part in enumerate(parts):
            # Check for extreme wind speed format (ABV49MPS, ABV99KT)
            extreme_match = re.match(WIND_EXTREME_PATTERN, part)
            if extreme_match:
                speed = int(extreme_match.group(1))
                unit = extreme_match.group(2)
                
                wind = {
                    'direction': 'VRB',  # Extreme winds typically don't have specific direction
                    'speed': speed,
                    'unit': unit,
                    'above': True  # Indicates speed is "above" this value
                }
                
                parts.pop(i)
                return wind
            
            # Enhanced wind pattern to match more formats including MPS
            match = re.match(WIND_PATTERN, part)
            if match:
                # Check for P prefix (speed above limit, e.g., P99KT)
                is_above = match.group(1) == 'P'
                direction_str = match.group(2)
                
                # Handle direction
                if direction_str == 'VRB':
                    direction = 'VRB'
                else:
                    direction = int(direction_str)
                
                # Handle speed
                speed = int(match.group(3))
                
                # Handle gusts if present
                gust = None
                if match.group(5):
                    gust = int(match.group(5))
                
                # Determine unit
                if 'KT' in part:
                    unit = 'KT'
                elif 'MPS' in part:
                    unit = 'MPS'
                elif 'KMH' in part:
                    unit = 'KMH'
                else:
                    unit = 'KT'  # Default
                
                wind = {
                    'direction': direction,
                    'speed': speed,
                    'unit': unit
                }
                
                if is_above:
                    wind['above'] = True
                
                if gust:
                    wind['gust'] = gust
                
                # Look for variable direction in the next part
                if i + 1 < len(parts):
                    var_match = re.match(WIND_VAR_PATTERN, parts[i+1])
                    if var_match:
                        wind['variable_direction'] = (int(var_match.group(1)), int(var_match.group(2)))
                        # Remove the variable direction part as it's been processed
                        parts.pop(i+1)
                
                # Remove the wind part as it's been processed
                parts.pop(i)
                return wind
        
        return None
    
    @staticmethod
    def parse_wind_string(wind_str: str) -> Optional[Dict]:
        """Parse a wind string directly"""
        # Check for extreme wind speed format (ABV49MPS, ABV99KT)
        extreme_match = re.match(WIND_EXTREME_PATTERN, wind_str)
        if extreme_match:
            speed = int(extreme_match.group(1))
            unit = extreme_match.group(2)
            
            return {
                'direction': 'VRB',
                'speed': speed,
                'unit': unit,
                'above': True
            }
        
        match = re.match(WIND_PATTERN, wind_str)
        if not match:
            return None
        
        # Check for P prefix (speed above limit)
        is_above = match.group(1) == 'P'
        direction_str = match.group(2)
        speed = int(match.group(3))
        gust = int(match.group(5)) if match.group(5) else None
        
        # Determine unit
        if wind_str.endswith('KT'):
            unit = 'KT'
        elif wind_str.endswith('MPS'):
            unit = 'MPS'
        elif wind_str.endswith('KMH'):
            unit = 'KMH'
        else:
            unit = 'KT'
        
        wind = {
            'direction': 'VRB' if direction_str == 'VRB' else int(direction_str),
            'speed': speed,
            'unit': unit
        }
        
        if is_above:
            wind['above'] = True
        
        if gust:
            wind['gust'] = gust
            
        return wind
    
    @staticmethod
    def parse_variable_direction(var_str: str) -> Optional[tuple]:
        """Parse variable wind direction string (e.g., '240V340')"""
        match = re.match(WIND_VAR_PATTERN, var_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None
