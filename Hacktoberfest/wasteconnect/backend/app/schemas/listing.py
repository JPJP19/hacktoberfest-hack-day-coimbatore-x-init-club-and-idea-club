from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class ListingCreate(BaseModel):
    category: str
    materials: List[str]
    description: str
    quantity: float
    unit: str = "kg"
    lat: float
    lng: float
    image_url: Optional[str] = None


class ListingConfirm(BaseModel):
    """Sent after analyze step to confirm/override and save the listing."""
    category: str
    materials: List[str]
    description: str
    quantity: float
    unit: str = "kg"
    lat: float
    lng: float
    image_url: Optional[str] = None


class ListingUpdate(BaseModel):
    category: Optional[str] = None
    materials: Optional[List[str]] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None


class ListingAnalysis(BaseModel):
    """Returned from analyze endpoint before user confirms."""
    category: str
    materials: List[str]
    hazards: List[str]
    condition: str
    recyclability: str
    confidence: float
    clarifying_questions: List[str]
    restricted: bool
    restriction_type: Optional[str] = None
    restriction_reason: Optional[str] = None
    allowed_vendor_type: Optional[str] = None
    consistent: Optional[bool] = None
    consistency_warning: Optional[str] = None
    suggested_quantity: Optional[float] = None
    suggested_unit: Optional[str] = None


class ListingOut(BaseModel):
    id: int
    user_id: int
    image_url: Optional[str] = None
    category: str
    materials: Optional[List[str]] = None
    description: str
    quantity: float
    unit: str
    lat: float
    lng: float
    status: str
    ai_analysis: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
