"""Request/response models for the chat API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # Cap history length to bound payload size / token usage.
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)
