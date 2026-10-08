import os
import uuid
import io
import base64
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, Listing, Notification
from app.schemas.listing import ListingCreate, ListingConfirm, ListingOut, ListingUpdate
from app.auth.auth import get_current_user
from app.services.gemma_client import gemma_client
from app.services.embedding_service import embedding_service
from app.services.matching_service import find_matching_recyclers
from app.services.bid_analysis_service import analyze_bids_with_ai
from app.services.prompts import (
    ANALYZE_WASTE_SYSTEM,
    SAFETY_TRIAGE_SYSTEM,
    CONSISTENCY_CHECK_SYSTEM,
)

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _save_image(file: UploadFile) -> tuple[str, bytes]:
    """Save uploaded image and return (url_path, raw_bytes)."""
    ext = os.path.splitext(file.filename or "img.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    data = await file.read()
    with open(filepath, "wb") as f:
        f.write(data)
    return f"/uploads/{filename}", data


# ---------------------------------------------------------------------------
# POST /listings/analyze
# ---------------------------------------------------------------------------
@router.post("/analyze")
async def analyze_listing(
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 1-3 pipeline:
    1. analyze_waste (image + text)
    2. safety_triage
    3. consistency_check (if image provided)
    Returns a draft analysis for the user to confirm.
    """
    image_url: Optional[str] = None
    image_bytes: Optional[bytes] = None

    if image:
        image_url, image_bytes = await _save_image(image)

    user_text = description or "No description provided"

    # Step 1: Waste analysis
    waste_result = await gemma_client.generate_json(
        ANALYZE_WASTE_SYSTEM,
        user_text,
        image=image_bytes,
        db=db,
        skill="analyze_waste",
    )

    # Step 2: Safety triage
    triage_input = (
        f"Category: {waste_result.get('category', '')}, "
        f"Materials: {waste_result.get('materials', [])}, "
        f"Description: {user_text}"
    )
    triage_result = await gemma_client.generate_json(
        SAFETY_TRIAGE_SYSTEM,
        triage_input,
        db=db,
        skill="safety_triage",
    )

    # Step 3: Consistency check (only if image was uploaded)
    consistency_result: dict = {"consistent": True, "confidence": 1.0, "warning": None}
    if image_bytes and description:
        consistency_input = (
            f"Declared: {description}\n"
            f"Image analysis: {waste_result.get('category', '')} - {waste_result.get('materials', [])}"
        )
        consistency_result = await gemma_client.generate_json(
            CONSISTENCY_CHECK_SYSTEM,
            consistency_input,
            db=db,
            skill="consistency_check",
        )

    # Compose response
    return {
        **waste_result,
        "image_url": image_url,
        "restricted": triage_result.get("restricted", False),
        "restriction_type": triage_result.get("restriction_type"),
        "restriction_reason": triage_result.get("reason"),
        "allowed_vendor_type": triage_result.get("allowed_vendor_type"),
        "consistent": consistency_result.get("consistent", True),
        "consistency_warning": consistency_result.get("warning"),
    }


# ---------------------------------------------------------------------------
# POST /listings — create confirmed listing
# ---------------------------------------------------------------------------
@router.post("", response_model=ListingOut, status_code=201)
async def create_listing(
    payload: ListingConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Build text for embedding
    embed_text = (
        f"{payload.category} {' '.join(payload.materials)} {payload.description}"
    )
    try:
        emb = embedding_service.encode(embed_text)
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        emb = None

    listing = Listing(
        user_id=current_user.id,
        image_url=payload.image_url,
        category=payload.category,
        materials=payload.materials,
        description=payload.description,
        quantity=payload.quantity,
        unit=payload.unit,
        lat=payload.lat,
        lng=payload.lng,
        status="open",
        embedding=emb,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# GET /listings — list with filters
# ---------------------------------------------------------------------------
@router.get("", response_model=List[ListingOut])
async def list_listings(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Listing)
    if status:
        q = q.where(Listing.status == status)
    if category:
        q = q.where(Listing.category == category)
    q = q.offset(offset).limit(limit).order_by(Listing.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /listings/{id}
# ---------------------------------------------------------------------------
@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


# ---------------------------------------------------------------------------
# PATCH /listings/{id}
# ---------------------------------------------------------------------------
@router.patch("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your listing")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(listing, field, value)

    await db.commit()
    await db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# GET /listings/{id}/matches
# ---------------------------------------------------------------------------
@router.get("/{listing_id}/matches")
async def get_matches(
    listing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    matches = await find_matching_recyclers(listing, db)
    return [
        {
            "recycler_id": r.id,
            "name": r.name,
            "materials_supported": r.materials_supported,
            "rating": r.rating,
            "completed_pickups": r.completed_pickups,
            "distance_km": round(dist, 2),
            "score": round(score, 4),
            "reason": reason,
            "contact_email": r.contact_email,
            "contact_phone": r.contact_phone,
        }
        for r, dist, score, reason in matches
    ]


# ---------------------------------------------------------------------------
# POST /listings/{id}/analyze-bids  (Phase 6)
# ---------------------------------------------------------------------------
@router.post("/{listing_id}/analyze-bids")
async def analyze_bids(
    listing_id: int,
    priority: str = Query("balanced"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Bid, Recycler
    from sqlalchemy.orm import selectinload

    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your listing")

    bids_result = await db.execute(
        select(Bid, Recycler)
        .join(Recycler, Bid.recycler_id == Recycler.id)
        .where(Bid.listing_id == listing_id, Bid.status == "pending")
    )
    rows = bids_result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="No pending bids found")

    bids_data = [
        {
            "bid_id": bid.id,
            "recycler_name": recycler.name,
            "price": bid.price,
            "pickup_date": bid.pickup_date,
            "rating": recycler.rating,
            "completion_rate": recycler.completed_pickups / max(recycler.completed_pickups + 10, 1),
            "distance_km": 0.0,  # precomputed if needed
        }
        for bid, recycler in rows
    ]

    analysis = await analyze_bids_with_ai(listing, bids_data, priority=priority, db=db)
    return analysis
