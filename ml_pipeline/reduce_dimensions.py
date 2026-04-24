from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

from common import ArtifactPaths, require_package


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run UMAP + HDBSCAN on galaxy embeddings.")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--neighbors", type=int, default=30)
    parser.add_argument("--min-dist", type=float, default=0.1)
    parser.add_argument("--components", type=int, default=3, choices=[2, 3])
    parser.add_argument("--min-cluster-size", type=int, default=40)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    umap = require_package("umap", "umap-learn")
    hdbscan = require_package("hdbscan")

    artifacts = ArtifactPaths(args.model_dir)
    frame = pd.read_parquet(artifacts.embeddings_path)
    embedding_columns = sorted(column for column in frame.columns if column.startswith("emb_"))
    if not embedding_columns:
        raise SystemExit("Embedding parquet does not contain emb_* columns.")
    embedding_matrix = frame[embedding_columns].to_numpy(dtype=np.float32)

    reducer = umap.UMAP(
        n_components=args.components,
        n_neighbors=args.neighbors,
        min_dist=args.min_dist,
        metric="cosine",
        random_state=42,
    )
    reduced = reducer.fit_transform(embedding_matrix)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    cluster_labels = clusterer.fit_predict(embedding_matrix)
    probabilities = getattr(clusterer, "probabilities_", np.ones(len(frame), dtype=float))

    map_frame = frame.copy()
    map_frame["x"] = reduced[:, 0]
    map_frame["y"] = reduced[:, 1]
    map_frame["z"] = reduced[:, 2] if args.components == 3 else 0.0
    map_frame["cluster_id"] = cluster_labels.astype(int)
    map_frame["confidence"] = probabilities.astype(float)
    map_frame["rarity_score"] = (1.0 - probabilities).astype(float)
    map_frame.to_parquet(artifacts.map_path, index=False)
    print(f"wrote reduced map artifact to {artifacts.map_path}")


if __name__ == "__main__":
    main()
