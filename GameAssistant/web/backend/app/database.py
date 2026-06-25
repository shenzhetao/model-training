from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import declarative_base
from app.config import settings
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
    """Initialize database tables and apply lightweight schema migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migration: ensure annotations.project_id exists
        try:
            from sqlalchemy import text
            dialect = engine.dialect.name
            if dialect == "sqlite":
                result = await conn.exec_driver_sql("PRAGMA table_info(annotations)")
                columns = {row[1] for row in result.fetchall()}
            else:
                result = await conn.execute(text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME = 'annotations' AND TABLE_SCHEMA = DATABASE()"
                ))
                columns = {row[0] for row in result.fetchall()}

            if "project_id" not in columns:
                if dialect == "sqlite":
                    await conn.exec_driver_sql("ALTER TABLE annotations ADD COLUMN project_id VARCHAR(36)")
                else:
                    await conn.execute(text("ALTER TABLE annotations ADD COLUMN project_id VARCHAR(36)"))
                if dialect == "sqlite":
                    await conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS idx_annotations_project_id ON annotations(project_id)")
                else:
                    await conn.execute(text("CREATE INDEX idx_annotations_project_id ON annotations (project_id)"))

            # Backfill project_id for any existing annotations that are NULL.
            from sqlalchemy import select
            from app.models.annotation import AnnotationProject, AnnotationProjectImage, Annotation
            async with async_session_maker() as session:
                null_anns = (await session.execute(
                    select(Annotation.id, Annotation.image_id).where(Annotation.project_id.is_(None))
                )).all()
                if null_anns:
                    fallback = (await session.execute(
                        select(AnnotationProject.id).order_by(AnnotationProject.created_at.asc()).limit(1)
                    )).scalar_one_or_none()
                    if fallback:
                        for ann_id, img_id in null_anns:
                            pid = (await session.execute(
                                select(AnnotationProjectImage.annotation_project_id)
                                .where(AnnotationProjectImage.image_id == img_id)
                                .order_by(AnnotationProjectImage.assigned_at.asc())
                                .limit(1)
                            )).scalar_one_or_none()
                            await session.execute(
                                text("UPDATE annotations SET project_id = :pid WHERE id = :aid"),
                                {"pid": pid or fallback, "aid": ann_id},
                            )
                        await session.commit()
        except Exception as e:
            logger.warning(f"Annotation project_id migration skipped: {e}")


async def ensure_admin_user():
    """Ensure admin user exists, create if not."""
    from app.models.user import User
    from app.security import get_password_hash
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
