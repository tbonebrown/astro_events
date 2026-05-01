from __future__ import annotations

import re


DEMO_TARGETS: list[dict] = [
    {
        "target_id": "kepler-10",
        "name": "Kepler-10",
        "aliases": ["KIC 11904151", "KIC11904151", "Kepler-10 b"],
        "mission": "Kepler",
        "description": "Compact Kepler system with a visually crisp short-period transit signal.",
        "ra": 285.679421,
        "dec": 50.241305,
        "known_period_days": 0.837491,
        "known_planet": "Kepler-10 b",
        "expected_depth_ppm": 152.0,
    },
    {
        "target_id": "kepler-22",
        "name": "Kepler-22",
        "aliases": ["KIC 10593626", "KIC10593626", "Kepler-22 b"],
        "mission": "Kepler",
        "description": "A famous long-period confirmed planet host; useful for archive matching demos.",
        "ra": 289.862,
        "dec": 47.887,
        "known_period_days": 289.8623,
        "known_planet": "Kepler-22 b",
        "expected_depth_ppm": 492.0,
    },
    {
        "target_id": "kepler-186",
        "name": "Kepler-186",
        "aliases": ["KIC 8120608", "KIC8120608", "Kepler-186 f"],
        "mission": "Kepler",
        "description": "Multi-planet Kepler system with several periodic transit signatures.",
        "ra": 298.472,
        "dec": 43.955,
        "known_period_days": 3.88679,
        "known_planet": "Kepler-186 b",
        "expected_depth_ppm": 420.0,
    },
    {
        "target_id": "wasp-12",
        "name": "WASP-12",
        "aliases": ["TIC 86396382", "WASP-12 b"],
        "mission": "TESS",
        "description": "Hot Jupiter host with deep transits that are excellent for public demos.",
        "ra": 97.637,
        "dec": 29.672,
        "known_period_days": 1.09142,
        "known_planet": "WASP-12 b",
        "expected_depth_ppm": 14000.0,
    },
    {
        "target_id": "hat-p-7",
        "name": "HAT-P-7",
        "aliases": ["KIC 10666592", "KIC10666592", "HAT-P-7 b", "Kepler-2"],
        "mission": "Kepler",
        "description": "Bright hot Jupiter host with a strong folded transit and phase-curve context.",
        "ra": 292.247,
        "dec": 47.969,
        "known_period_days": 2.20473,
        "known_planet": "HAT-P-7 b",
        "expected_depth_ppm": 6800.0,
    },
    {
        "target_id": "toi-700",
        "name": "TOI-700",
        "aliases": ["TIC 150428135", "TOI-700 d"],
        "mission": "TESS",
        "description": "Well-known TESS multi-planet system with confirmed planets and TOI context.",
        "ra": 96.406,
        "dec": -65.577,
        "known_period_days": 9.977,
        "known_planet": "TOI-700 b",
        "expected_depth_ppm": 900.0,
    },
]


def normalize_identifier(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9.+-]+", "-", normalized)
    return normalized.strip("-")


def demo_target_for_query(query: str) -> dict | None:
    normalized = normalize_identifier(query)
    for target in DEMO_TARGETS:
        candidates = [target["target_id"], target["name"], *target["aliases"]]
        if normalized in {normalize_identifier(candidate) for candidate in candidates}:
            return dict(target)
    return None


def parse_coordinates(query: str) -> tuple[float, float] | None:
    parts = re.split(r"[\s,]+", query.strip())
    if len(parts) < 2:
        return None
    try:
        ra = float(parts[0])
        dec = float(parts[1])
    except ValueError:
        return None
    if 0.0 <= ra <= 360.0 and -90.0 <= dec <= 90.0:
        return ra, dec
    return None


def resolve_target(query: str, target_type: str = "auto", mission: str = "auto") -> dict:
    query = query.strip()
    demo = demo_target_for_query(query)
    if demo:
        if mission != "auto":
            demo["mission"] = mission
        demo["query"] = query
        demo["resolver"] = "curated_demo"
        return demo

    coordinates = parse_coordinates(query)
    if target_type == "coordinates" or coordinates:
        ra, dec = coordinates or (None, None)
        return {
            "target_id": f"coord-{normalize_identifier(query)}",
            "name": query,
            "aliases": [],
            "mission": "TESS" if mission == "auto" else mission,
            "description": "Resolved from RA/Dec coordinates supplied by the user.",
            "ra": ra,
            "dec": dec,
            "known_period_days": None,
            "known_planet": None,
            "expected_depth_ppm": None,
            "query": query,
            "resolver": "coordinates",
        }

    tic_match = re.search(r"(?:tic\s*)?(\d{5,})", query, flags=re.IGNORECASE)
    if target_type == "tic" or (tic_match and query.lower().strip().startswith("tic")):
        tic_id = tic_match.group(1) if tic_match else query
        return {
            "target_id": f"tic-{tic_id}",
            "name": f"TIC {tic_id}",
            "aliases": [query],
            "mission": "TESS" if mission == "auto" else mission,
            "description": "TESS Input Catalog target supplied by the user.",
            "ra": None,
            "dec": None,
            "known_period_days": None,
            "known_planet": None,
            "expected_depth_ppm": None,
            "query": f"TIC {tic_id}",
            "resolver": "tic",
        }

    kic_match = re.search(r"(?:kic\s*)?(\d{5,})", query, flags=re.IGNORECASE)
    if target_type == "kic" or (kic_match and query.lower().strip().startswith("kic")):
        kic_id = kic_match.group(1) if kic_match else query
        return {
            "target_id": f"kic-{kic_id}",
            "name": f"KIC {kic_id}",
            "aliases": [query],
            "mission": "Kepler" if mission == "auto" else mission,
            "description": "Kepler Input Catalog target supplied by the user.",
            "ra": None,
            "dec": None,
            "known_period_days": None,
            "known_planet": None,
            "expected_depth_ppm": None,
            "query": f"KIC {kic_id}",
            "resolver": "kic",
        }

    return {
        "target_id": normalize_identifier(query),
        "name": query,
        "aliases": [],
        "mission": "TESS" if mission == "auto" else mission,
        "description": "Named target resolved through the selected mission archive.",
        "ra": None,
        "dec": None,
        "known_period_days": None,
        "known_planet": None,
        "expected_depth_ppm": None,
        "query": query,
        "resolver": "name",
    }
