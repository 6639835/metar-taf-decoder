"""Visibility information parser"""

import re
from typing import Dict, List, Optional


class VisibilityParser:
    """Parser for visibility information in METAR and TAF reports"""
    
    # Direction suffixes for directional visibility
    DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    
    @staticmethod
    def extract_visibility(parts: List[str]) -> Optional[Dict]:
        """Extract visibility information from weather report parts
        
        Handles:
        - CAVOK (Ceiling And Visibility OK)
        - 4-digit meter format (e.g., 1200, 9999, 0000)
        - SM format with fractions (e.g., 1/2SM, 3SM, P6SM, M1/4SM)
        - Mixed fractions (e.g., 1 1/2SM = 1.5 SM)
        - Directional visibility (e.g., 4000NE, 2000 1200NW)
        - NDV (No Directional Variation)
        """
        for i, part in enumerate(parts):
            # Check for CAVOK
            if part == 'CAVOK':
                parts.pop(i)
                return {
                    'value': 9999,
                    'unit': 'M',
                    'is_cavok': True
                }
            
            # Check for visibility with directional suffix (e.g., 4000NE, 1200NW)
            dir_match = re.match(r'^(\d{4})(N|NE|E|SE|S|SW|W|NW)$', part)
            if dir_match:
                vis_value = int(dir_match.group(1))
                direction = dir_match.group(2)
                parts.pop(i)
                return {
                    'value': vis_value,
                    'unit': 'M',
                    'is_cavok': False,
                    'direction': direction
                }
            
            # Check for standard visibility format (4 digits)
            if len(part) == 4 and part.isdigit():
                vis_value = int(part)
                parts.pop(i)
                
                result = {
                    'value': vis_value,
                    'unit': 'M',
                    'is_cavok': False
                }
                
                # Check if next part is directional visibility (e.g., "2000 1200NW")
                if i < len(parts):
                    next_dir_match = re.match(r'^(\d{4})(N|NE|E|SE|S|SW|W|NW)$', parts[i])
                    if next_dir_match:
                        result['directional_visibility'] = {
                            'value': int(next_dir_match.group(1)),
                            'direction': next_dir_match.group(2)
                        }
                        parts.pop(i)
                
                return result
            
            # Check for mixed fraction SM visibility (e.g., "1 1/2SM" requires looking at next part)
            # First check if current part is a whole number and next part is fraction+SM
            if part.isdigit() and i + 1 < len(parts):
                frac_match = re.match(r'^(\d+)/(\d+)SM$', parts[i + 1])
                if frac_match:
                    whole = int(part)
                    numerator = int(frac_match.group(1))
                    denominator = int(frac_match.group(2))
                    
                    parts.pop(i)  # Remove whole number
                    parts.pop(i)  # Remove fraction (now at index i)
                    return {
                        'value': whole + (numerator / denominator),
                        'unit': 'SM',
                        'is_cavok': False
                    }
            
            # Check for SM visibility with M (less than) or P (greater than) prefix
            # Formats: P6SM (greater than 6SM), M1/4SM (less than 1/4SM), 3SM, 1/2SM
            sm_match = re.match(r'^([PM])?(\d+)(?:/(\d+))?SM$', part)
            if sm_match:
                modifier = sm_match.group(1)
                is_greater_than = modifier == 'P'
                is_less_than = modifier == 'M'
                numerator = int(sm_match.group(2))
                denominator = int(sm_match.group(3)) if sm_match.group(3) else 1
                
                parts.pop(i)
                result = {
                    'value': numerator / denominator,
                    'unit': 'SM',
                    'is_cavok': False
                }
                
                if is_greater_than:
                    result['is_greater_than'] = True
                if is_less_than:
                    result['is_less_than'] = True
                    
                return result
            
            # Check for NDV (No Directional Variation) - METAR specific
            if part.endswith('NDV'):
                # Extract the numeric part
                numeric_part = part[:-3]
                if numeric_part.isdigit() and len(numeric_part) == 4:
                    vis_value = int(numeric_part)
                    parts.pop(i)
                    return {
                        'value': vis_value,
                        'unit': 'M',
                        'is_cavok': False,
                        'ndv': True
                    }
        
        return None
    
    @staticmethod
    def parse_visibility_string(vis_str: str) -> Optional[Dict]:
        """Parse a visibility string directly"""
        # Check for CAVOK
        if vis_str == 'CAVOK':
            return {
                'value': 9999,
                'unit': 'M',
                'is_cavok': True
            }
        
        # Check for visibility with directional suffix (e.g., 4000NE)
        dir_match = re.match(r'^(\d{4})(N|NE|E|SE|S|SW|W|NW)$', vis_str)
        if dir_match:
            return {
                'value': int(dir_match.group(1)),
                'unit': 'M',
                'is_cavok': False,
                'direction': dir_match.group(2)
            }
        
        # Check for standard 4-digit format
        if len(vis_str) == 4 and vis_str.isdigit():
            return {
                'value': int(vis_str),
                'unit': 'M',
                'is_cavok': False
            }
        
        # Check for NDV format
        if vis_str.endswith('NDV'):
            numeric_part = vis_str[:-3]
            if numeric_part.isdigit() and len(numeric_part) == 4:
                return {
                    'value': int(numeric_part),
                    'unit': 'M',
                    'is_cavok': False,
                    'ndv': True
                }
        
        # Check for SM format with M (less than) or P (greater than) prefix
        sm_match = re.match(r'^([PM])?(\d+)(?:/(\d+))?SM$', vis_str)
        if sm_match:
            modifier = sm_match.group(1)
            is_greater_than = modifier == 'P'
            is_less_than = modifier == 'M'
            numerator = int(sm_match.group(2))
            denominator = int(sm_match.group(3)) if sm_match.group(3) else 1
            
            result = {
                'value': numerator / denominator,
                'unit': 'SM',
                'is_cavok': False
            }
            
            if is_greater_than:
                result['is_greater_than'] = True
            if is_less_than:
                result['is_less_than'] = True
                
            return result
        
        return None
