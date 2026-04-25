from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from astro_api.config import AppSettings

try:
    from astro_jwst.pipeline import GalaxyMapPaths, build_galaxy_map_artifacts, ensure_thumbnail, galaxy_map_paths
except ModuleNotFoundError:  # pragma: no cover - fallback for direct repo execution
    from pipelines.jwst.astro_jwst.pipeline import (  # type: ignore
        GalaxyMapPaths,
        build_galaxy_map_artifacts,
        ensure_thumbnail,
        galaxy_map_paths,
    )


@dataclass(slots=True)
class GalaxyMapService:
    settings: AppSettings
    demo_size: int = 12_500
    neighbors_k: int = 12
    explanation_cache: dict[str, str] = field(default_factory=dict)
    paths: GalaxyMapPaths = field(init=False)
    _frame: pd.DataFrame | None = field(init=False, default=None)
    _embedding_matrix: np.ndarray | None = field(init=False, default=None)
    _cluster_records: list[dict[str, Any]] | None = field(init=False, default=None)
    _neighbors_model: NearestNeighbors | None = field(init=False, default=None)
    _bounds: dict[str, float] | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.demo_size = self.settings.galaxy_map_demo_size
        self.paths = galaxy_map_paths(self.settings.data_dir)

    @property
    def frame(self) -> pd.DataFrame:
        if self._frame is None:
            self._frame = self._load_frame()
        return self._frame

    @property
    def embedding_matrix(self) -> np.ndarray:
        if self._embedding_matrix is None:
            self._embedding_matrix = np.load(self.paths.embeddings_path).astype(np.float32)
        return self._embedding_matrix

    @property
    def neighbors_model(self) -> NearestNeighbors:
        if self._neighbors_model is None:
            model = NearestNeighbors(n_neighbors=min(self.neighbors_k + 1, max(2, len(self.frame))), metric="euclidean")
            model.fit(self.embedding_matrix)
            self._neighbors_model = model
        return self._neighbors_model

    @property
    def bounds(self) -> dict[str, float]:
        if self._bounds is None:
            frame = self.frame
            self._bounds = {
                "min_x": float(frame["x"].min()),
                "max_x": float(frame["x"].max()),
                "min_y": float(frame["y"].min()),
                "max_y": float(frame["y"].max()),
                "min_z": float(frame["z"].min()),
                "max_z": float(frame["z"].max()),
            }
        return self._bounds

    @property
    def cluster_records(self) -> list[dict[str, Any]]:
        if self._cluster_records is None:
            self._cluster_records = self._load_cluster_records()
        return self._cluster_records

    def manifest(self) -> dict[str, Any]:
        frame = self.frame
        clusters = self.list_clusters()
        return {
            "title": "Galaxy Embedding Map",
            "subtitle": "Explore the early universe through AI-assisted visual similarity maps built from JWST-style galaxy cutouts.",
            "total_galaxies": int(len(frame)),
            "data_mode": str(frame["data_mode"].mode(dropna=True).iloc[0]),
            "ranges": {
                "redshift_min": float(frame["redshift"].min()),
                "redshift_max": float(frame["redshift"].max()),
                "magnitude_min": float(frame["magnitude"].min()),
                "magnitude_max": float(frame["magnitude"].max()),
            },
            "instruments": sorted(frame["instrument"].dropna().astype(str).unique().tolist()),
            "filter_bands": sorted(frame["filter_band"].dropna().astype(str).unique().tolist()),
            "morphologies": sorted(frame["scientific_label"].dropna().astype(str).unique().tolist()),
            "source_fields": sorted(frame["source_field"].dropna().astype(str).unique().tolist()),
            "clusters": clusters,
            "story_steps": [
                {
                    "id": "embeddings",
                    "title": "What the map shows",
                    "body": "Each point is one galaxy. Nearby points have similar visual structure because the embedding model places related shapes close together.",
                },
                {
                    "id": "clusters",
                    "title": "Why clusters matter",
                    "body": "When many galaxies share bars, disks, clumps, or merger features, they gather into morphology clusters that make large-scale patterns easier to see.",
                },
                {
                    "id": "redshift",
                    "title": "Reading redshift",
                    "body": "Higher redshift usually means we are seeing a galaxy further back in time, so the map can be read as a rough tour through early-universe structure.",
                },
            ],
            "methodology": [
                {
                    "title": "Ingest",
                    "detail": "The pipeline accepts a self-contained synthetic sample today and can ingest a real JWST-style catalog with cutout URLs or pre-downloaded thumbnails later.",
                },
                {
                    "title": "Embed",
                    "detail": "Image-level features are converted into numerical embeddings, then reduced into three dimensions for interactive browsing and hover inspection.",
                },
                {
                    "title": "Cluster",
                    "detail": "Cluster summaries capture dominant morphology, representative examples, redshift spread, and plain-language descriptions for non-specialists.",
                },
            ],
            "data_sources": [
                {
                    "label": "Mock JWST sample",
                    "detail": "The repo ships with a deterministic JWST-inspired sample so the app stays runnable without external downloads.",
                },
                {
                    "label": "Public JWST / MAST upgrade path",
                    "detail": "Swap in a MAST-exported catalog and cutout URLs to regenerate the same artifacts with real metadata, thumbnails, embeddings, and cluster summaries.",
                },
            ],
            "artifacts": [
                {
                    "name": "galaxies.parquet",
                    "path": str(self.paths.galaxies_path),
                    "description": "Normalized metadata table used by the public map and detail drawer.",
                },
                {
                    "name": "embeddings.npy",
                    "path": str(self.paths.embeddings_path),
                    "description": "Dense image embedding matrix for nearest-neighbor search and downstream re-projection.",
                },
                {
                    "name": "umap_coordinates.parquet",
                    "path": str(self.paths.coordinates_path),
                    "description": "Three-dimensional map coordinates used for the rendered embedding view.",
                },
                {
                    "name": "cluster_summaries.json",
                    "path": str(self.paths.cluster_summaries_path),
                    "description": "Cluster-level summaries, counts, redshift ranges, and representative galaxy IDs.",
                },
                {
                    "name": "thumbnails/",
                    "path": str(self.paths.thumbnails_dir),
                    "description": "On-demand generated SVG cutouts for hover cards, cluster representatives, and detail views.",
                },
            ],
        }

    def list_points(
        self,
        limit: int = 12_000,
        offset: int = 0,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
        cluster_id: int | None = None,
        redshift_min: float | None = None,
        redshift_max: float | None = None,
        magnitude_min: float | None = None,
        magnitude_max: float | None = None,
        morphology: str | None = None,
        instrument: str | None = None,
        filter_band: str | None = None,
        source_field: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        filtered = self._filter_frame(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            cluster_id=cluster_id,
            redshift_min=redshift_min,
            redshift_max=redshift_max,
            magnitude_min=magnitude_min,
            magnitude_max=magnitude_max,
            morphology=morphology,
            instrument=instrument,
            filter_band=filter_band,
            source_field=source_field,
            search=search,
        )
        total = len(filtered)
        working = self._downsample_points(filtered, max(limit + offset, limit))
        paged = working.iloc[offset : offset + limit]
        bounds_frame = filtered if not filtered.empty else self.frame
        return {
            "total": int(total),
            "returned": int(len(paged)),
            "visible_clusters": sorted({int(value) for value in paged["cluster_id"].tolist()}),
            "bounds": {
                "min_x": float(bounds_frame["x"].min()),
                "max_x": float(bounds_frame["x"].max()),
                "min_y": float(bounds_frame["y"].min()),
                "max_y": float(bounds_frame["y"].max()),
                "min_z": float(bounds_frame["z"].min()),
                "max_z": float(bounds_frame["z"].max()),
            },
            "points": [self._point_payload(row) for row in paged.to_dict(orient="records")],
        }

    def list_clusters(self) -> list[dict[str, Any]]:
        return [
            {
                **record,
                "representatives": [self._neighbor_card(image_id) for image_id in record.get("representative_ids", [])],
            }
            for record in self.cluster_records
        ]

    def get_detail(self, image_id: str) -> dict[str, Any] | None:
        matches = self.frame[self.frame["image_id"] == image_id]
        if matches.empty:
            return None
        row = matches.iloc[0].to_dict()
        cluster_summary = self._cluster_summary(int(row["cluster_id"]))
        neighbor_ids = self._neighbor_ids(image_id, k=6)
        image_url = self._image_url(row)
        return {
            "image_id": row["image_id"],
            "image_url": image_url,
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "plain_cluster_name": str(row["plain_cluster_name"]),
            "predicted_class": str(row["predicted_class"]),
            "scientific_label": str(row["scientific_label"]),
            "simple_label": str(row["simple_label"]),
            "morphology": str(row["morphology"]),
            "confidence": float(row["confidence"]),
            "rarity_score": float(row["rarity_score"]),
            "coordinates": {
                "x": float(row["x"]),
                "y": float(row["y"]),
                "z": float(row["z"]),
                "ra": float(row["ra"]),
                "dec": float(row["dec"]),
            },
            "metadata": {
                "catalog": str(row["catalog"]),
                "survey": str(row["survey"]),
                "observation_source": str(row["observation_source"]),
                "observation_program": str(row["observation_program"]),
                "source_field": str(row["source_field"]),
                "instrument": str(row["instrument"]),
                "filter_band": str(row["filter_band"]),
                "redshift": float(row["redshift"]),
                "magnitude": float(row["magnitude"]),
                "brightness_score": float(row["brightness_score"]),
                "lookback_time_gyr": float(row["lookback_time_gyr"]),
                "stellar_mass_log10": float(row["stellar_mass_log10"]),
                "star_formation_rate": float(row["star_formation_rate"]),
                "surface_brightness": float(row["surface_brightness"]),
                "feature_tags": list(row["feature_tags"]),
                "morphology_tags": list(row["morphology_tags"]),
                "data_mode": str(row["data_mode"]),
            },
            "cluster_summary": cluster_summary,
            "nearest_neighbors": [self._neighbor_card(neighbor_id) for neighbor_id in neighbor_ids],
        }

    def explain_galaxy(self, image_id: str, inference_client) -> dict[str, Any] | None:
        detail = self.get_detail(image_id)
        if detail is None:
            return None
        cached = self.explanation_cache.get(image_id)
        if cached:
            return {"image_id": image_id, "explanation": cached, "source": "cache"}
        explanation, source = inference_client.galaxy_explanation(
            detail,
            detail["cluster_summary"],
            detail["nearest_neighbors"],
        )
        self.explanation_cache[image_id] = explanation
        return {"image_id": image_id, "explanation": explanation, "source": source}

    def _load_frame(self) -> pd.DataFrame:
        if not self.paths.galaxies_path.exists() or not self.paths.embeddings_path.exists() or not self.paths.coordinates_path.exists():
            build_galaxy_map_artifacts(
                data_dir=self.settings.data_dir,
                total=self.demo_size,
                source="synthetic",
                overwrite=False,
                precompute_thumbnails=False,
            )
        frame = pd.read_parquet(self.paths.galaxies_path).copy()
        return self._normalize_frame(frame)

    def _normalize_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        defaults = {
            "plain_cluster_name": frame.get("cluster_name", "Cluster"),
            "scientific_label": frame.get("predicted_class", "Galaxy"),
            "simple_label": frame.get("predicted_class", "Galaxy"),
            "predicted_class": frame.get("scientific_label", "Galaxy"),
            "morphology": frame.get("scientific_label", "Galaxy"),
            "catalog": "mock-jwst-catalog",
            "survey": "JWST public deep fields",
            "observation_source": "Synthetic JWST-inspired sample",
            "observation_program": "Deep field program",
            "source_field": "Deep field",
            "instrument": "NIRCam",
            "filter_band": "F200W",
            "data_mode": "synthetic",
        }
        for column, default in defaults.items():
            if column not in frame:
                frame[column] = default
        numeric_defaults = {
            "confidence": 0.82,
            "rarity_score": 0.2,
            "redshift": 2.5,
            "magnitude": 26.0,
            "lookback_time_gyr": 10.0,
            "brightness_score": 0.46,
            "ra": 180.0,
            "dec": 0.0,
            "stellar_mass_log10": 10.1,
            "star_formation_rate": 2.2,
            "surface_brightness": 22.8,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        }
        for column, default in numeric_defaults.items():
            source = frame[column] if column in frame else pd.Series([default] * len(frame))
            frame[column] = pd.to_numeric(source, errors="coerce").fillna(default)
        for column in ("feature_tags", "morphology_tags"):
            if column not in frame:
                frame[column] = [[] for _ in range(len(frame))]
            frame[column] = frame[column].apply(self._normalize_tags)
        if "thumbnail_name" not in frame:
            frame["thumbnail_name"] = frame["image_id"].astype(str) + ".svg"
        frame["cluster_id"] = pd.to_numeric(frame.get("cluster_id", -1), errors="coerce").fillna(-1).astype(int)
        frame["is_outlier"] = (frame["cluster_id"] == -1) | (frame["rarity_score"] >= 0.82)
        return frame.reset_index(drop=True)

    def _load_cluster_records(self) -> list[dict[str, Any]]:
        if self.paths.cluster_summaries_path.exists():
            with self.paths.cluster_summaries_path.open("r", encoding="utf-8") as handle:
                raw_records = json.load(handle)
            if isinstance(raw_records, list):
                return [self._cluster_record(record) for record in raw_records]
        records: list[dict[str, Any]] = []
        for cluster_id, cluster in self.frame.groupby("cluster_id", dropna=False):
            records.append(
                self._cluster_record(
                    {
                        "cluster_id": int(cluster_id),
                        "cluster_name": str(cluster["cluster_name"].iloc[0]),
                        "plain_cluster_name": str(cluster["plain_cluster_name"].iloc[0]),
                        "summary": f"{cluster['scientific_label'].mode(dropna=True).iloc[0]} objects cluster together in this region of the map.",
                        "plain_summary": f"{cluster['simple_label'].mode(dropna=True).iloc[0]} objects cluster together in this region of the map.",
                        "count": int(len(cluster)),
                        "dominant_class": str(cluster["scientific_label"].mode(dropna=True).iloc[0]),
                        "simple_label": str(cluster["simple_label"].mode(dropna=True).iloc[0]),
                        "centroid_x": float(cluster["x"].mean()),
                        "centroid_y": float(cluster["y"].mean()),
                        "extent_x": float(cluster["x"].max() - cluster["x"].min()),
                        "extent_y": float(cluster["y"].max() - cluster["y"].min()),
                        "avg_rarity": float(cluster["rarity_score"].mean()),
                        "redshift_min": float(cluster["redshift"].min()),
                        "redshift_max": float(cluster["redshift"].max()),
                        "representative_ids": cluster.head(3)["image_id"].astype(str).tolist(),
                    }
                )
            )
        return sorted(records, key=lambda item: (item["cluster_id"] == -1, item["cluster_id"]))

    def _cluster_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "cluster_id": int(record["cluster_id"]),
            "cluster_name": str(record["cluster_name"]),
            "plain_cluster_name": str(record.get("plain_cluster_name") or record["cluster_name"]),
            "count": int(record["count"]),
            "centroid_x": float(record["centroid_x"]),
            "centroid_y": float(record["centroid_y"]),
            "extent_x": float(record["extent_x"]),
            "extent_y": float(record["extent_y"]),
            "avg_rarity": float(record["avg_rarity"]),
            "dominant_class": str(record["dominant_class"]),
            "summary": str(record["summary"]),
            "plain_summary": str(record.get("plain_summary") or record["summary"]),
            "redshift_min": float(record.get("redshift_min", 0.0)),
            "redshift_max": float(record.get("redshift_max", 0.0)),
            "representative_ids": list(record.get("representative_ids", [])),
        }

    def _cluster_summary(self, cluster_id: int) -> dict[str, Any]:
        for record in self.cluster_records:
            if record["cluster_id"] == cluster_id:
                return {key: value for key, value in record.items() if key != "representative_ids"}
        return {
            "cluster_id": cluster_id,
            "cluster_name": "Unassigned",
            "plain_cluster_name": "Unassigned",
            "count": 1,
            "summary": "This object is not attached to a stable morphology cluster yet.",
            "plain_summary": "This object is not attached to a stable visual family yet.",
        }

    def _neighbor_ids(self, image_id: str, k: int = 6) -> list[str]:
        indices = self.frame.index[self.frame["image_id"] == image_id].tolist()
        if not indices:
            return []
        index = indices[0]
        _, neighbors = self.neighbors_model.kneighbors(
            self.embedding_matrix[index].reshape(1, -1),
            n_neighbors=min(k + 1, len(self.frame)),
        )
        output: list[str] = []
        for neighbor_index in neighbors[0]:
            candidate_id = str(self.frame.iloc[int(neighbor_index)]["image_id"])
            if candidate_id == image_id:
                continue
            output.append(candidate_id)
            if len(output) >= k:
                break
        return output

    def _neighbor_card(self, image_id: str) -> dict[str, Any]:
        row = self.frame[self.frame["image_id"] == image_id].iloc[0].to_dict()
        return {
            "image_id": row["image_id"],
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "plain_cluster_name": str(row["plain_cluster_name"]),
            "predicted_class": str(row["predicted_class"]),
            "scientific_label": str(row["scientific_label"]),
            "simple_label": str(row["simple_label"]),
            "x": float(row["x"]),
            "y": float(row["y"]),
            "confidence": float(row["confidence"]),
            "redshift": float(row["redshift"]),
            "magnitude": float(row["magnitude"]),
            "image_url": self._image_url(row),
        }

    def _point_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "image_id": row["image_id"],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "z": float(row["z"]),
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "plain_cluster_name": str(row["plain_cluster_name"]),
            "predicted_class": str(row["predicted_class"]),
            "scientific_label": str(row["scientific_label"]),
            "simple_label": str(row["simple_label"]),
            "morphology": str(row["morphology"]),
            "confidence": float(row["confidence"]),
            "rarity_score": float(row["rarity_score"]),
            "redshift": float(row["redshift"]),
            "magnitude": float(row["magnitude"]),
            "source_field": str(row["source_field"]),
            "instrument": str(row["instrument"]),
            "filter_band": str(row["filter_band"]),
            "thumbnail_url": None,
            "is_outlier": bool(row["is_outlier"]),
        }

    def _image_url(self, row: dict[str, Any]) -> str:
        path = ensure_thumbnail(row, self.paths)
        return f"/artifacts/galaxy_map/thumbnails/{path.name}"

    def _filter_frame(
        self,
        *,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
        cluster_id: int | None = None,
        redshift_min: float | None = None,
        redshift_max: float | None = None,
        magnitude_min: float | None = None,
        magnitude_max: float | None = None,
        morphology: str | None = None,
        instrument: str | None = None,
        filter_band: str | None = None,
        source_field: str | None = None,
        search: str | None = None,
    ) -> pd.DataFrame:
        filtered = self.frame
        if min_x is not None:
            filtered = filtered[filtered["x"] >= min_x]
        if max_x is not None:
            filtered = filtered[filtered["x"] <= max_x]
        if min_y is not None:
            filtered = filtered[filtered["y"] >= min_y]
        if max_y is not None:
            filtered = filtered[filtered["y"] <= max_y]
        if cluster_id is not None:
            filtered = filtered[filtered["cluster_id"] == cluster_id]
        if redshift_min is not None:
            filtered = filtered[filtered["redshift"] >= redshift_min]
        if redshift_max is not None:
            filtered = filtered[filtered["redshift"] <= redshift_max]
        if magnitude_min is not None:
            filtered = filtered[filtered["magnitude"] >= magnitude_min]
        if magnitude_max is not None:
            filtered = filtered[filtered["magnitude"] <= magnitude_max]
        if morphology:
            lowered = morphology.strip().lower()
            filtered = filtered[filtered["scientific_label"].str.lower() == lowered]
        if instrument:
            filtered = filtered[filtered["instrument"].str.lower() == instrument.strip().lower()]
        if filter_band:
            filtered = filtered[filtered["filter_band"].str.lower() == filter_band.strip().lower()]
        if source_field:
            filtered = filtered[filtered["source_field"].str.lower() == source_field.strip().lower()]
        if search:
            pattern = search.strip().lower()
            filtered = filtered[
                filtered["image_id"].str.lower().str.contains(pattern)
                | filtered["scientific_label"].str.lower().str.contains(pattern)
                | filtered["simple_label"].str.lower().str.contains(pattern)
            ]
        return filtered

    def _downsample_points(self, frame: pd.DataFrame, limit: int) -> pd.DataFrame:
        if len(frame) <= limit:
            return frame
        x_bins = max(12, int(math.sqrt(limit / 2)))
        y_bins = max(8, int(math.sqrt(limit / 3)))
        x_edges = np.linspace(frame["x"].min(), frame["x"].max(), x_bins + 1)
        y_edges = np.linspace(frame["y"].min(), frame["y"].max(), y_bins + 1)
        sampled_indices: list[int] = []
        for x_index in range(x_bins):
            x_start = x_edges[x_index]
            x_end = x_edges[x_index + 1]
            x_mask = (frame["x"] >= x_start) & (frame["x"] <= x_end if x_index == x_bins - 1 else frame["x"] < x_end)
            x_bucket = frame[x_mask]
            if x_bucket.empty:
                continue
            for y_index in range(y_bins):
                y_start = y_edges[y_index]
                y_end = y_edges[y_index + 1]
                y_mask = (x_bucket["y"] >= y_start) & (
                    x_bucket["y"] <= y_end if y_index == y_bins - 1 else x_bucket["y"] < y_end
                )
                cell = x_bucket[y_mask]
                if cell.empty:
                    continue
                selected = cell.sort_values(["rarity_score", "confidence"], ascending=[False, False]).head(1)
                sampled_indices.extend(selected.index.tolist())
        if len(sampled_indices) < limit:
            missing = limit - len(sampled_indices)
            extras = frame.drop(index=sampled_indices).nlargest(missing, "rarity_score")
            sampled_indices.extend(extras.index.tolist())
        sampled = frame.loc[sorted(set(sampled_indices))]
        return sampled.head(limit)

    @staticmethod
    def _normalize_tags(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return []
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [segment.strip() for segment in value.split(",") if segment.strip()]
        return [str(value)]
