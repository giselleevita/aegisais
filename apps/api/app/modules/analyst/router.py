"""Maritime Analyst AI assistant — conversational interface.

Provides a chat endpoint where analysts can ask questions about
vessels, alerts, threats, and maritime security. Powered by
Featherless AI (OpenAI-compatible LLM).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.llm import (
    SYSTEM_PROMPT_ANALYST,
    complete,
    complete_streaming,
    is_llm_enabled,
)

_log = logging.getLogger("aegisais.analyst")

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: Optional[dict[str, Any]] = None
    stream: bool = False


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    generated_at: str


@router.post("/chat")
async def analyst_chat(req: ChatRequest):
    """Conversational maritime analyst assistant.

    Send a message (or conversation history) and receive an LLM-powered
    analysis response. Optionally include vessel/alert context data.
    """
    if not is_llm_enabled():
        raise HTTPException(
            status_code=503,
            detail="LLM integration not configured. Set LLM_ENABLED=true and LLM_API_KEY in environment.",
        )

    # Build the user prompt from conversation + optional context
    user_parts = []
    if req.context:
        user_parts.append(f"Context data:\n```json\n{json.dumps(req.context, indent=2)}\n```\n")

    # Use the last user message as the primary prompt
    last_user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"),
        None,
    )
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message provided")

    # Include conversation history in the prompt
    if len(req.messages) > 1:
        history_parts = []
        for msg in req.messages[:-1]:
            history_parts.append(f"{msg.role.upper()}: {msg.content}")
        user_parts.append("Previous conversation:\n" + "\n".join(history_parts))

    user_parts.append(f"Current question: {last_user_msg}")
    user_prompt = "\n\n".join(user_parts)

    if req.stream:
        async def stream_response():
            async for chunk in complete_streaming(SYSTEM_PROMPT_ANALYST, user_prompt):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    response = await complete(SYSTEM_PROMPT_ANALYST, user_prompt, max_tokens=800)
    if response is None:
        raise HTTPException(status_code=502, detail="LLM service unavailable")

    return ChatResponse(
        content=response,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status")
async def analyst_status():
    """Check if the analyst AI assistant is available."""
    from app.core.config import settings
    return {
        "enabled": is_llm_enabled(),
        "provider": "featherless" if settings.LLM_BASE_URL and "featherless" in settings.LLM_BASE_URL else "openai-compatible",
        "model": settings.LLM_MODEL if is_llm_enabled() else None,
    }
