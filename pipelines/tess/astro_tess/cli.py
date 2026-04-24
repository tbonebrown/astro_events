from __future__ import annotations

import argparse
from pathlib import Path

from astro_tess.config import PipelineSettings
from astro_tess.pipeline import run_nightly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Astro Event Intelligence TESS pipeline.")
    parser.add_argument("--sector", type=int, default=PipelineSettings().default_sector)
    parser.add_argument("--limit", type=int, default=PipelineSettings().default_limit)
    parser.add_argument("--export-root", type=Path, default=PipelineSettings().export_root)
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic light curves for local testing.")
    parser.add_argument("--tic-target-file", type=Path, help="CSV file with a tic_id column for real TESS fetches.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = PipelineSettings(export_root=args.export_root)
    result = run_nightly(
        sector=args.sector,
        limit=args.limit,
        settings=settings,
        synthetic=args.synthetic,
        tic_target_file=args.tic_target_file,
    )
    print(f"Exported {len(result.candidates)} candidates to {result.export_dir}")


if __name__ == "__main__":
    main()
