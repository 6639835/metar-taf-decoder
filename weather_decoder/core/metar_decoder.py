"""Main METAR decoder that orchestrates parsing"""

import re
from datetime import datetime, timezone
from typing import Dict, List
from ..data.metar_data import MetarData
from ..parsers.wind_parser import WindParser
from ..parsers.visibility_parser import VisibilityParser
from ..parsers.weather_parser import WeatherParser
from ..parsers.sky_parser import SkyParser
from ..parsers.pressure_parser import PressureParser
from ..parsers.temperature_parser import TemperatureParser
from ..parsers.time_parser import TimeParser
from ..utils.patterns import COMPILED_PATTERNS, RVR_PATTERN
from ..utils.constants import TREND_TYPES, MILITARY_COLOR_CODES


class MetarDecoder:
    """METAR decoder class that parses raw METAR strings"""
    
    def __init__(self):
        """Initialize the METAR decoder"""
        self.wind_parser = WindParser()
        self.visibility_parser = VisibilityParser()
        self.weather_parser = WeatherParser()
        self.sky_parser = SkyParser()
        self.pressure_parser = PressureParser()
        self.temperature_parser = TemperatureParser()
        self.time_parser = TimeParser()
    
    def decode(self, raw_metar: str) -> MetarData:
        """
        Decode a raw METAR string into structured data
        
        Args:
            raw_metar: The raw METAR string to decode
            
        Returns:
            MetarData: A structured object containing all decoded METAR components
        """
        metar = raw_metar.strip()
        parts = metar.split()
        
        # Remove remarks section from parts to avoid processing remarks as main weather data
        if 'RMK' in parts:
            rmk_index = parts.index('RMK')
            parts = parts[:rmk_index]
        
        # Extract header information
        metar_type, station_id, observation_time, auto = self._extract_header(parts)
        
        # Extract main elements
        wind = self._extract_wind(parts)
        visibility = self._extract_visibility(parts)
        runway_visual_range = self._extract_rvr(parts)
        runway_conditions = []  # Placeholder for future implementation
        runway_state_reports = []  # Placeholder for future implementation
        weather_groups = self._extract_weather(parts)
        sky_conditions = self._extract_sky_conditions(parts)
        temperature, dewpoint = self._extract_temperature_dewpoint(parts)
        altimeter = self._extract_altimeter(parts)
        windshear = self._extract_windshear(parts)
        trends = self._extract_trends(parts)
        military_color_codes = self._extract_military_color_codes(parts)
        
        # Extract remarks
        remarks, remarks_decoded = self._extract_remarks(metar)
        
        return MetarData(
            raw_metar=raw_metar,
            metar_type=metar_type,
            station_id=station_id,
            observation_time=observation_time,
            auto=auto,
            wind=wind or {'direction': 0, 'speed': 0, 'unit': 'KT'},
            visibility=visibility or {'value': 9999, 'unit': 'M', 'is_cavok': False},
            runway_visual_range=runway_visual_range,
            runway_conditions=runway_conditions,
            runway_state_reports=runway_state_reports,
            weather_groups=weather_groups,
            sky_conditions=sky_conditions,
            temperature=temperature or 0.0,
            dewpoint=dewpoint or 0.0,
            altimeter=altimeter or {'value': 29.92, 'unit': 'inHg'},
            windshear=windshear,
            trends=trends,
            remarks=remarks,
            remarks_decoded=remarks_decoded,
            military_color_codes=military_color_codes
        )
    
    def _extract_header(self, parts: List[str]) -> tuple:
        """Extract METAR header information"""
        metar_type = "METAR"
        station_id = ""
        observation_time = datetime.now(timezone.utc)
        auto = False
        
        # Extract METAR type
        if parts and COMPILED_PATTERNS['metar_type'].match(parts[0]):
            metar_type = parts.pop(0)
        
        # Extract station ID
        if parts and COMPILED_PATTERNS['station_id'].match(parts[0]):
            station_id = parts.pop(0)
        
        # Extract observation time
        if parts and re.match(r'\d{6}Z', parts[0]):
            time_str = parts.pop(0)
            observation_time = self.time_parser.parse_observation_time(time_str) or observation_time
        
        # Check for AUTO
        if parts and parts[0] == 'AUTO':
            auto = True
            parts.pop(0)
        
        return metar_type, station_id, observation_time, auto
    
    def _extract_wind(self, parts: List[str]) -> Dict:
        """Extract wind information"""
        return self.wind_parser.extract_wind(parts)
    
    def _extract_visibility(self, parts: List[str]) -> Dict:
        """Extract visibility information"""
        return self.visibility_parser.extract_visibility(parts)
    
    def _extract_rvr(self, parts: List[str]) -> List[Dict]:
        """Extract runway visual range information"""
        rvr_list = []
        
        i = 0
        while i < len(parts):
            match = re.match(RVR_PATTERN, parts[i])
            if match:
                runway = match.group(1)
                is_less_than = match.group(2) == 'M'
                visual_range = int(match.group(3))
                variable_less_than = match.group(4) == 'M' if match.group(4) else False
                variable_range = int(match.group(5)) if match.group(5) else None
                trend = match.group(6)
                
                rvr = {
                    'runway': runway,
                    'visual_range': visual_range,
                    'unit': 'FT',
                    'is_less_than': is_less_than
                }
                
                if variable_range:
                    rvr['variable_range'] = variable_range
                    rvr['variable_less_than'] = variable_less_than
                
                if trend:
                    trend_map = {'U': 'improving', 'D': 'deteriorating', 'N': 'no change'}
                    rvr['trend'] = trend_map.get(trend, trend)
                
                rvr_list.append(rvr)
                parts.pop(i)
            else:
                i += 1
        
        return rvr_list
    
    def _extract_weather(self, parts: List[str]) -> List[Dict]:
        """Extract weather phenomena"""
        return self.weather_parser.extract_weather(parts)
    
    def _extract_sky_conditions(self, parts: List[str]) -> List[Dict]:
        """Extract sky conditions"""
        return self.sky_parser.extract_sky_conditions(parts)
    
    def _extract_temperature_dewpoint(self, parts: List[str]) -> tuple:
        """Extract temperature and dewpoint"""
        return self.temperature_parser.extract_temperature_dewpoint(parts)
    
    def _extract_altimeter(self, parts: List[str]) -> Dict:
        """Extract altimeter setting"""
        return self.pressure_parser.extract_altimeter(parts)
    
    def _extract_windshear(self, parts: List[str]) -> List[str]:
        """Extract windshear information"""
        windshear_list = []
        
        i = 0
        while i < len(parts):
            if parts[i].startswith('WS'):
                windshear_list.append(parts.pop(i))
            else:
                i += 1
        
        return windshear_list
    
    def _extract_trends(self, parts: List[str]) -> List[Dict]:
        """Extract trend information"""
        trends = []
        
        i = 0
        while i < len(parts):
            if parts[i] in TREND_TYPES:
                trend_type = parts.pop(i)
                
                # Collect trend elements
                trend_elements = []
                while i < len(parts) and parts[i] not in TREND_TYPES and not parts[i].startswith('RMK'):
                    trend_elements.append(parts.pop(i))
                
                trends.append({
                    'type': trend_type,
                    'description': f"{trend_type} {' '.join(trend_elements)}" if trend_elements else trend_type
                })
            else:
                i += 1
        
        return trends
    
    def _extract_military_color_codes(self, parts: List[str]) -> List[Dict]:
        """Extract military color codes"""
        color_codes = []
        
        i = 0
        while i < len(parts):
            if parts[i] in MILITARY_COLOR_CODES:
                code = parts.pop(i)
                color_codes.append({
                    'code': code,
                    'description': MILITARY_COLOR_CODES[code]
                })
            else:
                i += 1
        
        return color_codes
    
    def _extract_remarks(self, metar: str) -> tuple:
        """Extract and decode remarks section"""
        match = re.search(r'RMK\s+(.+)$', metar)
        if match:
            remarks = match.group(1)
            
            # Basic remarks decoding
            decoded = {}
            
            # Check for common patterns
            if 'AO2' in remarks:
                decoded['Station Type'] = "Automated station with precipitation discriminator"
            elif 'AO1' in remarks:
                decoded['Station Type'] = "Automated station without precipitation discriminator"
            
            # Wind information in remarks
            wind_patterns = re.findall(r'WIND\s+(\w+)\s+(\d{3})(\d{2,3})(?:G(\d{2,3}))?KT', remarks)
            if wind_patterns:
                decoded['runway_winds'] = []
                for pattern in wind_patterns:
                    location, direction, speed, gust = pattern
                    wind_info = {
                        'runway': location,
                        'direction': int(direction),
                        'speed': int(speed),
                        'unit': 'KT'
                    }
                    if gust:
                        wind_info['gust'] = int(gust)
                    decoded['runway_winds'].append(wind_info)
            
            # Sea Level Pressure (SLP)
            slp_match = re.search(r'SLP(\d{3})', remarks)
            if slp_match:
                slp = int(slp_match.group(1))
                # North American format: add decimal point (e.g., 095 -> 1009.5, 200 -> 1020.0)
                if slp < 500:
                    pressure = 1000 + slp / 10
                else:
                    pressure = 900 + slp / 10
                
                decoded['Sea Level Pressure'] = f"{pressure:.1f} hPa"
            
            # Pressure tendency
            if re.search(r'5[0-8]\d{3}', remarks):
                decoded['Pressure Tendency'] = "3-hour pressure tendency reported"
            
            # Temperature/dewpoint to tenths
            temp_match = re.search(r'T([01])(\d{3})([01])(\d{3})', remarks)
            if temp_match:
                temp_sign = -1 if temp_match.group(1) == '1' else 1
                temp_tenths = int(temp_match.group(2))
                dew_sign = -1 if temp_match.group(3) == '1' else 1
                dew_tenths = int(temp_match.group(4))
                
                decoded['Temperature (tenths)'] = f"{temp_sign * temp_tenths / 10:.1f}°C"
                decoded['Dewpoint (tenths)'] = f"{dew_sign * dew_tenths / 10:.1f}°C"
            
            # 24-hour temperature extremes (4MMMMNNNN format)
            temp_extremes_match = re.search(r'4([01])(\d{3})([01])(\d{3})', remarks)
            if temp_extremes_match:
                max_sign = -1 if temp_extremes_match.group(1) == '1' else 1
                max_temp_tenths = int(temp_extremes_match.group(2))
                min_sign = -1 if temp_extremes_match.group(3) == '1' else 1
                min_temp_tenths = int(temp_extremes_match.group(4))
                
                max_temp = max_sign * max_temp_tenths / 10
                min_temp = min_sign * min_temp_tenths / 10
                
                decoded['24-Hour Maximum Temperature'] = f"{max_temp:.1f}°C"
                decoded['24-Hour Minimum Temperature'] = f"{min_temp:.1f}°C"
            
            # Variable visibility (VIS)
            vis_match = re.search(r'VIS\s+(\d+(?:/\d+)?)V(\d+(?:/\d+)?)', remarks)
            if vis_match:
                min_vis_str = vis_match.group(1)
                max_vis_str = vis_match.group(2)
                
                # Parse fractions
                def parse_visibility_fraction(vis_str):
                    if '/' in vis_str:
                        num, den = vis_str.split('/')
                        return float(num) / float(den)
                    else:
                        return float(vis_str)
                
                min_vis = parse_visibility_fraction(min_vis_str)
                max_vis = parse_visibility_fraction(max_vis_str)
                
                if min_vis == int(min_vis):
                    min_vis_display = str(int(min_vis))
                else:
                    min_vis_display = min_vis_str
                    
                if max_vis == int(max_vis):
                    max_vis_display = str(int(max_vis))
                else:
                    max_vis_display = max_vis_str
                
                decoded['Variable Visibility'] = f"{min_vis_display} to {max_vis_display} statute miles"
            
            # Past weather (RAB11E24, SNB05E15, etc.)
            # Handle combined begin/end patterns like RAB11E24
            combined_weather_matches = re.findall(r'([A-Z]{2})B(\d{2})E(\d{2})', remarks)
            individual_weather_matches = re.findall(r'([A-Z]{2}[A-Z]?)([BE])(\d{2})(?![BE]\d{2})', remarks)
            
            past_weather_events = []
            
            # Process combined begin/end patterns (e.g., RAB11E24)
            for weather_code, begin_time, end_time in combined_weather_matches:
                if weather_code == 'RA':
                    weather_type = 'rain'
                elif weather_code == 'SN':
                    weather_type = 'snow'
                elif weather_code == 'DZ':
                    weather_type = 'drizzle'
                elif weather_code == 'TS':
                    weather_type = 'thunderstorm'
                else:
                    weather_type = weather_code.lower()
                
                past_weather_events.append(f"{weather_type} began at minute {begin_time}, ended at minute {end_time}")
            
            # Process individual begin/end patterns (e.g., RAB15, RAE20)
            for weather_code, begin_end, time_minutes in individual_weather_matches:
                if weather_code == 'RA':
                    weather_type = 'rain'
                elif weather_code == 'SN':
                    weather_type = 'snow'
                elif weather_code == 'DZ':
                    weather_type = 'drizzle'
                elif weather_code == 'TS':
                    weather_type = 'thunderstorm'
                else:
                    weather_type = weather_code.lower()
                
                action = 'began' if begin_end == 'B' else 'ended'
                past_weather_events.append(f"{weather_type} {action} at minute {time_minutes}")
            
            if past_weather_events:
                decoded['Past Weather'] = ', '.join(past_weather_events)
            
            # Precipitation amount (P0000, P0001, etc.)
            precip_match = re.search(r'P(\d{4})', remarks)
            if precip_match:
                precip_hundredths = int(precip_match.group(1))
                if precip_hundredths == 0:
                    decoded['Precipitation Amount'] = "Less than 0.01 inches"
                else:
                    precip_inches = precip_hundredths / 100.0
                    decoded['Precipitation Amount'] = f"{precip_inches:.2f} inches"
            
            return remarks, decoded
        else:
            return "", {}
