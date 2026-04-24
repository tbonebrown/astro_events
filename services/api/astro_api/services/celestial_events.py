from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import math

from sqlalchemy.orm import Session

from astro_api.config import AppSettings
from astro_api.repositories import (
    count_upcoming_celestial_events,
    get_cached_celestial_copy,
    get_celestial_event,
    get_event_visibility_cache,
    list_celestial_events,
    save_cached_celestial_copy,
    upsert_celestial_event,
    upsert_event_visibility,
)
from astro_api.services.llm import LocalInferenceClient
from astro_api.services.visibility_service import best_viewing_time, ensure_utc, evaluate_visibility


EVENT_TYPE_META = {
    "meteor_shower": {"rarity": 0.74, "importance": 0.81, "badge": "Meteor Shower"},
    "planetary_conjunction": {"rarity": 0.66, "importance": 0.72, "badge": "Conjunction"},
    "eclipse": {"rarity": 0.98, "importance": 0.98, "badge": "Eclipse"},
    "planet_visibility": {"rarity": 0.42, "importance": 0.6, "badge": "Planet Guide"},
    "iss_pass": {"rarity": 0.54, "importance": 0.68, "badge": "ISS Pass"},
    "comet": {"rarity": 0.88, "importance": 0.76, "badge": "Comet"},
    "lunar_phase": {"rarity": 0.3, "importance": 0.52, "badge": "Moon Phase"},
    "supermoon": {"rarity": 0.72, "importance": 0.7, "badge": "Supermoon"},
}

METEOR_SHOWERS = [
    {
        "slug": "quadrantids",
        "title": "Quadrantids meteor shower",
        "start": (1, 1),
        "peak": (1, 3, 8, 0),
        "end": (1, 8),
        "magnitude": 2.4,
        "description": "A brief but bright January shower with a compact peak that rewards a dark pre-dawn sky.",
        "region_bounds": {"lat_min": -10, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 49, "preferred_local_hour": 4.5, "azimuth_deg": 35, "peak_altitude_deg": 48},
    },
    {
        "slug": "lyrids",
        "title": "Lyrids meteor shower",
        "start": (4, 15),
        "peak": (4, 22, 6, 0),
        "end": (4, 29),
        "magnitude": 2.1,
        "description": "The Lyrids produce swift meteors and can surprise observers with occasional bright fireballs.",
        "region_bounds": {"lat_min": -20, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 34, "preferred_local_hour": 4.0, "azimuth_deg": 60, "peak_altitude_deg": 42},
    },
    {
        "slug": "eta-aquariids",
        "title": "Eta Aquariids meteor shower",
        "start": (4, 19),
        "peak": (5, 5, 9, 0),
        "end": (5, 28),
        "magnitude": 2.6,
        "description": "Halley's debris stream brings fast Eta Aquariid meteors, best before dawn from lower latitudes.",
        "region_bounds": {"lat_min": -65, "lat_max": 45, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": -1, "preferred_local_hour": 4.3, "azimuth_deg": 120, "peak_altitude_deg": 36},
    },
    {
        "slug": "perseids",
        "title": "Perseids meteor shower",
        "start": (7, 17),
        "peak": (8, 12, 3, 0),
        "end": (8, 24),
        "magnitude": 2.0,
        "description": "One of the most dependable meteor showers of the year, rich in bright meteors and long trains.",
        "region_bounds": {"lat_min": -25, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 58, "preferred_local_hour": 3.8, "azimuth_deg": 45, "peak_altitude_deg": 56},
    },
    {
        "slug": "orionids",
        "title": "Orionids meteor shower",
        "start": (10, 2),
        "peak": (10, 21, 10, 0),
        "end": (11, 7),
        "magnitude": 2.5,
        "description": "Another stream from Halley's Comet, with quick meteors radiating from Orion before dawn.",
        "region_bounds": {"lat_min": -55, "lat_max": 75, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 16, "preferred_local_hour": 4.7, "azimuth_deg": 110, "peak_altitude_deg": 40},
    },
    {
        "slug": "leonids",
        "title": "Leonids meteor shower",
        "start": (11, 6),
        "peak": (11, 17, 11, 0),
        "end": (11, 30),
        "magnitude": 2.4,
        "description": "The Leonids are usually modest, but their history includes dramatic meteor storms.",
        "region_bounds": {"lat_min": -40, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 22, "preferred_local_hour": 4.8, "azimuth_deg": 100, "peak_altitude_deg": 46},
    },
    {
        "slug": "geminids",
        "title": "Geminids meteor shower",
        "start": (12, 4),
        "peak": (12, 14, 2, 0),
        "end": (12, 20),
        "magnitude": 2.1,
        "description": "The Geminids are bright, abundant, and often the strongest all-around shower of the year.",
        "region_bounds": {"lat_min": -35, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 33, "preferred_local_hour": 2.0, "azimuth_deg": 95, "peak_altitude_deg": 50},
    },
]

PLANET_VISIBILITY = [
    {"name": "Mercury", "magnitude": -0.2, "preferred_local_hour": 19.6, "azimuth_deg": 285, "duration_minutes": 45, "observation": "binoculars recommended"},
    {"name": "Venus", "magnitude": -4.2, "preferred_local_hour": 5.2, "azimuth_deg": 95, "duration_minutes": 75, "observation": "naked eye"},
    {"name": "Mars", "magnitude": 0.7, "preferred_local_hour": 21.0, "azimuth_deg": 210, "duration_minutes": 140, "observation": "naked eye"},
    {"name": "Jupiter", "magnitude": -2.1, "preferred_local_hour": 4.7, "azimuth_deg": 110, "duration_minutes": 180, "observation": "naked eye"},
    {"name": "Saturn", "magnitude": 1.0, "preferred_local_hour": 4.1, "azimuth_deg": 135, "duration_minutes": 200, "observation": "naked eye or binoculars"},
]

FIXED_SPECIAL_EVENTS = [
    {
        "event_id": "eclipse-total-solar-2026-08-12",
        "title": "Total solar eclipse",
        "type": "eclipse",
        "start_time": datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
        "end_time": datetime(2026, 8, 12, 20, 30, tzinfo=UTC),
        "peak_time": datetime(2026, 8, 12, 17, 45, tzinfo=UTC),
        "magnitude": -26.7,
        "description": "A total solar eclipse with a narrow path of totality and a much wider partial-eclipse viewing region.",
        "region_bounds": {"lat_min": 35, "lat_max": 75, "lon_min": -60, "lon_max": 45},
        "coordinates": {"preferred_local_hour": 12.0, "azimuth_deg": 180, "peak_altitude_deg": 48},
        "observation": {"method": "certified solar glasses", "duration_minutes": 180},
        "source_name": "timeanddate_curated",
    },
    {
        "event_id": "eclipse-partial-lunar-2026-08-27",
        "title": "Partial lunar eclipse",
        "type": "eclipse",
        "start_time": datetime(2026, 8, 27, 18, 10, tzinfo=UTC),
        "end_time": datetime(2026, 8, 27, 22, 50, tzinfo=UTC),
        "peak_time": datetime(2026, 8, 27, 20, 30, tzinfo=UTC),
        "magnitude": -12.1,
        "description": "Earth's shadow takes a bite out of the Moon, creating an easy naked-eye eclipse event.",
        "region_bounds": {"lat_min": -75, "lat_max": 85, "lon_min": -30, "lon_max": 180},
        "coordinates": {"preferred_local_hour": 21.0, "azimuth_deg": 140, "peak_altitude_deg": 36},
        "observation": {"method": "naked eye", "duration_minutes": 280},
        "source_name": "timeanddate_curated",
    },
    {
        "event_id": "comet-watch-2026-09",
        "title": "Comet watch window",
        "type": "comet",
        "start_time": datetime(2026, 9, 3, 0, 0, tzinfo=UTC),
        "end_time": datetime(2026, 9, 18, 23, 59, tzinfo=UTC),
        "peak_time": datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
        "magnitude": 5.2,
        "description": "A diffuse small-body target is expected to be worth checking with binoculars in the western sky after dusk.",
        "region_bounds": {"lat_min": -40, "lat_max": 65, "lon_min": -180, "lon_max": 180},
        "coordinates": {"declination_deg": 14, "preferred_local_hour": 20.2, "azimuth_deg": 280, "peak_altitude_deg": 22},
        "observation": {"method": "binoculars or small telescope", "duration_minutes": 55},
        "source_name": "jpl_curated",
    },
]

NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
PERIGEE_EPOCH = datetime(2000, 1, 10, 11, 0, tzinfo=UTC)
SYNODIC_MONTH = 29.53058867
ANOMALISTIC_MONTH = 27.55454988


def slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-").replace("--", "-")


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def end_of_day(day: date) -> datetime:
    return datetime.combine(day, time.max, tzinfo=UTC)


def overlap(start_time: datetime, end_time: datetime, window_start: datetime, window_end: datetime) -> bool:
    return start_time <= window_end and end_time >= window_start


def day_fraction(target: datetime) -> float:
    seconds = (target - NEW_MOON_EPOCH).total_seconds() / 86400
    return seconds / SYNODIC_MONTH


def moon_declination(phase_index: int, phase_offset: float) -> float:
    return 18 * math.sin((phase_index + phase_offset) * 0.73)


def build_event(
    *,
    event_id: str,
    title: str,
    event_type: str,
    start_time: datetime,
    end_time: datetime,
    peak_time: datetime,
    description: str,
    magnitude: float | None,
    coordinates: dict,
    observation: dict,
    region_bounds: dict | None = None,
    source_name: str = "hybrid_catalog",
    source_payload: dict | None = None,
) -> dict:
    meta = EVENT_TYPE_META[event_type]
    duration_minutes = max((end_time - start_time).total_seconds() / 60, 1)
    return {
        "event_id": event_id,
        "title": title,
        "event_type": event_type,
        "source_name": source_name,
        "start_time": start_time,
        "end_time": end_time,
        "peak_time": peak_time,
        "magnitude": magnitude,
        "description": description,
        "region_bounds_json": region_bounds or {"lat_min": -90, "lat_max": 90, "lon_min": -180, "lon_max": 180},
        "coordinates_json": coordinates,
        "observation_json": {
            "method": observation.get("method", "naked eye"),
            "duration_minutes": observation.get("duration_minutes", round(duration_minutes)),
            "best_direction": observation.get("best_direction"),
        },
        "media_json": {
            "badge": meta["badge"],
            "palette": "aurora" if event_type in {"meteor_shower", "comet"} else "moonlight",
            "thumbnail_hint": event_type,
        },
        "source_payload_json": source_payload or {},
        "rarity_score": meta["rarity"],
        "importance_score": meta["importance"],
        "summary_seed": "",
    }


def meteor_shower_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    for year in range(window_start.year - 1, window_end.year + 2):
        for shower in METEOR_SHOWERS:
            start_time = start_of_day(date(year, shower["start"][0], shower["start"][1]))
            end_time = end_of_day(date(year, shower["end"][0], shower["end"][1]))
            peak_time = datetime(year, shower["peak"][0], shower["peak"][1], shower["peak"][2], shower["peak"][3], tzinfo=UTC)
            if not overlap(start_time, end_time, window_start, window_end):
                continue
            events.append(
                build_event(
                    event_id=f"meteor-{shower['slug']}-{year}",
                    title=shower["title"],
                    event_type="meteor_shower",
                    start_time=start_time,
                    end_time=end_time,
                    peak_time=peak_time,
                    description=shower["description"],
                    magnitude=shower["magnitude"],
                    coordinates=shower["coordinates"],
                    observation={"method": "naked eye", "duration_minutes": 120},
                    region_bounds=shower["region_bounds"],
                    source_name="annual_shower_catalog",
                )
            )
    return events


def lunar_phase_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    phase_templates = [
        ("New Moon", 0.0, "lunar_phase", 19.5, 270, 10, "Dark skies for deep-sky observing.", -0.2),
        ("First Quarter", 0.25, "lunar_phase", 20.0, 190, 42, "The Moon is half lit and rides high in the evening sky.", -10.4),
        ("Full Moon", 0.5, "lunar_phase", 22.0, 135, 38, "A bright Moon dominates the night and becomes an easy public-facing sky event.", -12.6),
        ("Last Quarter", 0.75, "lunar_phase", 4.5, 115, 35, "The half-lit Moon stands out before sunrise and pairs well with dawn observing.", -10.0),
    ]
    lunation_index_start = math.floor(day_fraction(window_start)) - 1
    lunation_index_end = math.ceil(day_fraction(window_end)) + 1
    for lunation_index in range(lunation_index_start, lunation_index_end + 1):
        base = NEW_MOON_EPOCH + timedelta(days=lunation_index * SYNODIC_MONTH)
        for title, phase_offset, event_type, local_hour, azimuth_deg, altitude_deg, description, magnitude in phase_templates:
            peak_time = base + timedelta(days=phase_offset * SYNODIC_MONTH)
            if not overlap(peak_time - timedelta(hours=10), peak_time + timedelta(hours=10), window_start, window_end):
                continue
            phase_kind = event_type
            phase_title = title
            if title == "Full Moon":
                perigee_index = round((peak_time - PERIGEE_EPOCH).total_seconds() / 86400 / ANOMALISTIC_MONTH)
                nearest_perigee = PERIGEE_EPOCH + timedelta(days=perigee_index * ANOMALISTIC_MONTH)
                if abs((peak_time - nearest_perigee).total_seconds()) <= 36 * 3600:
                    phase_kind = "supermoon"
                    phase_title = "Supermoon"
                    description = "A full Moon arrives close to lunar perigee, making it look a little larger and brighter than average."
            events.append(
                build_event(
                    event_id=f"{slugify(phase_title)}-{peak_time.date().isoformat()}",
                    title=phase_title,
                    event_type=phase_kind,
                    start_time=peak_time - timedelta(hours=12),
                    end_time=peak_time + timedelta(hours=12),
                    peak_time=peak_time,
                    description=description,
                    magnitude=magnitude,
                    coordinates={
                        "declination_deg": round(moon_declination(lunation_index, phase_offset), 1),
                        "preferred_local_hour": local_hour,
                        "azimuth_deg": azimuth_deg,
                        "peak_altitude_deg": altitude_deg,
                    },
                    observation={"method": "naked eye", "duration_minutes": 180},
                    source_name="lunar_cycle_model",
                )
            )
    return events


def planet_visibility_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    span_days = max((window_end - window_start).days, 1)
    for index, planet in enumerate(PLANET_VISIBILITY):
        phase = (window_start.timetuple().tm_yday / 365) + index * 0.17
        declination = 20 * math.sin(phase * math.tau)
        start_time = window_start
        end_time = min(window_end, window_start + timedelta(days=min(span_days, 10)))
        title = f"{planet['name']} visibility guide"
        description = (
            f"{planet['name']} is worth checking during its current viewing window, with the best look coming "
            f"{'before sunrise' if planet['preferred_local_hour'] < 12 else 'after sunset'}."
        )
        events.append(
            build_event(
                event_id=f"planet-{planet['name'].lower()}-{window_start.date().isoformat()}",
                title=title,
                event_type="planet_visibility",
                start_time=start_time,
                end_time=end_time,
                peak_time=start_time + (end_time - start_time) / 2,
                description=description,
                magnitude=planet["magnitude"],
                coordinates={
                    "declination_deg": round(declination, 1),
                    "preferred_local_hour": planet["preferred_local_hour"],
                    "azimuth_deg": planet["azimuth_deg"],
                    "peak_altitude_deg": 34 + index * 3,
                },
                observation={
                    "method": planet["observation"],
                    "duration_minutes": planet["duration_minutes"],
                },
                source_name="planet_visibility_model",
            )
        )
    return events


def conjunction_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    conjunction_offsets = [
        ("Moon and Mars close approach", "Mars", 4.8, 20.7),
        ("Moon and Jupiter close approach", "Jupiter", 9.2, 4.9),
        ("Moon and Saturn close approach", "Saturn", 22.0, 4.1),
    ]
    lunation_index_start = math.floor(day_fraction(window_start)) - 1
    lunation_index_end = math.ceil(day_fraction(window_end)) + 1
    planet_by_name = {planet["name"]: planet for planet in PLANET_VISIBILITY}
    for lunation_index in range(lunation_index_start, lunation_index_end + 1):
        base = NEW_MOON_EPOCH + timedelta(days=lunation_index * SYNODIC_MONTH)
        for title, planet_name, day_offset, local_hour in conjunction_offsets:
            peak_time = base + timedelta(days=day_offset)
            if not overlap(peak_time - timedelta(hours=6), peak_time + timedelta(hours=6), window_start, window_end):
                continue
            planet = planet_by_name[planet_name]
            events.append(
                build_event(
                    event_id=f"conjunction-{planet_name.lower()}-{peak_time.date().isoformat()}",
                    title=title,
                    event_type="planetary_conjunction",
                    start_time=peak_time - timedelta(hours=8),
                    end_time=peak_time + timedelta(hours=8),
                    peak_time=peak_time,
                    description=f"The Moon slides close to {planet_name}, creating an easy-to-spot pairing for casual skywatching.",
                    magnitude=planet["magnitude"],
                    coordinates={
                        "declination_deg": round(14 * math.sin((lunation_index + day_offset / 29.5) * 1.12), 1),
                        "preferred_local_hour": local_hour,
                        "azimuth_deg": planet["azimuth_deg"],
                        "peak_altitude_deg": 28 if local_hour < 12 else 38,
                    },
                    observation={"method": "naked eye or binoculars", "duration_minutes": 70},
                    source_name="lunar_pairing_model",
                )
            )
    return events


def iss_pass_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    cursor = window_start.date()
    toggle = 0
    while cursor <= window_end.date():
        local_hour = 20.4 if toggle % 2 == 0 else 4.8
        title = "ISS visibility window"
        events.append(
            build_event(
                event_id=f"iss-pass-{cursor.isoformat()}-{toggle % 2}",
                title=title,
                event_type="iss_pass",
                start_time=start_of_day(cursor),
                end_time=end_of_day(cursor),
                peak_time=start_of_day(cursor) + timedelta(hours=local_hour),
                description="A modeled International Space Station pass window. Exact pass timing varies by town, but this gives a strong observing slot.",
                magnitude=-3.3,
                coordinates={
                    "declination_deg": round(44 * math.sin(cursor.toordinal() * 0.11), 1),
                    "preferred_local_hour": local_hour,
                    "azimuth_deg": 250 if local_hour > 12 else 120,
                    "peak_altitude_deg": 50,
                },
                observation={"method": "naked eye", "duration_minutes": 8},
                region_bounds={"lat_min": -60, "lat_max": 60, "lon_min": -180, "lon_max": 180},
                source_name="iss_visibility_model",
            )
        )
        cursor += timedelta(days=3)
        toggle += 1
    return events


def fixed_events(window_start: datetime, window_end: datetime) -> list[dict]:
    events: list[dict] = []
    for raw in FIXED_SPECIAL_EVENTS:
        if not overlap(raw["start_time"], raw["end_time"], window_start, window_end):
            continue
        events.append(
            build_event(
                event_id=raw["event_id"],
                title=raw["title"],
                event_type=raw["type"],
                start_time=raw["start_time"],
                end_time=raw["end_time"],
                peak_time=raw["peak_time"],
                description=raw["description"],
                magnitude=raw["magnitude"],
                coordinates=raw["coordinates"],
                observation=raw["observation"],
                region_bounds=raw["region_bounds"],
                source_name=raw["source_name"],
            )
        )
    return events


def generate_catalog(window_start: datetime, window_end: datetime) -> list[dict]:
    events = []
    events.extend(meteor_shower_events(window_start, window_end))
    events.extend(lunar_phase_events(window_start, window_end))
    events.extend(planet_visibility_events(window_start, window_end))
    events.extend(conjunction_events(window_start, window_end))
    events.extend(iss_pass_events(window_start, window_end))
    events.extend(fixed_events(window_start, window_end))
    return sorted(events, key=lambda event: (event["peak_time"], event["title"]))


def rounded_region_key(latitude: float, longitude: float) -> str:
    return f"{round(latitude / 5) * 5:.0f}:{round(longitude / 5) * 5:.0f}"


@dataclass(slots=True)
class CelestialEventsService:
    settings: AppSettings
    llm_client: LocalInferenceClient

    def ensure_catalog(self, session: Session, horizon_days: int = 30) -> None:
        now = datetime.now(UTC)
        if count_upcoming_celestial_events(session, now=now) >= 12:
            return
        window_start = now - timedelta(days=1)
        window_end = now + timedelta(days=max(horizon_days, 45))
        for payload in generate_catalog(window_start, window_end):
            upsert_celestial_event(session, payload)
        session.commit()

    def list_feed(
        self,
        session: Session,
        *,
        user_lat: float | None = None,
        user_lon: float | None = None,
        timezone_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_type: str | None = None,
        min_visibility: float | None = None,
    ) -> list[dict]:
        self.ensure_catalog(session, horizon_days=max(((end_time or datetime.now(UTC)) - (start_time or datetime.now(UTC))).days, 30))
        rows = list_celestial_events(
            session,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
        )
        presented = [
            self._present_event(
                session,
                event,
                user_lat=user_lat,
                user_lon=user_lon,
                timezone_name=timezone_name,
            )
            for event in rows
        ]
        if min_visibility is None or user_lat is None or user_lon is None:
            return presented
        return [
            event
            for event in presented
            if event["visibility_score"] >= min_visibility
        ]

    def personalized_feed(
        self,
        session: Session,
        *,
        user_lat: float,
        user_lon: float,
        timezone_name: str,
        days: int = 14,
        event_type: str | None = None,
        min_visibility: float | None = None,
    ) -> dict:
        now = datetime.now(UTC)
        events = self.list_feed(
            session,
            user_lat=user_lat,
            user_lon=user_lon,
            timezone_name=timezone_name,
            start_time=now,
            end_time=now + timedelta(days=max(1, min(days, 30))),
            event_type=event_type,
            min_visibility=min_visibility,
        )
        for event in events:
            event["personalized_rank"] = round(
                event["visibility_score"] * 0.46
                + event["rarity_score"] * 0.24
                + event["brightness_score"] * 0.18
                + event["importance_score"] * 0.12,
                4,
            )
        events.sort(key=lambda event: (-event["personalized_rank"], event["best_viewing_time"]))
        for event in events:
            cached = get_cached_celestial_copy(
                session,
                event_id=event["event_id"],
                latitude=user_lat,
                longitude=user_lon,
                timezone_name=timezone_name,
            )
            if cached is not None:
                event["summary"] = cached.summary
                event["why_interesting"] = cached.why_interesting
        tonight_cutoff = now + timedelta(hours=24)
        tonight = [event for event in events if event["best_viewing_time"] <= tonight_cutoff][:3]
        return {
            "requested_location": {
                "latitude": user_lat,
                "longitude": user_lon,
                "timezone": timezone_name,
            },
            "generated_at": now,
            "tonight_summary": {
                "headline": tonight[0]["title"] if tonight else "A calm sky tonight",
                "summary": tonight[0].get("summary", tonight[0]["description"]) if tonight else "No strong sky events made the threshold tonight.",
                "count": len(tonight),
            },
            "events": events,
        }

    def event_detail(
        self,
        session: Session,
        event_id: str,
        *,
        user_lat: float | None = None,
        user_lon: float | None = None,
        timezone_name: str | None = None,
    ) -> dict | None:
        self.ensure_catalog(session)
        event = get_celestial_event(session, event_id)
        if event is None:
            return None
        detail = self._present_event(
            session,
            event,
            user_lat=user_lat,
            user_lon=user_lon,
            timezone_name=timezone_name,
        )
        detail["source_name"] = event.source_name
        detail["source_payload"] = event.source_payload_json
        detail["observation"] = event.observation_json
        return detail

    def get_or_generate_copy(
        self,
        session: Session,
        *,
        event_id: str,
        user_lat: float,
        user_lon: float,
        timezone_name: str,
    ) -> dict:
        cached = get_cached_celestial_copy(
            session,
            event_id=event_id,
            latitude=user_lat,
            longitude=user_lon,
            timezone_name=timezone_name,
        )
        if cached is not None:
            return {
                "summary": cached.summary,
                "why_interesting": cached.why_interesting,
                "explanation": cached.explanation,
                "source": cached.source,
            }

        event = get_celestial_event(session, event_id)
        if event is None:
            raise ValueError(f"Unknown event: {event_id}")
        view = self._present_event(
            session,
            event,
            user_lat=user_lat,
            user_lon=user_lon,
            timezone_name=timezone_name,
        )
        copy = self.llm_client.celestial_event_copy(view)
        save_cached_celestial_copy(
            session,
            {
                "event_id": event_id,
                "latitude": user_lat,
                "longitude": user_lon,
                "timezone_name": timezone_name,
                "summary": copy["summary"],
                "why_interesting": copy["why_interesting"],
                "explanation": copy["explanation"],
                "source": copy["source"],
            },
        )
        session.commit()
        return copy

    def _present_event(
        self,
        session: Session,
        event,
        *,
        user_lat: float | None,
        user_lon: float | None,
        timezone_name: str | None,
    ) -> dict:
        region_key = None
        assessment = None
        start_time = ensure_utc(event.start_time)
        end_time = ensure_utc(event.end_time)
        peak_time = ensure_utc(event.peak_time or event.start_time)
        best_time = peak_time
        if user_lat is not None and user_lon is not None:
            region_key = rounded_region_key(user_lat, user_lon)
            cached_visibility = get_event_visibility_cache(session, event.event_id, region_key)
            if cached_visibility is not None:
                assessment_payload = cached_visibility.summary_json
                assessment = {
                    "visibility_score": cached_visibility.visibility_score,
                    "visibility_label": assessment_payload.get("visibility_label", "Moderate"),
                    "altitude_deg": assessment_payload.get("altitude_deg"),
                    "azimuth_deg": assessment_payload.get("azimuth_deg"),
                    "direction": assessment_payload.get("direction"),
                }
                best_time = ensure_utc(cached_visibility.best_viewing_time)
            else:
                best_time = best_viewing_time(
                    peak_time,
                    timezone_name or "UTC",
                    event.coordinates_json,
                    start_time,
                    end_time,
                )
                measured = evaluate_visibility(
                    user_lat,
                    user_lon,
                    best_time,
                    event.coordinates_json,
                    event.magnitude,
                    event.observation_json.get("duration_minutes"),
                    event.region_bounds_json,
                )
                assessment = {
                    "visibility_score": measured.visibility_score,
                    "visibility_label": measured.visibility_label,
                    "altitude_deg": measured.altitude_deg,
                    "azimuth_deg": measured.azimuth_deg,
                    "direction": measured.direction,
                }
                upsert_event_visibility(
                    session,
                    {
                        "event_id": event.event_id,
                        "region_key": region_key,
                        "latitude": user_lat,
                        "longitude": user_lon,
                        "visibility_score": measured.visibility_score,
                        "best_viewing_time": best_time,
                        "summary_json": {
                            "visibility_label": measured.visibility_label,
                            "altitude_deg": measured.altitude_deg,
                            "azimuth_deg": measured.azimuth_deg,
                            "direction": measured.direction,
                        },
                    },
                )
                session.flush()

        brightness_score = max(0.12, min(1.0, (6.8 - (event.magnitude or 1.2)) / 9.0))
        response = {
            "event_id": event.event_id,
            "title": event.title,
            "type": event.event_type,
            "start_time": start_time,
            "end_time": end_time,
            "peak_time": peak_time,
            "best_viewing_time": best_time,
            "visibility_score": assessment["visibility_score"] if assessment else 0.58,
            "visibility_label": assessment["visibility_label"] if assessment else "Moderate",
            "magnitude": event.magnitude,
            "brightness_score": round(brightness_score, 3),
            "description": event.description,
            "region_applicability": event.region_bounds_json,
            "rarity_score": event.rarity_score,
            "importance_score": event.importance_score,
            "sky_position": {
                "azimuth_deg": assessment["azimuth_deg"] if assessment else event.coordinates_json.get("azimuth_deg"),
                "altitude_deg": assessment["altitude_deg"] if assessment else event.coordinates_json.get("peak_altitude_deg"),
                "direction": assessment["direction"] if assessment else "south",
            },
            "observation_method": event.observation_json.get("method", "naked eye"),
            "duration_minutes": event.observation_json.get("duration_minutes"),
            "thumbnail": event.media_json,
            "summary": event.summary_seed or self.llm_client.fallback_celestial_summary(
                {
                    "title": event.title,
                    "type": event.event_type,
                    "description": event.description,
                    "visibility_label": assessment["visibility_label"] if assessment else "Moderate",
                    "best_viewing_time": best_time.isoformat(),
                    "observation_method": event.observation_json.get("method", "naked eye"),
                    "sky_position": {
                        "direction": assessment["direction"] if assessment else "south",
                        "altitude_deg": assessment["altitude_deg"] if assessment else event.coordinates_json.get("peak_altitude_deg"),
                    },
                }
            ),
            "why_interesting": "",
        }
        return response
