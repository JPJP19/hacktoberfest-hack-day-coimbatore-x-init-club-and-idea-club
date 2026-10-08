from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class BidCreate(BaseModel):
    price: float  # INR
    pickup_date: datetime
    conditions: Optional[str] = None


class BidOut(BaseModel):
    id: int
    listing_id: int
    recycler_id: int
    price: float
    pickup_date: datetime
    conditions: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class BidUpdate(BaseModel):
    status: Optional[str] = None  # pending|accepted|rejected|withdrawn
    price: Optional[float] = None
    pickup_date: Optional[datetime] = None
    conditions: Optional[str] = None


class BidComparison(BaseModel):
    bid_id: int
    recycler_name: str
    price: float
    pickup_date: str
    score: float
    strengths: List[str]
    weaknesses: List[str]


class BidAnalysis(BaseModel):
    highest_bid: float
    best_convenience_bid_id: int
    best_overall_bid_id: int
    recommended_id: int
    comparison: List[BidComparison]
    explanation: str
    risks: List[str]
    confidence: float
