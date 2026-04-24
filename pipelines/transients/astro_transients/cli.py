from __future__ import annotations

import argparse
from pathlib import Path

from astro_transients.config import PipelineSettings
from astro_transients.pipeline import run_nightly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Astro Event Intelligence Gaia transient pipeline.")
    parser.add_argument("--limit", type=int, default=PipelineSettings().default_limit)
    parser.add_argument("--export-root", type=Path, default=PipelineSettings().export_root)
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic Gaia alerts for local testing.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = PipelineSettings(export_root=args.export_root)
    result = run_nightly(limit=args.limit, settings=settings, synthetic=args.synthetic)
    print(f"Exported {len(result.candidates)} transient candidates to {result.export_dir}")


if __name__ == "__main__":
    main()
