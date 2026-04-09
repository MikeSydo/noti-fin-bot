import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def init_db():
    try:
        async with engine.begin() as conn:
            logger.info("Initializing database schema...")
            # Import all models so Base knows about them before creation
            import models.user  # noqa: F401
            # Base.metadata.create_all is now handled by Alembic migrations
            logger.info("Database connection tested (schema managed by Alembic).")
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")
        raise