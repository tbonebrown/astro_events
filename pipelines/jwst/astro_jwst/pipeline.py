from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import math
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


FAMILY_DEFINITIONS = [
    {
        "cluster_id": 0,
        "cluster_name": "Grand Design Spirals",
        "plain_name": "Spiral cities",
        "scientific_label": "Grand design spiral galaxy",
        "simple_label": "Large spiral galaxy",
        "summary": "Orderly spiral disks with bright arms and clear central bulges anchor the low-redshift end of the map.",
        "plain_summary": "These galaxies have the classic pinwheel look people expect from spiral galaxies.",
        "morphology_tags": ["spiral arms", "disk", "bulge"],
        "source_field": "CEERS",
        "instrument": "NIRCam",
        "filter_band": "F200W",
        "redshift_center": 1.1,
        "magnitude_center": 24.3,
        "count_fraction": 0.1,
        "shape": "spiral",
    },
    {
        "cluster_id": 1,
        "cluster_name": "Barred Spirals",
        "plain_name": "Barred spirals",
        "scientific_label": "Barred spiral galaxy",
        "simple_label": "Barred spiral",
        "summary": "A bar-like ridge crosses the inner disk, making these systems easy to separate from cleaner two-arm spirals.",
        "plain_summary": "These spirals show a bright straight bar through the middle before the arms curve away.",
        "morphology_tags": ["bar", "spiral arms", "disk"],
        "source_field": "COSMOS-Web",
        "instrument": "NIRCam",
        "filter_band": "F277W",
        "redshift_center": 1.6,
        "magnitude_center": 24.9,
        "count_fraction": 0.08,
        "shape": "barred",
    },
    {
        "cluster_id": 2,
        "cluster_name": "Edge-On Disks",
        "plain_name": "Thin edge-on disks",
        "scientific_label": "Edge-on disk galaxy",
        "simple_label": "Edge-on disk",
        "summary": "Flattened profiles with dust lanes and elongated light distributions cluster together in a narrow band.",
        "plain_summary": "These are disk galaxies viewed from the side, so they look thin and stretched out.",
        "morphology_tags": ["edge-on disk", "dust lane", "elongated profile"],
        "source_field": "PRIMER",
        "instrument": "NIRCam",
        "filter_band": "F356W",
        "redshift_center": 2.2,
        "magnitude_center": 25.4,
        "count_fraction": 0.08,
        "shape": "edge_on",
    },
    {
        "cluster_id": 3,
        "cluster_name": "Smooth Ellipticals",
        "plain_name": "Smooth ellipticals",
        "scientific_label": "Elliptical galaxy",
        "simple_label": "Smooth elliptical",
        "summary": "Compact, centrally concentrated light profiles produce a quiet island of smooth morphologies.",
        "plain_summary": "These galaxies look rounded and smooth, with little sign of arms or clumpy structure.",
        "morphology_tags": ["smooth halo", "central concentration", "low asymmetry"],
        "source_field": "JADES",
        "instrument": "NIRCam",
        "filter_band": "F444W",
        "redshift_center": 2.8,
        "magnitude_center": 25.8,
        "count_fraction": 0.09,
        "shape": "elliptical",
    },
    {
        "cluster_id": 4,
        "cluster_name": "Lenticular Bridges",
        "plain_name": "Lens-like disks",
        "scientific_label": "Lenticular galaxy",
        "simple_label": "Lens-shaped disk",
        "summary": "These galaxies sit between disk-rich and smooth systems, with subdued arms and strong central light.",
        "plain_summary": "This group bridges spirals and ellipticals, looking like disks with very little visible arm structure.",
        "morphology_tags": ["smooth disk", "faded arms", "bright core"],
        "source_field": "CEERS",
        "instrument": "NIRCam",
        "filter_band": "F150W",
        "redshift_center": 2.0,
        "magnitude_center": 25.1,
        "count_fraction": 0.07,
        "shape": "lenticular",
    },
    {
        "cluster_id": 5,
        "cluster_name": "Ring Systems",
        "plain_name": "Ring galaxies",
        "scientific_label": "Ring galaxy",
        "simple_label": "Ring galaxy",
        "summary": "A bright shell or ring dominates the light profile, often hinting at resonances or past interactions.",
        "plain_summary": "These galaxies stand out because much of their light sits in a ring around the center.",
        "morphology_tags": ["ring", "central core", "structured outer light"],
        "source_field": "SMACS 0723",
        "instrument": "NIRCam",
        "filter_band": "F200W",
        "redshift_center": 3.5,
        "magnitude_center": 26.4,
        "count_fraction": 0.06,
        "shape": "ring",
    },
    {
        "cluster_id": 6,
        "cluster_name": "Merger Front",
        "plain_name": "Merging systems",
        "scientific_label": "Disturbed merger system",
        "simple_label": "Merging galaxies",
        "summary": "Strong asymmetry, double cores, and tidal distortions push these objects away from regular morphology families.",
        "plain_summary": "These galaxies look unsettled because two systems are colliding or have recently collided.",
        "morphology_tags": ["tidal debris", "double core", "asymmetry"],
        "source_field": "GLASS",
        "instrument": "NIRCam",
        "filter_band": "F356W",
        "redshift_center": 4.2,
        "magnitude_center": 26.7,
        "count_fraction": 0.09,
        "shape": "merger",
    },
    {
        "cluster_id": 7,
        "cluster_name": "Clumpy Starbursts",
        "plain_name": "Clumpy starbursts",
        "scientific_label": "Clumpy star-forming galaxy",
        "simple_label": "Clumpy young galaxy",
        "summary": "Small, knotty light concentrations dominate these actively star-forming galaxies in the early universe.",
        "plain_summary": "These young galaxies look patchy because bright star-forming regions stand out more than an organized disk.",
        "morphology_tags": ["clumpy light", "star-forming knots", "irregular disk"],
        "source_field": "JADES",
        "instrument": "NIRCam",
        "filter_band": "F277W",
        "redshift_center": 5.1,
        "magnitude_center": 27.1,
        "count_fraction": 0.11,
        "shape": "clumpy",
    },
    {
        "cluster_id": 8,
        "cluster_name": "Tidal Tail Group",
        "plain_name": "Tidal tails",
        "scientific_label": "Tidal-tail system",
        "simple_label": "Tidal-tail galaxy",
        "summary": "Long, faint extensions in the light profile make this cluster a good showcase for interaction-driven structure.",
        "plain_summary": "These galaxies have stretched tails of stars and gas pulled out by gravitational encounters.",
        "morphology_tags": ["tidal tail", "disturbed halo", "interaction"],
        "source_field": "COSMOS-Web",
        "instrument": "NIRCam",
        "filter_band": "F444W",
        "redshift_center": 4.8,
        "magnitude_center": 27.4,
        "count_fraction": 0.06,
        "shape": "tidal",
    },
    {
        "cluster_id": 9,
        "cluster_name": "Compact Blue Cores",
        "plain_name": "Compact blue cores",
        "scientific_label": "Compact blue galaxy",
        "simple_label": "Compact blue galaxy",
        "summary": "Tiny, bright cores create a dense pocket of compact systems that likely represent fast early growth.",
        "plain_summary": "These galaxies are small and bright, with most of the light squeezed into a compact center.",
        "morphology_tags": ["compact core", "blue light", "small radius"],
        "source_field": "JADES",
        "instrument": "NIRCam",
        "filter_band": "F150W",
        "redshift_center": 6.0,
        "magnitude_center": 27.9,
        "count_fraction": 0.08,
        "shape": "compact",
    },
    {
        "cluster_id": 10,
        "cluster_name": "Dust Lane Giants",
        "plain_name": "Dust lane systems",
        "scientific_label": "Dust-lane spiral galaxy",
        "simple_label": "Dusty spiral",
        "summary": "Obscured midplanes and patchy extinction separate these larger disks from cleaner spiral families.",
        "plain_summary": "These disks show dark dusty lanes cutting through otherwise bright starlight.",
        "morphology_tags": ["dust lane", "obscuration", "disk"],
        "source_field": "CEERS",
        "instrument": "NIRCam",
        "filter_band": "F444W",
        "redshift_center": 2.4,
        "magnitude_center": 25.7,
        "count_fraction": 0.05,
        "shape": "dust_lane",
    },
    {
        "cluster_id": 11,
        "cluster_name": "Red Nugget Candidates",
        "plain_name": "Red nuggets",
        "scientific_label": "Compact quiescent galaxy",
        "simple_label": "Compact quiet galaxy",
        "summary": "Dense, red, compact systems form a high-redshift pocket that reads like a possible quiescent population.",
        "plain_summary": "These galaxies are small, dense, and smooth, suggesting star formation may already be fading.",
        "morphology_tags": ["compact", "smooth", "quiescent candidate"],
        "source_field": "UNCOVER",
        "instrument": "NIRCam",
        "filter_band": "F356W",
        "redshift_center": 6.8,
        "magnitude_center": 28.1,
        "count_fraction": 0.05,
        "shape": "red_nugget",
    },
    {
        "cluster_id": 12,
        "cluster_name": "Arc and Lens Candidates",
        "plain_name": "Lensing arcs",
        "scientific_label": "Lensed arc candidate",
        "simple_label": "Lensing arc",
        "summary": "Extended curved shapes hint at gravitational lensing, making this cluster useful for explainable outlier tours.",
        "plain_summary": "These long curved smears may be background galaxies stretched by gravity.",
        "morphology_tags": ["arc", "lensing candidate", "elongated light"],
        "source_field": "SMACS 0723",
        "instrument": "NIRCam",
        "filter_band": "F200W",
        "redshift_center": 7.5,
        "magnitude_center": 28.5,
        "count_fraction": 0.04,
        "shape": "arc",
    },
]

OUTLIER_DEFINITION = {
    "cluster_id": -1,
    "cluster_name": "Rare Objects",
    "plain_name": "Rare shapes",
    "scientific_label": "Peculiar galaxy candidate",
    "simple_label": "Rare galaxy",
    "summary": "Sparse, off-manifold objects collect here when their visual signatures do not fit the dominant morphology families.",
    "plain_summary": "This is the part of the map for oddballs that do not look much like the rest.",
    "morphology_tags": ["peculiar", "rare", "follow-up target"],
    "source_field": "Mixed programs",
    "instrument": "NIRCam",
    "filter_band": "mixed",
    "redshift_center": 8.3,
    "magnitude_center": 28.7,
    "shape": "rare",
}


@dataclass(slots=True)
class GalaxyMapPaths:
    dataset_dir: Path
    artifacts_dir: Path
    galaxies_path: Path
    embeddings_path: Path
    coordinates_path: Path
    cluster_summaries_path: Path
    thumbnails_dir: Path


def galaxy_map_paths(data_dir: Path) -> GalaxyMapPaths:
    dataset_dir = data_dir / "galaxy_map"
    artifacts_dir = data_dir / "artifacts" / "galaxy_map"
    return GalaxyMapPaths(
        dataset_dir=dataset_dir,
        artifacts_dir=artifacts_dir,
        galaxies_path=dataset_dir / "galaxies.parquet",
        embeddings_path=dataset_dir / "embeddings.npy",
        coordinates_path=dataset_dir / "umap_coordinates.parquet",
        cluster_summaries_path=dataset_dir / "cluster_summaries.json",
        thumbnails_dir=artifacts_dir / "thumbnails",
    )


def build_galaxy_map_artifacts(
    *,
    data_dir: Path,
    total: int = 12_500,
    source: str = "synthetic",
    catalog_path: Path | None = None,
    overwrite: bool = False,
    precompute_thumbnails: bool = False,
) -> GalaxyMapPaths:
    paths = galaxy_map_paths(data_dir)
    paths.dataset_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    if not overwrite and paths.galaxies_path.exists() and paths.embeddings_path.exists() and paths.coordinates_path.exists():
        return paths

    if source == "catalog" and catalog_path:
        frame, embeddings = _build_from_catalog(catalog_path, total=total)
    else:
        frame, embeddings = _build_synthetic_catalog(total=total)

    coordinates = _reduce_embeddings(embeddings)
    frame["x"] = coordinates[:, 0]
    frame["y"] = coordinates[:, 1]
    frame["z"] = coordinates[:, 2]

    frame.to_parquet(paths.galaxies_path, index=False)
    np.save(paths.embeddings_path, embeddings.astype(np.float32))
    frame[["image_id", "cluster_id", "x", "y", "z"]].to_parquet(paths.coordinates_path, index=False)
    with paths.cluster_summaries_path.open("w", encoding="utf-8") as handle:
        json.dump(_cluster_summaries(frame), handle, indent=2)

    if precompute_thumbnails:
        for row in frame.itertuples(index=False):
            ensure_thumbnail(
                {
                    "image_id": row.image_id,
                    "cluster_id": int(row.cluster_id),
                    "morphology": row.morphology,
                    "filter_band": row.filter_band,
                    "source_field": row.source_field,
                    "rarity_score": float(row.rarity_score),
                    "redshift": float(row.redshift),
                    "scientific_label": row.scientific_label,
                },
                paths,
            )

    return paths


def ensure_thumbnail(row: dict[str, Any], paths: GalaxyMapPaths) -> Path:
    thumbnail_name = f"{row['image_id']}.svg"
    destination = paths.thumbnails_dir / thumbnail_name
    if destination.exists():
        return destination
    destination.write_text(_thumbnail_svg(row), encoding="utf-8")
    return destination


def _build_synthetic_catalog(total: int) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(5090)
    dimensions = 48
    families = FAMILY_DEFINITIONS.copy()
    family_total = sum(item["count_fraction"] for item in families)
    records: list[dict[str, Any]] = []
    embeddings: list[np.ndarray] = []

    centers = _family_centers(dimensions)
    cursor = 0
    for definition, center in zip(families, centers, strict=False):
        cluster_total = max(240, int(total * (definition["count_fraction"] / family_total)))
        for member in range(cluster_total):
            image_id = f"jwst-{definition['cluster_id']:02d}-{member:05d}"
            redshift = max(0.2, rng.normal(definition["redshift_center"], 0.5 + definition["cluster_id"] * 0.03))
            magnitude = max(21.2, rng.normal(definition["magnitude_center"], 0.65))
            embedding = center + rng.normal(0.0, 0.34, size=dimensions)
            rarity_score = float(np.clip(0.18 + (definition["cluster_id"] % 5) * 0.08 + rng.normal(0.0, 0.06), 0.04, 0.89))
            record = {
                "image_id": image_id,
                "cluster_id": definition["cluster_id"],
                "cluster_name": definition["cluster_name"],
                "plain_cluster_name": definition["plain_name"],
                "scientific_label": definition["scientific_label"],
                "simple_label": definition["simple_label"],
                "predicted_class": definition["scientific_label"],
                "morphology": definition["scientific_label"],
                "confidence": float(np.clip(rng.normal(0.88, 0.06), 0.58, 0.99)),
                "rarity_score": rarity_score,
                "redshift": float(round(redshift, 3)),
                "magnitude": float(round(magnitude, 2)),
                "lookback_time_gyr": float(round(_lookback_time(redshift), 2)),
                "source_field": definition["source_field"],
                "observation_program": f"{definition['source_field']} deep field",
                "instrument": definition["instrument"],
                "filter_band": definition["filter_band"],
                "morphology_tags": definition["morphology_tags"],
                "feature_tags": definition["morphology_tags"],
                "thumbnail_name": f"{image_id}.svg",
                "observation_source": "Synthetic JWST-inspired sample",
                "catalog": "mock-jwst-catalog",
                "survey": "JWST public deep fields",
                "brightness_score": float(round(_brightness_score(magnitude), 3)),
                "ra": float(round(rng.uniform(0.0, 360.0), 5)),
                "dec": float(round(rng.uniform(-70.0, 70.0), 5)),
                "shape_family": definition["shape"],
                "data_mode": "synthetic",
            }
            records.append(record)
            embeddings.append(embedding.astype(np.float32))
            cursor += 1

    while len(records) < total:
        definition = OUTLIER_DEFINITION
        member = len(records) - cursor
        image_id = f"jwst-rare-{member:05d}"
        redshift = max(0.5, rng.normal(definition["redshift_center"], 0.9))
        magnitude = max(22.0, rng.normal(definition["magnitude_center"], 0.85))
        embedding = rng.normal(0.0, 1.4, size=dimensions)
        record = {
            "image_id": image_id,
            "cluster_id": definition["cluster_id"],
            "cluster_name": definition["cluster_name"],
            "plain_cluster_name": definition["plain_name"],
            "scientific_label": definition["scientific_label"],
            "simple_label": definition["simple_label"],
            "predicted_class": definition["scientific_label"],
            "morphology": definition["scientific_label"],
            "confidence": float(np.clip(rng.normal(0.64, 0.08), 0.45, 0.91)),
            "rarity_score": float(np.clip(rng.normal(0.92, 0.04), 0.82, 0.99)),
            "redshift": float(round(redshift, 3)),
            "magnitude": float(round(magnitude, 2)),
            "lookback_time_gyr": float(round(_lookback_time(redshift), 2)),
            "source_field": definition["source_field"],
            "observation_program": "Mixed public lensing and deep fields",
            "instrument": definition["instrument"],
            "filter_band": definition["filter_band"],
            "morphology_tags": definition["morphology_tags"],
            "feature_tags": definition["morphology_tags"],
            "thumbnail_name": f"{image_id}.svg",
            "observation_source": "Synthetic JWST-inspired sample",
            "catalog": "mock-jwst-catalog",
            "survey": "JWST public deep fields",
            "brightness_score": float(round(_brightness_score(magnitude), 3)),
            "ra": float(round(rng.uniform(0.0, 360.0), 5)),
            "dec": float(round(rng.uniform(-70.0, 70.0), 5)),
            "shape_family": definition["shape"],
            "data_mode": "synthetic",
        }
        records.append(record)
        embeddings.append(embedding.astype(np.float32))

    frame = pd.DataFrame.from_records(records[:total]).reset_index(drop=True)
    return frame, np.vstack(embeddings[:total]).astype(np.float32)


def _build_from_catalog(catalog_path: Path, total: int) -> tuple[pd.DataFrame, np.ndarray]:
    if catalog_path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(catalog_path)
    else:
        frame = pd.read_csv(catalog_path)
    frame = frame.rename(
        columns={
            "id": "image_id",
            "label": "scientific_label",
            "class_label": "scientific_label",
            "field": "source_field",
            "band": "filter_band",
            "program": "observation_program",
            "thumbnail": "thumbnail_name",
        }
    ).copy()
    if "image_id" not in frame:
        frame["image_id"] = [f"jwst-import-{index:05d}" for index in range(len(frame))]
    defaults = {
        "scientific_label": "Galaxy candidate",
        "simple_label": "Galaxy",
        "cluster_name": "Imported sample",
        "plain_cluster_name": "Imported sample",
        "source_field": "User catalog",
        "observation_program": "Imported program",
        "instrument": "NIRCam",
        "filter_band": "unknown",
        "catalog": "user-supplied",
        "survey": "JWST catalog import",
        "observation_source": "Imported JWST-style catalog",
        "shape_family": "catalog",
        "data_mode": "catalog",
    }
    for column, value in defaults.items():
        if column not in frame:
            frame[column] = value
    frame["simple_label"] = frame.get("simple_label", frame["scientific_label"]).fillna(frame["scientific_label"])
    frame["predicted_class"] = frame["scientific_label"]
    frame["morphology"] = frame["scientific_label"]
    frame["morphology_tags"] = frame.get("morphology_tags", pd.Series([["structure"]] * len(frame))).apply(
        lambda value: value if isinstance(value, list) else [str(value)]
    )
    frame["feature_tags"] = frame.get("feature_tags", frame["morphology_tags"])
    frame["redshift"] = pd.to_numeric(frame.get("redshift", 3.0), errors="coerce").fillna(3.0)
    frame["magnitude"] = pd.to_numeric(frame.get("magnitude", 26.0), errors="coerce").fillna(26.0)
    frame["lookback_time_gyr"] = frame["redshift"].map(_lookback_time).round(2)
    frame["confidence"] = pd.to_numeric(frame.get("confidence", 0.78), errors="coerce").fillna(0.78)
    frame["rarity_score"] = pd.to_numeric(frame.get("rarity_score", 0.33), errors="coerce").fillna(0.33)
    frame["brightness_score"] = frame["magnitude"].map(_brightness_score).round(3)
    frame["thumbnail_name"] = frame.get("thumbnail_name", frame["image_id"].astype(str) + ".svg")
    frame["ra"] = pd.to_numeric(frame.get("ra", 0.0), errors="coerce").fillna(0.0)
    frame["dec"] = pd.to_numeric(frame.get("dec", 0.0), errors="coerce").fillna(0.0)

    embeddings = np.vstack([_stable_embedding(row) for row in frame.head(total).to_dict(orient="records")]).astype(np.float32)
    coords = _reduce_embeddings(embeddings)
    cluster_ids = _cluster_embeddings(embeddings)
    cluster_name_map = {definition["cluster_id"]: definition["cluster_name"] for definition in FAMILY_DEFINITIONS}
    frame = frame.head(total).reset_index(drop=True)
    frame["cluster_id"] = cluster_ids
    frame["cluster_name"] = frame["cluster_id"].map(cluster_name_map).fillna("Imported cluster")
    frame["plain_cluster_name"] = frame["cluster_name"]
    frame["x"] = coords[:, 0]
    frame["y"] = coords[:, 1]
    frame["z"] = coords[:, 2]
    return frame, embeddings


def _cluster_embeddings(embeddings: np.ndarray) -> np.ndarray:
    if len(embeddings) < 12:
        return np.zeros(len(embeddings), dtype=int)
    clusters = max(5, min(12, len(embeddings) // 120))
    model = KMeans(n_clusters=clusters, n_init=10, random_state=42)
    return model.fit_predict(embeddings)


def _reduce_embeddings(embeddings: np.ndarray) -> np.ndarray:
    if len(embeddings) < 4:
        padded = np.zeros((len(embeddings), 3), dtype=np.float32)
        padded[:, : min(embeddings.shape[1], 3)] = embeddings[:, : min(embeddings.shape[1], 3)]
        return padded
    reduced = PCA(n_components=3, random_state=42).fit_transform(embeddings)
    scale = np.std(reduced, axis=0, keepdims=True)
    scale[scale == 0] = 1.0
    return (reduced / scale).astype(np.float32)


def _cluster_summaries(frame: pd.DataFrame) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for cluster_id, cluster in frame.groupby("cluster_id", dropna=False):
        scientific_label = str(cluster["scientific_label"].mode(dropna=True).iloc[0])
        simple_label = str(cluster["simple_label"].mode(dropna=True).iloc[0])
        summary = (
            cluster["cluster_name"].iloc[0]
            if cluster_id == -1
            else scientific_label
        )
        representatives = (
            cluster.assign(center_distance=np.sqrt((cluster["x"] - cluster["x"].mean()) ** 2 + (cluster["y"] - cluster["y"].mean()) ** 2))
            .sort_values(["center_distance", "rarity_score"], ascending=[True, False])
            .head(3)
        )
        base_summary = _family_summary(int(cluster_id), scientific_label, simple_label, int(len(cluster)))
        summaries.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_name": str(cluster["cluster_name"].iloc[0]),
                "plain_cluster_name": str(cluster["plain_cluster_name"].iloc[0]),
                "summary": base_summary["summary"],
                "plain_summary": base_summary["plain_summary"],
                "count": int(len(cluster)),
                "dominant_class": scientific_label,
                "simple_label": simple_label,
                "centroid_x": float(cluster["x"].mean()),
                "centroid_y": float(cluster["y"].mean()),
                "extent_x": float(cluster["x"].max() - cluster["x"].min()),
                "extent_y": float(cluster["y"].max() - cluster["y"].min()),
                "avg_rarity": float(cluster["rarity_score"].mean()),
                "redshift_min": float(cluster["redshift"].min()),
                "redshift_max": float(cluster["redshift"].max()),
                "representative_ids": representatives["image_id"].astype(str).tolist(),
            }
        )
    return sorted(summaries, key=lambda item: (item["cluster_id"] == -1, item["cluster_id"]))


def _family_summary(cluster_id: int, scientific_label: str, simple_label: str, count: int) -> dict[str, str]:
    for definition in FAMILY_DEFINITIONS:
        if definition["cluster_id"] == cluster_id:
            return {
                "summary": f"{definition['summary']} This cluster currently holds {count:,} galaxies in the sample.",
                "plain_summary": f"{definition['plain_summary']} There are {count:,} examples in this sample cluster.",
            }
    return {
        "summary": f"{scientific_label} objects cluster together in a shared region of embedding space. This cluster has {count:,} members.",
        "plain_summary": f"{simple_label} objects gather together in a similar-looking part of the map. This cluster has {count:,} members.",
    }


def _family_centers(dimensions: int) -> list[np.ndarray]:
    centers: list[np.ndarray] = []
    for definition in FAMILY_DEFINITIONS:
        rng = np.random.default_rng(7100 + definition["cluster_id"])
        centers.append(rng.normal(0.0, 0.7, size=dimensions) + (definition["cluster_id"] / 3.1))
    return centers


def _lookback_time(redshift: float) -> float:
    return max(0.1, 13.8 * redshift / (redshift + 1.55))


def _brightness_score(magnitude: float) -> float:
    return float(np.clip((30.5 - magnitude) / 10.0, 0.02, 0.98))


def _stable_embedding(row: dict[str, Any], dimensions: int = 48) -> np.ndarray:
    seed = int.from_bytes(hashlib.blake2b(str(row["image_id"]).encode("utf-8"), digest_size=8).digest(), "big")
    rng = np.random.default_rng(seed)
    vector = rng.normal(0.0, 0.4, size=dimensions)
    redshift = float(row.get("redshift", 3.0))
    magnitude = float(row.get("magnitude", 26.0))
    vector[0] = redshift
    vector[1] = magnitude / 10.0
    vector[2] = len(str(row.get("scientific_label", "Galaxy"))) / 40.0
    return vector.astype(np.float32)


def _thumbnail_svg(row: dict[str, Any]) -> str:
    cluster_id = int(row.get("cluster_id", -1))
    seed = int.from_bytes(hashlib.blake2b(str(row["image_id"]).encode("utf-8"), digest_size=8).digest(), "big")
    rng = np.random.default_rng(seed)
    palette = _palette(cluster_id)
    morphology = str(row.get("morphology", row.get("scientific_label", "galaxy"))).lower()
    stars = []
    for _ in range(26):
        stars.append(
            f'<circle cx="{rng.integers(0, 256)}" cy="{rng.integers(0, 256)}" '
            f'r="{rng.uniform(0.35, 1.6):.2f}" fill="rgba(255,255,255,{rng.uniform(0.2, 0.88):.2f})" />'
        )
    overlays = [
        '<rect width="256" height="256" fill="#020611" />',
        '<rect width="256" height="256" fill="url(#bgGlow)" />',
        *stars,
        f'<ellipse cx="128" cy="128" rx="{72 + (cluster_id % 4) * 8}" ry="{50 + (cluster_id % 3) * 6}" fill="{palette[2]}" opacity="0.32" />',
    ]
    if "spiral" in morphology:
        for direction in (-1, 1):
            points = []
            for step in range(9):
                angle = direction * step * 0.72 + (cluster_id * 0.15)
                radius = 22 + step * 12
                x = 128 + math.cos(angle) * radius
                y = 128 + math.sin(angle) * radius * 0.66
                points.append(f"{x:.1f},{y:.1f}")
            overlays.append(
                f'<polyline points="{" ".join(points)}" fill="none" stroke="{palette[1]}" stroke-width="8" stroke-linecap="round" opacity="0.72" />'
            )
        if "bar" in morphology:
            overlays.append(f'<rect x="82" y="118" width="92" height="20" rx="10" fill="{palette[3]}" opacity="0.58" />')
    elif "ring" in morphology or "arc" in morphology:
        overlays.append(f'<circle cx="128" cy="128" r="58" stroke="{palette[1]}" stroke-width="18" fill="none" opacity="0.64" />')
        if "arc" in morphology:
            overlays.append(f'<path d="M52 164 Q132 50 214 108" stroke="{palette[0]}" stroke-width="14" fill="none" opacity="0.78" />')
    elif "merger" in morphology or "tidal" in morphology or "peculiar" in morphology:
        overlays.append(f'<path d="M42 142 C78 66, 162 54, 214 114 S170 206, 88 178" stroke="{palette[1]}" stroke-width="22" fill="none" opacity="0.56" />')
        overlays.append(f'<circle cx="100" cy="120" r="28" fill="{palette[3]}" opacity="0.56" />')
        overlays.append(f'<circle cx="154" cy="136" r="24" fill="{palette[0]}" opacity="0.46" />')
    elif "edge-on" in morphology:
        overlays.append(f'<rect x="56" y="118" width="144" height="20" rx="10" fill="{palette[1]}" opacity="0.56" />')
        overlays.append(f'<rect x="56" y="124" width="144" height="8" rx="4" fill="{palette[0]}" opacity="0.42" />')
    elif "compact" in morphology:
        overlays.append(f'<circle cx="128" cy="128" r="42" fill="{palette[1]}" opacity="0.56" />')
    else:
        overlays.append(f'<ellipse cx="128" cy="128" rx="66" ry="54" fill="{palette[1]}" opacity="0.42" />')
    overlays.append(f'<circle cx="128" cy="128" r="24" fill="{palette[3]}" opacity="0.94" />')
    overlays.append('<circle cx="128" cy="128" r="7" fill="#fff4d4" opacity="0.95" />')
    filter_band = str(row.get("filter_band", "unknown"))
    source_field = str(row.get("source_field", "JWST"))
    scientific_label = str(row.get("scientific_label", "Galaxy"))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
        '<defs>'
        '<radialGradient id="bgGlow" cx="50%" cy="40%" r="80%">'
        '<stop offset="0%" stop-color="rgba(90,173,255,0.18)" />'
        '<stop offset="100%" stop-color="rgba(2,6,17,0)" />'
        '</radialGradient>'
        '</defs>'
        + "".join(overlays)
        + f'<rect x="10" y="10" width="92" height="28" rx="14" fill="rgba(6,16,30,0.76)" stroke="rgba(255,255,255,0.08)" />'
        + f'<text x="22" y="29" fill="#dff2ff" font-size="12" font-family="Avenir Next, Segoe UI, sans-serif">{filter_band}</text>'
        + f'<rect x="10" y="214" width="140" height="26" rx="13" fill="rgba(6,16,30,0.76)" stroke="rgba(255,255,255,0.08)" />'
        + f'<text x="20" y="231" fill="#dff2ff" font-size="11" font-family="Avenir Next, Segoe UI, sans-serif">{source_field[:20]}</text>'
        + f'<title>{scientific_label}</title>'
        "</svg>"
    )
    return svg


def _palette(cluster_id: int) -> tuple[str, str, str, str]:
    palettes = [
        ("#8bddff", "#9fffb2", "#15406a", "#fff4ca"),
        ("#7dd4ff", "#d7ff72", "#1d4661", "#fff2b6"),
        ("#9cb6ff", "#79f0e0", "#27315f", "#fff0cf"),
        ("#ffd07b", "#ffb17d", "#60364f", "#fff6dc"),
        ("#87f0ff", "#a5ff9d", "#264665", "#fff5db"),
        ("#ff9dc3", "#ffd870", "#61254e", "#fff2d4"),
        ("#ff8f6b", "#f5cf73", "#5c2d45", "#fff4d8"),
        ("#83ffd1", "#8fe5ff", "#1f4d4d", "#fff4d8"),
        ("#ffb37f", "#ff95ad", "#6a3050", "#fff1d7"),
        ("#9ae4ff", "#7bf7ac", "#1d4965", "#fff5dc"),
        ("#d8b8ff", "#ffd66e", "#41295f", "#fff3da"),
        ("#ffd6ad", "#eaff8f", "#64496b", "#fff6df"),
        ("#8dc5ff", "#f4f6ff", "#384374", "#fff7e1"),
        ("#fff1ad", "#ffffff", "#54548f", "#fff6eb"),
    ]
    if cluster_id < 0:
        return palettes[-1]
    return palettes[cluster_id % len(palettes)]


def _data_uri(svg: str) -> str:
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('ascii')}"


def download_cutouts_from_catalog(catalog_path: Path, output_dir: Path, limit: int = 48) -> list[Path]:
    if catalog_path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(catalog_path)
    else:
        frame = pd.read_csv(catalog_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for row in frame.head(limit).to_dict(orient="records"):
        url = row.get("cutout_url")
        if not isinstance(url, str) or not url:
            continue
        parsed = urlparse(url)
        extension = Path(parsed.path).suffix or ".fits"
        destination = output_dir / f"{row.get('image_id', 'cutout')}{extension}"
        urlretrieve(url, destination)
        downloaded.append(destination)
    return downloaded


def seed_example_catalog(destination: Path) -> None:
    source = Path(__file__).resolve().parent / "examples" / "mock_jwst_catalog.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
