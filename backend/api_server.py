#!/usr/bin/env python3
"""
Unified API Server for Universal AI Assistant
Connects frontend to all backend systems: AI chat, MCP tools, Knowledge Graph
"""
import os
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Import existing systems
from main import AsyncState, ask_counselor_question, llm2_background_worker
from KG.kg_builder import RobustKnowledgeGraphBuilder
import sys
import os
# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server as MCPServer

# Global state management
class GlobalState:
    def __init__(self):
        self.active_sessions: Dict[str, AsyncState] = {}
        self.kg_builder: Optional[RobustKnowledgeGraphBuilder] = None
        self.mcp_server = None
        self.notion_client = None
        self.llm = None
        
global_state = GlobalState()

# Pydantic models for API
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_type: str = "ai_response"
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

class TaskPlanRequest(BaseModel):
    goal: str
    deadline: Optional[str] = None
    max_steps: int = 8

class NotionPageRequest(BaseModel):
    title: str
    content: Optional[str] = None
    database_id: Optional[str] = None

class ScheduleRequest(BaseModel):
    date: Optional[str] = None

class EventRequest(BaseModel):
    title: str
    start: str
    end: str
    description: Optional[str] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.session_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.session_connections[session_id] = websocket

    def disconnect(self, websocket: WebSocket, session_id: str):
        self.active_connections.remove(websocket)
        if session_id in self.session_connections:
            del self.session_connections[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.session_connections:
            websocket = self.session_connections[session_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all backend systems on startup"""
    load_dotenv()
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize LLM
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key:
            global_state.llm = ChatGroq(
                api_key=groq_api_key,
                model="gemma2-9b-it",
                temperature=0.7
            )
            logger.info("✅ LLM (ChatGroq) initialized")
        else:
            logger.warning("⚠️ GROQ API key missing")
        
        # Initialize Knowledge Graph
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_username = os.getenv('NEO4J_USERNAME')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        if all([groq_api_key, neo4j_uri, neo4j_username, neo4j_password]):
            global_state.kg_builder = RobustKnowledgeGraphBuilder(
                groq_api_key, neo4j_uri, neo4j_username, neo4j_password
            )
            logger.info("✅ Knowledge Graph Builder initialized")
        else:
            logger.warning("⚠️ Knowledge Graph credentials missing")
        
        # Initialize MCP Server
        global_state.mcp_server = MCPServer("genai_mcp")
        logger.info("✅ MCP Server initialized")
        
        # Note: MCP tools will be configured separately if needed
        logger.info("✅ Basic MCP server ready")
            
        logger.info("🚀 All backend systems initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize backend systems: {e}")
        raise
    
    yield
    
    # Cleanup on shutdown
    logger.info("🔄 Shutting down backend systems...")
    for session_id, state in global_state.active_sessions.items():
        state.conversation_active = False
    logger.info("🔄 Server shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Universal AI Assistant API",
    description="Unified API for AI chat, MCP tools, and Knowledge Graph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "kg_builder": global_state.kg_builder is not None,
            "notion_client": global_state.notion_client is not None,
            "active_sessions": len(global_state.active_sessions)
        }
    }

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    # Initialize session if not exists
    if session_id not in global_state.active_sessions:
        state = AsyncState()
        state.kg_builder = global_state.kg_builder
        state.session_id = session_id
        state.conversation_active = True
        global_state.active_sessions[session_id] = state
        
        # Start background LLM2 worker
        import threading
        llm2_thread = threading.Thread(
            target=llm2_background_worker, 
            args=(state, global_state.llm), 
            daemon=True
        )
        llm2_thread.start()
    
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            state = global_state.active_sessions[session_id]
            
            # Set original question if first message
            if not state.original_question:
                state.original_question = user_message
                # Generate first response
                ai_response = ask_counselor_question(state, llm=global_state.llm)
            else:
                # Continue conversation
                ai_response = ask_counselor_question(state, user_message, llm=global_state.llm)
            
            # Send AI response back
            response_data = {
                "response": ai_response,
                "session_id": session_id,
                "message_type": "ai_response",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "qa_pairs_count": len(state.qa_pairs),
                    "llm2_analyzing": state.llm2_analyzing,
                    "has_insights": state.llm2_insights is not None
                }
            }
            
            await websocket.send_text(json.dumps(response_data))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        # Mark session as inactive
        if session_id in global_state.active_sessions:
            global_state.active_sessions[session_id].conversation_active = False

# REST API endpoints for MCP tools
@app.post("/api/chat/message", response_model=ChatResponse)
async def send_chat_message(request: ChatMessage):
    """Send a single chat message (alternative to WebSocket)"""
    session_id = request.session_id or f"session_{int(datetime.now().timestamp())}"
    
    # Initialize session if not exists
    if session_id not in global_state.active_sessions:
        state = AsyncState()
        state.kg_builder = global_state.kg_builder
        state.session_id = session_id
        state.conversation_active = True
        global_state.active_sessions[session_id] = state
    
    state = global_state.active_sessions[session_id]
    
    # Check if user is asking for task creation or planning
    user_message = request.message.lower()
    mcp_action_taken = False
    mcp_result = ""
    
    # Detect task creation requests
    if any(phrase in user_message for phrase in ["create task", "add task", "make task", "create a task", "add to notion"]):
        try:
            from local_mcp.tools.notion_tools import NotionClientWrapper
            notion_token = os.getenv("NOTION_API_KEY")
            if notion_token:
                notion = NotionClientWrapper(auth_token=notion_token, default_database_id=os.getenv("NOTION_DEFAULT_DATABASE_ID"))
                result = notion.create_page_tool(title="Task from AI Chat", content=request.message)
                if result.get("status") == "created":
                    mcp_result = "✅ I've created that task in your Notion workspace! "
                    mcp_action_taken = True
                else:
                    mcp_result = "❌ I tried to create the task but encountered an issue. "
        except Exception as e:
            mcp_result = f"❌ Error creating task: {str(e)} "
    
    # Detect planning requests
    elif any(phrase in user_message for phrase in ["plan", "schedule", "break down", "steps", "organize"]):
        try:
            from local_mcp.tools.planning_tools import plan_tasks_tool
            result = plan_tasks_tool(goal=request.message, max_steps=5)
            mcp_result = f"✅ I've created a plan with {len(result.get('tasks', []))} steps for you! "
            mcp_action_taken = True
        except Exception as e:
            mcp_result = f"❌ Error creating plan: {str(e)} "
    
    # Generate AI response using the therapy system
    if not request.message.strip():
        # Initial greeting
        ai_response = ask_counselor_question(state, llm=global_state.llm)
    else:
        ai_response = ask_counselor_question(state, request.message, llm=global_state.llm)
    
    # Prepend MCP action result if any action was taken
    if mcp_action_taken:
        ai_response = mcp_result + ai_response
    
    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        timestamp=datetime.now().isoformat(),
        metadata={
            "qa_pairs_count": len(state.qa_pairs),
            "llm2_analyzing": state.llm2_analyzing,
            "has_insights": state.llm2_insights is not None
        }
    )

@app.post("/api/mcp/plan-tasks")
async def plan_tasks(request: TaskPlanRequest):
    """Create a task plan using MCP planning tools"""
    try:
        from local_mcp.tools.planning_tools import plan_tasks_tool
        result = plan_tasks_tool(
            goal=request.goal,
            deadline=request.deadline,
            max_steps=request.max_steps
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/mcp/schedule")
async def get_schedule(request: ScheduleRequest):
    """Get schedule for a specific date"""
    try:
        from local_mcp.tools.planning_tools import get_schedule_tool
        result = get_schedule_tool(date=request.date)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/mcp/add-event")
async def add_event(request: EventRequest):
    """Add an event to schedule"""
    try:
        from local_mcp.tools.planning_tools import add_event_tool
        result = add_event_tool(
            title=request.title,
            start=request.start,
            end=request.end,
            description=request.description
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Notion MCP endpoints
@app.post("/api/mcp/notion/create-page")
async def create_notion_page(request: NotionPageRequest):
    """Create a new page in Notion using MCP tools"""
    try:
        from local_mcp.tools.notion_tools import NotionClientWrapper
        notion_token = os.getenv("NOTION_API_KEY")
        default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
        
        if not notion_token:
            return {"success": False, "error": "Notion API key not configured"}
        
        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
        result = notion.create_page_tool(
            parent_database_id=request.database_id,
            title=request.title,
            content=request.content
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/mcp/notion/recent-pages")
async def get_recent_notion_pages():
    """Get recent pages from Notion database"""
    try:
        from local_mcp.tools.notion_tools import NotionClientWrapper
        notion_token = os.getenv("NOTION_API_KEY")
        default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
        
        if not notion_token:
            return {"success": False, "error": "Notion API key not configured"}
        
        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
        result = notion.query_database_tool(page_size=10)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/mcp/notion/query-database")
async def query_notion_database(database_id: Optional[str] = None):
    """Query Notion database with optional database_id parameter"""
    try:
        from local_mcp.tools.notion_tools import NotionClientWrapper
        notion_token = os.getenv("NOTION_API_KEY")
        default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
        
        if not notion_token:
            return {"success": False, "error": "Notion API key not configured"}
        
        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
        result = notion.query_database_tool(database_id=database_id, page_size=10)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/kg/sessions/{session_id}")
async def get_session_analysis(session_id: str):
    """Get Knowledge Graph analysis for a session"""
    if not global_state.kg_builder:
        raise HTTPException(status_code=503, detail="Knowledge Graph not configured")
    
    try:
        # Get session state
        if session_id not in global_state.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        state = global_state.active_sessions[session_id]
        analysis = global_state.kg_builder.analyze_therapy_patterns(
            session_id=session_id,
            current_qa_pairs=state.qa_pairs
        )
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "analysis": analysis,
                "qa_pairs_count": len(state.qa_pairs),
                "insights": state.llm2_insights
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_active_sessions():
    """Get list of active chat sessions"""
    sessions = []
    for session_id, state in global_state.active_sessions.items():
        sessions.append({
            "session_id": session_id,
            "original_question": state.original_question,
            "qa_pairs_count": len(state.qa_pairs),
            "active": state.conversation_active,
            "has_insights": state.llm2_insights is not None
        })
    
    return {"success": True, "data": sessions}

@app.get("/api/sessions/{session_id}/tasks")
async def get_session_tasks(session_id: str):
    """Get temporary tasks and events for a session"""
    if session_id not in global_state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = global_state.active_sessions[session_id]
    
    # Get temporary tasks and events
    tasks = getattr(state, 'temp_tasks', [])
    events = getattr(state, 'temp_events', [])
    
    return {
        "success": True,
        "data": {
            "tasks": tasks,
            "events": events,
            "session_id": session_id
        }
    }

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    if session_id in global_state.active_sessions:
        global_state.active_sessions[session_id].conversation_active = False
        del global_state.active_sessions[session_id]
        return {"success": True, "message": "Session deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
