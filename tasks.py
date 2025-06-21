"""
Celery tasks for asynchronous slide extraction and processing.
Handles video processing, content analysis, and file generation in background workers.
"""

import os
import time
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from celery import current_task
from celery.exceptions import Retry
from celery_config import make_celery
from job_storage import job_storage
from models import db, Job, Slide, JobMetrics

# Import processing modules
from enhanced_slide_extractor import EnhancedSlideExtractor
from content_analyzer import ContentAnalyzer
from gemini_transcription import GeminiTranscriptionService
from slide_description_generator import SlideDescriptionGenerator

logger = logging.getLogger(__name__)

# Create Celery instance
celery = make_celery()

@celery.task(bind=True, name='tasks.extract_slides_task')
def extract_slides_task(self, job_id: str, params: Dict[str, Any]):
    """
    Main task for extracting slides from video.
    
    Args:
        job_id: Unique job identifier
        params: Extraction parameters
    """
    start_time = time.time()
    
    try:
        # Update job status
        job_storage.update_job_status(job_id, 'processing', 0, 'Starting slide extraction')
        
        # Create extractor
        extractor = EnhancedSlideExtractor(
            video_url=params['video_url'],
            output_dir=params['output_dir'],
            adaptive_sampling=params.get('adaptive_sampling', True),
            extract_content=params.get('extract_content', True),
            organize_slides=params.get('organize_slides', True),
            callback=lambda msg: update_task_progress(job_id, None, msg)
        )
        
        # Set AI features
        extractor.gemini_api_key = params.get('gemini_api_key', '')
        extractor.enable_transcription = params.get('enable_transcription', False)
        extractor.enable_ocr_enhancement = params.get('enable_ocr_enhancement', False)
        extractor.enable_concept_extraction = params.get('enable_concept_extraction', False)
        extractor.enable_slide_descriptions = params.get('enable_slide_descriptions', False)
        
        # Extract slides
        update_task_progress(job_id, 20, 'Extracting slides from video')
        success = extractor.extract_slides()
        
        if not success:
            raise Exception('Slide extraction failed')
        
        # Get extracted slides
        update_task_progress(job_id, 70, 'Processing extracted slides')
        slides = extractor.get_slides()
        
        # Store slides in database
        store_slides_in_db(job_id, slides)
        
        # Update job with results
        job_storage.update_job_results(
            job_id,
            slides_count=len(slides)
        )
        
        # Generate PDF if requested
        pdf_path = None
        if params.get('generate_pdf', True):
            update_task_progress(job_id, 80, 'Generating PDF')
            pdf_path = extractor.convert_slides_to_pdf()
            if pdf_path:
                job_storage.update_job_results(job_id, pdf_path=pdf_path)
        
        # Generate study guide if enhanced features are available
        study_guide_path = None
        if params.get('extract_content', True):
            update_task_progress(job_id, 90, 'Generating study guide')
            study_guide_path = generate_study_guide(job_id, extractor)
            if study_guide_path:
                job_storage.update_job_results(job_id, study_guide_path=study_guide_path)
        
        # Record metrics
        processing_time = time.time() - start_time
        record_job_metrics(job_id, extractor, processing_time)
        
        # Complete job
        update_task_progress(job_id, 100, 'Extraction completed successfully')
        job_storage.update_job_status(job_id, 'completed')
        
        return {
            'job_id': job_id,
            'status': 'completed',
            'slides_count': len(slides),
            'pdf_path': pdf_path,
            'study_guide_path': study_guide_path,
            'processing_time': processing_time
        }
        
    except Exception as e:
        error_msg = f"Error in slide extraction: {str(e)}"
        logger.error(f"Task {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        job_storage.update_job_status(job_id, 'failed', error=error_msg)
        
        # Record failure metrics
        processing_time = time.time() - start_time
        record_job_metrics(job_id, None, processing_time, error=error_msg)
        
        raise

@celery.task(bind=True, name='tasks.analyze_content_task')
def analyze_content_task(self, job_id: str, slide_data: Dict[str, Any]):
    """
    Task for analyzing slide content with AI.
    
    Args:
        job_id: Job identifier
        slide_data: Slide content and metadata
    """
    try:
        job_storage.update_job_status(job_id, 'analyzing', message='Analyzing slide content')
        
        # Initialize content analyzer
        analyzer = ContentAnalyzer()
        
        # Analyze content
        analysis_result = analyzer.analyze_slide_content(
            slide_data.get('content', ''),
            slide_type=slide_data.get('type'),
            ocr_data=slide_data.get('ocr_data')
        )
        
        # Store analysis results
        slide = Slide.query.filter_by(
            job_id=job_id,
            filename=slide_data['filename']
        ).first()
        
        if slide:
            slide.keywords = analysis_result.get('keywords', [])
            slide.concepts = analysis_result.get('key_concepts', [])
            slide.description = analysis_result.get('summary', '')
            slide.metadata = analysis_result
            db.session.commit()
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Content analysis failed for job {job_id}: {e}")
        raise

@celery.task(bind=True, name='tasks.transcribe_audio_task')
def transcribe_audio_task(self, job_id: str, video_path: str, gemini_api_key: str):
    """
    Task for transcribing video audio.
    
    Args:
        job_id: Job identifier
        video_path: Path to video file
        gemini_api_key: Gemini API key
    """
    try:
        job_storage.update_job_status(job_id, 'transcribing', message='Transcribing audio')
        
        # Initialize transcription service
        transcription_service = GeminiTranscriptionService(api_key=gemini_api_key)
        
        # Extract audio
        output_dir = os.path.dirname(video_path)
        audio_path = transcription_service.extract_audio(video_path, output_dir)
        
        if not audio_path:
            raise Exception('Failed to extract audio from video')
        
        # Transcribe audio
        transcription_data = transcription_service.transcribe(audio_path)
        
        if not transcription_data:
            raise Exception('Failed to transcribe audio')
        
        # Store transcription in job metadata
        job = Job.query.filter_by(job_id=job_id).first()
        if job:
            if not job.metadata:
                job.metadata = {}
            job.metadata['transcription'] = transcription_data
            db.session.commit()
        
        return transcription_data
        
    except Exception as e:
        logger.error(f"Transcription failed for job {job_id}: {e}")
        raise

@celery.task(bind=True, name='tasks.generate_pdf_task')
def generate_pdf_task(self, job_id: str, slides_data: list):
    """
    Task for generating PDF from slides.
    
    Args:
        job_id: Job identifier
        slides_data: List of slide data
    """
    try:
        job_storage.update_job_status(job_id, 'generating', message='Generating PDF')
        
        # This would integrate with your PDF generation logic
        # For now, return a placeholder
        pdf_path = f"/path/to/generated/{job_id}.pdf"
        
        job_storage.update_job_results(job_id, pdf_path=pdf_path)
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"PDF generation failed for job {job_id}: {e}")
        raise

@celery.task(name='tasks.cleanup_old_jobs_task')
def cleanup_old_jobs_task():
    """Periodic task to clean up old completed jobs."""
    try:
        cleaned_count = job_storage.cleanup_completed_jobs(max_age_hours=24)
        logger.info(f"Cleaned up {cleaned_count} old jobs")
        return cleaned_count
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise

@celery.task(name='tasks.health_check_task')
def health_check_task():
    """Periodic health check task."""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check Redis connection
        if job_storage.redis_client:
            job_storage.redis_client.ping()
        
        return {'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}

# Helper functions

def update_task_progress(job_id: str, progress: Optional[float], message: str):
    """Update task progress and message."""
    if current_task:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': progress, 'message': message}
        )
    
    job_storage.update_job_status(job_id, 'processing', progress, message)

def store_slides_in_db(job_id: str, slides: list):
    """Store extracted slides in database."""
    try:
        for i, slide_data in enumerate(slides):
            slide = Slide(
                job_id=job_id,
                filename=slide_data.get('filename', f'slide_{i+1}'),
                slide_number=i + 1,
                image_path=slide_data.get('path', ''),
                timestamp=slide_data.get('timestamp', 0),
                title=slide_data.get('title', ''),
                content=slide_data.get('content', ''),
                slide_type=slide_data.get('type', 'unknown'),
                keywords=slide_data.get('keywords', []),
                transcription=slide_data.get('transcription', ''),
                metadata=slide_data.get('analysis', {})
            )
            db.session.add(slide)
        
        db.session.commit()
        logger.info(f"Stored {len(slides)} slides for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error storing slides for job {job_id}: {e}")
        db.session.rollback()
        raise

def generate_study_guide(job_id: str, extractor) -> Optional[str]:
    """Generate study guide from extracted content."""
    try:
        # Get enhanced metadata
        metadata = extractor.get_metadata()
        
        # Initialize content analyzer
        analyzer = ContentAnalyzer()
        
        # Generate study guide
        study_guide_path = os.path.join(extractor.base_extractor.output_dir, 'study_guide.md')
        study_guide = analyzer.generate_study_guide(metadata, output_file=study_guide_path)
        
        return study_guide_path if os.path.exists(study_guide_path) else None
        
    except Exception as e:
        logger.error(f"Error generating study guide for job {job_id}: {e}")
        return None

def record_job_metrics(job_id: str, extractor, processing_time: float, error: str = None):
    """Record job processing metrics."""
    try:
        metrics = JobMetrics(
            job_id=job_id,
            total_processing_time=processing_time,
            errors_count=1 if error else 0
        )
        
        if extractor:
            # Add extractor-specific metrics
            if hasattr(extractor, 'base_extractor'):
                base = extractor.base_extractor
                if hasattr(base, 'slides_metadata'):
                    metrics.slides_extracted = len(base.slides_metadata)
        
        db.session.add(metrics)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error recording metrics for job {job_id}: {e}")
        db.session.rollback()
