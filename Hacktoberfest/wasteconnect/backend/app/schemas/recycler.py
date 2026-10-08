from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class RecyclerCreate(BaseModel):
    name: str
    lat: float
    lng: float
    materials_supported: List[str]
    service_radius_km: float = 20.0
    profile_text: str
    contact_email: str
    contact_phone: str
    is_authorized_hazardous: bool = False


class RecyclerUpdate(BaseModel):
    name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    materials_supported: Optional[List[str]] = None
    service_radius_km: Optional[float] = None
    profile_text: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_authorized_hazardous: Optional[bool] = None
    pickup_available: Optional[bool] = None


class RecyclerOut(BaseModel):
    id: int
    user_id: int
    name: str
    lat: float
    lng: float
    materials_supported: Optional[List[str]] = None
    service_radius_km: float
    rating: float
    completed_pickups: int
    verified: bool
    is_authorized_hazardous: bool
    pickup_available: bool
    profile_text: str
    contact_email: str
    contact_phone: str
    created_at: datetime

    class Config:
        from_attributes = True


class RecyclerProfile(RecyclerOut):
    """Extended profile returned to the recycler themselves."""
    pass


class RecyclerMatch(BaseModel):
    """A recycler returned in match results with extra match metadata."""
    recycler: RecyclerOut
    distance_km: float
    score: float
    reason: str


class CopilotRequest(BaseModel):
    listing_id: int
    priority: str = "balanced"  # price|speed|reliability|balanced


class CopilotResponse(BaseModel):
    suggested_price_min: float
    suggested_price_max: float
    pitch: str
