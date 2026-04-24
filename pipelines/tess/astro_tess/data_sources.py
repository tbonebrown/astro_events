from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import csv

import numpy as np

from astro_tess.models import LightCurveSample


class TessSourceError(RuntimeError):
    """Raised when a TESS source cannot load samples."""


@dataclass(slots=True)
class SyntheticTessSource:
    seed: int = 7

    def fetch_samples(self, sector: int, limit: int) -> list[LightCurveSample]:
        rng = np.random.default_rng(self.seed + sector)
        samples: list[LightCurveSample] = []

        for index in range(limit):
            tic_id = f"{sector:03d}{index + 1000:06d}"
            time = np.linspace(0.0, 27.0, 720)
            baseline = 1.0 + 0.002 * np.sin(time * rng.uniform(0.2, 1.4))
            periodic = 0.01 * np.sin(time * rng.uniform(1.0, 5.0) + rng.uniform(0, np.pi))
            noise = rng.normal(0.0, 0.0025, size=time.size)
            flux = baseline + periodic + noise

            if index % 6 == 0:
                event_center = rng.uniform(3.0, 24.0)
                flux -= 0.04 * np.exp(-0.5 * ((time - event_center) / 0.25) ** 2)
            if index % 10 == 0:
                jump_index = rng.integers(100, 600)
                flux[jump_index:] += rng.uniform(-0.03, 0.03)
            if index % 15 == 0:
                flux += 0.02 * np.sign(np.sin(time * 0.8))

            samples.append(
                LightCurveSample(
                    tic_id=tic_id,
                    sector=sector,
                    time=time,
                    flux=flux,
                    provenance={"source": "synthetic", "generator_seed": self.seed + sector},
                )
            )
        return samples


def load_tic_ids(target_file: Path) -> list[str]:
    tic_ids: list[str] = []
    with target_file.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("tic_id"):
                tic_ids.append(str(row["tic_id"]).strip())
    return tic_ids


@dataclass(slots=True)
class LightkurveTessSource:
    tic_ids: Iterable[str]

    def fetch_samples(self, sector: int, limit: int) -> list[LightCurveSample]:
        try:
            from lightkurve import search_lightcurve
        except ImportError as exc:
            raise TessSourceError(
                "lightkurve is required for real TESS downloads. Install with `pip install .[tess]`."
            ) from exc

        samples: list[LightCurveSample] = []
        for tic_id in list(self.tic_ids)[:limit]:
            result = search_lightcurve(f"TIC {tic_id}", mission="TESS", sector=sector)
            if len(result) == 0:
                continue
            light_curve = result[0].download()
            cleaned = light_curve.remove_nans()
            samples.append(
                LightCurveSample(
                    tic_id=str(tic_id),
                    sector=sector,
                    time=np.asarray(cleaned.time.value),
                    flux=np.asarray(cleaned.flux.value),
                    provenance={"source": "mast", "author": getattr(result[0], "author", "unknown")},
                )
            )

        if not samples:
            raise TessSourceError("No TESS light curves were downloaded for the requested sector.")
        return samples

