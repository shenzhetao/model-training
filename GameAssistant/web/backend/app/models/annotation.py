"""ORM models for annotations and related entities."""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, JSON, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AnnotationClass(Base):
    """YOLO class definition — maps class names to integer IDs."""
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=False, default="#3B82F6")
    short_key = Column(String(8), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    yolo_class_id = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_classes_yolo_class_id", "yolo_class_id"),
        Index("idx_classes_sort_order", "sort_order"),
    )

    def __repr__(self):
        return f"<AnnotationClass({self.name}, yolo_id={self.yolo_class_id})>"


class Annotation(Base):
    """Bounding-box annotation on a single image."""
    __tablename__ = "annotations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    class_id = Column(String(36), nullable=False, index=True)
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_width = Column(Float, nullable=False)
    bbox_height = Column(Float, nullable=False)
    conf = Column(Float, nullable=True)
    is_auto_annotated = Column(Boolean, nullable=False, default=False)
    annotated_by = Column(String(36), nullable=True)
    annotated_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    review_status = Column(String(32), nullable=True)
    review_comment = Column(Text, nullable=True)
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_annotations_image_id", "image_id"),
        Index("idx_annotations_class_id", "class_id"),
        Index("idx_annotations_project_id", "project_id"),
        Index("idx_annotations_image_class", "image_id", "class_id"),
    )

    def __repr__(self):
        return f"<Annotation(image={self.image_id}, class={self.class_id})>"

    def to_yolo_line(self, img_width: int, img_height: int) -> str:
        """Convert absolute bbox to YOLO normalized format: `<class_id> <x_center> <y_center> <w> <h>`."""
        cx = (self.bbox_x + self.bbox_width / 2) / img_width
        cy = (self.bbox_y + self.bbox_height / 2) / img_height
        w = self.bbox_width / img_width
        h = self.bbox_height / img_height
        return f"{self.yolo_class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


class AnnotationProject(Base):
    """A named annotation task grouping multiple images."""
    __tablename__ = "annotation_projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    class_ids = Column(JSON, nullable=False, default=list)
    total_images = Column(Integer, nullable=False, default=0)
    annotated_images = Column(Integer, nullable=False, default=0)
    reviewed_images = Column(Integer, nullable=False, default=0)
    assigned_to = Column(String(36), nullable=True)
    reviewed_by = Column(String(36), nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    review_feedback = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_annotation_projects_status", "status"),
        Index("idx_annotation_projects_assigned_to", "assigned_to"),
    )

    def __repr__(self):
        return f"<AnnotationProject({self.name}, status={self.status})>"


class AnnotationProjectImage(Base):
    """Many-to-many link between annotation projects and images."""
    __tablename__ = "annotation_project_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    annotation_project_id = Column(String(36), nullable=False, index=True)
    image_id = Column(String(36), nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_annotation_project_images_project_id", "annotation_project_id"),
        Index("idx_annotation_project_images_image_id", "image_id"),
    )


class AnnotationReview(Base):
    """Review decision for a single image within a project."""
    __tablename__ = "annotation_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    annotation_project_id = Column(String(36), nullable=False, index=True)
    image_id = Column(String(36), nullable=False, index=True)
    review_status = Column(String(32), nullable=False)
    reviewer_id = Column(String(36), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_annotation_reviews_project", "annotation_project_id"),
        Index("idx_annotation_reviews_image", "image_id"),
    )
