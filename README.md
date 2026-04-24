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
uvicorn services.api.main:app --reload --proxy-headers --forwarded-allow-ips='*'
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

### Windows workstation quick start

If you are running the pipelines on the Windows 5090 workstation, the repository now includes
PowerShell helpers under `ops/windows`:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File .\ops\windows\seed_demo_data.ps1
powershell -ExecutionPolicy Bypass -File .\ops\windows\register_tasks.ps1
```

`seed_demo_data.ps1` runs the first synthetic publish so the local API has content immediately.
`register_tasks.ps1` creates an `Astro Events API` scheduled task that starts the API on logon.
`publish_latest_to_server.ps1` copies the current `latest` TESS and transient export trees from the
workstation to the Linux server runtime path at `tbone@100.81.22.102:~/astro_events_runtime/exports`.
`register_nightly_task.ps1` creates a `3:00 AM` scheduled task that runs transients nightly, publishes
them to the server, and runs TESS only when `TESS_TARGET_FILE` exists in `.env` or at
`data\tic_targets.csv`.
`refresh_tess_targets.ps1` can download that CSV automatically before the nightly run when
`TESS_TARGET_URL` is set in `.env`, or copy it from the server first when
`TESS_TARGET_SERVER_PATH` is set to something like
`tbone@100.81.22.102:astro_events_runtime/config/tic_targets.csv`.

### Automated TESS target generation

The repository also includes a server-side generator for `tic_targets.csv`. It queries the official
MAST TIC or CTL services, writes the result to `TESS_TARGET_OUTPUT`, and can be scheduled before the
workstation's `3:00 AM` run:

```bash
source .venv/bin/activate
python3 ./scripts/generate_tess_targets.py
```

The default configuration uses the curated `CTL` catalog and writes a target list with a `tic_id`
column plus helpful metadata. You can tune the generated target list using environment variables such
as `TESS_TARGET_LIMIT`, `TESS_TARGET_MIN_TMAG`, `TESS_TARGET_MAX_TMAG`, `TESS_TARGET_MIN_TEFF`,
`TESS_TARGET_MAX_TEFF`, `TESS_TARGET_MIN_LOGG`, and `TESS_TARGET_MAX_LOGG`.

## Deployment notes

- The public app is intended to run on the R9700 server behind Cloudflare Tunnel.
- The transient module is Gaia-first in v1 and defers raw ZTF/Rubin difference imaging to a later phase.
- The public entrypoint is the root hostname `ohnita.com`.
- Individual app views are published as SPA paths under the same origin, including `/transients`,
  `/transients/reports/latest`, and `/tess`.
- Postgres is the application system of record; Parquet exports remain the immutable ML artifact layer.
- The repository includes example `systemd`, Docker, and Cloudflare Tunnel scaffolding under `ops/`.
- The server-side ingest path now includes a transient ingest script and example `systemd` timer/service.

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
7. In Cloudflare, enable an edge redirect so `http://ohnita.com/...` is upgraded to HTTPS before the request reaches the app.
