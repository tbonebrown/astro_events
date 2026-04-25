from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import build_galaxy_map_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build artifacts for the Ohnita Galaxy Embedding Map.")
    parser.add_argument("--data-dir", type=Path, default=Path("./var/data"))
    parser.add_argument("--source", choices=["synthetic", "catalog"], default="synthetic")
    parser.add_argument("--catalog-path", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=12_500)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--precompute-thumbnails", action="store_true")
    args = parser.parse_args()

    build_galaxy_map_artifacts(
        data_dir=args.data_dir,
        total=max(200, args.limit),
        source=args.source,
        catalog_path=args.catalog_path,
        overwrite=args.overwrite,
        precompute_thumbnails=args.precompute_thumbnails,
    )


if __name__ == "__main__":
    main()
