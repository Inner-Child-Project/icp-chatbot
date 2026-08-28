import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from .agent import build_graph
from .models import ChatRequest, ChatResponse
from .security import SlidingWindowRateLimiter, client_ip

load_dotenv()

_cors_raw = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else ["*"]

_limiter = SlidingWindowRateLimiter(
    limit=int(os.getenv("RATE_LIMIT", "20")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
)

graph = None


@asynccontextmanager
async def lifespan(app):
    global graph
    graph = await build_graph()
    yield


app = FastAPI(title="ICP Chatbot", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _last_ai_content(state: dict) -> str:
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
            return msg.content or ""
    return ""


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    if not _limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests")

    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    if req.resume_value:
        result = await graph.ainvoke(
            Command(resume=req.resume_value),
            config=config,
        )
    else:
        result = await graph.ainvoke(
            {
                "messages": [("user", req.message)],
                "lead_info": {},
                "info_complete": False,
            },
            config=config,
        )

    # Check for pending interrupt (proposal review)
    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0]
        payload = first.value if isinstance(first.value, dict) else {}
        proposal_text = payload.get("proposal") or ""
        question = payload.get("question") or ""

        last_ai = _last_ai_content(result) or question
        return ChatResponse(
            reply=last_ai,
            info_complete=True,
            proposal=proposal_text,
            submitted=False,
            awaiting_approval=True,
        )

    submitted = result.get("submitted", False)
    approved = result.get("proposal_approved")

    reply_text = _last_ai_content(result)

    if not submitted and approved is False:
        reply_text = reply_text or "Got it — tell me more about what you'd like to adjust."

    return ChatResponse(
        reply=reply_text,
        info_complete=result.get("info_complete", False),
        proposal=result.get("proposal"),
        submitted=submitted,
        awaiting_approval=False,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
