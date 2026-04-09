"""
Shopping Companion — Chat Server

FastAPI backend that exposes the two-stage agent as a stateful chat API.

The conversation has two states per session:
  awaiting_query        → user sends a shopping request
                          Stage 1 runs: retrieves preferences from Mem0
                          → transitions to awaiting_confirmation
  awaiting_confirmation → user confirms or corrects preferences
                          Stage 2 runs: searches catalog, returns recommendation
                          → transitions back to awaiting_query

Usage:
    pip install fastapi uvicorn
    python app.py

    Or:
    uvicorn app:app --reload --port 8000
"""

import os
import uuid
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agents.shopping_companion import ShoppingCompanion

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Shopping Companion", docs_url=None, redoc_url=None)

# ── In-memory session store ───────────────────────────────────────────────────
# In production: replace with Redis

sessions: dict[str, dict] = {}


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "guest"
    bundle: Optional[bool] = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    state: str                  # awaiting_query | awaiting_confirmation | done
    stage: Optional[int] = None # 1 or 2


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = {
            "state": "awaiting_query",
            "user_id": req.user_id,
            "query": None,
            "pending_preferences": None,   # from Stage 1, awaiting user confirmation
            "confirmed_preferences": None, # confirmed once, reused for rest of session
            "bundle": req.bundle,
            "companion": ShoppingCompanion(),
        }

    session = sessions[session_id]
    companion: ShoppingCompanion = session["companion"]

    # ── State: awaiting_query ─────────────────────────────────────────────────
    if session["state"] == "awaiting_query":
        session["query"] = req.message
        session["bundle"] = req.bundle

        # If preferences are already confirmed from an earlier turn in this
        # session, skip Stage 1 entirely and go straight to product search
        if session["confirmed_preferences"] is not None:
            recommendation = companion.find_products(
                user_id=session["user_id"],
                query=req.message,
                confirmed_preferences=session["confirmed_preferences"],
                bundle=req.bundle,
            )
            return ChatResponse(
                session_id=session_id,
                reply=recommendation,
                state="awaiting_query",
                stage=2,
            )

        # First request in session — run Stage 1 to identify preferences
        preferences = companion.identify_preferences(
            user_id=session["user_id"],
            query=req.message,
        )

        session["pending_preferences"] = preferences
        session["state"] = "awaiting_confirmation"

        return ChatResponse(
            session_id=session_id,
            reply=preferences,
            state="awaiting_confirmation",
            stage=1,
        )

    # ── State: awaiting_confirmation ─────────────────────────────────────────
    elif session["state"] == "awaiting_confirmation":
        # Let the agent decide if the response contains actual corrections
        # worth saving, or is just a confirmation to proceed
        confirmed = companion.process_confirmation(
            user_id=session["user_id"],
            identified_preferences=session["pending_preferences"],
            user_response=req.message.strip(),
        )

        # Store confirmed preferences for the rest of this session
        session["confirmed_preferences"] = confirmed
        session["pending_preferences"] = None
        session["state"] = "awaiting_query"

        recommendation = companion.find_products(
            user_id=session["user_id"],
            query=session["query"],
            confirmed_preferences=confirmed,
            bundle=session["bundle"],
        )

        return ChatResponse(
            session_id=session_id,
            reply=recommendation,
            state="awaiting_query",
            stage=2,
        )

    return JSONResponse(status_code=400, content={"error": "Unknown session state"})


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": session_id}


# ── Static files + root ───────────────────────────────────────────────────────

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    index = Path(__file__).parent / "static" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "Shopping Companion API running. No UI found at static/index.html."}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
