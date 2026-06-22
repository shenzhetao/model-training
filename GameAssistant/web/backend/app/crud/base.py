from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import TypeVar, Generic, Type, Optional, Any
from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """Base CRUD class with common operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: str) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters: Any
    ) -> list[ModelType]:
        """Get multiple records with optional filters."""
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, obj_in: dict) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, id: str, obj_in: dict
    ) -> Optional[ModelType]:
        """Update a record by ID."""
        await db.execute(
            update(self.model).where(self.model.id == id).values(**obj_in)
        )
        await db.flush()
        return await self.get(db, id)

    async def delete(self, db: AsyncSession, id: str) -> bool:
        """Delete a record by ID."""
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.flush()
        return result.rowcount > 0

    async def count(self, db: AsyncSession, **filters: Any) -> int:
        """Count records with optional filters."""
        query = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return len(list(result.scalars().all()))
