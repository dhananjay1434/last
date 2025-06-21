"""
Celery configuration for asynchronous task processing.
Handles video processing, slide extraction, and AI analysis in background workers.
"""

import os
from celery import Celery
from kombu import Queue

def make_celery(app=None):
    """
    Create and configure Celery instance.
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured Celery instance
    """
    # Get configuration from environment
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Create Celery instance
    celery = Celery(
        'slide_extractor',
        broker=redis_url,
        backend=redis_url,
        include=['tasks']
    )
    
    # Configure Celery
    celery.conf.update(
        # Task routing
        task_routes={
            'tasks.extract_slides_task': {'queue': 'extraction'},
            'tasks.analyze_content_task': {'queue': 'analysis'},
            'tasks.generate_pdf_task': {'queue': 'generation'},
            'tasks.transcribe_audio_task': {'queue': 'transcription'},
            'tasks.cleanup_old_jobs_task': {'queue': 'maintenance'},
        },
        
        # Queue configuration
        task_default_queue='default',
        task_queues=(
            Queue('default', routing_key='default'),
            Queue('extraction', routing_key='extraction'),
            Queue('analysis', routing_key='analysis'),
            Queue('generation', routing_key='generation'),
            Queue('transcription', routing_key='transcription'),
            Queue('maintenance', routing_key='maintenance'),
        ),
        
        # Worker configuration
        worker_prefetch_multiplier=1,  # Process one task at a time for memory efficiency
        task_acks_late=True,  # Acknowledge tasks only after completion
        worker_disable_rate_limits=False,
        
        # Task execution
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Task timeouts and retries
        task_soft_time_limit=3600,  # 1 hour soft limit
        task_time_limit=7200,       # 2 hour hard limit
        task_default_retry_delay=60,  # 1 minute retry delay
        task_max_retries=3,
        
        # Result backend configuration
        result_expires=86400,  # Results expire after 24 hours
        result_backend_transport_options={
            'master_name': 'mymaster',
            'visibility_timeout': 3600,
        },
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Memory management
        worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to prevent memory leaks
        worker_max_memory_per_child=2000000,  # 2GB memory limit per worker
        
        # Beat schedule for periodic tasks
        beat_schedule={
            'cleanup-old-jobs': {
                'task': 'tasks.cleanup_old_jobs_task',
                'schedule': 3600.0,  # Run every hour
                'options': {'queue': 'maintenance'}
            },
            'health-check': {
                'task': 'tasks.health_check_task',
                'schedule': 300.0,  # Run every 5 minutes
                'options': {'queue': 'maintenance'}
            },
        },
    )
    
    # Update task base if Flask app is provided
    if app:
        class ContextTask(celery.Task):
            """Make celery tasks work with Flask app context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Environment-specific configurations
class CeleryConfig:
    """Base Celery configuration."""
    
    # Broker settings
    broker_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    result_backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Task settings
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    
    # Worker settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_disable_rate_limits = False
    
    # Monitoring
    worker_send_task_events = True
    task_send_sent_event = True

class DevelopmentConfig(CeleryConfig):
    """Development Celery configuration."""
    
    # More verbose logging in development
    worker_log_level = 'INFO'
    worker_hijack_root_logger = False
    
    # Shorter timeouts for development
    task_soft_time_limit = 1800  # 30 minutes
    task_time_limit = 3600       # 1 hour
    
    # Less aggressive memory management
    worker_max_tasks_per_child = 50
    worker_max_memory_per_child = 1000000  # 1GB

class ProductionConfig(CeleryConfig):
    """Production Celery configuration."""
    
    # Production logging
    worker_log_level = 'WARNING'
    worker_hijack_root_logger = True
    
    # Longer timeouts for production
    task_soft_time_limit = 3600  # 1 hour
    task_time_limit = 7200       # 2 hours
    
    # Aggressive memory management
    worker_max_tasks_per_child = 10
    worker_max_memory_per_child = 2000000  # 2GB
    
    # Production-specific broker settings
    broker_transport_options = {
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True
    }
    
    # Connection pooling
    broker_pool_limit = 10
    broker_connection_retry_on_startup = True

class TestingConfig(CeleryConfig):
    """Testing Celery configuration."""
    
    # Use in-memory broker for testing
    task_always_eager = True
    task_eager_propagates = True
    
    # Disable beat for testing
    beat_schedule = {}

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_celery_config():
    """Get Celery configuration based on environment."""
    env = os.environ.get('ENVIRONMENT', 'development').lower()
    return config_map.get(env, DevelopmentConfig)

# Task priority levels
class TaskPriority:
    """Task priority constants."""
    HIGH = 9
    NORMAL = 5
    LOW = 1

# Queue configurations for different deployment scenarios
QUEUE_CONFIGS = {
    'single_worker': {
        'queues': ['default'],
        'description': 'Single worker processes all tasks'
    },
    'specialized_workers': {
        'queues': ['extraction', 'analysis', 'generation', 'transcription', 'maintenance'],
        'description': 'Specialized workers for different task types'
    },
    'hybrid': {
        'queues': ['default', 'extraction', 'analysis'],
        'description': 'Hybrid approach with some specialization'
    }
}

def get_recommended_queue_config(worker_count: int) -> str:
    """
    Get recommended queue configuration based on worker count.
    
    Args:
        worker_count: Number of available workers
        
    Returns:
        Recommended queue configuration name
    """
    if worker_count <= 2:
        return 'single_worker'
    elif worker_count <= 5:
        return 'hybrid'
    else:
        return 'specialized_workers'

# Monitoring and health check utilities
def get_celery_health():
    """Get Celery cluster health information."""
    try:
        from celery import current_app
        
        # Get active workers
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        
        # Get queue lengths
        queue_lengths = {}
        for queue_name in ['default', 'extraction', 'analysis', 'generation', 'transcription']:
            try:
                # This would need to be implemented based on your broker
                queue_lengths[queue_name] = 0  # Placeholder
            except Exception:
                queue_lengths[queue_name] = -1
        
        return {
            'status': 'healthy' if active_workers else 'unhealthy',
            'active_workers': len(active_workers) if active_workers else 0,
            'worker_details': active_workers,
            'queue_lengths': queue_lengths
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Export the factory function
__all__ = ['make_celery', 'CeleryConfig', 'get_celery_config', 'TaskPriority', 'get_celery_health']
