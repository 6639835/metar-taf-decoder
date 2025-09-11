"""Visibility information parser"""

import re
from typing import Dict, List, Optional


class VisibilityParser:
    """Parser for visibility information in METAR and TAF reports"""
    
    @staticmethod
    def extract_visibility(parts: List[str]) -> Optional[Dict]:
        """Extract visibility information from weather report parts"""
        for i, part in enumerate(parts):
            # Check for CAVOK
            if part == 'CAVOK':
                parts.pop(i)
                return {
                    'value': 9999,
                    'unit': 'M',
                    'is_cavok': True
                }
            
            # Check for standard visibility format (4 digits)
            if len(part) == 4 and part.isdigit():
                vis_value = int(part)
                parts.pop(i)
                
                return {
                    'value': vis_value,
                    'unit': 'M',
                    'is_cavok': False
                }
            
            # Check for SM visibility, including P6SM pattern
            sm_match = re.match(r'(P)?(\d+)(?:/(\d+))?SM', part)
            if sm_match:
                is_greater_than = sm_match.group(1) == 'P'
                numerator = int(sm_match.group(2))
                denominator = int(sm_match.group(3)) if sm_match.group(3) else 1
                
                parts.pop(i)
                return {
                    'value': numerator / denominator,
                    'unit': 'SM',
                    'is_cavok': False,
                    'is_greater_than': is_greater_than
                }
            
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
        
        # Check for SM format
        sm_match = re.match(r'(P)?(\d+)(?:/(\d+))?SM', vis_str)
        if sm_match:
            is_greater_than = sm_match.group(1) == 'P'
            numerator = int(sm_match.group(2))
            denominator = int(sm_match.group(3)) if sm_match.group(3) else 1
            
            return {
                'value': numerator / denominator,
                'unit': 'SM',
                'is_cavok': False,
                'is_greater_than': is_greater_than
            }
        
        return None
