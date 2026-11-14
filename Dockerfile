# One service: FastAPI backend + built frontend on the same origin. PORT is provided by Render.
FROM node:20-slim AS web
WORKDIR /src/frontend/app
COPY frontend/app/package.json frontend/app/package-lock.json ./
RUN npm ci
COPY frontend/app/ ./
ENV VITE_API_BASE=/api
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
# Only what the API reads (committed outputs and caches; no keys needed)
COPY backend/api/ backend/api/
COPY backend/engine/ backend/engine/
COPY backend/field/out/ backend/field/out/
COPY backend/field/polygons/ backend/field/polygons/
COPY backend/ai/out/ backend/ai/out/
COPY backend/outlook/out/ backend/outlook/out/
COPY backend/news/out/ backend/news/out/
COPY backend/regional/out/ backend/regional/out/
COPY data/cache/ data/cache/
COPY schemas/ schemas/
COPY fixtures/ fixtures/
COPY --from=web /src/frontend/app/dist /app/frontend/app/dist
WORKDIR /app/backend/api
RUN uv sync --frozen --no-dev
ENV FRONTEND_DIST=/app/frontend/app/dist FIELDSHIFT_ROOT=/app PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uv run --frozen --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
