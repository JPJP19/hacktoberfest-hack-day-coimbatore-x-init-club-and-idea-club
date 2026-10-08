import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, Transaction, Recycler, Listing, Notification
from app.schemas.transaction import (
    TransactionOut,
    TransactionStatusUpdate,
    QuantityConfirm,
    RatingSubmit,
)
from app.auth.auth import get_current_user
from app.services.gemma_client import gemma_client
from app.services.prompts import DISPUTE_HELPER_SYSTEM

logger = logging.getLogger(__name__)
router = APIRouter()

DISPUTE_THRESHOLD = 0.15  # 15% quantity deviation triggers dispute check


async def _notify(db: AsyncSession, user_id: int, title: str, message: str):
    db.add(Notification(user_id=user_id, title=title, message=message))


# ---------------------------------------------------------------------------
# GET /transactions — my transactions
# ---------------------------------------------------------------------------
@router.get("", response_model=List[TransactionOut])
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    
    stmt = select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    )

    if current_user.role == "admin":
        result = await db.execute(stmt)
    elif current_user.role == "recycler":
        recycler_result = await db.execute(
            select(Recycler).where(Recycler.user_id == current_user.id)
        )
        recycler = recycler_result.scalar_one_or_none()
        if not recycler:
            return []
        result = await db.execute(
            stmt.where(Transaction.recycler_id == recycler.id)
        )
    else:
        result = await db.execute(
            stmt.where(Transaction.user_id == current_user.id)
        )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /transactions/{id}
# ---------------------------------------------------------------------------
@router.get("/{txn_id}", response_model=TransactionOut)
async def get_transaction(
    txn_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    result = await db.execute(select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    ).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Authorization: owner, recycler's user, or admin
    recycler_result = await db.execute(
        select(Recycler).where(Recycler.id == txn.recycler_id)
    )
    recycler = recycler_result.scalar_one_or_none()
    is_recycler_user = recycler and recycler.user_id == current_user.id

    if txn.user_id != current_user.id and not is_recycler_user and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return txn


# ---------------------------------------------------------------------------
# PATCH /transactions/{id}/status
# ---------------------------------------------------------------------------
@router.patch("/{txn_id}/status", response_model=TransactionOut)
async def update_status(
    txn_id: int,
    payload: TransactionStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    result = await db.execute(select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    ).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.status = payload.status

    # Notify the other party
    recycler_result = await db.execute(
        select(Recycler).where(Recycler.id == txn.recycler_id)
    )
    recycler = recycler_result.scalar_one_or_none()

    if payload.status == "pickup_scheduled":
        if recycler:
            await _notify(db, recycler.user_id, "Pickup Scheduled",
                          f"Pickup for transaction #{txn.id} has been scheduled.")
    elif payload.status == "collected":
        await _notify(db, txn.user_id, "Waste Collected",
                      f"Your waste for transaction #{txn.id} has been collected.")
    elif payload.status == "paid":
        await _notify(db, txn.user_id, "Payment Received",
                      f"Payment of ₹{txn.agreed_price:.0f} for transaction #{txn.id} confirmed.")

    await db.commit()
    await db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# POST /transactions/{id}/confirm-quantity
# ---------------------------------------------------------------------------
@router.post("/{txn_id}/confirm-quantity", response_model=TransactionOut)
async def confirm_quantity(
    txn_id: int,
    payload: QuantityConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    result = await db.execute(select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    ).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.confirmed_quantity = payload.confirmed_quantity
    txn.status = "quantity_confirmed"

    # Check for dispute threshold
    listing_result = await db.execute(
        select(Listing).where(Listing.id == txn.listing_id)
    )
    listing = listing_result.scalar_one_or_none()

    if listing and listing.quantity > 0:
        deviation = abs(payload.confirmed_quantity - listing.quantity) / listing.quantity
        if deviation > DISPUTE_THRESHOLD:
            logger.info(
                "Quantity deviation %.1f%% exceeds threshold for txn %d", deviation * 100, txn_id
            )
            # Run Gemma dispute resolution
            user_msg = (
                f"agreed_price={txn.agreed_price}, "
                f"declared_quantity={listing.quantity}, "
                f"confirmed_quantity={payload.confirmed_quantity}, "
                f"unit={listing.unit}"
            )
            dispute = await gemma_client.generate_json(
                DISPUTE_HELPER_SYSTEM, user_msg, db=db, skill="dispute_helper"
            )
            txn.dispute_suggestion = dispute

            # Notify both parties
            await _notify(db, txn.user_id, "Quantity Dispute Flagged",
                          f"Confirmed quantity differs by {deviation*100:.1f}%. "
                          f"AI suggests adjustment to ₹{dispute.get('fair_adjustment', '?')}.")
            recycler_result = await db.execute(
                select(Recycler).where(Recycler.id == txn.recycler_id)
            )
            recycler = recycler_result.scalar_one_or_none()
            if recycler:
                await _notify(db, recycler.user_id, "Quantity Dispute Flagged",
                              f"Transaction #{txn.id} has a quantity discrepancy. Review dispute suggestion.")

    await db.commit()
    await db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# POST /transactions/{id}/complete
# ---------------------------------------------------------------------------
@router.post("/{txn_id}/complete", response_model=TransactionOut)
async def complete_transaction(
    txn_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    result = await db.execute(select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    ).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.status = "recycled"

    # Update recycler stats
    recycler_result = await db.execute(
        select(Recycler).where(Recycler.id == txn.recycler_id)
    )
    recycler = recycler_result.scalar_one_or_none()
    if recycler:
        recycler.completed_pickups += 1

    # Update listing status
    listing_result = await db.execute(
        select(Listing).where(Listing.id == txn.listing_id)
    )
    listing = listing_result.scalar_one_or_none()
    if listing:
        listing.status = "completed"

    await _notify(db, txn.user_id, "Transaction Complete ✅",
                  f"Transaction #{txn.id} marked as recycled. Thank you for recycling!")

    await db.commit()
    await db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# POST /transactions/{id}/rate
# ---------------------------------------------------------------------------
@router.post("/{txn_id}/rate", response_model=TransactionOut)
async def rate_transaction(
    txn_id: int,
    payload: RatingSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from app.models.models import Bid
    result = await db.execute(select(Transaction).options(
        selectinload(Transaction.listing),
        selectinload(Transaction.bid).selectinload(Bid.recycler)
    ).where(Transaction.id == txn_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    if payload.role == "user":
        # User rates the recycler
        if txn.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your transaction")
        txn.user_rating = payload.rating

        # Update recycler's average rating
        recycler_result = await db.execute(
            select(Recycler).where(Recycler.id == txn.recycler_id)
        )
        recycler = recycler_result.scalar_one_or_none()
        if recycler:
            total = recycler.rating * recycler.completed_pickups
            recycler.rating = round(
                (total + payload.rating) / (recycler.completed_pickups + 1), 2
            )

    elif payload.role == "recycler":
        # Recycler rates the user
        recycler_result = await db.execute(
            select(Recycler).where(Recycler.id == txn.recycler_id)
        )
        recycler = recycler_result.scalar_one_or_none()
        if not recycler or recycler.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your transaction")
        txn.recycler_rating = payload.rating
    else:
        raise HTTPException(status_code=400, detail="role must be 'user' or 'recycler'")

    await db.commit()
    await db.refresh(txn)
    return txn
