# Multi-stage: build the React app, then serve everything from FastAPI.
# ---- stage 1: frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python app ----
FROM python:3.12-slim AS app
WORKDIR /app

# System deps kept minimal; fastembed uses onnxruntime (pure wheels).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + source data.
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/raw/ ./data/raw/
COPY --from=web /web/dist ./frontend/dist

# Build the extracted text, synthetic tickets, SQLite DB, and pre-download the
# local embedding model so the first request is fast and runtime is offline.
RUN python scripts/extract.py \
 && python scripts/gen_synthetic.py \
 && python -m src.data.db \
 && python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

ENV PYTHONUNBUFFERED=1
# GROQ_API_KEY / GEMINI_API_KEY are injected by the host (never baked in).
# Hosts (Render/Railway) provide $PORT.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
