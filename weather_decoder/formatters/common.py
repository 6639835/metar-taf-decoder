"""Common formatting utilities for weather data

This module provides shared formatting functions used by both
METAR and TAF formatters.
"""

from typing import Dict, List


def format_wind(wind: Dict) -> str:
    """Format wind information into a readable string
    
    Args:
        wind: Dictionary with wind data (direction, speed, unit, etc.)
        
    Returns:
        Human-readable wind string
    """
    if wind.get("direction") == "VRB":
        dir_text = "Variable"
    else:
        dir_text = f"{wind['direction']}°"

    # Handle extreme wind speeds (above limit)
    if wind.get("above"):
        speed_text = f"above {wind['speed']} {wind['unit']}"
    else:
        speed_text = f"{wind['speed']} {wind['unit']}"

    if wind.get("gust"):
        speed_text += f", gusting to {wind['gust']} {wind['unit']}"

    if wind.get("variable_direction"):
        var_dir = wind["variable_direction"]
        speed_text += f" (varying between {var_dir[0]}° and {var_dir[1]}°)"

    return f"{dir_text} at {speed_text}"


def format_visibility(visibility: Dict) -> str:
    """Format visibility information into a readable string
    
    Args:
        visibility: Dictionary with visibility data
        
    Returns:
        Human-readable visibility string
    """
    if visibility.get("is_cavok"):
        return "CAVOK (Ceiling and Visibility OK)"

    vis_value = visibility["value"]
    vis_unit = visibility["unit"]

    # Handle less than (M prefix for SM or 0000 for meters)
    if visibility.get("is_less_than"):
        result = _format_less_than_visibility(vis_value, vis_unit)
    elif vis_value == 9999:
        result = "10 km or more"
    elif vis_unit == "M" and 1000 <= vis_value <= 9000:
        result = _format_km_visibility(vis_value)
    elif visibility.get("is_greater_than"):
        result = _format_greater_than_visibility(vis_value, vis_unit)
    else:
        result = _format_standard_visibility(vis_value, vis_unit)

    # Add direction if present
    if visibility.get("direction"):
        result += f" to the {visibility['direction']}"

    # Add directional visibility if present
    if visibility.get("directional_visibility"):
        dir_vis = visibility["directional_visibility"]
        dir_text = _format_directional_visibility(dir_vis)
        result += f", {dir_text}"

    # Add minimum visibility if present
    if visibility.get("minimum_visibility"):
        min_vis = visibility["minimum_visibility"]
        min_text = _format_minimum_visibility(min_vis)
        result += f" (minimum {min_text})"

    # Add NDV indicator if present
    if visibility.get("ndv"):
        result += " (No Directional Variation)"

    return result


def _format_less_than_visibility(vis_value: float, vis_unit: str) -> str:
    """Format less-than visibility"""
    if vis_unit == "SM":
        if isinstance(vis_value, float) and not vis_value.is_integer():
            return f"Less than {vis_value} {vis_unit}"
        return f"Less than {int(vis_value)} {vis_unit}"
    elif vis_value == 0:
        return "Less than 50 M"
    return f"Less than {vis_value} {vis_unit}"


def _format_km_visibility(vis_value: float) -> str:
    """Format visibility in kilometers"""
    km_value = vis_value / 1000
    if km_value % 1 != 0:
        return f"{km_value:.1f} km"
    return f"{int(km_value)} km"


def _format_greater_than_visibility(vis_value: float, vis_unit: str) -> str:
    """Format greater-than visibility"""
    if vis_unit == "SM":
        return f"Greater than {vis_value} {vis_unit}"
    if vis_value >= 1000:
        km_value = vis_value / 1000
        if km_value % 1 != 0:
            return f"Greater than {km_value:.1f} km"
        return f"Greater than {int(km_value)} km"
    return f"Greater than {vis_value} {vis_unit}"


def _format_standard_visibility(vis_value: float, vis_unit: str) -> str:
    """Format standard visibility value"""
    if vis_unit == "SM":
        if isinstance(vis_value, float) and vis_value.is_integer():
            return f"{int(vis_value)} {vis_unit}"
        return f"{vis_value} {vis_unit}"
    if vis_unit == "M" and vis_value >= 1000:
        km_value = vis_value / 1000
        if km_value % 1 != 0:
            return f"{km_value:.1f} km"
        return f"{int(km_value)} km"
    return f"{vis_value} {vis_unit}"


def _format_directional_visibility(dir_vis: Dict) -> str:
    """Format directional visibility"""
    dir_val = dir_vis["value"]
    dir_dir = dir_vis["direction"]
    if dir_val >= 1000:
        dir_km = dir_val / 1000
        dir_text = f"{dir_km:.1f} km" if dir_km % 1 != 0 else f"{int(dir_km)} km"
    else:
        dir_text = f"{dir_val} M"
    return f"{dir_text} to the {dir_dir}"


def _format_minimum_visibility(min_vis: Dict) -> str:
    """Format minimum visibility"""
    min_val = min_vis["value"]
    if min_val >= 1000:
        min_km = min_val / 1000
        return f"{min_km:.1f} km" if min_km % 1 != 0 else f"{int(min_km)} km"
    return f"{min_val} M"


def format_temperature(temp_value: float) -> str:
    """Format temperature value
    
    Args:
        temp_value: Temperature in Celsius
        
    Returns:
        Formatted temperature string
    """
    return f"{temp_value}°C"


def format_pressure(pressure: Dict) -> str:
    """Format pressure information
    
    Args:
        pressure: Dictionary with pressure data (value, unit)
        
    Returns:
        Formatted pressure string
    """
    return f"{pressure['value']} {pressure['unit']}"


def format_sky_condition(sky: Dict) -> str:
    """Format a single sky condition
    
    Args:
        sky: Dictionary with sky condition data
        
    Returns:
        Human-readable sky condition string
    """
    sky_type = sky["type"]

    if sky_type in ["CLR", "SKC"]:
        return "Clear skies"
    elif sky_type == "NSC":
        return "No significant cloud"
    elif sky_type == "NCD":
        return "No cloud detected"
    elif sky_type == "VV":
        if sky.get("unknown_height"):
            return "Vertical visibility (unknown height)"
        return f"Vertical visibility {sky['height']} feet"
    elif sky_type == "///":
        if sky.get("unknown_height"):
            return "Unknown cloud amount at unknown height"
        return f"Unknown cloud amount at {sky['height']} feet"
    else:
        # Standard cloud layer
        if sky.get("unknown_height"):
            height_str = "unknown height"
        else:
            height_str = f"{sky['height']} feet"

        result = f"{sky_type} clouds at {height_str}"
        
        # Add cloud type modifiers
        if sky.get("cb"):
            result += " (CB)"
        elif sky.get("tcu"):
            result += " (TCU)"
        elif sky.get("unknown_type"):
            result += " (unknown type)"
            
        return result


def format_weather_group(weather: Dict) -> str:
    """Format a weather phenomena group
    
    Args:
        weather: Dictionary with weather phenomena data
        
    Returns:
        Human-readable weather string
    """
    parts: List[str] = []

    if weather.get("intensity"):
        parts.append(weather["intensity"])

    if weather.get("descriptor"):
        parts.append(weather["descriptor"])

    if weather.get("phenomena"):
        parts.append(", ".join(weather["phenomena"]))

    return " ".join(parts) if parts else ""


def format_sky_conditions_list(sky_conditions: List[Dict]) -> List[str]:
    """Format a list of sky conditions
    
    Args:
        sky_conditions: List of sky condition dictionaries
        
    Returns:
        List of formatted sky condition strings
    """
    lines: List[str] = []
    
    for sky in sky_conditions:
        sky_type = sky["type"]
        
        if sky_type in ["CLR", "SKC"]:
            lines.append("Clear skies")
        elif sky_type == "NSC":
            lines.append("No significant cloud")
        elif sky_type == "NCD":
            lines.append("No cloud detected")
        elif sky_type == "VV":
            if sky.get("unknown_height"):
                lines.append("Vertical visibility (unknown height)")
            else:
                lines.append(f"Vertical visibility {sky['height']} feet")
        elif sky_type == "///":
            if sky.get("unknown_height"):
                lines.append("Unknown cloud amount at unknown height (AUTO station)")
            else:
                lines.append(f"Unknown cloud amount at {sky['height']} feet (AUTO station)")
        elif sky_type == "AUTO" and sky.get("missing_data"):
            lines.append("Cloud data missing (AUTO station)")
        elif sky_type == "unknown" and sky.get("missing_data"):
            cloud_type_text = ""
            if sky.get("cloud_type"):
                cloud_type_text = f" ({sky['cloud_type']})"
            elif sky.get("cb"):
                cloud_type_text = " (CB)"
            elif sky.get("tcu"):
                cloud_type_text = " (TCU)"
            lines.append(f"Unknown cloud height{cloud_type_text} (AUTO station)")
        else:
            # Standard cloud layer
            if sky.get("unknown_height"):
                height_str = "unknown height"
            else:
                height_str = f"{sky['height']} feet"
            
            line = f"{sky_type} clouds at {height_str}"
            
            if sky.get("cb") or sky.get("tcu"):
                cb_tcu = "CB" if sky.get("cb") else "TCU"
                line += f" ({cb_tcu})"
            elif sky.get("unknown_type"):
                line += " (unknown type)"
            
            lines.append(line)
    
    return lines


def format_weather_groups_list(weather_groups: List[Dict]) -> List[str]:
    """Format a list of weather phenomena
    
    Args:
        weather_groups: List of weather phenomena dictionaries
        
    Returns:
        List of formatted weather strings
    """
    lines: List[str] = []
    
    for wx in weather_groups:
        intensity = wx.get("intensity", "")
        descriptor = wx.get("descriptor", "")
        phenomena = wx.get("phenomena", [])

        if intensity or descriptor or phenomena:
            wx_text = []
            if intensity:
                wx_text.append(intensity)
            if descriptor:
                wx_text.append(descriptor)
            if phenomena:
                wx_text.append(", ".join(phenomena))

            lines.append(" ".join(wx_text))
    
    return lines

