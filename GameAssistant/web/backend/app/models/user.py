from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="annotator")
    email = Column(String(128), unique=True, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_users_role", "role"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
