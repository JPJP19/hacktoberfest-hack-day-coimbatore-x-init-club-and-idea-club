from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Swap postgresql -> postgresql+asyncpg for async driver
_url = settings.database_url
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    _url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in _url else {},
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


async def create_tables():
    # Import models so they're registered on Base.metadata before create_all
    from app.models import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
