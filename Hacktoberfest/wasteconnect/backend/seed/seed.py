"""
Seed script for WasteConnect.
Creates 8 recyclers, 2 test users, and demo copper cable listing with 3 bids.
Can be run standalone: python -m seed.seed
or called from admin router: await run_seed(db)
"""
import asyncio
import sys
import os

# Ensure project root is on path when running standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import SessionLocal, create_tables
from app.models.models import User, Recycler, Listing, Bid
from app.auth.auth import get_password_hash
from app.services.embedding_service import embedding_service

RECYCLERS_DATA = [
    {
        "name": "GreenMetal Recyclers",
        "lat": 12.9716, "lng": 77.5946,
        "materials": ["copper", "aluminum", "brass", "steel"],
        "radius": 25, "verified": True, "hazardous": True,
        "rating": 4.8, "pickups": 234,
        "profile_text": "Specialized in ferrous and non-ferrous metal recycling. 15+ years experience in copper, aluminum, brass and steel. Licensed hazardous waste handler.",
        "email": "contact@greenmetal.in", "phone": "+91-9876543210",
    },
    {
        "name": "EcoPlastics Hub",
        "lat": 12.9352, "lng": 77.6245,
        "materials": ["plastic", "hdpe", "pvc", "pet"],
        "radius": 20, "verified": True, "hazardous": False,
        "rating": 4.5, "pickups": 189,
        "profile_text": "Expert plastic recycling for HDPE, PVC, PET and mixed plastics. ISO certified. Serving residential and industrial clients.",
        "email": "info@ecoplastics.in", "phone": "+91-9876543211",
    },
    {
        "name": "PaperCycle India",
        "lat": 13.0012, "lng": 77.5850,
        "materials": ["paper", "cardboard", "newspaper", "books"],
        "radius": 30, "verified": True, "hazardous": False,
        "rating": 4.3, "pickups": 156,
        "profile_text": "Paper and cardboard recycling specialists. Handle bulk quantities from offices, schools, and warehouses.",
        "email": "hello@papercycle.in", "phone": "+91-9876543212",
    },
    {
        "name": "TechRecycle Pro",
        "lat": 12.9141, "lng": 77.6012,
        "materials": ["electronics", "copper", "circuit_boards", "batteries"],
        "radius": 35, "verified": True, "hazardous": True,
        "rating": 4.7, "pickups": 312,
        "profile_text": "E-waste and electronic recycling with data destruction. Authorized handler for batteries and electronic hazardous materials.",
        "email": "ops@techrecycle.in", "phone": "+91-9876543213",
    },
    {
        "name": "GlassWorks Recycling",
        "lat": 12.9500, "lng": 77.6800,
        "materials": ["glass", "bottles", "containers"],
        "radius": 15, "verified": True, "hazardous": False,
        "rating": 4.2, "pickups": 89,
        "profile_text": "Glass bottle and container recycling. Serving restaurants, hotels and households.",
        "email": "pick@glassworks.in", "phone": "+91-9876543214",
    },
    {
        "name": "AllMaterials Corp",
        "lat": 12.9850, "lng": 77.5500,
        "materials": ["copper", "aluminum", "plastic", "paper", "steel", "electronics"],
        "radius": 40, "verified": True, "hazardous": True,
        "rating": 4.6, "pickups": 445,
        "profile_text": "Full-service recycling for all material types. Large fleet, competitive prices, fastest pickup in the city.",
        "email": "contact@allmaterials.in", "phone": "+91-9876543215",
    },
    {
        "name": "SafeDispose Solutions",
        "lat": 13.0200, "lng": 77.6100,
        "materials": ["batteries", "chemicals", "paint", "oil"],
        "radius": 50, "verified": True, "hazardous": True,
        "rating": 4.9, "pickups": 178,
        "profile_text": "Certified hazardous waste disposal. Batteries, chemicals, solvents, paint disposal with full compliance documentation.",
        "email": "safe@safedispose.in", "phone": "+91-9876543216",
    },
    {
        "name": "TextileReborn",
        "lat": 12.9300, "lng": 77.5200,
        "materials": ["textile", "clothes", "fabric", "cotton"],
        "radius": 20, "verified": True, "hazardous": False,
        "rating": 4.1, "pickups": 67,
        "profile_text": "Textile and clothing recycling. Upcycling and repurposing fabric waste.",
        "email": "reborn@textilereborn.in", "phone": "+91-9876543217",
    },
]


async def run_seed(db: AsyncSession):
    """Insert seed data. Idempotent: skips if admin user already exists."""

    # Check if already seeded
    existing = await db.execute(select(User).where(User.email == "admin@wasteconnect.in"))
    if existing.scalar_one_or_none():
        print("Seed already run. Skipping.")
        return

    # --- Test users ---
    admin_user = User(
        email="admin@wasteconnect.in",
        password_hash=get_password_hash("admin123"),
        full_name="WasteConnect Admin",
        role="admin",
    )
    demo_user = User(
        email="rahul@example.com",
        password_hash=get_password_hash("test1234"),
        full_name="Rahul Sharma",
        phone="+91-9000000001",
        role="user",
    )
    db.add_all([admin_user, demo_user])
    await db.flush()

    # --- Recycler users + profiles ---
    recycler_users: list[User] = []
    recycler_profiles: list[Recycler] = []

    for i, rd in enumerate(RECYCLERS_DATA):
        ru = User(
            email=rd["email"],
            password_hash=get_password_hash("recycler123"),
            full_name=rd["name"],
            role="recycler",
        )
        db.add(ru)
        await db.flush()

        try:
            emb = embedding_service.encode(rd["profile_text"])
        except Exception:
            emb = None

        rp = Recycler(
            user_id=ru.id,
            name=rd["name"],
            lat=rd["lat"],
            lng=rd["lng"],
            materials_supported=rd["materials"],
            service_radius_km=rd["radius"],
            verified=rd["verified"],
            is_authorized_hazardous=rd["hazardous"],
            rating=rd["rating"],
            completed_pickups=rd["pickups"],
            profile_text=rd["profile_text"],
            embedding=emb,
            contact_email=rd["email"],
            contact_phone=rd["phone"],
            pickup_available=True,
        )
        db.add(rp)
        recycler_users.append(ru)
        recycler_profiles.append(rp)

    await db.flush()

    # --- Demo listing: 10 kg copper cables in Bangalore ---
    listing_text = "10 kg copper cables, stripped, good condition"
    try:
        listing_emb = embedding_service.encode(f"Metals copper {listing_text}")
    except Exception:
        listing_emb = None

    copper_listing = Listing(
        user_id=demo_user.id,
        category="Metals",
        materials=["copper"],
        description=listing_text,
        quantity=10.0,
        unit="kg",
        lat=12.9600,
        lng=77.5900,
        status="open",
        ai_analysis={
            "category": "Metals",
            "materials": ["copper"],
            "hazards": [],
            "condition": "Good",
            "recyclability": "High",
            "confidence": 0.92,
            "clarifying_questions": [],
        },
        embedding=listing_emb,
    )
    db.add(copper_listing)
    await db.flush()

    # --- 3 demo bids (₹3800, ₹4100, ₹3950) ---
    bids_config = [
        {"recycler_idx": 0, "price": 3800.0},   # GreenMetal
        {"recycler_idx": 5, "price": 4100.0},   # AllMaterials Corp
        {"recycler_idx": 3, "price": 3950.0},   # TechRecycle Pro
    ]
    for bc in bids_config:
        recycler = recycler_profiles[bc["recycler_idx"]]
        bid = Bid(
            listing_id=copper_listing.id,
            recycler_id=recycler.id,
            price=bc["price"],
            pickup_date=datetime.utcnow() + timedelta(days=2),
            conditions="Payment via bank transfer after weighing.",
            status="pending",
        )
        db.add(bid)

    await db.commit()
    print(f"Seed complete: admin, demo user, {len(RECYCLERS_DATA)} recyclers, 1 listing, 3 bids.")


async def main():
    await create_tables()
    async with SessionLocal() as db:
        await run_seed(db)


if __name__ == "__main__":
    asyncio.run(main())
