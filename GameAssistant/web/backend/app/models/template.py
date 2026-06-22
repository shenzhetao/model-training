"""ORM models for templates and template classes."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, BigInteger
from sqlalchemy.sql import func
from app.database import Base
import uuid


class TemplateClass(Base):
    """UI element class for template matching (e.g. btn_attack, btn_skill)."""
    __tablename__ = "template_classes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    class_name = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)
    default_threshold = Column(Float, nullable=False, default=0.8)
    icon = Column(String(64), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<TemplateClass({self.class_name})>"


class Template(Base):
    """A single template image for template matching."""
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    class_id = Column(String(36), nullable=True)
    class_name = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    roi_x = Column(Integer, nullable=True)
    roi_y = Column(Integer, nullable=True)
    roi_width = Column(Integer, nullable=True)
    roi_height = Column(Integer, nullable=True)
    match_threshold = Column(Float, nullable=False, default=0.8)
    is_active = Column(Boolean, nullable=False, default=True)
    trained_at = Column(DateTime, nullable=True)
    uploaded_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Template({self.class_name}/{self.name}, {self.width}x{self.height})>"
