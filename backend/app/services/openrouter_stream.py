"""Stream chat completions from OpenRouter (OpenAI-compatible API).

Reliability model: free models get saturated, so we fall back across a small
list of *known chat* models ourselves (rather than OpenRouter's `models` array,
which can opaquely route to a non-chat model and emit junk like
"User Safety: safe"). We try each model in order; if one errors *before*
producing any token we move to the next. The whole thing runs inside the async
generator so a failure becomes a clean SSE ``error`` frame, never a broken
response.
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

# Errors worth trying the next model for (transient / provider-side).
RETRYABLE = (RateLimitError, APITimeoutError, APIError, asyncio.TimeoutError)


async def stream_completion(
    messages: list[dict], settings: Settings
) -> AsyncIterator[dict]:
    client = AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=0,
    )
    headers = {"HTTP-Referer": settings.app_url, "X-Title": settings.app_title}
    try:
        last_error: Exception | None = None
        for model in settings.model_list:
            produced = False
            try:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    temperature=0.3,
                    extra_headers=headers,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        produced = True
                        yield {"type": "delta", "content": delta}
                if produced:
                    yield {"type": "done", "finish_reason": "stop"}
                    return
                # Model returned nothing — try the next one.
                logger.warning("Model %s returned an empty response; trying next", model)
            except AuthenticationError:
                raise  # same key for every model — no point retrying
            except RETRYABLE as exc:
                if produced:
                    raise  # already mid-stream; can't switch models cleanly
                last_error = exc
                logger.warning("Model %s failed (%s); trying next", model, type(exc).__name__)
                continue

        # Every model failed or was empty.
        if last_error is not None:
            raise last_error
        yield {"type": "error",
               "message": "No free model returned a response. Please try again shortly."}

    except AuthenticationError:
        yield {"type": "error", "message": "Invalid or missing OpenRouter API key."}
    except RateLimitError:
        yield {"type": "error",
               "message": "All free models are rate-limited right now. Please try again shortly."}
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
