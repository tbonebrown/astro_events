from __future__ import annotations

from dataclasses import dataclass, field
import base64
import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from astro_api.config import AppSettings


DEFAULT_CLUSTER_NAMES = {
    -1: "Rare Objects",
    0: "Grand Design Spirals",
    1: "Barred Spirals",
    2: "Edge-On Disks",
    3: "Golden Ellipticals",
    4: "Lenticular Bridges",
    5: "Ring Systems",
    6: "Merger Front",
    7: "Irregular Starbursts",
    8: "Tidal Tail Group",
    9: "Blue Compact Core",
    10: "Dust Lane Giants",
    11: "Shell Ellipticals",
    12: "Low Surface Brightness",
    13: "Polar Ring Collective",
}


def _stable_seed(value: str) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)


def _data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


@dataclass(slots=True)
class GalaxyMapService:
    settings: AppSettings
    demo_size: int = 12_500
    neighbors_k: int = 12
    explanation_cache: dict[str, str] = field(default_factory=dict)
    dataset_dir: Path = field(init=False)
    dataset_path: Path = field(init=False)
    _frame: pd.DataFrame | None = field(init=False, default=None)
    _embedding_matrix: np.ndarray | None = field(init=False, default=None)
    _cluster_frame: pd.DataFrame | None = field(init=False, default=None)
    _neighbors_model: NearestNeighbors | None = field(init=False, default=None)
    _bounds: dict[str, float] | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.demo_size = self.settings.galaxy_map_demo_size
        self.dataset_dir = self.settings.galaxy_map_artifact.parent
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_path = self.settings.galaxy_map_artifact

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
    def frame(self) -> pd.DataFrame:
        if self._frame is None:
            self._frame = self._load_frame()
        return self._frame

    @property
    def embedding_matrix(self) -> np.ndarray:
        if self._embedding_matrix is None:
            frame = self.frame
            embedding_columns = [column for column in frame.columns if column.startswith("emb_")]
            if embedding_columns:
                self._embedding_matrix = frame[embedding_columns].to_numpy(dtype=np.float32)
            else:
                self._embedding_matrix = frame[["x", "y", "z"]].to_numpy(dtype=np.float32)
        return self._embedding_matrix

    @property
    def neighbors_model(self) -> NearestNeighbors:
        if self._neighbors_model is None:
            model = NearestNeighbors(n_neighbors=min(self.neighbors_k + 1, len(self.frame)), metric="euclidean")
            model.fit(self.embedding_matrix)
            self._neighbors_model = model
        return self._neighbors_model

    @property
    def cluster_frame(self) -> pd.DataFrame:
        if self._cluster_frame is None:
            self._cluster_frame = self._build_cluster_frame()
        return self._cluster_frame

    def _load_frame(self) -> pd.DataFrame:
        if not self.dataset_path.exists():
            self._write_demo_dataset()
        frame = pd.read_parquet(self.dataset_path).copy()
        return self._normalize_frame(frame)

    def _normalize_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        renamed = frame.rename(
            columns={
                "id": "image_id",
                "galaxy_id": "image_id",
                "label": "predicted_class",
                "class_label": "predicted_class",
                "cluster": "cluster_id",
                "image_path": "image_url",
                "source_image_url": "image_url",
            }
        )
        if "image_id" not in renamed:
            renamed["image_id"] = [f"galaxy-{index:06d}" for index in range(len(renamed))]
        for column in ("x", "y"):
            if column not in renamed:
                raise ValueError(f"Galaxy map artifact is missing required column '{column}'.")
        if "z" not in renamed:
            renamed["z"] = 0.0
        if "cluster_id" not in renamed:
            renamed["cluster_id"] = -1
        renamed["cluster_id"] = renamed["cluster_id"].fillna(-1).astype(int)
        renamed["cluster_name"] = renamed.get("cluster_name", renamed["cluster_id"].map(DEFAULT_CLUSTER_NAMES))
        renamed["cluster_name"] = renamed["cluster_name"].fillna(
            renamed["cluster_id"].map(lambda cluster_id: f"Cluster {cluster_id}" if cluster_id >= 0 else "Rare Objects")
        )
        renamed["predicted_class"] = renamed.get("predicted_class", renamed["cluster_name"])
        renamed["morphology"] = renamed.get("morphology", renamed["predicted_class"])
        renamed["catalog"] = renamed.get("catalog", "galaxy-zoo-demo")
        renamed["survey"] = renamed.get("survey", "SDSS")
        renamed["confidence"] = pd.to_numeric(renamed.get("confidence", 0.84), errors="coerce").fillna(0.84)
        renamed["redshift"] = pd.to_numeric(renamed.get("redshift", 0.08), errors="coerce").fillna(0.08)
        renamed["stellar_mass_log10"] = pd.to_numeric(
            renamed.get("stellar_mass_log10", 10.4),
            errors="coerce",
        ).fillna(10.4)
        renamed["star_formation_rate"] = pd.to_numeric(
            renamed.get("star_formation_rate", 2.1),
            errors="coerce",
        ).fillna(2.1)
        renamed["surface_brightness"] = pd.to_numeric(
            renamed.get("surface_brightness", 21.3),
            errors="coerce",
        ).fillna(21.3)
        renamed["ra"] = pd.to_numeric(renamed.get("ra", 180.0), errors="coerce").fillna(180.0)
        renamed["dec"] = pd.to_numeric(renamed.get("dec", 0.0), errors="coerce").fillna(0.0)
        renamed["rarity_score"] = pd.to_numeric(renamed.get("rarity_score", 0.12), errors="coerce").fillna(0.12)
        if "feature_tags" not in renamed:
            renamed["feature_tags"] = renamed["cluster_name"].map(self._default_feature_tags)
        if "metadata_json" not in renamed:
            renamed["metadata_json"] = [
                {
                    "catalog": catalog,
                    "survey": survey,
                    "morphology": morphology,
                    "redshift": round(float(redshift), 4),
                    "surface_brightness": round(float(surface_brightness), 2),
                    "stellar_mass_log10": round(float(stellar_mass), 2),
                }
                for catalog, survey, morphology, redshift, surface_brightness, stellar_mass in zip(
                    renamed["catalog"],
                    renamed["survey"],
                    renamed["morphology"],
                    renamed["redshift"],
                    renamed["surface_brightness"],
                    renamed["stellar_mass_log10"],
                    strict=False,
                )
            ]
        renamed = renamed.sort_values(["cluster_id", "image_id"]).reset_index(drop=True)
        return renamed

    def list_points(
        self,
        limit: int = 5_000,
        offset: int = 0,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
        cluster_id: int | None = None,
    ) -> dict:
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

        total = len(filtered)
        working = filtered
        sample_limit = max(limit + offset, limit)
        if total > sample_limit:
            working = self._downsample_points(filtered, sample_limit)
        paged = working.iloc[offset : offset + limit]

        points = [
            {
                "image_id": row.image_id,
                "x": float(row.x),
                "y": float(row.y),
                "z": float(row.z),
                "cluster_id": int(row.cluster_id),
                "cluster_name": str(row.cluster_name),
                "predicted_class": str(row.predicted_class),
                "morphology": str(row.morphology),
                "confidence": float(row.confidence),
                "rarity_score": float(row.rarity_score),
                "is_outlier": bool(row.cluster_id == -1 or row.rarity_score >= 0.82),
            }
            for row in paged.itertuples()
        ]
        visible_clusters = sorted({point["cluster_id"] for point in points})
        return {
            "total": int(total),
            "returned": len(points),
            "visible_clusters": visible_clusters,
            "bounds": self.bounds,
            "points": points,
        }

    def list_clusters(self) -> list[dict]:
        clusters: list[dict] = []
        for row in self.cluster_frame.itertuples():
            clusters.append(
                {
                    "cluster_id": int(row.cluster_id),
                    "cluster_name": str(row.cluster_name),
                    "count": int(row.count),
                    "centroid_x": float(row.centroid_x),
                    "centroid_y": float(row.centroid_y),
                    "extent_x": float(row.extent_x),
                    "extent_y": float(row.extent_y),
                    "avg_rarity": float(row.avg_rarity),
                    "dominant_class": str(row.dominant_class),
                    "summary": str(row.summary),
                    "representatives": [
                        self._neighbor_card(representative_id)
                        for representative_id in row.representative_ids
                    ],
                }
            )
        return clusters

    def get_detail(self, image_id: str) -> dict | None:
        matches = self.frame[self.frame["image_id"] == image_id]
        if matches.empty:
            return None
        row = matches.iloc[0]
        neighbor_ids = self._neighbor_ids(image_id, k=6)
        return {
            "image_id": row["image_id"],
            "image_url": self._render_image(row),
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "predicted_class": str(row["predicted_class"]),
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
                "redshift": float(row["redshift"]),
                "stellar_mass_log10": float(row["stellar_mass_log10"]),
                "star_formation_rate": float(row["star_formation_rate"]),
                "surface_brightness": float(row["surface_brightness"]),
                "feature_tags": list(row["feature_tags"]) if isinstance(row["feature_tags"], list) else [],
            },
            "cluster_summary": self._cluster_summary(int(row["cluster_id"])),
            "nearest_neighbors": [self._neighbor_card(neighbor_id) for neighbor_id in neighbor_ids],
        }

    def explain_galaxy(self, image_id: str, inference_client) -> dict | None:
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

    def _build_cluster_frame(self) -> pd.DataFrame:
        cluster_rows: list[dict] = []
        for cluster_id, cluster in self.frame.groupby("cluster_id", dropna=False):
            cluster_name = str(cluster["cluster_name"].iloc[0])
            centroid_x = float(cluster["x"].mean())
            centroid_y = float(cluster["y"].mean())
            count = int(len(cluster))
            representative_ids = self._representative_ids(cluster, count=3)
            dominant_class = str(cluster["predicted_class"].mode(dropna=True).iloc[0])
            avg_rarity = float(cluster["rarity_score"].mean())
            summary = self._cluster_blurb(cluster_name, dominant_class, count, avg_rarity)
            cluster_rows.append(
                {
                    "cluster_id": int(cluster_id),
                    "cluster_name": cluster_name,
                    "count": count,
                    "centroid_x": centroid_x,
                    "centroid_y": centroid_y,
                    "extent_x": float(cluster["x"].max() - cluster["x"].min()),
                    "extent_y": float(cluster["y"].max() - cluster["y"].min()),
                    "avg_rarity": avg_rarity,
                    "dominant_class": dominant_class,
                    "summary": summary,
                    "representative_ids": representative_ids,
                }
            )
        cluster_frame = pd.DataFrame(cluster_rows)
        return cluster_frame.sort_values(["cluster_id", "cluster_name"]).reset_index(drop=True)

    def _cluster_summary(self, cluster_id: int) -> dict:
        matches = self.cluster_frame[self.cluster_frame["cluster_id"] == cluster_id]
        if matches.empty:
            return {
                "cluster_id": cluster_id,
                "cluster_name": "Unassigned",
                "count": 1,
                "summary": "This point is not yet attached to a stable morphology cluster.",
            }
        row = matches.iloc[0]
        return {
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "count": int(row["count"]),
            "dominant_class": str(row["dominant_class"]),
            "avg_rarity": float(row["avg_rarity"]),
            "centroid_x": float(row["centroid_x"]),
            "centroid_y": float(row["centroid_y"]),
            "extent_x": float(row["extent_x"]),
            "extent_y": float(row["extent_y"]),
            "summary": str(row["summary"]),
        }

    def _neighbor_ids(self, image_id: str, k: int = 6) -> list[str]:
        indices = self.frame.index[self.frame["image_id"] == image_id].tolist()
        if not indices:
            return []
        index = indices[0]
        distances, neighbors = self.neighbors_model.kneighbors(
            self.embedding_matrix[index].reshape(1, -1),
            n_neighbors=min(k + 1, len(self.frame)),
        )
        neighbor_ids: list[str] = []
        for neighbor_index in neighbors[0]:
            candidate_id = str(self.frame.iloc[int(neighbor_index)]["image_id"])
            if candidate_id == image_id:
                continue
            neighbor_ids.append(candidate_id)
            if len(neighbor_ids) >= k:
                break
        return neighbor_ids

    def _neighbor_card(self, image_id: str) -> dict:
        row = self.frame[self.frame["image_id"] == image_id].iloc[0]
        return {
            "image_id": row["image_id"],
            "cluster_id": int(row["cluster_id"]),
            "cluster_name": str(row["cluster_name"]),
            "predicted_class": str(row["predicted_class"]),
            "x": float(row["x"]),
            "y": float(row["y"]),
            "confidence": float(row["confidence"]),
            "image_url": self._render_image(row),
        }

    def _representative_ids(self, cluster: pd.DataFrame, count: int = 3) -> list[str]:
        centroid = np.array([cluster["x"].mean(), cluster["y"].mean()])
        distances = np.sqrt(((cluster[["x", "y"]].to_numpy() - centroid) ** 2).sum(axis=1))
        representatives = cluster.assign(distance_to_center=distances).nsmallest(count, "distance_to_center")
        return representatives["image_id"].astype(str).tolist()

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

    def _render_image(self, row: pd.Series) -> str:
        seed = _stable_seed(str(row["image_id"]))
        rng = np.random.default_rng(seed)
        cluster_id = int(row["cluster_id"])
        palette = self._palette(cluster_id)
        morphology = str(row["morphology"]).lower()
        arm_color = palette[1]
        halo_color = palette[2]
        stars = []
        for _ in range(36):
            stars.append(
                f'<circle cx="{rng.integers(0, 240)}" cy="{rng.integers(0, 240)}" '
                f'r="{rng.uniform(0.3, 1.6):.2f}" fill="rgba(255,255,255,{rng.uniform(0.25, 0.9):.2f})" />'
            )
        layers = [
            '<rect width="240" height="240" fill="#020611" />',
            '<circle cx="120" cy="120" r="106" fill="rgba(31,56,97,0.35)" />',
            *stars,
            f'<ellipse cx="120" cy="120" rx="{72 + cluster_id % 18}" ry="{34 + cluster_id % 11}" '
            f'fill="{halo_color}" opacity="0.26" />',
        ]
        if "spiral" in morphology:
            for direction in (-1, 1):
                path_points = []
                for step in range(8):
                    angle = (step * 0.7 * direction) + (cluster_id * 0.12)
                    radius = 24 + step * 11
                    x = 120 + math.cos(angle) * radius
                    y = 120 + math.sin(angle) * radius * 0.65
                    path_points.append(f"{x:.1f},{y:.1f}")
                layers.append(
                    f'<polyline points="{" ".join(path_points)}" fill="none" stroke="{arm_color}" '
                    'stroke-linecap="round" stroke-width="7" opacity="0.68" />'
                )
        elif "ring" in morphology:
            layers.append(
                f'<circle cx="120" cy="120" r="58" stroke="{arm_color}" stroke-width="18" fill="none" opacity="0.58" />'
            )
        elif "merger" in morphology or "tidal" in morphology:
            layers.append(
                f'<path d="M48 124 C82 70, 152 62, 198 112 S168 190, 92 168" '
                f'stroke="{arm_color}" stroke-width="22" fill="none" opacity="0.5" />'
            )
            layers.append(
                f'<circle cx="96" cy="114" r="28" fill="{palette[3]}" opacity="0.52" />'
            )
            layers.append(
                f'<circle cx="148" cy="132" r="22" fill="{palette[1]}" opacity="0.44" />'
            )
        else:
            layers.append(
                f'<ellipse cx="120" cy="120" rx="62" ry="48" fill="{arm_color}" opacity="0.38" />'
            )
        layers.append(f'<circle cx="120" cy="120" r="22" fill="{palette[3]}" opacity="0.92" />')
        layers.append('<circle cx="120" cy="120" r="6" fill="#fff4d4" opacity="0.96" />')
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">'
            + "".join(layers)
            + "</svg>"
        )
        return _data_uri(svg)

    def _write_demo_dataset(self) -> None:
        rng = np.random.default_rng(5090)
        dimensions = 32
        cluster_counts = [1_120, 1_050, 960, 980, 910, 880, 860, 920, 790, 740, 680, 640, 620, 570]
        total_clustered = sum(cluster_counts)
        outliers = max(300, self.demo_size - total_clustered)
        records: list[dict] = []
        cluster_centers = self._cluster_centers(dimensions)
        for cluster_id, count in enumerate(cluster_counts):
            center_x, center_y, center_z = self._cluster_canvas_center(cluster_id)
            cluster_name = DEFAULT_CLUSTER_NAMES[cluster_id]
            morphology = self._morphology_for_cluster(cluster_id)
            feature_tags = self._default_feature_tags(cluster_name)
            embedding_center = cluster_centers[cluster_id]
            covariance = 0.14 + (cluster_id % 4) * 0.02
            for member in range(count):
                galaxy_id = f"galaxy-{cluster_id:02d}-{member:05d}"
                embedding = embedding_center + rng.normal(0.0, covariance, size=dimensions)
                x = center_x + rng.normal(0.0, 0.9 + (cluster_id % 3) * 0.18)
                y = center_y + rng.normal(0.0, 0.6 + (cluster_id % 2) * 0.2)
                z = center_z + rng.normal(0.0, 0.35)
                records.append(
                    self._demo_record(
                        rng=rng,
                        galaxy_id=galaxy_id,
                        cluster_id=cluster_id,
                        cluster_name=cluster_name,
                        morphology=morphology,
                        feature_tags=feature_tags,
                        x=x,
                        y=y,
                        z=z,
                        embedding=embedding,
                    )
                )
        for member in range(outliers):
            galaxy_id = f"galaxy-rare-{member:05d}"
            embedding = rng.normal(0.0, 1.2, size=dimensions)
            x = rng.uniform(-9.2, 9.2)
            y = rng.uniform(-5.6, 5.6)
            z = rng.uniform(-2.0, 2.0)
            feature_tags = ["off-manifold", "peculiar", "low-density"]
            records.append(
                self._demo_record(
                    rng=rng,
                    galaxy_id=galaxy_id,
                    cluster_id=-1,
                    cluster_name=DEFAULT_CLUSTER_NAMES[-1],
                    morphology="Peculiar merger remnant",
                    feature_tags=feature_tags,
                    x=x,
                    y=y,
                    z=z,
                    embedding=embedding,
                    confidence=rng.uniform(0.51, 0.79),
                    rarity_score=rng.uniform(0.86, 0.99),
                    survey="SDSS x Galaxy Zoo",
                    catalog="galaxy-zoo-outlier",
                )
            )
        frame = pd.DataFrame.from_records(records[: self.demo_size])
        frame.to_parquet(self.dataset_path, index=False)

    def _demo_record(
        self,
        *,
        rng: np.random.Generator,
        galaxy_id: str,
        cluster_id: int,
        cluster_name: str,
        morphology: str,
        feature_tags: list[str],
        x: float,
        y: float,
        z: float,
        embedding: np.ndarray,
        confidence: float | None = None,
        rarity_score: float | None = None,
        survey: str = "SDSS DR17",
        catalog: str = "galaxy-zoo",
    ) -> dict:
        record = {
            "image_id": galaxy_id,
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "predicted_class": morphology,
            "morphology": morphology,
            "confidence": float(confidence if confidence is not None else rng.uniform(0.76, 0.98)),
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "ra": float(rng.uniform(0.0, 360.0)),
            "dec": float(rng.uniform(-60.0, 70.0)),
            "redshift": float(max(0.002, rng.normal(0.09 if cluster_id != -1 else 0.16, 0.04))),
            "stellar_mass_log10": float(rng.normal(10.6 if cluster_id != -1 else 9.9, 0.5)),
            "star_formation_rate": float(abs(rng.normal(2.4 if "spiral" in morphology.lower() else 1.1, 0.8))),
            "surface_brightness": float(rng.normal(21.8 if cluster_id != -1 else 23.4, 0.7)),
            "rarity_score": float(rarity_score if rarity_score is not None else rng.uniform(0.08, 0.55)),
            "survey": survey,
            "catalog": catalog,
            "feature_tags": feature_tags,
            "metadata_json": {
                "catalog": catalog,
                "survey": survey,
                "morphology": morphology,
                "cluster": cluster_name,
            },
        }
        for index, value in enumerate(embedding):
            record[f"emb_{index}"] = float(value)
        return record

    def _cluster_centers(self, dimensions: int) -> list[np.ndarray]:
        centers: list[np.ndarray] = []
        for cluster_id in range(14):
            rng = np.random.default_rng(7000 + cluster_id)
            centers.append(rng.normal(0.0, 1.0, size=dimensions) + (cluster_id / 3.5))
        return centers

    def _cluster_canvas_center(self, cluster_id: int) -> tuple[float, float, float]:
        angle = 0.62 * cluster_id
        radius_x = 5.8 + (cluster_id % 4) * 0.65
        radius_y = 3.1 + (cluster_id % 3) * 0.45
        return (
            math.cos(angle) * radius_x,
            math.sin(angle) * radius_y,
            math.sin(angle * 1.6) * 1.15,
        )

    def _morphology_for_cluster(self, cluster_id: int) -> str:
        mapping = {
            0: "Grand design spiral",
            1: "Barred spiral",
            2: "Edge-on disk galaxy",
            3: "Elliptical galaxy",
            4: "Lenticular galaxy",
            5: "Ring galaxy",
            6: "Disturbed merger",
            7: "Irregular starburst",
            8: "Tidal tail system",
            9: "Compact blue galaxy",
            10: "Dust lane spiral",
            11: "Shell elliptical",
            12: "Low surface brightness disk",
            13: "Polar ring galaxy",
        }
        return mapping.get(cluster_id, "Galaxy")

    def _cluster_blurb(self, cluster_name: str, dominant_class: str, count: int, avg_rarity: float) -> str:
        if avg_rarity >= 0.8:
            rarity_line = "This region is unusually sparse and worth scanning for one-off structures."
        elif avg_rarity >= 0.45:
            rarity_line = "The cluster mixes common forms with a visible tail of unusual members."
        else:
            rarity_line = "This is a dense morphology family with very consistent visual signatures."
        return (
            f"{cluster_name} contains {count:,} galaxies dominated by {dominant_class.lower()} examples. "
            f"{rarity_line}"
        )

    def _default_feature_tags(self, cluster_name: str) -> list[str]:
        lowered = cluster_name.lower()
        if "spiral" in lowered:
            return ["spiral arms", "disk", "star-forming knots"]
        if "elliptical" in lowered:
            return ["smooth halo", "central bulge", "low asymmetry"]
        if "ring" in lowered:
            return ["outer ring", "bright core", "resonant structure"]
        if "merger" in lowered or "tail" in lowered:
            return ["asymmetric light", "tidal debris", "disturbed profile"]
        if "rare" in lowered:
            return ["off-manifold", "rare shape", "follow-up target"]
        return ["compact core", "diffuse halo", "structural contrast"]

    def _palette(self, cluster_id: int) -> tuple[str, str, str, str]:
        palettes = [
            ("#5dc8ff", "#77f0d8", "#1a4d88", "#fff1c1"),
            ("#a5ff83", "#e2ff7a", "#30595c", "#fff2ab"),
            ("#8cc4ff", "#8ca9ff", "#26326d", "#ffe7c6"),
            ("#ffc98b", "#ffd57d", "#6b3654", "#fff7d9"),
            ("#b8fff5", "#7dd4ff", "#294a74", "#fff6e0"),
            ("#ff93b8", "#ffd86f", "#6d1d4f", "#fff3da"),
            ("#ff8d73", "#f9d173", "#5c2840", "#fff6db"),
            ("#7cf7c2", "#8af3ff", "#1c4f4e", "#fff2cf"),
            ("#f7b477", "#ff8a9a", "#643050", "#fff4dc"),
            ("#8ee7ff", "#73f8a1", "#1a4564", "#fff4d4"),
            ("#f7b1ff", "#ffd66e", "#4e2769", "#fff4da"),
            ("#ffd0a4", "#ffe98f", "#69456d", "#fff7df"),
            ("#9de5d2", "#b7f4ff", "#2a5561", "#fff3dd"),
            ("#fcb3ce", "#8de7ff", "#4d326a", "#fff6dc"),
            ("#d9d9ff", "#ffffff", "#2e3359", "#fff6e7"),
        ]
        return palettes[(cluster_id + 1) % len(palettes)]
