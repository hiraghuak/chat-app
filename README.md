# 🏠 Real Estate RAG Chatbot — DarGlobal × Wasalt

An AI chatbot that answers questions about real-estate listings **scraped from
[DarGlobal](https://darglobal.co.uk) and [Wasalt](https://wasalt.sa)**. It uses
Retrieval-Augmented Generation (RAG) grounded in that scraped data and a **free
model on [OpenRouter](https://openrouter.ai)**. Fully containerized with Docker
and deployed on Render.

> **🔗 Live demo:** https://real-estate-chatbot-47lr.onrender.com
>
> _(Free instance — the first request after ~15 min idle can take ~50s to wake.)_

---

## What it does

- Chat UI (React) that streams answers **token-by-token** like ChatGPT.
- Every answer is **grounded** in the scraped listings — the model is told to
  answer only from retrieved properties, and the UI shows a **Sources panel**
  citing the exact listings used (with links).
- Understands structured queries: _"3-bedroom apartments for sale in Riyadh under
  2 million"_ applies city + type + bedroom + price filters, not just semantics.

## Architecture

```
 OFFLINE (once)                              BAKED INTO IMAGE
 scraper (Playwright) ──▶ data/listings.json ──▶ build_index ──▶ embeddings.npy + meta.json
   DarGlobal (Incapsula)                                                │
   Wasalt   (Cloudflare)                                               │
                                                                        ▼
 SINGLE DOCKER CONTAINER (port 7860, Hugging Face Space)
   React SPA ──served by──▶ FastAPI ──embed query──▶ numpy cosine top-k ──▶ listings
      browser ──POST /api/chat──┘── grounded prompt ──▶ OpenRouter (free LLM) ──▶ SSE stream
```

- **One container** serves both the API and the built React UI (same origin).
- **Scraping is a one-time offline snapshot** baked into the image, so the live
  demo never depends on the source sites being reachable or unblocked.

## Quick start (Docker — under 2 minutes)

```bash
cp .env.example .env         # then paste your OpenRouter key into .env
docker compose up --build    # first build downloads torch + the embedding model
# open http://localhost:7860
```

You'll know it worked when `docker compose` logs show
`Ready: 445 listings indexed; OpenRouter key configured=True` and the page loads
a chat box at http://localhost:7860.

Get a **free** OpenRouter key at https://openrouter.ai/keys (no credit card
needed for free models).

## Local development (no Docker)

```bash
# 1) Backend  (Python 3.12)
python3.12 -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python -m app.build_index                       # build the vector index (run from backend/)
OPENROUTER_API_KEY=sk-or-... uvicorn app.main:app --reload --port 7860 --app-dir backend

# 2) Frontend  (in another terminal)
cd frontend && npm install && npm run dev        # http://localhost:5173 (proxies /api to :7860)
```

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter key (server-side only) |
| `OPENROUTER_MODEL` | | `openrouter/free` | auto-routes over free models; or set any `:free` model id |
| `TOP_K` | | `5` | listings retrieved per query |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_DAY` | | `15` / `200` | per-IP abuse limits |

## API

- `GET /health` → `{"status":"ok","openrouter_key_configured":true}`
- `POST /api/chat` → Server-Sent Events. Frames: `sources`, then `delta`…, then
  `done` (or an `error` frame). Example:

```bash
curl -N -X POST http://localhost:7860/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"3-bed apartments for sale in Riyadh under 2M"}]}'
```

## Deploy to Render (free, no credit card)

The image is intentionally small (~470MB, ~200MB RAM at runtime), so it fits
Render's free 512MB web-service tier. A `render.yaml` blueprint is included.

1. Push this repo to GitHub.
2. On [render.com](https://render.com) → **New → Blueprint** → connect the repo
   (Render reads `render.yaml` and creates a free Docker web service), **or**
   **New → Web Service** → pick the repo → it auto-detects the `Dockerfile` →
   choose the **Free** plan.
3. In the service's **Environment** tab, add `OPENROUTER_API_KEY` = your key.
4. Deploy. First build takes a few minutes; then your public URL is
   `https://<service-name>.onrender.com`. Put it at the top of this README.

> Free instances sleep after ~15 min idle and cold-start (~30–60s) on the next
> request — expected for a free demo. The app reads `$PORT` (Render injects it)
> and falls back to 7860 locally.

_The same image also runs on any Docker host (Google Cloud Run, Koyeb, a VM, …)._

## Re-running the scraper (optional)

```bash
python3.12 -m venv scraper/.venv && scraper/.venv/bin/pip install -r scraper/requirements.txt
scraper/.venv/bin/playwright install chromium
scraper/.venv/bin/python scraper/run_scrape.py           # full snapshot -> data/listings.json
# then rebuild the index:  (from backend/)  python -m app.build_index
```

## Tests

```bash
# backend  (from backend/)
.venv/bin/python -m pytest -q
# frontend (from frontend/)
npm test
```

## Design decisions & trade-offs

- **Both sites are bot-protected** — DarGlobal via Imperva Incapsula, Wasalt via
  Cloudflare — so the scraper uses a **headless browser (Playwright)** that clears
  the JS challenge, and reads the embedded `__NEXT_DATA__` JSON rather than
  brittle CSS selectors.
- **Snapshot, not live scraping.** A cleaned dataset is baked into the image, so
  the demo is reliable even if a site changes or blocks traffic.
- **RAG over a numpy vector store.** For a few-hundred-listing snapshot, a single
  normalized-embedding matmul is instant and removes a heavier ANN dependency;
  embeddings are computed by a **local** `all-MiniLM-L6-v2` model (no embedding
  API cost). Swap in FAISS/pgvector if the dataset grows large.
- **Single container.** Simplest thing to deploy on free single-service hosting
  while keeping a clean UI/API split in code.

## Security

- **API key** is server-side only (local `.env`, gitignored; HF secret in prod),
  never sent to the browser, never logged, never baked into an image layer.
- **Prompt-injection resistant**: scraped text and user input are treated as
  data, not instructions; the model is told to ignore instructions embedded in
  listings.
- **XSS-safe**: markdown is rendered without raw HTML; links use
  `rel="noopener noreferrer"`.
- **Abuse protection**: per-IP rate limits on `/api/chat`.
- **Container**: runs as a non-root user; HF serves the URL over HTTPS.

## Scope & ethics

- Only **public listing data** is scraped, politely (rate-limited, honoring the
  sites' robots directives — Wasalt explicitly allows AI crawlers). This is a
  demo snapshot, not a continuous crawler.
- Prices/details are a **snapshot** (see the "data as of" note in-app); no auth,
  no database, conversation state is in-memory in the browser.
```
