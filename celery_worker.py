#!/usr/bin/env python3
"""
Celery worker startup script for the Slide Extractor application.
Handles background processing of video extraction and analysis tasks.
"""

import os
import sys
import logging
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from celery_config import make_celery, get_celery_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("celery_worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CeleryWorker")

def create_app():
    """Create Flask app for Celery context."""
    from flask import Flask
    from models import db
    
    app = Flask(__name__)
    
    # Configure database
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///slide_extractor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    db.init_app(app)
    
    return app

# Create Flask app and Celery instance
app = create_app()
celery = make_celery(app)

# Apply configuration
config_class = get_celery_config()
celery.config_from_object(config_class)

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler called when worker is ready."""
    logger.info(f"Celery worker {sender.hostname} is ready")
    logger.info(f"Worker configuration: {sender.app.conf}")
    
    # Log available queues
    queues = getattr(sender.app.conf, 'task_routes', {})
    logger.info(f"Available task routes: {queues}")

@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handler called when worker is shutting down."""
    logger.info(f"Celery worker {sender.hostname} is shutting down")

def get_worker_config():
    """Get worker configuration based on environment and arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Celery Worker for Slide Extractor')
    parser.add_argument('--queue', '-Q', default='default', 
                       help='Comma-separated list of queues to consume from')
    parser.add_argument('--concurrency', '-c', type=int, default=1,
                       help='Number of concurrent worker processes')
    parser.add_argument('--loglevel', '-l', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--worker-type', choices=['general', 'extraction', 'analysis', 'maintenance'],
                       default='general', help='Type of worker to start')
    
    args = parser.parse_args()
    
    # Configure queues based on worker type
    queue_configs = {
        'general': 'default,extraction,analysis',
        'extraction': 'extraction',
        'analysis': 'analysis,transcription,generation',
        'maintenance': 'maintenance'
    }
    
    if args.worker_type in queue_configs:
        args.queue = queue_configs[args.worker_type]
    
    return args

def start_worker():
    """Start the Celery worker with appropriate configuration."""
    config = get_worker_config()
    
    logger.info(f"Starting Celery worker")
    logger.info(f"Worker type: {config.worker_type}")
    logger.info(f"Queues: {config.queue}")
    logger.info(f"Concurrency: {config.concurrency}")
    logger.info(f"Log level: {config.loglevel}")
    
    # Build worker arguments
    worker_args = [
        'worker',
        f'--queues={config.queue}',
        f'--concurrency={config.concurrency}',
        f'--loglevel={config.loglevel}',
        '--without-gossip',
        '--without-mingle',
        '--without-heartbeat'
    ]
    
    # Add environment-specific options
    environment = os.environ.get('ENVIRONMENT', 'development').lower()
    
    if environment == 'production':
        worker_args.extend([
            '--optimization=fair',
            '--prefetch-multiplier=1',
            '--max-tasks-per-child=10',
            '--max-memory-per-child=2000000'  # 2GB
        ])
    else:
        worker_args.extend([
            '--prefetch-multiplier=4',
            '--max-tasks-per-child=50'
        ])
    
    # Start worker
    try:
        celery.start(worker_args)
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed to start: {e}")
        sys.exit(1)

def start_beat():
    """Start the Celery beat scheduler."""
    logger.info("Starting Celery beat scheduler")
    
    beat_args = [
        'beat',
        '--loglevel=INFO',
        '--schedule=/tmp/celerybeat-schedule',
        '--pidfile=/tmp/celerybeat.pid'
    ]
    
    try:
        celery.start(beat_args)
    except KeyboardInterrupt:
        logger.info("Beat scheduler interrupted by user")
    except Exception as e:
        logger.error(f"Beat scheduler failed to start: {e}")
        sys.exit(1)

def start_flower():
    """Start Flower monitoring tool."""
    logger.info("Starting Flower monitoring")
    
    flower_args = [
        'flower',
        '--port=5555',
        '--broker=' + os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    ]
    
    try:
        celery.start(flower_args)
    except KeyboardInterrupt:
        logger.info("Flower interrupted by user")
    except Exception as e:
        logger.error(f"Flower failed to start: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Celery services for Slide Extractor')
    parser.add_argument('service', choices=['worker', 'beat', 'flower'],
                       help='Service to start')
    
    args, remaining = parser.parse_known_args()
    
    # Set remaining args back for service-specific parsing
    sys.argv = [sys.argv[0]] + remaining
    
    if args.service == 'worker':
        start_worker()
    elif args.service == 'beat':
        start_beat()
    elif args.service == 'flower':
        start_flower()

if __name__ == '__main__':
    main()
