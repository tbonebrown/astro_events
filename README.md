# Astro Event Intelligence

Astro Event Intelligence is an astronomy MVP intended to live at `ohnita.com` as a single public
homepage with path-based app routes such as `/transients`, `/transients/reports/latest`, and
`/tess`.

The root homepage acts as a launcher for the hosted tools, with buttons that send visitors into
each module without changing domains.

The stack currently includes two complementary pipelines:

- TESS light-curve anomaly detection for unusual stellar variability.
- Gaia-first transient alert triage for newly changing sky events, ranked for citizen astronomers.

## Architecture

- `pipelines/tess`: nightly ingest, cleaning, feature extraction, anomaly scoring, artifact export, and sync from the 5090 workstation.
- `pipelines/transients`: nightly Gaia alert ingest, enrichment, scoring, summary generation, export, and sync from the 5090 workstation.
- `services/api`: FastAPI backend, Postgres ingestion, candidate APIs, nightly report generation, and React asset serving on the R9700 server.
- `services/web`: React + Vite public frontend for the root launcher, transient feeds, candidate detail pages, nightly reports, and TESS watchlist views.

## Quick start

1. Create a virtual environment and install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .[dev]
```

2. Install frontend dependencies:

```bash
cd services/web
npm install
```

3. Copy `.env.example` to `.env` and adjust the database and inference settings.
4. Run the backend:

```bash
uvicorn services.api.main:app --reload
```

5. Run the frontend during development:

```bash
cd services/web
npm run dev
```

6. Run the synthetic nightly pipelines:

```bash
astro-tess-nightly --synthetic --limit 12 --export-root ./exports
astro-api-ingest --export-dir ./exports/latest
astro-transients-nightly --synthetic --limit 12 --export-root ./exports
astro-api-ingest-transients --export-dir ./exports/transients/latest
```

## Deployment notes

- The public app is intended to run on the R9700 server behind Cloudflare Tunnel.
- The transient module is Gaia-first in v1 and defers raw ZTF/Rubin difference imaging to a later phase.
- The public entrypoint is the root hostname `ohnita.com`.
- Individual app views are published as SPA paths under the same origin, including `/transients`,
  `/transients/reports/latest`, and `/tess`.
- Postgres is the application system of record; Parquet exports remain the immutable ML artifact layer.
- The repository includes example `systemd`, Docker, and Cloudflare Tunnel scaffolding under `ops/`.

### Minimum steps to make the site live

1. Build the frontend on the server:

```bash
cd /srv/astro_events/services/web
npm install
npm run build
```

2. Install Python dependencies and create `.env` from `.env.example`.
3. Start the API on the server so it listens on `127.0.0.1:8000`.
4. Install the Cloudflare tunnel config from `ops/cloudflare/cloudflared.example.yml` and point it at your real tunnel credentials file.
5. In Cloudflare DNS/Tunnel routing, map `ohnita.com` to that tunnel.
6. Start `cloudflared` and verify `http://127.0.0.1:8000/api/health` works locally on the server before checking the public domain.
