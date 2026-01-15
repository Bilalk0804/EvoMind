"""
FastAPI server for Simplified AI Assistant
Clean API with single LLM + KG context retrieval.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from main import SimpleChatBot, ChatSession, init_chatbot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("api_server")


# Global state
class AppState:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.chatbot: Optional[SimpleChatBot] = None
        self.kg_builder = None

STATE = AppState()


# Request/Response models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str


# Session helpers
def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in STATE.sessions:
        session = ChatSession(session_id=session_id, kg_builder=STATE.kg_builder)
        STATE.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
    return STATE.sessions[session_id]


def close_session(session_id: str) -> None:
    if session_id in STATE.sessions:
        del STATE.sessions[session_id]
        logger.info(f"Closed session: {session_id}")


# App lifespan
@asynccontextmanager
async def lifespan(_: FastAPI):
    load_dotenv()
    
    STATE.chatbot, STATE.kg_builder = init_chatbot()
    logger.info("Chatbot initialized successfully")
    
    yield
    
    logger.info("Server shutting down")
    STATE.sessions.clear()


# FastAPI app
app = FastAPI(
    title="AI Assistant API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": len(STATE.sessions),
        "kg_enabled": STATE.kg_builder is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }


# WebSocket chat
@app.websocket("/ws/chat/{session_id}")
async def chat_ws(ws: WebSocket, session_id: str):
    await ws.accept()
    session = get_or_create_session(session_id)

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "").strip()
            
            if not user_message:
                continue

            response = STATE.chatbot.chat(user_message, session)

            await ws.send_text(json.dumps({
                "response": response,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }))

    except WebSocketDisconnect:
        close_session(session_id)


# HTTP chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_http(req: ChatMessage):
    session_id = req.session_id or f"session_{int(datetime.utcnow().timestamp())}"
    session = get_or_create_session(session_id)

    if not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    response = STATE.chatbot.chat(req.message, session)

    return ChatResponse(
        response=response,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat(),
    )


# Session management
@app.get("/api/sessions")
async def list_sessions():
    return {
        "sessions": [
            {
                "session_id": sid,
                "message_count": len(s.messages),
            }
            for sid, s in STATE.sessions.items()
        ]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    close_session(session_id)
    return {"success": True}


# KG analysis (if available)
@app.get("/api/kg/{session_id}")
async def session_kg(session_id: str):
    if not STATE.kg_builder:
        raise HTTPException(503, "Knowledge Graph not available")

    session = STATE.sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    return {
        "session_id": session_id,
        "message_count": len(session.messages),
        "kg_enabled": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
