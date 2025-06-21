"""
Job storage service using Redis for caching and PostgreSQL for persistence.
Provides high-performance job tracking with fallback to database.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import redis
from models import db, Job, Slide, JobMetrics

logger = logging.getLogger(__name__)

class JobStorageService:
    """
    Hybrid job storage service using Redis for fast access and PostgreSQL for persistence.
    """
    
    def __init__(self, redis_url: str = None, enable_redis: bool = True):
        """
        Initialize the job storage service.
        
        Args:
            redis_url: Redis connection URL
            enable_redis: Whether to use Redis for caching
        """
        self.enable_redis = enable_redis
        self.redis_client = None
        
        # Initialize Redis if enabled
        if self.enable_redis:
            try:
                redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to database only.")
                self.enable_redis = False
                self.redis_client = None
        
        # Redis key prefixes
        self.JOB_PREFIX = "job:"
        self.JOB_STATUS_PREFIX = "job_status:"
        self.JOB_PROGRESS_PREFIX = "job_progress:"
        self.JOB_LIST_KEY = "active_jobs"
        
        # Cache TTL (Time To Live) in seconds
        self.CACHE_TTL = 3600  # 1 hour
        self.ACTIVE_JOB_TTL = 86400  # 24 hours
    
    def create_job(self, job_data: Dict[str, Any]) -> str:
        """
        Create a new job in both Redis and database.

        Args:
            job_data: Job configuration and metadata

        Returns:
            job_id: Unique job identifier
        """
        try:
            # Try to create job in database
            try:
                job = Job(
                    job_id=job_data['job_id'],
                    video_url=job_data['video_url'],
                    output_dir=job_data['output_dir'],
                    adaptive_sampling=job_data.get('adaptive_sampling', True),
                    extract_content=job_data.get('extract_content', True),
                    organize_slides=job_data.get('organize_slides', True),
                    generate_pdf=job_data.get('generate_pdf', True),
                    enable_transcription=job_data.get('enable_transcription', False),
                    enable_ocr_enhancement=job_data.get('enable_ocr_enhancement', False),
                    enable_concept_extraction=job_data.get('enable_concept_extraction', False),
                    enable_slide_descriptions=job_data.get('enable_slide_descriptions', False),
                    status='pending',
                    job_metadata=job_data.get('metadata', {})
                )

                db.session.add(job)
                db.session.commit()
                logger.info(f"Created job {job_data['job_id']} in database")

            except Exception as db_error:
                logger.warning(f"Failed to create job in database: {db_error}")
                db.session.rollback()
                logger.info("Continuing with Redis/memory storage only")

            # Cache in Redis if available
            if self.redis_client:
                try:
                    job_key = f"{self.JOB_PREFIX}{job_data['job_id']}"
                    self.redis_client.hset(job_key, mapping=job_data)
                    self.redis_client.expire(job_key, self.CACHE_TTL)

                    # Add to active jobs list
                    self.redis_client.sadd(self.JOB_LIST_KEY, job_data['job_id'])
                    self.redis_client.expire(self.JOB_LIST_KEY, self.ACTIVE_JOB_TTL)
                    logger.info(f"Cached job {job_data['job_id']} in Redis")
                except Exception as redis_error:
                    logger.warning(f"Failed to cache job in Redis: {redis_error}")

            logger.info(f"Created job {job_data['job_id']}")
            return job_data['job_id']

        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data from Redis cache or database.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job data dictionary or None if not found
        """
        try:
            # Try Redis first if available
            if self.redis_client:
                job_key = f"{self.JOB_PREFIX}{job_id}"
                cached_job = self.redis_client.hgetall(job_key)
                if cached_job:
                    # Convert string values back to appropriate types
                    return self._deserialize_job_data(cached_job)
            
            # Fallback to database
            job = Job.query.filter_by(job_id=job_id).first()
            if job:
                job_data = job.to_dict()
                
                # Cache in Redis for future requests
                if self.redis_client:
                    job_key = f"{self.JOB_PREFIX}{job_id}"
                    serialized_data = self._serialize_job_data(job_data)
                    self.redis_client.hset(job_key, mapping=serialized_data)
                    self.redis_client.expire(job_key, self.CACHE_TTL)
                
                return job_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: str, progress: float = None, 
                         message: str = None, error: str = None) -> bool:
        """
        Update job status in both Redis and database.
        
        Args:
            job_id: Job identifier
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            error: Error message if any
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update database
            job = Job.query.filter_by(job_id=job_id).first()
            if not job:
                logger.warning(f"Job {job_id} not found in database")
                return False
            
            job.update_status(status, progress, message, error)
            db.session.commit()
            
            # Update Redis cache
            if self.redis_client:
                job_key = f"{self.JOB_PREFIX}{job_id}"
                updates = {'status': status}
                
                if progress is not None:
                    updates['progress'] = str(progress)
                if message is not None:
                    updates['message'] = message
                if error is not None:
                    updates['error'] = error
                
                self.redis_client.hset(job_key, mapping=updates)
                
                # Update quick status cache
                status_key = f"{self.JOB_STATUS_PREFIX}{job_id}"
                self.redis_client.set(status_key, status, ex=self.CACHE_TTL)
                
                if progress is not None:
                    progress_key = f"{self.JOB_PROGRESS_PREFIX}{job_id}"
                    self.redis_client.set(progress_key, progress, ex=self.CACHE_TTL)
            
            logger.info(f"Updated job {job_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} status: {e}")
            db.session.rollback()
            return False
    
    def update_job_results(self, job_id: str, slides_count: int = None, 
                          pdf_path: str = None, study_guide_path: str = None) -> bool:
        """
        Update job results in both Redis and database.
        
        Args:
            job_id: Job identifier
            slides_count: Number of slides extracted
            pdf_path: Path to generated PDF
            study_guide_path: Path to study guide
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update database
            job = Job.query.filter_by(job_id=job_id).first()
            if not job:
                return False
            
            if slides_count is not None:
                job.slides_count = slides_count
            if pdf_path is not None:
                job.pdf_path = pdf_path
            if study_guide_path is not None:
                job.study_guide_path = study_guide_path
            
            db.session.commit()
            
            # Update Redis cache
            if self.redis_client:
                job_key = f"{self.JOB_PREFIX}{job_id}"
                updates = {}
                
                if slides_count is not None:
                    updates['slides_count'] = str(slides_count)
                if pdf_path is not None:
                    updates['pdf_path'] = pdf_path
                if study_guide_path is not None:
                    updates['study_guide_path'] = study_guide_path
                
                if updates:
                    self.redis_client.hset(job_key, mapping=updates)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating job {job_id} results: {e}")
            db.session.rollback()
            return False
    
    def get_active_jobs(self) -> List[str]:
        """
        Get list of active job IDs.
        
        Returns:
            List of active job IDs
        """
        try:
            # Try Redis first
            if self.redis_client:
                active_jobs = self.redis_client.smembers(self.JOB_LIST_KEY)
                if active_jobs:
                    return list(active_jobs)
            
            # Fallback to database
            active_statuses = ['pending', 'processing', 'downloading', 'extracting', 'analyzing']
            jobs = Job.query.filter(Job.status.in_(active_statuses)).all()
            return [job.job_id for job in jobs]
            
        except Exception as e:
            logger.error(f"Error getting active jobs: {e}")
            return []
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed jobs from Redis cache.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        if not self.redis_client:
            return 0
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Get completed jobs from database
            completed_jobs = Job.query.filter(
                Job.status.in_(['completed', 'failed']),
                Job.completed_at < cutoff_time
            ).all()
            
            cleaned_count = 0
            for job in completed_jobs:
                job_key = f"{self.JOB_PREFIX}{job.job_id}"
                status_key = f"{self.JOB_STATUS_PREFIX}{job.job_id}"
                progress_key = f"{self.JOB_PROGRESS_PREFIX}{job.job_id}"
                
                # Remove from Redis
                self.redis_client.delete(job_key, status_key, progress_key)
                self.redis_client.srem(self.JOB_LIST_KEY, job.job_id)
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old jobs from Redis")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up jobs: {e}")
            return 0
    
    def _serialize_job_data(self, job_data: Dict[str, Any]) -> Dict[str, str]:
        """Convert job data to Redis-compatible string format."""
        serialized = {}
        for key, value in job_data.items():
            if value is None:
                continue
            elif isinstance(value, (dict, list)):
                serialized[key] = json.dumps(value)
            else:
                serialized[key] = str(value)
        return serialized
    
    def _deserialize_job_data(self, cached_data: Dict[str, str]) -> Dict[str, Any]:
        """Convert Redis string data back to appropriate types."""
        deserialized = {}
        for key, value in cached_data.items():
            if key in ['job_metadata', 'slide_metadata', 'keywords', 'concepts'] and value:
                try:
                    deserialized[key] = json.loads(value)
                except json.JSONDecodeError:
                    deserialized[key] = value
            elif key in ['progress', 'slides_count']:
                try:
                    deserialized[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    deserialized[key] = value
            elif key in ['adaptive_sampling', 'extract_content', 'organize_slides', 
                        'generate_pdf', 'enable_transcription', 'enable_ocr_enhancement',
                        'enable_concept_extraction', 'enable_slide_descriptions']:
                deserialized[key] = value.lower() in ('true', '1', 'yes')
            else:
                deserialized[key] = value
        return deserialized

# Global instance
job_storage = JobStorageService()
