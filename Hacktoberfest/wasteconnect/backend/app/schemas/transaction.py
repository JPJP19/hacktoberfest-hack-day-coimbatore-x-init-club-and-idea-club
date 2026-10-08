from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class TransactionOut(BaseModel):
    id: int
    listing_id: int
    bid_id: int
    user_id: int
    recycler_id: int
    agreed_price: float
    confirmed_quantity: Optional[float] = None
    status: str
    qr_code: Optional[str] = None
    payment_receipt: Optional[str] = None
    user_rating: Optional[float] = None
    recycler_rating: Optional[float] = None
    dispute_suggestion: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    listing_lat: Optional[float] = None
    listing_lng: Optional[float] = None
    recycler_lat: Optional[float] = None
    recycler_lng: Optional[float] = None

    class Config:
        from_attributes = True


class TransactionStatusUpdate(BaseModel):
    status: str  # pickup_scheduled|collected|quantity_confirmed|paid|recycled


class QuantityConfirm(BaseModel):
    confirmed_quantity: float


class RatingSubmit(BaseModel):
    rating: float  # 1-5
    role: str  # "user" or "recycler" — which side is submitting
