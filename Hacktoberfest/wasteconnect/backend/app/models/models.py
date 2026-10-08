from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user|recycler|admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    recycler_profile: Mapped[Optional["Recycler"]] = relationship("Recycler", back_populates="user", uselist=False)
    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user")


class Recycler(Base):
    __tablename__ = "recyclers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    materials_supported: Mapped[Optional[List]] = mapped_column(JSON, default=list)
    service_radius_km: Mapped[float] = mapped_column(Float, default=20.0)
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    completed_pickups: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_authorized_hazardous: Mapped[bool] = mapped_column(Boolean, default=False)
    pickup_available: Mapped[bool] = mapped_column(Boolean, default=True)
    profile_text: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    contact_phone: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="recycler_profile")
    bids: Mapped[List["Bid"]] = relationship("Bid", back_populates="recycler")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    materials: Mapped[Optional[List]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), default="kg")
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lng: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="open")  # draft|open|accepted|collected|completed|restricted
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    embedding: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="listings")
    bids: Mapped[List["Bid"]] = relationship("Bid", back_populates="listing")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="listing", uselist=False)


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.id"), nullable=False)
    recycler_id: Mapped[int] = mapped_column(Integer, ForeignKey("recyclers.id"), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # INR
    pickup_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending|accepted|rejected|withdrawn
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listing: Mapped["Listing"] = relationship("Listing", back_populates="bids")
    recycler: Mapped["Recycler"] = relationship("Recycler", back_populates="bids")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="bid", uselist=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.id"), nullable=False)
    bid_id: Mapped[int] = mapped_column(Integer, ForeignKey("bids.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    recycler_id: Mapped[int] = mapped_column(Integer, ForeignKey("recyclers.id"), nullable=False)
    agreed_price: Mapped[float] = mapped_column(Float, nullable=False)
    confirmed_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="accepted")
    # accepted|pickup_scheduled|collected|quantity_confirmed|paid|recycled
    qr_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # base64 PNG
    payment_receipt: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recycler_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dispute_suggestion: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    listing: Mapped["Listing"] = relationship("Listing", back_populates="transaction")
    bid: Mapped["Bid"] = relationship("Bid", back_populates="transaction")

    @property
    def listing_lat(self) -> float | None:
        return self.listing.lat if self.listing else None

    @property
    def listing_lng(self) -> float | None:
        return self.listing.lng if self.listing else None

    @property
    def recycler_lat(self) -> float | None:
        return self.bid.recycler.lat if self.bid and self.bid.recycler else None

    @property
    def recycler_lng(self) -> float | None:
        return self.bid.recycler.lng if self.bid and self.bid.recycler else None


class AILog(Base):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    skill: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_system: Mapped[str] = mapped_column(Text, default="")
    prompt_user: Mapped[str] = mapped_column(Text, default="")
    response_raw: Mapped[str] = mapped_column(Text, default="")
    response_parsed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="notifications")
