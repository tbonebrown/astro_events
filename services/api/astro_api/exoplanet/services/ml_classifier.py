from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from astro_api.config import AppSettings


CLASSES = ("likely_transit", "eclipsing_binary", "stellar_variability", "noise")


@dataclass(slots=True)
class FoldedClassifier:
    settings: AppSettings

    def classify(self, phase: np.ndarray, flux: np.ndarray, snr: float, depth: float) -> dict:
        torch_module = self._import_torch()
        if torch_module is None or not self.settings.use_gpu_classifier:
            return self._heuristic(phase, flux, snr, depth, device="cpu", backend="numpy")

        torch, device = torch_module
        try:
            binned = self._bin_phase_curve(phase, flux, bins=128)
            tensor = torch.tensor(binned, dtype=torch.float32, device=device)
            median_flux = torch.nanmedian(tensor)
            min_flux = torch.nanmin(tensor)
            dip = torch.clamp(median_flux - min_flux, min=0.0)
            scatter = torch.nanstd(tensor - median_flux) + 1e-6
            compactness = torch.mean((tensor < median_flux - 0.35 * dip).float())
            transit_logit = (snr - 5.0) / 2.8 + float(torch.clamp(dip / scatter, 0, 8)) / 4.0
            eb_logit = max(0.0, float(depth) - 0.035) * 32.0 + max(0.0, float(compactness) - 0.20) * 6.0
            variability_logit = max(0.0, float(scatter) - max(float(depth), 1e-4)) * 18.0
            noise_logit = max(0.0, 5.0 - snr) / 2.0
            logits = torch.tensor(
                [transit_logit, eb_logit, variability_logit, noise_logit],
                dtype=torch.float32,
                device=device,
            )
            probs = torch.softmax(logits, dim=0).detach().cpu().numpy()
            probabilities = {label: round(float(prob), 4) for label, prob in zip(CLASSES, probs)}
            label = max(probabilities, key=probabilities.get)
            return {
                "label": label,
                "probabilities": probabilities,
                "device": str(device),
                "backend": "torch",
            }
        except Exception:
            return self._heuristic(phase, flux, snr, depth, device="cpu", backend="numpy-fallback")

    def _import_torch(self):
        try:
            import torch
        except Exception:
            return None

        requested = self.settings.gpu_device
        if requested.startswith("hip") and getattr(torch.version, "hip", None):
            requested = "cuda:" + requested.split(":", 1)[1] if ":" in requested else "cuda:0"
        if requested.startswith("cuda") and not torch.cuda.is_available():
            requested = self.settings.rocm_device if getattr(torch.version, "hip", None) else "cpu"
        if requested.startswith("hip") and not getattr(torch.version, "hip", None):
            requested = "cpu"
        try:
            device = torch.device(requested)
            _ = torch.zeros(1, device=device)
        except Exception:
            device = torch.device("cpu")
        return torch, device

    @staticmethod
    def _bin_phase_curve(phase: np.ndarray, flux: np.ndarray, bins: int) -> np.ndarray:
        phase = np.asarray(phase, dtype=float)
        flux = np.asarray(flux, dtype=float)
        edges = np.linspace(-0.5, 0.5, bins + 1)
        centers = 0.5 * (edges[:-1] + edges[1:])
        binned = np.interp(centers, phase, flux, left=np.nanmedian(flux), right=np.nanmedian(flux))
        return np.where(np.isfinite(binned), binned, np.nanmedian(flux))

    @staticmethod
    def _heuristic(phase: np.ndarray, flux: np.ndarray, snr: float, depth: float, device: str, backend: str) -> dict:
        flux = np.asarray(flux, dtype=float)
        scatter = float(np.nanstd(flux - np.nanmedian(flux))) or 1e-6
        depth_to_scatter = max(0.0, float(depth)) / scatter
        transit = 1.0 / (1.0 + math.exp(-((snr - 5.0) / 2.8 + depth_to_scatter / 4.0)))
        eb = min(0.85, max(0.02, depth * 18.0))
        variability = min(0.75, max(0.03, scatter * 18.0))
        noise = min(0.9, max(0.03, (5.0 - snr) / 8.0))
        raw = np.asarray([transit, eb, variability, noise], dtype=float)
        raw = raw / raw.sum()
        probabilities = {label: round(float(prob), 4) for label, prob in zip(CLASSES, raw)}
        label = max(probabilities, key=probabilities.get)
        return {
            "label": label,
            "probabilities": probabilities,
            "device": device,
            "backend": backend,
        }
