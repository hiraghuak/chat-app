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

# Hugging Face Spaces runs the container as UID 1000; match that and stay non-root.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /home/user

# Install CPU-only torch first (avoids the large CUDA build), then the rest.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r backend/requirements.txt

# App code, prebuilt data snapshot + FAISS index, and the built SPA.
COPY backend/ backend/
COPY data/ data/
COPY --from=frontend /fe/dist frontend/dist

RUN chown -R user:user /home/user
USER user

# Pre-download the embedding model into the image so runtime needs no network
# for embeddings (only OpenRouter is contacted at request time).
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

WORKDIR /home/user/backend
EXPOSE 7860

HEALTHCHECK --interval=20s --timeout=4s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:7860/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
