from __future__ import annotations

from dataclasses import dataclass
import json

import httpx

from astro_api.config import AppSettings


@dataclass(slots=True)
class LocalInferenceClient:
    settings: AppSettings

    def _post_prompt(self, prompt: str) -> str | None:
        try:
            if self.settings.local_inference_provider == "openai_compatible":
                payload = {
                    "model": self.settings.local_inference_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "temperature": 0.2,
                }
            else:
                payload = {
                    "model": self.settings.local_inference_model,
                    "prompt": prompt,
                    "stream": False,
                }
            response = httpx.post(self.settings.local_inference_url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                if self.settings.local_inference_provider == "openai_compatible":
                    choices = data.get("choices")
                    if isinstance(choices, list) and choices:
                        message = choices[0].get("message", {})
                        if isinstance(message, dict) and isinstance(message.get("content"), str):
                            return message["content"]
                return data.get("response") or data.get("text") or data.get("output")
        except Exception:
            return None
        return None

    def candidate_explanation(self, candidate: dict) -> tuple[str, str]:
        prompt = (
            "You are an astronomy assistant writing concise public-facing explanations.\n"
            f"Candidate ID: {candidate['candidate_id']}\n"
            f"Sector: {candidate['sector']}\n"
            f"Anomaly score: {candidate['anomaly_score']:.4f}\n"
            f"Variability hint: {candidate['variability_hint']}\n"
            f"Top features: {candidate['top_features']}\n"
            f"Score breakdown: {candidate['score_breakdown']}\n"
            "Explain in 2-4 sentences why this object is interesting and what pattern stands out."
        )
        generated = self._post_prompt(prompt)
        if generated:
            return generated.strip(), "generated"
        return self._fallback_candidate_explanation(candidate), "fallback"

    def nightly_report(self, run_payload: dict) -> tuple[str, str]:
        prompt = (
            "You are preparing a nightly astronomy candidate summary for a public dashboard.\n"
            f"Run: {run_payload['run_date']} sector {run_payload['sector']}\n"
            f"Top candidates: {run_payload['top_candidates']}\n"
            "Write a short markdown report with a headline and a concise summary of the strongest patterns."
        )
        generated = self._post_prompt(prompt)
        if generated:
            return generated.strip(), "generated"
        return self._fallback_report(run_payload), "fallback"

    def transient_summary(self, candidate: dict) -> tuple[str, str]:
        prompt = (
            "You are an astronomy assistant writing concise public-facing transient summaries.\n"
            f"Candidate ID: {candidate['candidate_id']}\n"
            f"Classification: {candidate['classification_hint']}\n"
            f"Magnitude: {candidate['magnitude']:.3f}\n"
            f"Magnitude change: {candidate['magnitude_change']:.3f}\n"
            f"Score breakdown: {candidate['score_breakdown']}\n"
            "Explain in 2-3 sentences why this alert matters to a citizen astronomer."
        )
        generated = self._post_prompt(prompt)
        if generated:
            return generated.strip(), "generated"
        return self._fallback_transient_summary(candidate), "fallback"

    def transient_report(self, run_payload: dict) -> tuple[str, str]:
        prompt = (
            "You are preparing a nightly transient summary for a public astronomy dashboard.\n"
            f"Run: {run_payload['run_date']} source {run_payload['source_name']}\n"
            f"Top candidates: {run_payload['top_candidates']}\n"
            "Write a short markdown report with a headline, why these alerts matter, and a brief watchlist."
        )
        generated = self._post_prompt(prompt)
        if generated:
            return generated.strip(), "generated"
        return self._fallback_transient_report(run_payload), "fallback"

    def galaxy_explanation(
        self,
        galaxy: dict,
        cluster_summary: dict,
        neighbors: list[dict],
    ) -> tuple[str, str]:
        prompt = (
            "You are an astronomy assistant explaining a galaxy embedding map for a public demo.\n"
            f"Galaxy ID: {galaxy['image_id']}\n"
            f"Morphology: {galaxy['morphology']}\n"
            f"Predicted class: {galaxy['predicted_class']}\n"
            f"Classification confidence: {galaxy['confidence']:.3f}\n"
            f"Cluster: {cluster_summary.get('cluster_name', 'Unknown')} "
            f"({cluster_summary.get('count', 0)} members)\n"
            f"Cluster summary: {cluster_summary.get('summary', '')}\n"
            f"Feature tags: {galaxy['metadata'].get('feature_tags', [])}\n"
            f"Nearest neighbors: {[neighbor['predicted_class'] for neighbor in neighbors[:5]]}\n"
            "Explain the morphology and characteristics of this galaxy based on its cluster and nearest neighbors. "
            "Keep the answer to 3-4 sentences, visually descriptive, and clear for a client demo."
        )
        generated = self._post_prompt(prompt)
        if generated:
            return generated.strip(), "generated"
        return self._fallback_galaxy_explanation(galaxy, cluster_summary, neighbors), "fallback"

    def celestial_event_copy(self, event: dict) -> dict:
        prompt = (
            "You are an astronomy assistant writing a personalized sky guide.\n"
            "Return strict JSON with keys: summary, why_interesting, explanation.\n"
            f"Title: {event['title']}\n"
            f"Type: {event['type']}\n"
            f"Description: {event['description']}\n"
            f"Visibility label: {event['visibility_label']}\n"
            f"Best viewing time: {event['best_viewing_time']}\n"
            f"Observation method: {event['observation_method']}\n"
            f"Sky direction: {event['sky_position']}\n"
            "Explain what it is, why it happens, how rare it is, and how to view it from the user's location."
        )
        generated = self._post_prompt(prompt)
        if generated:
            parsed = self._parse_json(generated)
            if parsed:
                return {
                    "summary": str(parsed.get("summary") or self.fallback_celestial_summary(event)),
                    "why_interesting": str(
                        parsed.get("why_interesting") or self._fallback_celestial_why(event)
                    ),
                    "explanation": str(
                        parsed.get("explanation") or self._fallback_celestial_explanation(event)
                    ),
                    "source": "generated",
                }
        return {
            "summary": self.fallback_celestial_summary(event),
            "why_interesting": self._fallback_celestial_why(event),
            "explanation": self._fallback_celestial_explanation(event),
            "source": "fallback",
        }

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        candidate = text.strip()
        if candidate.startswith("```"):
            candidate = candidate.strip("`")
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
        try:
            payload = json.loads(candidate)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _fallback_candidate_explanation(candidate: dict) -> str:
        return (
            f"{candidate['candidate_id']} stands out because its ensemble anomaly score is "
            f"{candidate['anomaly_score']:.3f}, driven by a {candidate['variability_hint']} signature. "
            f"The strongest signals are {', '.join(list(candidate['top_features'])[:3])}, which makes it a useful "
            "follow-up target for visual inspection and downstream vetting."
        )

    @staticmethod
    def _fallback_report(run_payload: dict) -> str:
        lines = [
            f"# Nightly TESS Report: Sector {run_payload['sector']}",
            "",
            f"Processed {run_payload['candidate_count']} ranked candidates for {run_payload['run_date']}.",
            "",
            "## Highlights",
        ]
        for candidate in run_payload["top_candidates"][:5]:
            lines.append(
                f"- `{candidate['candidate_id']}` scored {candidate['anomaly_score']:.3f} with a "
                f"{candidate['variability_hint']} signature."
            )
        return "\n".join(lines)

    @staticmethod
    def _fallback_transient_summary(candidate: dict) -> str:
        novelty = " It is flagged as novel for follow-up." if candidate["novelty_flag"] else ""
        return (
            f"{candidate['external_alert_id']} is a {candidate['classification_hint'].lower()} alert with "
            f"a score of {candidate['score']:.3f}. Its brightness changed by "
            f"{candidate['magnitude_change']:.2f} magnitudes, making it a strong dashboard candidate."
            f"{novelty}"
        )

    @staticmethod
    def _fallback_transient_report(run_payload: dict) -> str:
        lines = [
            f"# Nightly Transient Report: {run_payload['source_name'].upper()}",
            "",
            f"Processed {run_payload['candidate_count']} ranked alerts for {run_payload['run_date']}.",
            "",
            "## Why These Matter",
            "These alerts combine strong brightness changes, recent publication times, and useful context for follow-up.",
            "",
            "## Watchlist",
        ]
        for candidate in run_payload["top_candidates"][:5]:
            lines.append(
                f"- `{candidate['external_alert_id']}` scored {candidate['score']:.3f} as a "
                f"{candidate['classification_hint'].lower()} candidate."
            )
        return "\n".join(lines)

    @staticmethod
    def _fallback_galaxy_explanation(
        galaxy: dict,
        cluster_summary: dict,
        neighbors: list[dict],
    ) -> str:
        neighbor_labels = ", ".join(neighbor["predicted_class"].lower() for neighbor in neighbors[:3]) or "similar systems"
        feature_tags = ", ".join(galaxy["metadata"].get("feature_tags", [])[:3]) or "shared morphology cues"
        rarity_note = (
            "It also sits in a sparse region of the embedding map, so it is a good rare-object candidate."
            if galaxy.get("rarity_score", 0.0) >= 0.82
            else "It lives inside a dense morphology family, which makes its nearest neighbors visually consistent."
        )
        return (
            f"This galaxy lands in {cluster_summary.get('cluster_name', 'a morphology cluster')}, where "
            f"{cluster_summary.get('dominant_class', galaxy['predicted_class']).lower()} shapes dominate. "
            f"Its visual signature is consistent with {feature_tags}, and its nearest neighbors look most like {neighbor_labels}. "
            f"{rarity_note}"
        )

    @staticmethod
    def fallback_celestial_summary(event: dict) -> str:
        direction = event.get("sky_position", {}).get("direction", "the southern sky")
        altitude = event.get("sky_position", {}).get("altitude_deg", 35)
        return (
            f"{event['title']} looks {event.get('visibility_label', 'moderate').lower()} from this location. "
            f"Plan to look {direction} with the event about {altitude} degrees above the horizon."
        )

    @staticmethod
    def _fallback_celestial_why(event: dict) -> str:
        return (
            f"This {event['type'].replace('_', ' ')} stands out because it combines a "
            f"{event.get('visibility_label', 'moderate').lower()} viewing window with an easy public-facing observing story."
        )

    @staticmethod
    def _fallback_celestial_explanation(event: dict) -> str:
        return (
            f"{event['title']} is a {event['type'].replace('_', ' ')} event. {event['description']} "
            f"It reaches its best local viewing window around {event['best_viewing_time']}. "
            f"For this location, the most comfortable plan is to look {event.get('sky_position', {}).get('direction', 'south')} "
            f"and use {event['observation_method']}."
        )
