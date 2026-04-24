from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save_light_curve_plot(
    candidate_id: str,
    time: np.ndarray,
    flux: np.ndarray,
    output_dir: Path,
    dpi: int = 150,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{candidate_id.replace(':', '_')}.png"

    figure, axis = plt.subplots(figsize=(8, 3.2), constrained_layout=True)
    axis.plot(time, flux, linewidth=1.0, color="#35c8ff")
    axis.set_title(candidate_id)
    axis.set_xlabel("Time")
    axis.set_ylabel("Normalized flux")
    axis.grid(alpha=0.25)
    figure.savefig(target, dpi=dpi)
    plt.close(figure)
    return target

