from typing import Optional, List, Any
from pydantic import BaseModel


class WasteAnalysis(BaseModel):
    category: str
    materials: List[str]
    hazards: List[str]
    condition: str
    recyclability: str
    confidence: float
    clarifying_questions: List[str]


class SafetyTriage(BaseModel):
    restricted: bool
    restriction_type: Optional[str] = None
    reason: Optional[str] = None
    allowed_vendor_type: Optional[str] = None


class ConsistencyCheck(BaseModel):
    consistent: bool
    confidence: float
    warning: Optional[str] = None


class StructuredListing(BaseModel):
    category: str
    quantity: float
    unit: str
    materials: List[str]
    missing_fields: List[str]


class RankedRecycler(BaseModel):
    recycler_id: int
    reason: str


class MatchRerank(BaseModel):
    ranked_recyclers: List[RankedRecycler]


class BidComparisonItem(BaseModel):
    bid_id: int
    recycler_name: str
    price: float
    pickup_date: str
    score: float
    strengths: List[str]
    weaknesses: List[str]


class BidAnalysisResult(BaseModel):
    highest_bid: float
    best_convenience_bid_id: int
    best_overall_bid_id: int
    recommended_id: int
    comparison: List[BidComparisonItem]
    explanation: str
    risks: List[str]
    confidence: float


class DisputeResult(BaseModel):
    fair_adjustment: float
    rationale: str


class CopilotResult(BaseModel):
    suggested_price_range: dict  # {min: float, max: float}
    pitch: str
