"""
Cleaned & refactored FastAPI server for Universal AI Assistant
- Removed redundant imports, dead code, and defensive try/except spam
- Centralized session creation and teardown
- Clear separation: startup, session lifecycle, transport (HTTP / WS)
- Thread-safe background LLM2 worker handling
- Production-ready structure (easy to extend to Redis, auth, etc.)
"""

import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from main import AsyncState, ask_counselor_question, llm2_background_worker
from KG.kg_builder import RobustKnowledgeGraphBuilder

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("api_server")

# -----------------------------------------------------------------------------
# Global runtime state (replace with Redis later if needed)
# -----------------------------------------------------------------------------
class GlobalState:
    def __init__(self):
        self.sessions: Dict[str, AsyncState] = {}
        self.kg_builder: Optional[RobustKnowledgeGraphBuilder] = None
        self.llm: Optional[ChatGroq] = None

STATE = GlobalState()

# -----------------------------------------------------------------------------
# API Models
# -----------------------------------------------------------------------------
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    metadata: Dict[str, Any]

# -----------------------------------------------------------------------------
# Session helpers
# -----------------------------------------------------------------------------

def create_session(session_id: str) -> AsyncState:
    state = AsyncState()
    state.session_id = session_id
    state.kg_builder = STATE.kg_builder
    state.conversation_active = True

    STATE.sessions[session_id] = state

    thread = threading.Thread(
        target=llm2_background_worker,
        args=(state, STATE.llm),
        daemon=True,
    )
    thread.start()

    logger.info("Session started: %s", session_id)
    return state


def get_session(session_id: str) -> AsyncState:
    if session_id not in STATE.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return STATE.sessions[session_id]


def close_session(session_id: str) -> None:
    state = STATE.sessions.pop(session_id, None)
    if state:
        state.conversation_active = False
        logger.info("Session closed: %s", session_id)

# -----------------------------------------------------------------------------
# App lifespan
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    load_dotenv()

    groq_key = os.getenv("GROQ_API_KEY")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_pass = os.getenv("NEO4J_PASSWORD")

    if not groq_key:
        raise RuntimeError("GROQ_API_KEY missing")

    STATE.llm = ChatGroq(
        api_key=groq_key,
        model="llama-3.1-8b-instant",
        temperature=0.7,
    )
    logger.info("LLM initialized")

    if all([neo4j_uri, neo4j_user, neo4j_pass]):
        STATE.kg_builder = RobustKnowledgeGraphBuilder(
            groq_key, neo4j_uri, neo4j_user, neo4j_pass
        )
        logger.info("Knowledge Graph initialized")
    else:
        logger.warning("Neo4j credentials missing — KG disabled")

    yield

    logger.info("Server shutting down")
    for sid in list(STATE.sessions.keys()):
        close_session(sid)

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Universal AI Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": len(STATE.sessions),
        "kg_enabled": STATE.kg_builder is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }

# -----------------------------------------------------------------------------
# WebSocket Chat
# -----------------------------------------------------------------------------
@app.websocket("/ws/chat/{session_id}")
async def chat_ws(ws: WebSocket, session_id: str):
    await ws.accept()

    state = STATE.sessions.get(session_id) or create_session(session_id)

    try:
        while True:
            payload = json.loads(await ws.receive_text())
            user_message = payload.get("message", "").strip()
            if not user_message:
                continue

            if not state.original_question:
                state.original_question = user_message
                response = ask_counselor_question(state, llm=STATE.llm)
            else:
                response = ask_counselor_question(state, user_message, llm=STATE.llm)

            await ws.send_text(json.dumps({
                "response": response,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "qa_pairs": len(state.qa_pairs),
                    "llm2_analyzing": state.llm2_analyzing,
                    "has_insights": state.llm2_insights is not None,
                },
            }))

    except WebSocketDisconnect:
        close_session(session_id)

# -----------------------------------------------------------------------------
# HTTP Chat (fallback / REST)
# -----------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_http(req: ChatMessage):
    session_id = req.session_id or f"session_{int(datetime.utcnow().timestamp())}"
    state = STATE.sessions.get(session_id) or create_session(session_id)

    if not req.message.strip():
        response = ask_counselor_question(state, llm=STATE.llm)
    else:
        response = ask_counselor_question(state, req.message, llm=STATE.llm)

    return ChatResponse(
        response=response,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "qa_pairs": len(state.qa_pairs),
            "llm2_analyzing": state.llm2_analyzing,
            "has_insights": state.llm2_insights is not None,
        },
    )

# -----------------------------------------------------------------------------
# Sessions & KG
# -----------------------------------------------------------------------------
@app.get("/api/sessions")
async def list_sessions():
    return {
        "sessions": [
            {
                "session_id": sid,
                "qa_pairs": len(s.qa_pairs),
                "active": s.conversation_active,
                "has_insights": s.llm2_insights is not None,
            }
            for sid, s in STATE.sessions.items()
        ]
    }

@app.get("/api/kg/{session_id}")
async def session_kg(session_id: str):
    if not STATE.kg_builder:
        raise HTTPException(503, "Knowledge Graph disabled")

    state = get_session(session_id)
    analysis = STATE.kg_builder.analyze_therapy_patterns(
        session_id=session_id,
        current_qa_pairs=state.qa_pairs,
    )

    return {
        "session_id": session_id,
        "analysis": analysis,
        "insights": state.llm2_insights,
    }

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    close_session(session_id)
    return {"success": True}

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server_cleaned:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
