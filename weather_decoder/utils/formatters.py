"""Formatting utilities for weather data"""

from typing import Dict


def format_wind(wind: Dict) -> str:
    """Format wind information into a readable string"""
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
    """Format visibility information into a readable string"""
    if visibility.get("is_cavok"):
        return "CAVOK (Ceiling and Visibility OK)"

    vis_value = visibility["value"]
    vis_unit = visibility["unit"]

    # Handle less than (M prefix for SM or 0000 for meters)
    if visibility.get("is_less_than"):
        if vis_unit == "SM":
            if isinstance(vis_value, float) and not vis_value.is_integer():
                result = f"Less than {vis_value} {vis_unit}"
            else:
                result = f"Less than {int(vis_value)} {vis_unit}"
        elif vis_value == 0:
            result = "Less than 50 M"
        else:
            result = f"Less than {vis_value} {vis_unit}"
    elif vis_value == 9999:
        result = "10 km or more"
    elif vis_unit == "M" and vis_value >= 1000 and vis_value <= 9000:
        # Format meter values to km if 1000 or greater
        km_value = vis_value / 1000
        result = f"{km_value:.1f} km" if km_value % 1 != 0 else f"{int(km_value)} km"
    elif visibility.get("is_greater_than"):
        if vis_unit == "SM":
            result = f"Greater than {vis_value} {vis_unit}"
        else:
            # If meters and greater than 1000, convert to km
            if vis_value >= 1000:
                km_value = vis_value / 1000
                result = f"Greater than {km_value:.1f} km" if km_value % 1 != 0 else f"Greater than {int(km_value)} km"
            else:
                result = f"Greater than {vis_value} {vis_unit}"
    else:
        # Handle fractional statute miles
        if vis_unit == "SM" and isinstance(vis_value, float):
            if vis_value.is_integer():
                result = f"{int(vis_value)} {vis_unit}"
            else:
                result = f"{vis_value} {vis_unit}"
        # Handle meters - convert to km if 1000 or greater
        elif vis_unit == "M" and vis_value >= 1000:
            km_value = vis_value / 1000
            result = f"{km_value:.1f} km" if km_value % 1 != 0 else f"{int(km_value)} km"
        else:
            result = f"{vis_value} {vis_unit}"

    # Add direction if present (directional visibility)
    if visibility.get("direction"):
        result += f" to the {visibility['direction']}"

    # Add directional visibility if present (e.g., "2000 1200NW")
    if visibility.get("directional_visibility"):
        dir_vis = visibility["directional_visibility"]
        dir_val = dir_vis["value"]
        dir_dir = dir_vis["direction"]
        if dir_val >= 1000:
            dir_km = dir_val / 1000
            dir_text = f"{dir_km:.1f} km" if dir_km % 1 != 0 else f"{int(dir_km)} km"
        else:
            dir_text = f"{dir_val} M"
        result += f", {dir_text} to the {dir_dir}"

    # Add NDV indicator if present (METAR specific)
    if visibility.get("ndv"):
        result += " (No Directional Variation)"

    return result


def format_temperature(temp_value: float) -> str:
    """Format temperature value"""
    return f"{temp_value}°C"


def format_pressure(pressure: Dict) -> str:
    """Format pressure information"""
    return f"{pressure['value']} {pressure['unit']}"


def format_sky_condition(sky: Dict) -> str:
    """Format a single sky condition"""
    if sky["type"] in ["CLR", "SKC"]:
        return "Clear skies"
    elif sky["type"] == "NSC":
        return "No significant cloud"
    elif sky["type"] == "NCD":
        return "No cloud detected"
    elif sky["type"] == "VV":
        if sky.get("unknown_height"):
            return "Vertical visibility (unknown height)"
        return f"Vertical visibility {sky['height']} feet"
    elif sky["type"] == "///":
        if sky.get("unknown_height"):
            return "Unknown cloud amount at unknown height"
        return f"Unknown cloud amount at {sky['height']} feet"
    else:
        # Handle unknown height
        if sky.get("unknown_height"):
            height_str = "unknown height"
        else:
            height_str = f"{sky['height']} feet"

        result = f"{sky['type']} clouds at {height_str}"
        if sky.get("cb"):
            result += " (CB)"
        elif sky.get("tcu"):
            result += " (TCU)"
        elif sky.get("unknown_type"):
            result += " (unknown type)"
        return result


def format_weather_group(weather: Dict) -> str:
    """Format a weather phenomena group"""
    parts = []

    if weather.get("intensity"):
        parts.append(weather["intensity"])

    if weather.get("descriptor"):
        parts.append(weather["descriptor"])

    if weather.get("phenomena"):
        parts.append(", ".join(weather["phenomena"]))

    return " ".join(parts) if parts else ""
