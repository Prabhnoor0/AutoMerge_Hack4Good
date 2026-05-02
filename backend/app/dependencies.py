"""
FastAPI Dependencies
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User
from app.services.auth_service import decode_access_token

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Dependency to get the currently authenticated user from HttpOnly cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    # Strip "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
        
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    user_id = payload["sub"]
    
    # Fetch user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user

async def get_current_user_optional(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    """Dependency to optionally get the current user, without raising an exception if unauthenticated."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
