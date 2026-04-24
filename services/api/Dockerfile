FROM node:22-alpine AS web-build

WORKDIR /web

COPY services/web/package.json services/web/package-lock.json ./
RUN npm install

COPY services/web ./
RUN npm run build

FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY services/api ./services/api
COPY pipelines/tess ./pipelines/tess
COPY pipelines/transients ./pipelines/transients
COPY --from=web-build /web/dist ./services/web/dist

RUN python -m pip install --upgrade pip && \
    python -m pip install .

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
