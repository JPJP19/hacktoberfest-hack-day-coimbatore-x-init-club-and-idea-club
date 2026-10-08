import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, Bid, Listing, Recycler, Transaction, Notification
from app.schemas.bid import BidCreate, BidOut, BidUpdate
from app.auth.auth import get_current_user, get_current_recycler

logger = logging.getLogger(__name__)
router = APIRouter()


async def _create_notification(db: AsyncSession, user_id: int, title: str, message: str):
    notif = Notification(user_id=user_id, title=title, message=message)
    db.add(notif)


def _gen_qr(transaction_id: int) -> str:
    """Generate base64-encoded QR PNG for a transaction ID."""
    import qrcode
    import io
    import base64

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(f"wasteconnect://transaction/{transaction_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------------------
# POST /listings/{id}/bids — place a bid
# ---------------------------------------------------------------------------
@router.post("/listings/{listing_id}/bids", response_model=BidOut, status_code=201)
async def place_bid(
    listing_id: int,
    payload: BidCreate,
    recycler: Recycler = Depends(get_current_recycler),
    db: AsyncSession = Depends(get_db),
):
    if payload.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")

    # Check listing exists and is open
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != "open":
        raise HTTPException(status_code=400, detail="Listing is not open for bids")

    # One active bid per recycler per listing
    existing = await db.execute(
        select(Bid).where(
            Bid.listing_id == listing_id,
            Bid.recycler_id == recycler.id,
            Bid.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have an active bid on this listing")

    bid = Bid(
        listing_id=listing_id,
        recycler_id=recycler.id,
        price=payload.price,
        pickup_date=payload.pickup_date,
        conditions=payload.conditions,
        status="pending",
    )
    db.add(bid)

    # Notify the listing owner
    await _create_notification(
        db, listing.user_id,
        title="New Bid Received",
        message=f"{recycler.name} placed a bid of ₹{payload.price:.0f} on your listing.",
    )

    await db.commit()
    await db.refresh(bid)
    return bid


# ---------------------------------------------------------------------------
# GET /listings/{id}/bids
# ---------------------------------------------------------------------------
@router.get("/listings/{listing_id}/bids", response_model=List[BidOut])
async def list_bids(
    listing_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Bid).where(Bid.listing_id == listing_id))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /recyclers/me/bids — recycler's own bids
# ---------------------------------------------------------------------------
@router.get("/recyclers/me/bids", response_model=List[BidOut])
async def my_bids(
    recycler: Recycler = Depends(get_current_recycler),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bid).where(Bid.recycler_id == recycler.id))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# PATCH /bids/{id} — update bid status (accept/reject/withdraw)
# ---------------------------------------------------------------------------
@router.patch("/bids/{bid_id}", response_model=BidOut)
async def update_bid(
    bid_id: int,
    payload: BidUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    # Get listing to find owner
    listing_result = await db.execute(select(Listing).where(Listing.id == bid.listing_id))
    listing = listing_result.scalar_one_or_none()

    # Only listing owner can accept/reject; only recycler can withdraw their own bid
    recycler_result = await db.execute(
        select(Recycler).where(Recycler.id == bid.recycler_id)
    )
    recycler = recycler_result.scalar_one_or_none()

    is_listing_owner = listing and listing.user_id == current_user.id
    is_bid_recycler = recycler and recycler.user_id == current_user.id
    is_admin = current_user.role == "admin"

    if payload.status:
        if payload.status == "withdrawn" and not (is_bid_recycler or is_admin):
            raise HTTPException(status_code=403, detail="Only the bidding recycler can withdraw")
        if payload.status in ("accepted", "rejected") and not (is_listing_owner or is_admin):
            raise HTTPException(status_code=403, detail="Only the listing owner can accept/reject bids")

        bid.status = payload.status

        # If accepted → create Transaction and reject other bids
        if payload.status == "accepted" and listing:
            listing.status = "accepted"

            # Reject all other pending bids
            other_bids_result = await db.execute(
                select(Bid).where(
                    Bid.listing_id == bid.listing_id,
                    Bid.id != bid.id,
                    Bid.status == "pending",
                )
            )
            for other in other_bids_result.scalars().all():
                other.status = "rejected"
                if other.recycler_id:
                    # Notify rejected recyclers
                    r_result = await db.execute(
                        select(Recycler).where(Recycler.id == other.recycler_id)
                    )
                    r = r_result.scalar_one_or_none()
                    if r:
                        await _create_notification(
                            db, r.user_id,
                            title="Bid Not Selected",
                            message=f"Your bid on listing #{bid.listing_id} was not selected.",
                        )

            # Create Transaction
            txn = Transaction(
                listing_id=bid.listing_id,
                bid_id=bid.id,
                user_id=listing.user_id,
                recycler_id=bid.recycler_id,
                agreed_price=bid.price,
                status="accepted",
            )
            db.add(txn)
            await db.flush()  # get txn.id

            txn.qr_code = _gen_qr(txn.id)

            # Notify recycler of acceptance
            if recycler:
                await _create_notification(
                    db, recycler.user_id,
                    title="Bid Accepted! 🎉",
                    message=(
                        f"Your bid of ₹{bid.price:.0f} on listing #{bid.listing_id} was accepted. "
                        "Proceed to schedule pickup."
                    ),
                )

    for field, value in payload.model_dump(exclude_none=True, exclude={"status"}).items():
        setattr(bid, field, value)

    await db.commit()
    await db.refresh(bid)
    return bid
