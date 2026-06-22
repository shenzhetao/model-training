from sqlalchemy import Column, String, DateTime, Boolean, Integer, BigInteger, Float, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Image(Base):
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(256), nullable=False)
    original_filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    md5_hash = Column(String(32), nullable=False, index=True)
    phash = Column(String(64), nullable=True)
    source = Column(String(16), nullable=False, default="upload", index=True)
    source_video_id = Column(String(36), nullable=True)
    source_video_timestamp = Column(Float, nullable=True)
    uploaded_by = Column(String(36), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_images_source_video", "source_video_id"),
    )

    def __repr__(self):
        return f"<Image(id={self.id}, filename={self.filename}, size={self.file_size})>"
