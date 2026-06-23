from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.models.user import User
from app.security import get_password_hash
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DB_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=False,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_admin_user():
    """Ensure admin user exists, create if not."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin is None:
            admin_user = User(
                id=settings.ADMIN_USERNAME,  # Use fixed ID for consistency
                username=settings.ADMIN_USERNAME,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                email=settings.ADMIN_EMAIL,
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            logger.info(
                f"Admin user created: username={settings.ADMIN_USERNAME}, "
                f"password={settings.ADMIN_PASSWORD} (change in production!)"
            )
        else:
            logger.info(f"Admin user already exists: username={settings.ADMIN_USERNAME}")
