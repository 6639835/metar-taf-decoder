"""Sky conditions parser"""

import re
from typing import Dict, List
from ..utils.patterns import SKY_PATTERN
from ..utils.constants import SKY_CONDITIONS


class SkyParser:
    """Parser for sky conditions in METAR and TAF reports"""
    
    @staticmethod
    def extract_sky_conditions(parts: List[str]) -> List[Dict]:
        """Extract sky conditions from weather report parts"""
        sky_conditions = []
        
        i = 0
        while i < len(parts):
            part = parts[i]
            
            # Check for sky condition pattern
            match = re.match(SKY_PATTERN, part)
            if match:
                sky_type = match.group(1)
                height_str = match.group(2)
                # Height can be /// when unknown, or 3 digits
                if height_str == '///':
                    height = None
                    unknown_height = True
                else:
                    height = int(height_str) * 100  # Convert to feet
                    unknown_height = False
                cloud_type = match.group(3) or None
                
                sky = {
                    'type': sky_type,
                    'height': height
                }
                
                if unknown_height:
                    sky['unknown_height'] = True
                
                if cloud_type == 'CB':
                    sky['cb'] = True
                elif cloud_type == 'TCU':
                    sky['tcu'] = True
                elif cloud_type == '///':
                    sky['unknown_type'] = True
                
                sky_conditions.append(sky)
                parts.pop(i)
                continue
            
            # Check for no cloud codes
            elif part in ['SKC', 'CLR', 'NSC', 'NCD']:
                sky_conditions.append({
                    'type': part,
                    'height': None
                })
                parts.pop(i)
                continue
            
            i += 1
        
        return sky_conditions
    
    @staticmethod
    def parse_sky_string(sky_str: str) -> Dict:
        """Parse a single sky condition string"""
        # Check for no cloud codes first
        if sky_str in ['SKC', 'CLR', 'NSC', 'NCD']:
            return {
                'type': sky_str,
                'height': None
            }
        
        # Check for sky condition pattern
        match = re.match(SKY_PATTERN, sky_str)
        if match:
            sky_type = match.group(1)
            height_str = match.group(2)
            # Height can be /// when unknown, or 3 digits
            if height_str == '///':
                height = None
                unknown_height = True
            else:
                height = int(height_str) * 100  # Convert to feet
                unknown_height = False
            cloud_type = match.group(3) or None
            
            sky = {
                'type': sky_type,
                'height': height
            }
            
            if unknown_height:
                sky['unknown_height'] = True
            
            if cloud_type == 'CB':
                sky['cb'] = True
            elif cloud_type == 'TCU':
                sky['tcu'] = True
            elif cloud_type == '///':
                sky['unknown_type'] = True
            
            return sky
        
        return None
    
    @staticmethod
    def get_sky_description(sky_type: str) -> str:
        """Get human-readable description for sky condition type"""
        return SKY_CONDITIONS.get(sky_type, sky_type)
