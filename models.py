"""
Database models for the Slide Extractor application.
Provides persistent storage for jobs, slides, and metadata.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Text, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional, Dict, Any, List
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Job(db.Model):
    """Model for extraction jobs with full lifecycle tracking."""
    
    __tablename__ = 'jobs'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Job identification
    job_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Job configuration
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    output_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Processing options
    adaptive_sampling: Mapped[bool] = mapped_column(Boolean, default=True)
    extract_content: Mapped[bool] = mapped_column(Boolean, default=True)
    organize_slides: Mapped[bool] = mapped_column(Boolean, default=True)
    generate_pdf: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_transcription: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_ocr_enhancement: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_concept_extraction: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_slide_descriptions: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Job status and progress
    status: Mapped[str] = mapped_column(String(50), default='pending', index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Results
    slides_count: Mapped[int] = mapped_column(Integer, default=0)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    study_guide_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Metadata (renamed to avoid SQLAlchemy reserved word)
    job_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Processing statistics
    processing_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    file_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            'id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'error': self.error,
            'slides_count': self.slides_count,
            'has_pdf': bool(self.pdf_path),
            'has_study_guide': bool(self.study_guide_path),
            'has_transcription': self.enable_transcription,
            'has_concepts': self.enable_concept_extraction,
            'has_descriptions': self.enable_slide_descriptions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processing_time': self.processing_time,
            'video_url': self.video_url
        }
    
    def update_status(self, status: str, progress: float = None, message: str = None, error: str = None):
        """Update job status with optional progress and message."""
        self.status = status
        if progress is not None:
            self.progress = progress
        if message is not None:
            self.message = message
        if error is not None:
            self.error = error
        
        # Set timestamps based on status
        if status == 'processing' and not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        elif status in ['completed', 'failed']:
            self.completed_at = datetime.now(timezone.utc)
            if self.started_at:
                self.processing_time = (self.completed_at - self.started_at).total_seconds()

class Slide(db.Model):
    """Model for individual slides extracted from videos."""
    
    __tablename__ = 'slides'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign key to job
    job_id: Mapped[str] = mapped_column(String(50), db.ForeignKey('jobs.job_id'), nullable=False, index=True)
    
    # Slide identification
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    slide_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # File paths
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Timing information
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)  # seconds
    duration: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    
    # Content
    title: Mapped[Optional[str]] = mapped_column(String(500))
    content: Mapped[Optional[str]] = mapped_column(Text)
    slide_type: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Analysis results
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON)
    concepts: Mapped[Optional[List[str]]] = mapped_column(JSON)
    transcription: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Quality metrics
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Metadata (renamed to avoid SQLAlchemy reserved word)
    slide_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert slide to dictionary for API responses."""
        return {
            'filename': self.filename,
            'slide_number': self.slide_number,
            'path': self.image_path,
            'thumbnail_path': self.thumbnail_path,
            'timestamp': self.timestamp,
            'duration': self.duration,
            'title': self.title,
            'content': self.content,
            'type': self.slide_type,
            'keywords': self.keywords or [],
            'concepts': self.concepts or [],
            'transcription': self.transcription,
            'description': self.description,
            'ocr_confidence': self.ocr_confidence,
            'similarity_score': self.similarity_score,
            'metadata': self.slide_metadata or {}
        }

class JobMetrics(db.Model):
    """Model for tracking job processing metrics and analytics."""
    
    __tablename__ = 'job_metrics'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Foreign key to job
    job_id: Mapped[str] = mapped_column(String(50), db.ForeignKey('jobs.job_id'), nullable=False, index=True)
    
    # Performance metrics
    download_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    extraction_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    analysis_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    total_processing_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    
    # Resource usage
    peak_memory_usage: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float)  # percentage
    disk_usage: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    
    # Video metrics
    video_duration: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    video_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    video_resolution: Mapped[Optional[str]] = mapped_column(String(50))
    video_fps: Mapped[Optional[float]] = mapped_column(Float)
    
    # Processing results
    frames_processed: Mapped[Optional[int]] = mapped_column(Integer)
    slides_extracted: Mapped[Optional[int]] = mapped_column(Integer)
    duplicates_removed: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Quality metrics
    average_ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)
    average_similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Error tracking
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for API responses."""
        return {
            'job_id': self.job_id,
            'download_time': self.download_time,
            'extraction_time': self.extraction_time,
            'analysis_time': self.analysis_time,
            'total_processing_time': self.total_processing_time,
            'peak_memory_usage': self.peak_memory_usage,
            'cpu_usage': self.cpu_usage,
            'video_duration': self.video_duration,
            'video_size': self.video_size,
            'frames_processed': self.frames_processed,
            'slides_extracted': self.slides_extracted,
            'duplicates_removed': self.duplicates_removed,
            'average_ocr_confidence': self.average_ocr_confidence,
            'errors_count': self.errors_count,
            'warnings_count': self.warnings_count
        }
