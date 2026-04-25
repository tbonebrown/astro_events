# Astro Event Intelligence

Astro Event Intelligence powers `ohnita.com` as a single-origin astronomy experience with multiple public modules, including a new flagship Labs feature at `/labs/galaxy-map`.

## What is in this repo

- `services/web`: React + Vite frontend for the Ohnita homepage, feeds, reports, and Labs pages.
- `services/api`: FastAPI backend, API routes, explanation services, and static asset serving.
- `pipelines/tess`: TESS anomaly detection pipeline.
- `pipelines/transients`: transient ranking and reporting pipeline.
- `pipelines/jwst/astro_jwst`: Galaxy Embedding Map artifact builder for synthetic and JWST-style catalogs.
- `ops/`: deployment helpers for `systemd`, Cloudflare Tunnel, Docker, and Windows workstation automation.

## Galaxy Embedding Map

Public routes:

- `/labs/galaxy-map`
- `/labs/galaxy-map/about`
- `/labs/galaxy-map/data`

The app is designed to feel native to Ohnita instead of like a separate science microsite. It reuses the current visual language:

- dark-only gradient backgrounds with soft glows
- rounded glass panels and pill controls
- Avenir-style display typography
- restrained blue, lime, and warm coral accents
- concise, guided copy rather than academic or sci-fi-heavy language

Core features:

- full-screen Labs hero with CTA
- interactive 2D embedding map for 10k+ points
- hover previews and detail drawer
- redshift, morphology, magnitude, cluster, band, and source-field filters
- cluster summaries with representative thumbnails
- approachable story mode
- shareable URL state
- scientific vs simplified labels

## Quick start

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .[dev]
```

Optional extras for richer pipeline work:

```bash
python3 -m pip install -e .[ml]
```

### 2. Frontend dependencies

```bash
cd services/web
npm install
```

### 3. Environment

Copy `.env.example` to `.env` and adjust the paths you want to use. The galaxy map defaults to:

- data root: `./var/data`
- galaxy artifacts: `./var/data/galaxy_map`
- generated thumbnails: `./var/data/artifacts/galaxy_map/thumbnails`

### 4. Build galaxy-map artifacts

Self-contained sample:

```bash
astro-jwst-galaxy-map --data-dir ./var/data --source synthetic --limit 12500
```

Optional thumbnail precompute:

```bash
astro-jwst-galaxy-map --data-dir ./var/data --source synthetic --limit 12500 --precompute-thumbnails
```

### 5. Run the backend

```bash
uvicorn services.api.main:app --reload --proxy-headers --forwarded-allow-ips='*'
```

### 6. Run the frontend

```bash
cd services/web
npm run dev
```

The Vite dev server proxies `/api`, `/assets`, and `/artifacts` to FastAPI.

## Tool guide

### How to use the tools

Install the project with `python3 -m pip install -e .[dev]` from the repo root, then run any CLI tool by name. Use `--help` to inspect options, start with the synthetic modes for local testing, and re-run a tool whenever its source data changes.

### What the tools are doing

- `astro-jwst-galaxy-map` builds the artifact files and thumbnails used by the Labs galaxy map.
- `astro-tess-nightly` generates a nightly TESS candidate export for anomaly review.
- `astro-transients-nightly` generates a nightly transient candidate export for the feed and reports.
- `astro-api-ingest` and `astro-api-ingest-transients` load those exports into the API database so the app can query them.
- `astro-api-refresh-events` refreshes the celestial-events catalog that powers the sky-feed style experiences.

### Why it matters

These tools are the handoff points between raw astronomy data, generated artifacts, and the user-facing app. If you skip a build, ingest, or refresh step, the frontend can still run, but it will be missing fresh data, map assets, or event content.

## Galaxy pipeline

The galaxy-map artifact builder writes:

- `var/data/galaxy_map/galaxies.parquet`
- `var/data/galaxy_map/embeddings.npy`
- `var/data/galaxy_map/umap_coordinates.parquet`
- `var/data/galaxy_map/cluster_summaries.json`
- `var/data/artifacts/galaxy_map/thumbnails/`

### Synthetic mode

`synthetic` mode creates a deterministic JWST-inspired sample with:

- morphology families
- approximate redshift and magnitude metadata
- embedding vectors
- 2D/3D map coordinates
- cluster summaries
- on-demand SVG thumbnails

This is the default because it keeps the full Ohnita Labs experience runnable with no network dependency.

### Catalog mode

`catalog` mode ingests your own CSV or Parquet table:

```bash
astro-jwst-galaxy-map \
  --data-dir ./var/data \
  --source catalog \
  --catalog-path ./path/to/jwst_catalog.csv \
  --limit 8000 \
  --overwrite
```

Recommended columns:

- `image_id`
- `scientific_label`
- `simple_label`
- `source_field`
- `observation_program`
- `instrument`
- `filter_band`
- `redshift`
- `magnitude`
- `confidence`
- `rarity_score`
- `ra`
- `dec`

The repo includes a tiny example at [mock_jwst_catalog.csv](/Users/babo/Documents/GitHub/astro_events/pipelines/jwst/astro_jwst/examples/mock_jwst_catalog.csv).

## How to swap in real JWST data

The simplest path is:

1. Export or assemble a small JWST / MAST catalog with the columns above.
2. Add cutout or thumbnail URLs during your metadata prep step if you have them.
3. Run `astro-jwst-galaxy-map --source catalog --catalog-path ... --overwrite`.
4. Restart the API so it serves the new artifacts.

The artifact contract stays the same, so the public UI does not need to change when you replace the synthetic sample with real data.

## LLM explanations

The detail drawer already supports natural-language explanations through the existing local inference client.

Useful environment variables:

- `LOCAL_INFERENCE_URL`
- `LOCAL_INFERENCE_MODEL`
- `LOCAL_INFERENCE_PROVIDER`

For a llama.cpp-compatible endpoint, use the OpenAI-compatible mode if your gateway exposes chat-completions style responses:

- `LOCAL_INFERENCE_PROVIDER=openai_compatible`

## Tests and verification

Backend:

```bash
pytest tests/test_galaxy_map_api.py
```

Frontend:

```bash
cd services/web
npm test
npm run build
```

## Deployment notes

The app is intended to run behind Cloudflare Tunnel at `ohnita.com`.

### Server build steps

```bash
cd /srv/astro_events
source .venv/bin/activate
python3 -m pip install -e .[dev]
astro-jwst-galaxy-map --data-dir ./var/data --source synthetic --limit 12500
cd services/web
npm install
npm run build
```

Then start the API so it serves:

- `index.html` from `services/web/dist`
- static bundle assets from `services/web/dist/assets`
- generated thumbnails from `/artifacts`

### Minimum production checklist

1. Build the frontend bundle.
2. Generate or ingest galaxy-map artifacts.
3. Confirm `http://127.0.0.1:8000/api/health` works locally.
4. Confirm `http://127.0.0.1:8000/api/galaxy-map/manifest` returns data.
5. Put FastAPI behind Cloudflare Tunnel or your preferred reverse proxy.
6. Keep HTTPS redirect and HSTS enabled for `ohnita.com`.

## Legacy modules

The repo still includes the original public Ohnita experiences:

- transient feed
- nightly transient report
- TESS anomaly watchlist
- sky-feed / celestial events guide

The Galaxy Embedding Map now sits alongside them as the flagship Labs showcase.
