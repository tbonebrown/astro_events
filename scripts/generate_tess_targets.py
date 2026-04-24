from __future__ import annotations

import csv
import os
from pathlib import Path



def _env_float(name: str, default: float | None) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _build_criteria() -> dict[str, list[float]]:
    criteria: dict[str, list[float]] = {}

    min_tmag = _env_float("TESS_TARGET_MIN_TMAG", 8.0)
    max_tmag = _env_float("TESS_TARGET_MAX_TMAG", 13.0)
    min_teff = _env_float("TESS_TARGET_MIN_TEFF", 3500.0)
    max_teff = _env_float("TESS_TARGET_MAX_TEFF", 7500.0)
    min_logg = _env_float("TESS_TARGET_MIN_LOGG", 4.1)
    max_logg = _env_float("TESS_TARGET_MAX_LOGG", 5.2)

    numeric_filters = [
        ("Tmag", min_tmag, max_tmag),
        ("Teff", min_teff, max_teff),
        ("logg", min_logg, max_logg),
    ]

    for column, minimum, maximum in numeric_filters:
        if minimum is None and maximum is None:
            continue
        lower = minimum if minimum is not None else float("-inf")
        upper = maximum if maximum is not None else float("inf")
        criteria[column] = [lower, upper]

    return criteria


def _clean_value(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def main() -> None:
    catalog = os.getenv("TESS_TARGET_CATALOG", "ctl").strip().lower()
    if catalog not in {"ctl", "tic"}:
        raise SystemExit("TESS_TARGET_CATALOG must be either 'ctl' or 'tic'.")

    try:
        from astroquery.mast import Catalogs
    except ImportError as exc:
        raise SystemExit(
            "astroquery is required for TESS target generation. Install with `pip install -e .[targets]`."
        ) from exc

    output_path = Path(
        os.getenv(
            "TESS_TARGET_OUTPUT",
            "/home/tbone/astro_events_runtime/config/tic_targets.csv",
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    limit = _env_int("TESS_TARGET_LIMIT", 500)
    criteria = _build_criteria()
    table = Catalogs.query_criteria(catalog=catalog.capitalize(), **criteria)
    available_columns = set(table.colnames)

    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in table:
        tic_id = str(_clean_value(row["ID"])).strip()
        if not tic_id or tic_id in seen_ids:
            continue
        seen_ids.add(tic_id)
        deduped.append(
            {
                "tic_id": tic_id,
                "source_catalog": catalog,
                "tmag": _clean_value(row["Tmag"]) if "Tmag" in available_columns else None,
                "teff": _clean_value(row["Teff"]) if "Teff" in available_columns else None,
                "logg": _clean_value(row["logg"]) if "logg" in available_columns else None,
                "ra": _clean_value(row["ra"]) if "ra" in available_columns else None,
                "dec": _clean_value(row["dec"]) if "dec" in available_columns else None,
            }
        )
        if len(deduped) >= limit:
            break

    if not deduped:
        raise SystemExit("No TESS targets were returned from the configured MAST query.")

    temp_path = output_path.with_suffix(".csv.tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["tic_id", "source_catalog", "tmag", "teff", "logg", "ra", "dec"],
        )
        writer.writeheader()
        writer.writerows(deduped)
    temp_path.replace(output_path)
    print(f"Wrote {len(deduped)} TESS targets to {output_path}")


if __name__ == "__main__":
    main()
