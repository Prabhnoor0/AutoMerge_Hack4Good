"""
BugFix Arena — API Routes

All battle endpoints under /api/battle/*.
Fully isolated from existing routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import battle_service

router = APIRouter()


# ─── Request Models ───────────────────────────────────────

class CreateRequest(BaseModel):
    host_name: str
    challenge_id: str = ""
    title: str = ""

class JoinRequest(BaseModel):
    room_code: str
    player_name: str

class SubmitRequest(BaseModel):
    player_id: str
    code: str
    explanation: str = ""


# ─── Endpoints ────────────────────────────────────────────

@router.post("/create")
async def create_battle(req: CreateRequest):
    """Create a new battle session."""
    try:
        session = battle_service.create_session(req.host_name, req.challenge_id, req.title)
        return {"status": "ok", "data": session}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/join")
async def join_battle(req: JoinRequest):
    """Join an existing battle by room code."""
    try:
        session = battle_service.join_session(req.room_code, req.player_name)
        return {"status": "ok", "data": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/start")
async def start_battle(session_id: str):
    """Start the battle timer."""
    try:
        session = battle_service.start_battle(session_id)
        return {"status": "ok", "data": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/submit")
async def submit_solution(session_id: str, req: SubmitRequest):
    """Submit a player's solution."""
    try:
        session = battle_service.submit_solution(session_id, req.player_id, req.code, req.explanation)
        return {"status": "ok", "data": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get full session data."""
    session = battle_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Battle not found")
    return {"status": "ok", "data": session}


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    """Get live battle state (safe for polling)."""
    try:
        state = battle_service.get_state(session_id)
        return {"status": "ok", "data": state}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/finish")
async def finish_battle(session_id: str):
    """Force-finish a battle."""
    try:
        session = battle_service.finish_battle(session_id)
        return {"status": "ok", "data": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/result")
async def get_result(session_id: str):
    """Get battle result with full submissions."""
    result = battle_service.get_result(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not available yet")
    return {"status": "ok", "data": result}


@router.get("/meta/leaderboard")
async def leaderboard():
    """Get all-time leaderboard."""
    return {"status": "ok", "data": battle_service.get_leaderboard()}


@router.get("/meta/challenges")
async def list_challenges():
    """List available battle challenges."""
    return {"status": "ok", "data": battle_service.list_challenges()}
