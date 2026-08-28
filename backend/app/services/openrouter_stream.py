"""Stream chat completions from OpenRouter (OpenAI-compatible API).

The whole call — including opening the stream — runs inside the async generator
so that an auth/network error raised on stream-open becomes a clean ``error``
frame instead of a half-written HTTP response.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from openai import (
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.config import Settings

logger = logging.getLogger("chatapp.openrouter")


async def stream_completion(
    messages: list[dict], settings: Settings
) -> AsyncIterator[dict]:
    client = AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=1,
    )
    try:
        stream = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=messages,
            stream=True,
            temperature=0.3,
            extra_headers={
                "HTTP-Referer": settings.app_url,
                "X-Title": settings.app_title,
            },
            # OpenRouter fallback routing: try each model in order until one
            # is available, so a saturated free model doesn't break the reply.
            extra_body={"models": settings.model_list},
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield {"type": "delta", "content": delta}
        yield {"type": "done", "finish_reason": "stop"}
    except AuthenticationError:
        yield {"type": "error", "message": "Invalid or missing OpenRouter API key."}
    except RateLimitError:
        yield {"type": "error",
               "message": "Rate limited by OpenRouter (free tier). Please try again shortly."}
    except (APITimeoutError, asyncio.TimeoutError):
        yield {"type": "error", "message": "The AI request timed out. Please try again."}
    except APIError as exc:
        logger.exception("OpenRouter API error: %s", exc)
        yield {"type": "error", "message": "The AI service returned an error. Please try again."}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected streaming error: %s", exc)
        yield {"type": "error", "message": "Something went wrong generating a response."}
    finally:
        await client.close()
