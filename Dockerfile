# syntax=docker/dockerfile:1

# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build           # -> /fe/dist (served by FastAPI, same-origin)

# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim

# Non-root user (also matches Hugging Face's UID-1000 convention).
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /home/user

# Lightweight deps (fastembed/ONNX — no torch), so the image + runtime memory
# fit a 512MB free host.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r backend/requirements.txt

# App code, prebuilt data snapshot (embeddings + meta), and the built SPA.
COPY backend/ backend/
COPY data/ data/
COPY --from=frontend /fe/dist frontend/dist

RUN chown -R user:user /home/user
USER user

# Pre-bake the embedding model so runtime needs no network for embeddings
# (cache dir matches Settings.embedding_cache_dir = ROOT/.fastembed_cache).
RUN python -c "from fastembed import TextEmbedding; \
TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/home/user/.fastembed_cache')"

WORKDIR /home/user/backend
EXPOSE 7860

# Honor $PORT (Render/most PaaS inject it); default 7860 for local/compose.
HEALTHCHECK --interval=20s --timeout=4s --start-period=25s --retries=3 \
  CMD sh -c 'python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f\"http://localhost:{os.environ.get(\"PORT\",\"7860\")}/health\").status==200 else 1)"'

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
