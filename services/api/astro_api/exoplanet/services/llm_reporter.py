from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import httpx

from astro_api.config import AppSettings


REPORT_TITLES = [
    "Summary",
    "What the light curve shows",
    "Candidate signal",
    "Known object lookup",
    "Why this could be a planet",
    "Why this could be a false positive",
    "Recommended next steps",
]


@dataclass(slots=True)
class LLMReporter:
    settings: AppSettings

    def build_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        generated = self._call_llm(payload)
        if generated:
            parsed = self._parse_report(generated, payload)
            if parsed:
                return parsed
        return self._fallback_report(payload)

    def _call_llm(self, payload: dict[str, Any]) -> str | None:
        prompt = (
            "You are writing an astronomy report for Exoplanet Hunter. "
            "Use only the JSON measurements supplied. Do not invent missing values. "
            "Never say a new planet was discovered or confirmed by this app. "
            "Use the phrase candidate requiring validation when the object is not a catalog match. "
            "Return strict JSON with keys title, sections. sections must be an array of "
            "{title, body} and use these section titles: "
            f"{REPORT_TITLES}.\n\n"
            f"MEASUREMENTS_JSON={json.dumps(payload, sort_keys=True)}"
        )
        base_url = self.settings.llm_base_url.rstrip("/")
        url = base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions" if url.endswith("/v1") else f"{url}/v1/chat/completions"
        try:
            response = httpx.post(
                url,
                json={
                    "model": self.settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.15,
                    "stream": False,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
        except Exception:
            return None
        return None

    def _parse_report(self, text: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            return None
        sections = data.get("sections") if isinstance(data, dict) else None
        if not isinstance(sections, list):
            return None
        normalized_sections = []
        for title in REPORT_TITLES:
            match = next((section for section in sections if section.get("title") == title), None)
            if match and isinstance(match.get("body"), str):
                normalized_sections.append({"title": title, "body": self._guardrail(match["body"])})
        if len(normalized_sections) < 4:
            return None
        return {
            "title": self._guardrail(str(data.get("title") or f"Exoplanet Hunter report for {payload['target_name']}")),
            "generated_by": "local_llm",
            "safety_note": "This report explains a possible transit signal. It does not claim discovery or confirmation.",
            "sections": normalized_sections,
            "technical_metrics": payload,
        }

    @staticmethod
    def _guardrail(text: str) -> str:
        replacements = {
            "new planet discovered": "possible transit signal identified",
            "discovered a new planet": "identified a candidate requiring validation",
            "confirmed a new exoplanet": "found a candidate requiring validation",
            "new exoplanet": "candidate signal",
        }
        guarded = text
        for bad, good in replacements.items():
            guarded = guarded.replace(bad, good).replace(bad.title(), good)
        return guarded

    def _fallback_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        archive = payload["archive_match"]
        candidate_phrase = (
            f"matches {archive['object_name']} in {archive['catalog']}"
            if archive.get("status") == "match"
            else "is a candidate requiring validation"
        )
        sections = [
            {
                "title": "Summary",
                "body": (
                    f"{payload['target_name']} shows a possible transit signal near "
                    f"{payload['period_days']:.5f} days. The signal {candidate_phrase}."
                ),
            },
            {
                "title": "What the light curve shows",
                "body": (
                    f"The pipeline normalized, cleaned, and detrended {payload['point_count']} photometric points. "
                    f"The best periodic dip has a depth of about {payload['depth_ppm']:.1f} ppm."
                ),
            },
            {
                "title": "Candidate signal",
                "body": (
                    f"Box Least Squares prefers period {payload['period_days']:.5f} days, duration "
                    f"{payload['duration_hours']:.2f} hours, and SNR {payload['snr']:.2f}. "
                    f"The approximate planet-to-star radius ratio from sqrt(depth) is {payload['radius_ratio']:.4f}."
                ),
            },
            {
                "title": "Known object lookup",
                "body": archive.get("notes") or "No archive match was available.",
            },
            {
                "title": "Why this could be a planet",
                "body": (
                    "Repeated, shallow, period-consistent dips are the pattern expected when an orbiting body "
                    "crosses the face of its star."
                ),
            },
            {
                "title": "Why this could be a false positive",
                "body": (
                    "Eclipsing binaries, stellar variability, instrumental trends, blended sources, or poor detrending "
                    "can mimic a transit-like dip."
                ),
            },
            {
                "title": "Recommended next steps",
                "body": (
                    "Inspect nearby sources, compare sectors or quarters, run centroid and odd-even transit checks, "
                    "and confirm the ephemeris with independent observations before making any scientific claim."
                ),
            },
        ]
        return {
            "title": f"Exoplanet Hunter report for {payload['target_name']}",
            "generated_by": "fallback",
            "safety_note": "This report explains a possible transit signal. It does not claim discovery or confirmation.",
            "sections": sections,
            "technical_metrics": payload,
        }
