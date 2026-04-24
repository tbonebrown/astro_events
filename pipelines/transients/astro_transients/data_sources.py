from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
import csv
import io
import re

import httpx
import numpy as np

from astro_transients.models import GaiaAlert


class GaiaSourceError(RuntimeError):
    """Raised when Gaia alerts cannot be fetched or parsed."""


def _safe_float(value: str | float | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_value(row: dict[str, str], *keys: str) -> str:
    normalized = {
        key.strip().lower().replace(" ", "").replace(".", "").replace("_", ""): value
        for key, value in row.items()
    }
    for key in keys:
        normalized_key = key.strip().lower().replace(" ", "").replace(".", "").replace("_", "")
        if normalized_key in normalized:
            return str(normalized[normalized_key]).strip()
    return ""


class _AlertsIndexTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_header = False
        self.current_cells: list[str] = []
        self.headers: list[str] = []
        self.rows: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and not self.in_table:
            self.in_table = True
            return
        if not self.in_table:
            return
        if tag == "tr":
            self.in_row = True
            self.current_cells = []
        elif tag in {"th", "td"} and self.in_row:
            self.in_cell = True
            self.current_header = tag == "th"
            self.current_cells.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.in_table:
            self.in_table = False
            return
        if not self.in_table:
            return
        if tag in {"th", "td"}:
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.current_cells:
                if not self.headers and self.current_header:
                    self.headers = [cell.strip() for cell in self.current_cells]
                elif self.headers and len(self.current_cells) >= len(self.headers):
                    row = {
                        header: self.current_cells[index].strip()
                        for index, header in enumerate(self.headers)
                    }
                    self.rows.append(row)
            self.in_row = False
            self.current_header = False

    def handle_data(self, data: str) -> None:
        if self.in_table and self.in_row and self.in_cell and self.current_cells:
            self.current_cells[-1] += data


def _normalize_row(row: dict[str, str], base_url: str) -> GaiaAlert | None:
    name = _row_value(row, "Name")
    if not name:
        return None

    observed_at = _row_value(row, "Observed", "ObsTime")
    published_at = _row_value(row, "Published") or observed_at
    ra = _safe_float(_row_value(row, "RA (deg.)", "RA"))
    dec = _safe_float(_row_value(row, "Dec. (deg.)", "Dec"))
    magnitude = _safe_float(_row_value(row, "Mag.", "Magnitude", "GMag"))
    if ra is None or dec is None or magnitude is None:
        return None

    historic_magnitude = _safe_float(_row_value(row, "Historic mag.", "Historic mag"))
    historic_scatter = _safe_float(_row_value(row, "Historic scatter", "GMagErr"))
    alert_url = urljoin(base_url, f"/alerts/alert/{name}")
    return GaiaAlert(
        name=name,
        external_alert_id=name,
        observed_at=observed_at,
        published_at=published_at,
        ra=ra,
        dec=dec,
        magnitude=magnitude,
        historic_magnitude=historic_magnitude,
        historic_scatter=historic_scatter,
        classification=_row_value(row, "Class"),
        comment=_row_value(row, "Comment"),
        tns_name=_row_value(row, "TNS"),
        source_id=_row_value(row, "SourceID"),
        alert_url=alert_url,
        metadata={key: value for key, value in row.items() if value not in ("", None)},
    )


def _parse_delimited_payload(text: str, base_url: str) -> list[GaiaAlert]:
    sample = text[:1024]
    delimiter = "|"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",|\t;")
        delimiter = dialect.delimiter
    except csv.Error:
        if "," in sample:
            delimiter = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    alerts = [_normalize_row(dict(row), base_url) for row in reader]
    return [alert for alert in alerts if alert is not None]


def _parse_html_table(text: str, base_url: str) -> list[GaiaAlert]:
    parser = _AlertsIndexTableParser()
    parser.feed(text)
    alerts = [_normalize_row(row, base_url) for row in parser.rows]
    return [alert for alert in alerts if alert is not None]


@dataclass(slots=True)
class SyntheticGaiaSource:
    seed: int = 29

    def fetch_alerts(self, limit: int) -> list[GaiaAlert]:
        rng = np.random.default_rng(self.seed + limit)
        now = datetime.now(timezone.utc)
        classifications = [
            "SN candidate",
            "Microlensing",
            "CV candidate",
            "Unknown",
            "Fast transient",
        ]
        alerts: list[GaiaAlert] = []
        for index in range(limit):
            observed = now - timedelta(hours=float(index * 4 + rng.uniform(0.5, 2.5)))
            published = observed + timedelta(hours=float(rng.uniform(3.0, 24.0)))
            magnitude = float(rng.uniform(14.2, 19.4))
            historic = magnitude + float(rng.uniform(-3.2, 1.2))
            classification = classifications[index % len(classifications)]
            name = f"Gaia{now.year % 100:02d}{chr(97 + (index % 26))}{chr(97 + ((index // 26) % 26))}{index:02d}"
            alerts.append(
                GaiaAlert(
                    name=name,
                    external_alert_id=name,
                    observed_at=observed.isoformat(),
                    published_at=published.isoformat(),
                    ra=float(rng.uniform(0.0, 360.0)),
                    dec=float(rng.uniform(-70.0, 70.0)),
                    magnitude=magnitude,
                    historic_magnitude=historic,
                    historic_scatter=float(rng.uniform(0.03, 0.8)),
                    classification=classification,
                    comment="Synthetic Gaia alert for local testing.",
                    tns_name="" if index % 3 else f"AT {now.year}{index:03d}",
                    source_id=f"{int(rng.integers(10**17, 10**18 - 1))}",
                    alert_url=f"https://gsaweb.ast.cam.ac.uk/alerts/alert/{name}",
                    metadata={"source": "synthetic"},
                )
            )
        return alerts


@dataclass(slots=True)
class GaiaAlertsSource:
    alerts_url: str

    def fetch_alerts(self, limit: int) -> list[GaiaAlert]:
        try:
            response = httpx.get(self.alerts_url, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
        except Exception as exc:
            raise GaiaSourceError(f"Unable to fetch Gaia alerts from {self.alerts_url}.") from exc

        text = response.text.strip()
        if not text:
            raise GaiaSourceError("Gaia alerts response was empty.")

        content_type = response.headers.get("content-type", "")
        if "html" in content_type or text.lstrip().startswith("<"):
            alerts = _parse_html_table(text, str(response.url))
            if not alerts:
                csv_links = re.findall(r'href=["\']([^"\']+\.csv)["\']', text, flags=re.IGNORECASE)
                for link in csv_links:
                    csv_url = urljoin(str(response.url), link)
                    try:
                        csv_response = httpx.get(csv_url, follow_redirects=True, timeout=60.0)
                        csv_response.raise_for_status()
                    except Exception:
                        continue
                    alerts = _parse_delimited_payload(csv_response.text, csv_url)
                    if alerts:
                        break
        else:
            alerts = _parse_delimited_payload(text, str(response.url))

        if not alerts:
            raise GaiaSourceError("No Gaia alerts were parsed from the configured source.")
        return alerts[:limit]
