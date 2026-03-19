"""
index.py — FastAPI application for the Alpha-Guide RAG chatbot.

Endpoints
---------
GET  /               → health-check
POST /api/chat       → RAG-powered chat (SSE streaming)
"""

import json
import logging
import os
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse, Response

from helpers.agent import get_agent
from helpers.trading_tools import reset_chat_thread_context, set_chat_thread_context

load_dotenv()

# ---------------------------------------------------------------------------
# Logging (replaces raw print statements to avoid PII leakage in prod)
# ---------------------------------------------------------------------------
logger = logging.getLogger("alpha-guide")
logging.basicConfig(level=logging.INFO)

_is_production = os.getenv("ENVIRONMENT", "local") != "local"

# ---------------------------------------------------------------------------
# App & middleware
# ---------------------------------------------------------------------------
# Disable the interactive API docs in production to avoid exposing the schema.
app = FastAPI(
    title="Alpha-Guide API",
    version="0.1.0",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)


# ---------------------------------------------------------------------------
# Security headers middleware — adds standard hardening headers to every
# response so browser-side attack surface is minimised.
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if _is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# --- CORS: restrict origins in production, allow all in local dev -----------
_ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")  # comma-separated
if _ALLOWED_ORIGINS_ENV:
    _allowed_origins = [o.strip() for o in _ALLOWED_ORIGINS_ENV.split(",") if o.strip()]
else:
    # Fallback: accept the Vercel preview/production URLs + localhost
    _allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # If a known production URL is set, add it automatically
    _vercel_url = os.getenv("VERCEL_URL")  # Vercel injects this
    if _vercel_url:
        _allowed_origins.append(f"https://{_vercel_url}")
    _vercel_project_url = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if _vercel_project_url:
        _allowed_origins.append(f"https://{_vercel_project_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
# Max message length to prevent token-draining abuse (≈ 10 000 chars ≈ ~2 500 tokens)
MAX_MESSAGE_LENGTH = 10_000


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    context: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    # Conversation thread for memory; auto-generated if omitted.
    # Constrained to a reasonable length to avoid abuse.
    thread_id: str | None = Field(default=None, max_length=128)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """Health-check / ping endpoint."""
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Stream an agent response via Server-Sent Events."""
    try:
        agent = await get_agent()
    except Exception:
        logger.exception("Failed to initialise agent")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    agent_input = {
        "messages": [{"role": "user", "content": request.message}]
    }

    # The checkpointer needs a thread_id to track conversation state
    thread_id = request.thread_id or str(uuid.uuid4())
    agent_config = {"configurable": {"thread_id": thread_id}}

    # Structured log — no raw user content in production logs
    logger.info(
        "chat request: thread_id=%s message_len=%d",
        thread_id,
        len(request.message),
    )

    async def stream_response():
        # So execute_trade and other tools can log trades against this conversation.
        ctx_token = set_chat_thread_context(thread_id)
        try:
            try:
                async for message, metadata in agent.astream(
                    agent_input,
                    config=agent_config,
                    context=request.context,
                    stream_mode="messages",
                ):
                    yield (
                        f"event: message\n"
                        f"data: {json.dumps([message.model_dump(mode='json'), metadata], default=str)}\n\n"
                    )
            except Exception:
                # Log the real error server-side; send a safe message to the client
                logger.exception("Streaming error for thread %s", thread_id)
                error_payload = json.dumps({"error": "An internal error occurred."})
                yield f"event: error\ndata: {error_payload}\n\n"
        finally:
            reset_chat_thread_context(ctx_token)

    return StreamingResponse(stream_response(), media_type="text/event-stream")
