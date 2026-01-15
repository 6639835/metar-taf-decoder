"""Common formatting utilities for decoded weather data."""

from __future__ import annotations

from typing import List, Optional

from ..models import (
    DirectionalVisibility,
    MinimumVisibility,
    SkyCondition,
    Visibility,
    WeatherPhenomenon,
    Wind,
)


def format_wind(wind: Optional[Wind]) -> str:
    if wind is None:
        return "Not reported"

    if wind.is_variable or wind.direction is None:
        direction_text = "Variable"
    else:
        direction_text = f"{wind.direction}°"

    if wind.is_above:
        speed_text = f"above {wind.speed} {wind.unit}"
    else:
        speed_text = f"{wind.speed} {wind.unit}"

    if wind.gust:
        speed_text += f", gusting to {wind.gust} {wind.unit}"

    if wind.variable_range:
        from_dir, to_dir = wind.variable_range
        speed_text += f" (varying between {from_dir}° and {to_dir}°)"

    return f"{direction_text} at {speed_text}"


def format_visibility(visibility: Optional[Visibility]) -> str:
    if visibility is None:
        return "Not reported"

    if visibility.is_cavok:
        return "CAVOK (Ceiling and Visibility OK)"

    vis_value = visibility.value
    vis_unit = visibility.unit

    if visibility.is_less_than:
        result = _format_less_than_visibility(vis_value, vis_unit)
    elif vis_value == 9999:
        result = "10 km or more"
    elif vis_unit == "M" and 1000 <= vis_value <= 9000:
        result = _format_km_visibility(vis_value)
    elif visibility.is_greater_than:
        result = _format_greater_than_visibility(vis_value, vis_unit)
    else:
        result = _format_standard_visibility(vis_value, vis_unit)

    if visibility.direction:
        result += f" to the {visibility.direction}"

    if visibility.directional_visibility:
        result += f", {_format_directional_visibility(visibility.directional_visibility)}"

    if visibility.minimum_visibility:
        result += f" (minimum {_format_minimum_visibility(visibility.minimum_visibility)})"

    if visibility.ndv:
        result += " (No Directional Variation)"

    return result


def format_temperature(temp_value: Optional[float]) -> str:
    if temp_value is None:
        return "Not reported"
    return f"{temp_value}°C"


def format_pressure(pressure) -> str:
    if pressure is None:
        return "Not reported"
    return f"{pressure.value} {pressure.unit}"


def format_sky_condition(sky: SkyCondition) -> str:
    sky_type = sky.coverage

    if sky_type in ["CLR", "SKC"]:
        return "Clear skies"
    if sky_type == "NSC":
        return "No significant cloud"
    if sky_type == "NCD":
        return "No cloud detected"
    if sky_type == "VV":
        if sky.unknown_height or sky.height is None:
            return "Vertical visibility (unknown height)"
        return f"Vertical visibility {sky.height} feet"
    if sky_type == "///":
        if sky.unknown_height:
            return "Unknown cloud amount at unknown height"
        return f"Unknown cloud amount at {sky.height} feet"

    height_str = "unknown height" if sky.unknown_height or sky.height is None else f"{sky.height} feet"
    result = f"{sky_type} clouds at {height_str}"

    if sky.cb:
        result += " (CB)"
    elif sky.tcu:
        result += " (TCU)"
    elif sky.unknown_type:
        result += " (unknown type)"

    return result


def format_weather_group(weather: WeatherPhenomenon) -> str:
    parts: List[str] = []

    if weather.intensity:
        parts.append(weather.intensity)

    if weather.descriptor:
        parts.append(weather.descriptor)

    if weather.phenomena:
        parts.append(", ".join(weather.phenomena))

    return " ".join(parts) if parts else ""


def format_sky_conditions_list(sky_conditions: List[SkyCondition]) -> List[str]:
    return [format_sky_condition(sky) for sky in sky_conditions]


def format_weather_groups_list(weather_groups: List[WeatherPhenomenon]) -> List[str]:
    lines: List[str] = []

    for wx in weather_groups:
        wx_text = format_weather_group(wx)
        if wx_text:
            lines.append(wx_text)

    return lines


def _format_less_than_visibility(vis_value: float, vis_unit: str) -> str:
    if vis_unit == "SM":
        if isinstance(vis_value, float) and not vis_value.is_integer():
            return f"Less than {vis_value} {vis_unit}"
        return f"Less than {int(vis_value)} {vis_unit}"
    if vis_value == 0:
        return "Less than 50 M"
    return f"Less than {vis_value} {vis_unit}"


def _format_km_visibility(vis_value: float) -> str:
    km_value = vis_value / 1000
    if km_value % 1 != 0:
        return f"{km_value:.1f} km"
    return f"{int(km_value)} km"


def _format_greater_than_visibility(vis_value: float, vis_unit: str) -> str:
    if vis_unit == "SM":
        return f"Greater than {vis_value} {vis_unit}"
    if vis_value >= 1000:
        km_value = vis_value / 1000
        if km_value % 1 != 0:
            return f"Greater than {km_value:.1f} km"
        return f"Greater than {int(km_value)} km"
    return f"Greater than {vis_value} {vis_unit}"


def _format_standard_visibility(vis_value: float, vis_unit: str) -> str:
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


def _format_directional_visibility(dir_vis: DirectionalVisibility) -> str:
    if dir_vis.value >= 1000:
        dir_km = dir_vis.value / 1000
        dir_text = f"{dir_km:.1f} km" if dir_km % 1 != 0 else f"{int(dir_km)} km"
    else:
        dir_text = f"{dir_vis.value} M"
    return f"{dir_text} to the {dir_vis.direction}"


def _format_minimum_visibility(min_vis: MinimumVisibility) -> str:
    if min_vis.value >= 1000:
        min_km = min_vis.value / 1000
        return f"{min_km:.1f} km" if min_km % 1 != 0 else f"{int(min_km)} km"
    return f"{min_vis.value} M"
