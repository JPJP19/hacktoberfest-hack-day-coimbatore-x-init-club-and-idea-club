from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import create_tables
from app.routers import auth, listings, bids, recyclers, transactions, notifications, admin

app = FastAPI(
    title="WasteConnect API",
    version="1.0.0",
    description="AI-powered waste marketplace connecting households with certified recyclers",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup():
    await create_tables()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "WasteConnect API"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(listings.router, prefix="/listings", tags=["listings"])
app.include_router(bids.router, tags=["bids"])
app.include_router(recyclers.router, prefix="/recyclers", tags=["recyclers"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
