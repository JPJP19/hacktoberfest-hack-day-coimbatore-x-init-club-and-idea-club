import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, Recycler, Listing
from app.schemas.recycler import (
    RecyclerCreate,
    RecyclerUpdate,
    RecyclerOut,
    CopilotRequest,
    CopilotResponse,
)
from app.auth.auth import get_current_user, get_current_recycler
from app.services.embedding_service import embedding_service
from app.services.gemma_client import gemma_client
from app.services.prompts import RECYCLER_COPILOT_SYSTEM

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# POST /recyclers/profile — create or update recycler profile
# ---------------------------------------------------------------------------
@router.post("/profile", response_model=RecyclerOut)
async def upsert_profile(
    payload: RecyclerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("recycler", "admin"):
        raise HTTPException(status_code=403, detail="Only recycler accounts can create profiles")

    # Generate embedding from profile_text
    try:
        emb = embedding_service.encode(payload.profile_text)
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        emb = None

    result = await db.execute(
        select(Recycler).where(Recycler.user_id == current_user.id)
    )
    recycler = result.scalar_one_or_none()

    if recycler:
        # Update existing
        for field, value in payload.model_dump().items():
            if field != "embedding":
                setattr(recycler, field, value)
        recycler.embedding = emb
    else:
        recycler = Recycler(
            user_id=current_user.id,
            embedding=emb,
            **payload.model_dump(),
        )
        db.add(recycler)

    await db.commit()
    await db.refresh(recycler)
    return recycler


# ---------------------------------------------------------------------------
# GET /recyclers/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=RecyclerOut)
async def get_my_profile(
    recycler: Recycler = Depends(get_current_recycler),
):
    return recycler


# ---------------------------------------------------------------------------
# GET /recyclers/listings — open listings near recycler
# ---------------------------------------------------------------------------
@router.get("/listings")
async def get_nearby_listings(
    recycler: Recycler = Depends(get_current_recycler),
    db: AsyncSession = Depends(get_db),
):
    from app.services.matching_service import haversine

    result = await db.execute(
        select(Listing).where(Listing.status == "open")
    )
    listings = result.scalars().all()

    recycler_mats = set(m.lower() for m in (recycler.materials_supported or []))
    nearby = []
    for listing in listings:
        listing_mats = set(m.lower() for m in (listing.materials or []))
        if not listing_mats.intersection(recycler_mats):
            continue
        dist = haversine(recycler.lat, recycler.lng, listing.lat, listing.lng)
        if dist <= recycler.service_radius_km:
            nearby.append({"listing": listing, "distance_km": round(dist, 2)})

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby


# ---------------------------------------------------------------------------
# GET /recyclers/{id} — public profile
# ---------------------------------------------------------------------------
@router.get("/{recycler_id}", response_model=RecyclerOut)
async def get_recycler(
    recycler_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Recycler).where(Recycler.id == recycler_id))
    recycler = result.scalar_one_or_none()
    if not recycler:
        raise HTTPException(status_code=404, detail="Recycler not found")
    return recycler


# ---------------------------------------------------------------------------
# POST /recyclers/copilot — Gemma pricing suggestion
# ---------------------------------------------------------------------------
@router.post("/copilot", response_model=CopilotResponse)
async def copilot(
    payload: CopilotRequest,
    recycler: Recycler = Depends(get_current_recycler),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Listing).where(Listing.id == payload.listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    user_msg = (
        f"Category: {listing.category}, "
        f"Materials: {listing.materials}, "
        f"Quantity: {listing.quantity} {listing.unit}, "
        f"Description: {listing.description}, "
        f"Priority: {payload.priority}"
    )
    ai_result = await gemma_client.generate_json(
        RECYCLER_COPILOT_SYSTEM, user_msg, db=db, skill="recycler_copilot"
    )

    price_range = ai_result.get("suggested_price_range", {"min": 0, "max": 0})
    return CopilotResponse(
        suggested_price_min=float(price_range.get("min", 0)),
        suggested_price_max=float(price_range.get("max", 0)),
        pitch=ai_result.get("pitch", ""),
    )
