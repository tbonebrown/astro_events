from __future__ import annotations

import argparse
from pathlib import Path

from astro_api.config import AppSettings
from astro_api.database import Base, SessionLocal, engine
from astro_api.services.ingestion import ingest_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a nightly export into the Astro Events API database.")
    parser.add_argument("--export-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = AppSettings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        run = ingest_export(args.export_dir, session=session, settings=settings)
    print(f"Ingested sector {run.sector} run {run.run_date} from {args.export_dir}")


if __name__ == "__main__":
    main()
