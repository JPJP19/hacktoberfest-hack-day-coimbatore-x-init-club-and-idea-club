"""
Deterministic bid scoring + Gemma-assisted recommendation with result validation.
"""
import json
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

WEIGHTS = {
    "price":       {"price": 0.50, "speed": 0.20, "rating": 0.20, "completion": 0.10},
    "speed":       {"price": 0.10, "speed": 0.50, "rating": 0.20, "completion": 0.20},
    "reliability": {"price": 0.10, "speed": 0.10, "rating": 0.40, "completion": 0.40},
    "balanced":    {"price": 0.25, "speed": 0.25, "rating": 0.25, "completion": 0.25},
}


def _hours_until(pickup_date: datetime) -> float:
    """Hours from now until pickup date (clamped to 0)."""
    now = datetime.utcnow()
    delta = (pickup_date - now).total_seconds() / 3600
    return max(0.0, delta)


def compute_bid_scores(bids_data: List[dict], priority: str = "balanced") -> List[dict]:
    """
    Pure deterministic scoring of bid candidates.
    Each item in bids_data is expected to have:
      price, pickup_date (datetime), rating, completion_rate, distance_km (optional)
    Returns list sorted by baseline_score descending.
    """
    if not bids_data:
        return []

    prices = [b["price"] for b in bids_data]
    max_price, min_price = max(prices), min(prices)
    price_range = max_price - min_price or 1.0

    hours_list = [_hours_until(b["pickup_date"]) for b in bids_data]
    max_hours = max(hours_list) or 1.0

    weights = WEIGHTS.get(priority, WEIGHTS["balanced"])

    for b, hours in zip(bids_data, hours_list):
        # Higher price → better for seller → higher norm_price
        b["norm_price"] = (b["price"] - min_price) / price_range
        b["pickup_hours"] = hours
        b["norm_speed"] = 1.0 - hours / max_hours  # sooner = higher score
        b["norm_rating"] = b.get("rating", 4.0) / 5.0
        b["norm_completion"] = b.get("completion_rate", 0.8)

        b["baseline_score"] = (
            weights["price"]      * b["norm_price"]
            + weights["speed"]    * b["norm_speed"]
            + weights["rating"]   * b["norm_rating"]
            + weights["completion"] * b["norm_completion"]
        )

    return sorted(bids_data, key=lambda x: -x["baseline_score"])


async def analyze_bids_with_ai(
    listing,
    bids_with_recyclers: List[dict],
    priority: str = "balanced",
    db=None,
) -> dict:
    """
    1. Compute deterministic scores.
    2. Send to Gemma for narrative analysis.
    3. Validate Gemma's recommended_id and highest_bid; override if wrong.
    Returns the final structured dict.
    """
    from app.services.gemma_client import gemma_client
    from app.services.prompts import ANALYZE_BIDS_SYSTEM

    if not bids_with_recyclers:
        return {}

    # Deterministic pre-processing
    scored = compute_bid_scores(
        [dict(b) for b in bids_with_recyclers],  # deep-ish copy
        priority=priority,
    )

    # True highest price
    true_highest = max(b["price"] for b in scored)
    true_highest_id = max(bids_with_recyclers, key=lambda b: b["price"])["bid_id"]
    true_best_id = scored[0]["bid_id"]  # top by combined score

    # Build Gemma input
    bids_for_ai = [
        {
            "bid_id": b["bid_id"],
            "recycler_name": b.get("recycler_name", ""),
            "price": b["price"],
            "pickup_date": b["pickup_date"].isoformat() if isinstance(b["pickup_date"], datetime) else str(b["pickup_date"]),
            "rating": b.get("rating", 4.0),
            "completion_rate": b.get("completion_rate", 0.8),
            "baseline_score": round(b["baseline_score"], 4),
        }
        for b in scored
    ]
    listing_info = {
        "category": listing.category,
        "materials": listing.materials,
        "quantity": listing.quantity,
        "unit": listing.unit,
        "priority": priority,
    }
    user_msg = (
        f"Listing: {json.dumps(listing_info)}\n"
        f"Bids: {json.dumps(bids_for_ai)}\n"
        f"Analyse and recommend the best bid."
    )

    ai_result = await gemma_client.generate_json(
        ANALYZE_BIDS_SYSTEM, user_msg, db=db, skill="analyze_bids"
    )

    # Validate Gemma's claims
    valid_bid_ids = {b["bid_id"] for b in bids_with_recyclers}

    if not ai_result:
        # Full fallback
        return _build_fallback(scored, true_highest, true_highest_id, true_best_id)

    # Validate recommended_id
    if ai_result.get("recommended_id") not in valid_bid_ids:
        logger.warning(
            "Gemma returned invalid recommended_id=%s; overriding with %s",
            ai_result.get("recommended_id"), true_best_id,
        )
        ai_result["recommended_id"] = true_best_id

    # Validate highest_bid (allow 1% tolerance)
    gemma_highest = ai_result.get("highest_bid", 0)
    if abs(gemma_highest - true_highest) / (true_highest + 1e-6) > 0.01:
        logger.warning(
            "Gemma highest_bid=%s wrong; overriding with %s", gemma_highest, true_highest
        )
        ai_result["highest_bid"] = true_highest

    return ai_result


def _build_fallback(scored: List[dict], highest: float, highest_id: int, best_id: int) -> dict:
    """Rule-based fallback if Gemma completely fails."""
    return {
        "highest_bid": highest,
        "best_convenience_bid_id": highest_id,
        "best_overall_bid_id": best_id,
        "recommended_id": best_id,
        "comparison": [
            {
                "bid_id": b["bid_id"],
                "recycler_name": b.get("recycler_name", ""),
                "price": b["price"],
                "pickup_date": str(b.get("pickup_date", "")),
                "score": round(b["baseline_score"], 3),
                "strengths": [],
                "weaknesses": [],
            }
            for b in scored
        ],
        "explanation": "Recommended based on deterministic scoring (AI analysis unavailable).",
        "risks": [],
        "confidence": 0.6,
    }
