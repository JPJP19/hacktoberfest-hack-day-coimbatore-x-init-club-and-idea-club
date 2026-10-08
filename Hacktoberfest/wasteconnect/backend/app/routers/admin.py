import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.models import AILog, User, Recycler, Listing, Bid, Transaction
from app.auth.auth import get_current_admin
from app.services.embedding_service import embedding_service
from app.auth.auth import get_password_hash

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ai-logs")
async def get_ai_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    skill: str = Query(None),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(AILog).order_by(AILog.created_at.desc())
    if skill:
        q = q.where(AILog.skill == skill)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "skill": l.skill,
            "success": l.success,
            "fallback_used": l.fallback_used,
            "latency_ms": round(l.latency_ms, 1),
            "error": l.error,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.post("/seed")
async def seed_data(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Run seed data from seed/seed.py logic inline."""
    from seed.seed import run_seed
    await run_seed(db)
    return {"ok": True, "message": "Seed data inserted"}


@router.post("/reset-demo")
async def reset_demo(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete all listings, bids, transactions for demo reset."""
    for model in (Transaction, Bid, Listing):
        items = await db.execute(select(model))
        for item in items.scalars().all():
            await db.delete(item)
    await db.commit()
    return {"ok": True, "message": "Demo data reset"}
