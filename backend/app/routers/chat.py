"""Grounded, streaming chat endpoint (Server-Sent Events)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.schemas import ChatRequest
from app.services.openrouter_stream import stream_completion

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _source_summary(listing: dict) -> dict:
    return {
        "id": listing.get("id"),
        "title": listing.get("title"),
        "source": listing.get("source"),
        "city": listing.get("city"),
        "country": listing.get("country"),
        "price": listing.get("price"),
        "currency": listing.get("currency"),
        "property_type": listing.get("property_type"),
        "listing_type": listing.get("listing_type"),
        "url": listing.get("url"),
    }


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    settings = get_settings()

    # Pre-stream, plain-JSON checks (can return a real non-200 response).
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured with an OPENROUTER_API_KEY.",
        )
    client_ip = request.client.host if request.client else "unknown"
    allowed, message = request.app.state.rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    rag = request.app.state.rag
    listings, _filters, _score = rag.retrieve(body.messages)
    messages = rag.build_messages(body.messages, listings)

    async def event_stream():
        # Tell the UI which listings grounded the answer, before tokens arrive.
        yield _sse({"type": "sources", "listings": [_source_summary(l) for l in listings]})
        async for frame in stream_completion(messages, settings):
            yield _sse(frame)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
