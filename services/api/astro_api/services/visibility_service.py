from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
from zoneinfo import ZoneInfo


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def direction_label(azimuth_deg: float) -> str:
    directions = [
        "north",
        "northeast",
        "east",
        "southeast",
        "south",
        "southwest",
        "west",
        "northwest",
    ]
    index = round((azimuth_deg % 360) / 45) % len(directions)
    return directions[index]


def matches_region(region_bounds: dict | None, latitude: float, longitude: float) -> bool:
    if not region_bounds:
        return True
    lat_min = region_bounds.get("lat_min", -90.0)
    lat_max = region_bounds.get("lat_max", 90.0)
    lon_min = region_bounds.get("lon_min", -180.0)
    lon_max = region_bounds.get("lon_max", 180.0)
    return lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max


def solar_altitude_deg(timestamp: datetime, latitude: float, longitude: float) -> float:
    instant = ensure_utc(timestamp)
    day_of_year = instant.timetuple().tm_yday
    hour = instant.hour + instant.minute / 60 + instant.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hour - 12) / 24)
    declination = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    time_offset_minutes = equation_of_time + 4 * longitude
    true_solar_minutes = (hour * 60 + time_offset_minutes) % 1440
    hour_angle_deg = true_solar_minutes / 4 - 180
    if hour_angle_deg < -180:
        hour_angle_deg += 360
    latitude_rad = math.radians(latitude)
    hour_angle_rad = math.radians(hour_angle_deg)
    altitude_rad = math.asin(
        math.sin(latitude_rad) * math.sin(declination)
        + math.cos(latitude_rad) * math.cos(declination) * math.cos(hour_angle_rad)
    )
    return math.degrees(altitude_rad)


def sky_position(latitude: float, longitude: float, timestamp: datetime, coordinates: dict | None) -> tuple[float, float]:
    coordinates = coordinates or {}
    declination_deg = coordinates.get("declination_deg")
    preferred_local_hour = coordinates.get("preferred_local_hour")
    fallback_altitude = float(coordinates.get("peak_altitude_deg", 28.0))
    fallback_azimuth = float(coordinates.get("azimuth_deg", 180.0))

    if declination_deg is None or preferred_local_hour is None:
        return fallback_azimuth % 360, clamp(fallback_altitude, 0.0, 90.0)

    instant = ensure_utc(timestamp)
    local_solar_hour = (instant.hour + instant.minute / 60 + longitude / 15) % 24
    hour_angle_deg = (local_solar_hour - float(preferred_local_hour)) * 15
    latitude_rad = math.radians(latitude)
    declination_rad = math.radians(float(declination_deg))
    hour_angle_rad = math.radians(hour_angle_deg)

    altitude_rad = math.asin(
        math.sin(latitude_rad) * math.sin(declination_rad)
        + math.cos(latitude_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad)
    )
    altitude_deg = math.degrees(altitude_rad)

    denominator = math.cos(altitude_rad) * math.cos(latitude_rad)
    if abs(denominator) < 1e-6:
        azimuth_deg = fallback_azimuth
    else:
        cos_azimuth = (
            math.sin(declination_rad) - math.sin(altitude_rad) * math.sin(latitude_rad)
        ) / denominator
        cos_azimuth = clamp(cos_azimuth, -1.0, 1.0)
        azimuth_deg = math.degrees(math.acos(cos_azimuth))
        if math.sin(hour_angle_rad) > 0:
            azimuth_deg = 360 - azimuth_deg

    blended_altitude = altitude_deg * 0.78 + fallback_altitude * 0.22
    return azimuth_deg % 360, clamp(blended_altitude, 0.0, 90.0)


def magnitude_factor(magnitude: float | None) -> float:
    if magnitude is None:
        return 0.62
    return clamp((6.8 - magnitude) / 9.0, 0.12, 1.0)


def darkness_factor(timestamp: datetime, latitude: float, longitude: float) -> float:
    sun_altitude = solar_altitude_deg(timestamp, latitude, longitude)
    if sun_altitude <= -12:
        return 1.0
    if sun_altitude <= -6:
        return 0.84
    if sun_altitude <= 0:
        return 0.58
    return 0.18


@dataclass(slots=True)
class VisibilityAssessment:
    visibility_score: float
    visibility_label: str
    altitude_deg: float
    azimuth_deg: float
    direction: str
    night_factor: float
    brightness_factor: float
    duration_factor: float
    region_factor: float


def visibility_label(score: float) -> str:
    if score >= 0.72:
        return "Great"
    if score >= 0.48:
        return "Moderate"
    return "Low"


def best_viewing_time(
    timestamp: datetime,
    timezone_name: str,
    coordinates: dict | None,
    start_time: datetime,
    end_time: datetime,
) -> datetime:
    coordinates = coordinates or {}
    preferred_local_hour = coordinates.get("preferred_local_hour")
    if preferred_local_hour is None:
        return min(max(ensure_utc(timestamp), ensure_utc(start_time)), ensure_utc(end_time))

    timestamp = ensure_utc(timestamp)
    start_time = ensure_utc(start_time)
    end_time = ensure_utc(end_time)
    local = timestamp.astimezone()
    try:
        local = timestamp.astimezone(ZoneInfo(timezone_name))
    except Exception:
        local = timestamp.astimezone()
    preferred_hour = int(preferred_local_hour)
    preferred_minute = int(round((float(preferred_local_hour) - preferred_hour) * 60))
    candidate = local.replace(hour=preferred_hour, minute=preferred_minute, second=0, microsecond=0)
    candidate_utc = candidate.astimezone(UTC)
    if candidate_utc < start_time:
        candidate_utc += timedelta(days=1)
    return min(max(candidate_utc, start_time), end_time)


def evaluate_visibility(
    user_lat: float,
    user_lon: float,
    timestamp: datetime,
    coordinates: dict | None,
    magnitude: float | None,
    duration_minutes: float | None,
    region_bounds: dict | None,
) -> VisibilityAssessment:
    azimuth_deg, altitude_deg = sky_position(user_lat, user_lon, timestamp, coordinates)
    altitude_factor = clamp((altitude_deg + 5) / 70, 0.0, 1.0)
    night = darkness_factor(timestamp, user_lat, user_lon)
    brightness = magnitude_factor(magnitude)
    duration = clamp(((duration_minutes or 45) / 160), 0.18, 1.0)
    region = 1.0 if matches_region(region_bounds, user_lat, user_lon) else 0.2
    score = (
        altitude_factor * 0.36
        + night * 0.24
        + brightness * 0.18
        + duration * 0.12
        + region * 0.10
    )
    score = clamp(score)
    return VisibilityAssessment(
        visibility_score=score,
        visibility_label=visibility_label(score),
        altitude_deg=round(altitude_deg, 1),
        azimuth_deg=round(azimuth_deg, 1),
        direction=direction_label(azimuth_deg),
        night_factor=round(night, 3),
        brightness_factor=round(brightness, 3),
        duration_factor=round(duration, 3),
        region_factor=round(region, 3),
    )
