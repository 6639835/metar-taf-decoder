"""Ordered remarks handler registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple


@dataclass(frozen=True)
class RemarkHandler:
    method_name: str
    needs_positions: bool = False
    needs_report_time: bool = False

    def apply(
        self,
        parser: object,
        remarks: str,
        decoded: Dict[str, object],
        positions: Dict[str, int],
        report_time: Optional[Tuple[int, int, int]],
    ) -> None:
        method = getattr(parser, self.method_name)
        if self.needs_positions:
            method(remarks, decoded, positions)
        elif self.needs_report_time:
            method(remarks, decoded, report_time)
        else:
            method(remarks, decoded)


ORDERED_HANDLERS = [
    RemarkHandler("_parse_station_type", needs_positions=True, needs_report_time=False),
    RemarkHandler(
        "_parse_runway_winds", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_location_winds", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_sea_level_pressure", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_pressure_tendency", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_temperature_tenths", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_24hr_temperature_extremes",
        needs_positions=False,
        needs_report_time=False,
    ),
    RemarkHandler(
        "_parse_6hr_temperatures", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_6hr_precipitation", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_24hr_precipitation", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_snow_depth", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_water_equivalent_snow", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_sunshine_duration", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_ice_accretion", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_variable_visibility", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_sector_visibility", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_lower_visibility", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_jma_directional_visibility",
        needs_positions=False,
        needs_report_time=False,
    ),
    RemarkHandler(
        "_parse_visibility_second_location",
        needs_positions=False,
        needs_report_time=False,
    ),
    RemarkHandler(
        "_parse_thunderstorm_begin_end", needs_positions=False, needs_report_time=True
    ),
    RemarkHandler("_parse_past_weather", needs_positions=False, needs_report_time=True),
    RemarkHandler("_parse_qfe", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_altimeter_remarks", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_precipitation_amount", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_hailstone_size", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_snow_pellet_intensity", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_snincr", needs_positions=False, needs_report_time=False),
    RemarkHandler("_parse_peak_wind", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_surface_visibility", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_tower_visibility", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_lightning", needs_positions=False, needs_report_time=False),
    RemarkHandler("_parse_virga", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_directional_weather", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_thunderstorm_location", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_acsl", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_significant_cloud_remarks",
        needs_positions=False,
        needs_report_time=False,
    ),
    RemarkHandler("_parse_cloud_types", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_cloud_type_8group", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_variable_sky_condition", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_ceiling", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_ceiling_second_location", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_density_altitude", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_obscuration", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_obscuration_coded", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_qbb", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_pressure_change", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_p_fr_p_rr", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_frontal_passage", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_wind_shift", needs_positions=False, needs_report_time=False),
    RemarkHandler("_parse_slp_status", needs_positions=False, needs_report_time=False),
    RemarkHandler("_parse_rvr_status", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_runway_state_remarks", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_sensor_status", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_jma_pirep_turbulence", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_pirep_cloud_layers", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_jma_forecast_amendment", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_ri_precip_intensity", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler("_parse_acft_mshp", needs_positions=False, needs_report_time=False),
    RemarkHandler("_parse_nospeci", needs_positions=False, needs_report_time=False),
    RemarkHandler(
        "_parse_tornadic_activity", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_volcanic_eruption", needs_positions=False, needs_report_time=False
    ),
    RemarkHandler(
        "_parse_maintenance_indicator", needs_positions=True, needs_report_time=False
    ),
]


def iter_handlers() -> Iterable[RemarkHandler]:
    return ORDERED_HANDLERS
