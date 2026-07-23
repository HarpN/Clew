"""
mobile_server.py - Mobile Web Hub API & Static Asset Server for Clew
Exposes REST API endpoints for tasks, chat timeline, LiveKit WebRTC token generation,
and Server-Sent Events (SSE) token streaming for mobile/native iOS clients.
"""

import os
import sys
import json
import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Access root workspace
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import orchestrator
import distillery
import graph_memory
from router import ModelRouter
from brain_orchestrator_v5 import CognitiveBrainV5

router_instance = ModelRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.mobile_server")

app = FastAPI(title="Clew V5 Mobile Proxy API", version="2.0.0")

# Enable CORS for local Xcode Simulator and Tailscale clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

brain = CognitiveBrainV5()

class ChatRequest(BaseModel):
    prompt: str
    goal_tether_id: str = "mobile_default"
    manual_override_key: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "P2"
    energy_level: Optional[str] = "medium"

class TaskStatusUpdate(BaseModel):
    status: str

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Server-Sent Events (SSE) endpoint yielding token-by-token Broca Area responses
    to the native Swift iOS client.
    """
    logger.info(f"[MOBILE_API] Received streaming request: '{request.prompt[:40]}...'")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            success, result_stream, persona_name = await brain.process_thought_cycle_v5(
                user_prompt=request.prompt,
                goal_tether_id=request.goal_tether_id,
                manual_override_key=request.manual_override_key
            )

            # 1. Send initial metadata event (Persona name, status)
            init_payload = json.dumps({"type": "init", "persona": persona_name, "success": success})
            yield f"data: {init_payload}\n\n"

            if not success:
                # Handle constraint guard vetoes instantly
                veto_payload = json.dumps({"type": "veto", "text": str(result_stream)})
                yield f"data: {veto_payload}\n\n"
                yield "data: [DONE]\n\n"
                return

            # 2. Handle string vs stream generator
            if isinstance(result_stream, str):
                chunk_payload = json.dumps({"type": "token", "text": result_stream})
                yield f"data: {chunk_payload}\n\n"
            else:
                async for token in result_stream:
                    if token:
                        chunk_payload = json.dumps({"type": "token", "text": token})
                        yield f"data: {chunk_payload}\n\n"
                        # Yield control briefly to ensure low-latency socket flushing
                        await asyncio.sleep(0.001)

            # 3. Yield completion signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[MOBILE_API] SSE Streaming error: {e}")
            err_payload = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# API Routes
@app.get("/api/tasks")
def get_tasks_api(status: Optional[str] = None):
    try:
        tasks = database.get_tasks(status=status)
        return tasks
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks")
def create_task_api(task: TaskCreate):
    p_map = {"P1": 1, "P2": 2, "P3": 3, "1": 1, "2": 2, "3": 3}
    priority_val = p_map.get(task.priority.upper() if task.priority else "P2", 2)
    try:
        task_id = database.add_task(
            title=task.title,
            description=task.description,
            priority=priority_val,
            energy_level=task.energy_level or "medium",
            context_tags=["mobile"]
        )
        database.log_telemetry(
            action="add_task_mobile",
            task_id=task_id,
            energy_level=task.energy_level
        )
        return {"success": True, "task_id": task_id}
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/status")
def update_task_status_api(task_id: int, payload: TaskStatusUpdate):
    try:
        success = database.update_task_status(task_id, payload.status)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task #{task_id} not found")
        database.log_telemetry(
            action=f"update_task_{payload.status}",
            task_id=task_id
        )
        return {"success": True, "task_id": task_id, "status": payload.status}
    except Exception as e:
        logger.error(f"Error updating task #{task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat")
def get_chat_api(limit: int = 50):
    try:
        return database.get_chat_timeline(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching chat timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ChatMessagePayload(BaseModel):
    message: str
    source: Optional[str] = "mobile_web"

from brain import clew_brain

@app.post("/api/chat")
async def create_chat_api(payload: ChatMessagePayload):
    try:
        database.add_chat_message(
            content=payload.message,
            source=payload.source or "mobile_web",
            speaker="user"
        )
        
        # Process the intent via the split-brain CognitiveBrain cycle
        result = await clew_brain.process_thought_cycle(payload.message, None)
        
        if isinstance(result, str):
            reply_text = result
        else:
            reply_text = result.message
        
        database.add_chat_message(
            content=reply_text,
            source="agent",
            speaker="agent"
        )
        
        return {"success": True, "reply": reply_text}
    except Exception as e:
        logger.error(f"Error adding chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intent")
def process_intent_api(payload: Dict[str, Any]):
    """
    Direct REST gateway into the Clew Intent-Command-Response Orchestrator Middleware.
    Validates schema against protocol.py models and evaluates ConstraintGuard rules.
    """
    try:
        result = orchestrator.orchestrator.process_intent(payload)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error processing intent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class FeedbackPayload(BaseModel):
    command_id: str
    user_rating: int
    correction_text: Optional[str] = None

@app.post("/api/feedback")
def submit_feedback_api(payload: FeedbackPayload):
    try:
        fb_id = database.submit_intent_feedback(
            command_id=payload.command_id,
            user_rating=payload.user_rating,
            correction_text=payload.correction_text
        )
        return {"success": True, "feedback_id": fb_id}
    except Exception as e:
        logger.error(f"Error logging feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/distillery/run")
def run_distillery_api():
    try:
        summary = distillery.distillery.run_daily_distillation()
        return summary
    except Exception as e:
        logger.error(f"Error running distillation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/distillery/proposals")
def get_distillery_proposals_api():
    try:
        return distillery.distillery.get_pending_proposals()
    except Exception as e:
        logger.error(f"Error fetching proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/distillery/accept/{proposal_id}")
def accept_proposal_api(proposal_id: str):
    try:
        success = distillery.distillery.accept_optimization(proposal_id)
        return {"success": success, "proposal_id": proposal_id}
    except Exception as e:
        logger.error(f"Error accepting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/distillery/reject/{proposal_id}")
def reject_proposal_api(proposal_id: str):
    try:
        success = distillery.distillery.reject_optimization(proposal_id)
        return {"success": success, "proposal_id": proposal_id}
    except Exception as e:
        logger.error(f"Error rejecting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/export")
def export_memory_api():
    """
    Serializes the entire project graph (Entities, Relationships, Standards, Goals)
    into a portable JSON structure for zero-friction agent migration.
    """
    try:
        return graph_memory.export_memory()
    except Exception as e:
        logger.error(f"Error exporting memory graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/livekit/token")
def generate_livekit_token():
    livekit_url = os.getenv("LIVEKIT_URL", "wss://livekit.local")
    api_key = os.getenv("LIVEKIT_API_KEY", "dev_key")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "dev_secret")
    room_name = "clew-voice-room"
    identity = "mobile_user"

    return {
        "success": True,
        "token": "simulated_livekit_token_xyz",
        "url": livekit_url,
        "room": room_name,
        "identity": identity
    }

# Serve Mobile Static Assets
mobile_dir = os.path.join(BASE_DIR, "mobile")
if os.path.exists(mobile_dir):
    app.mount("/static", StaticFiles(directory=mobile_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(mobile_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Clew Mobile Hub Server running. static assets folder 'mobile' ready."}

if __name__ == "__main__":
    import uvicorn
    database.init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
