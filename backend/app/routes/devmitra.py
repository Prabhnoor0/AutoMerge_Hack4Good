"""
Devमित्र API Routes

Isolated endpoints for the Devमित्र global chatbot feature.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.devmitra_service import (
    generate_chat_response,
    get_session_history,
    reset_session,
    update_context,
    get_or_create_session
)

router = APIRouter()

# --- Schemas ---

class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Session ID. If null, a new one is created.")
    message: str = Field(..., description="User's chat message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current UI context (code, logs, repo_url, etc.)")

class ChatMessageResponse(BaseModel):
    session_id: str
    message: str
    history: List[Dict[str, str]]

class ContextUpdateRequest(BaseModel):
    session_id: str
    context: Dict[str, Any]

class ResetSessionRequest(BaseModel):
    session_id: str

# --- Routes ---

@router.post("/chat", response_model=ChatMessageResponse)
async def devmitra_chat(payload: ChatMessageRequest):
    """Send a message to Devमित्र and get a response."""
    session_id = get_or_create_session(payload.session_id)
    
    # Generate response
    response_text = await generate_chat_response(
        session_id=session_id,
        message=payload.message,
        current_context=payload.context
    )
    
    # Get updated history
    history = get_session_history(session_id)
    
    return ChatMessageResponse(
        session_id=session_id,
        message=response_text,
        history=history
    )

@router.post("/context")
async def devmitra_update_context(payload: ContextUpdateRequest):
    """Explicitly push context updates to an active session."""
    update_context(payload.session_id, payload.context)
    return {"status": "success", "session_id": payload.session_id}

@router.post("/session/reset")
async def devmitra_reset_session(payload: ResetSessionRequest):
    """Clear chat history for a session."""
    reset_session(payload.session_id)
    return {"status": "success"}

@router.get("/health")
async def devmitra_health():
    """Health check for Devमित्र module."""
    return {"status": "ok", "module": "devmitra", "version": "1.0.0"}
