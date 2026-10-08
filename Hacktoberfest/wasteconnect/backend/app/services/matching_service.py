import math
import json
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Recycler, Listing
from app.services.embedding_service import embedding_service
from app.services.gemma_client import gemma_client
from app.services.prompts import MATCH_RERANK_SYSTEM

logger = logging.getLogger(__name__)


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Returns great-circle distance in kilometres."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def find_matching_recyclers(
    listing: Listing,
    db: AsyncSession,
    top_k: int = 5,
) -> List[Tuple]:
    """
    Returns a list of (Recycler, distance_km, combined_score, reason).
    Pipeline: deterministic filter → semantic + proximity scoring → Gemma re-rank.
    """
    result = await db.execute(
        select(Recycler).where(Recycler.verified == True, Recycler.pickup_available == True)
    )
    recyclers = result.scalars().all()

    # Determine if listing is hazardous
    is_hazardous = False
    if listing.ai_analysis:
        hazards = listing.ai_analysis.get("hazards", [])
        is_hazardous = bool(hazards)

    listing_mats = set(m.lower() for m in (listing.materials or []))

    filtered: List[Tuple[Recycler, float]] = []
    for r in recyclers:
        recycler_mats = set(m.lower() for m in (r.materials_supported or []))
        # Require material overlap
        if not listing_mats.intersection(recycler_mats):
            continue
        # Distance check
        dist = haversine(listing.lat, listing.lng, r.lat, r.lng)
        if dist > r.service_radius_km:
            continue
        # Hazard authorization
        if is_hazardous and not r.is_authorized_hazardous:
            continue
        filtered.append((r, dist))

    if not filtered:
        return []

    # Semantic + proximity scoring
    listing_emb = listing.embedding or []
    scored: List[Tuple[Recycler, float, float]] = []
    max_dist = max(d for _, d in filtered) or 1.0
    for r, dist in filtered:
        sem_score = 0.0
        if listing_emb and r.embedding:
            sem_score = embedding_service.cosine_similarity(listing_emb, r.embedding)
        proximity_score = max(0.0, 1.0 - dist / r.service_radius_km)
        combined = 0.6 * sem_score + 0.4 * proximity_score
        scored.append((r, dist, combined))

    scored.sort(key=lambda x: -x[2])
    top5 = scored[:top_k]

    # Gemma re-rank (advisory – failures are silently swallowed)
    try:
        recycler_data = [
            {
                "recycler_id": r.id,
                "name": r.name,
                "materials": r.materials_supported,
                "rating": r.rating,
                "distance_km": round(dist, 2),
                "completed": r.completed_pickups,
            }
            for r, dist, _ in top5
        ]
        listing_info = {
            "category": listing.category,
            "materials": listing.materials,
            "description": listing.description,
        }
        user_msg = (
            f"Listing: {json.dumps(listing_info)}\n"
            f"Candidates: {json.dumps(recycler_data)}\n"
            f"Return ranked_recyclers JSON."
        )
        rerank_result = await gemma_client.generate_json(
            MATCH_RERANK_SYSTEM, user_msg, db=db, skill="match_rerank"
        )
        if rerank_result and "ranked_recyclers" in rerank_result:
            id_order = [item["recycler_id"] for item in rerank_result["ranked_recyclers"]]
            id_reasons = {
                item["recycler_id"]: item.get("reason", "")
                for item in rerank_result["ranked_recyclers"]
            }
            top5_dict = {r.id: (r, dist, score) for r, dist, score in top5}
            reranked = [
                (top5_dict[rid][0], top5_dict[rid][1], top5_dict[rid][2], id_reasons.get(rid, ""))
                for rid in id_order
                if rid in top5_dict
            ]
            # Append any recyclers not returned by Gemma at the end
            returned_ids = set(id_order)
            for r, dist, score in top5:
                if r.id not in returned_ids:
                    reranked.append((r, dist, score, ""))
            return reranked
    except Exception as exc:
        logger.warning("Gemma re-rank failed, using deterministic order: %s", exc)

    return [(r, dist, score, "") for r, dist, score in top5]
