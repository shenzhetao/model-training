from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserCreateByAdmin
from app.crud.base import CRUDBase
from app.security import get_password_hash


class CRUDUser(CRUDBase[User]):
    """CRUD operations for User model."""

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Create a new user."""
        user_data = user_in.model_dump()
        user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        return await super().create(db, user_data)

    async def create_by_admin(self, db: AsyncSession, user_in: UserCreateByAdmin) -> User:
        """Create a new user by admin with default password."""
        user_data = user_in.model_dump()
        password = user_data.pop("password")
        user_data["password_hash"] = get_password_hash(password)
        user_data["is_password_changed"] = False  # Force password change on first login
        return await super().create(db, user_data)

    async def update(self, db: AsyncSession, id: str, user_in: UserUpdate) -> User | None:
        """Update a user."""
        update_data = user_in.model_dump(exclude_unset=True)
        # Handle password update
        if "password" in update_data and update_data["password"]:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
            update_data["is_password_changed"] = True
        elif "password" in update_data:
            update_data.pop("password")
        return await super().update(db, id, update_data)

    async def update_password_changed(self, db: AsyncSession, id: str) -> User | None:
        """Mark user's password as changed."""
        await db.execute(
            User.__table__.update().where(User.id == id).values(is_password_changed=True)
        )
        await db.flush()
        return await self.get(db, id)


user_crud = CRUDUser(User)
