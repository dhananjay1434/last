import os
import sys
import json
import logging
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import threading
import time
from datetime import datetime, timezone

# Add the cracker-master directory to the Python path
cracker_master_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cracker-master')
sys.path.append(cracker_master_dir)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import slide extractor components
from slide_extractor import SlideExtractor
from enhanced_slide_extractor import EnhancedSlideExtractor

# Import scalability components
from models import db, Job, Slide, JobMetrics
from job_storage import job_storage
from celery_config import make_celery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("API_Server")

# Import enhanced modules if available
try:
    from content_analyzer import ContentAnalyzer
    from syllabus_manager import SyllabusManager
    ENHANCED_FEATURES_AVAILABLE = True

    # Try to import Gemini transcription service
    try:
        # First try to import from the current directory
        import gemini_transcription
        from gemini_transcription import GeminiTranscriptionService
        logger.info("Successfully imported Gemini transcription service")
        TRANSCRIPTION_AVAILABLE = True
    except ImportError as e:
        logger.error(f"Error importing Gemini transcription service: {e}")
        TRANSCRIPTION_AVAILABLE = False

    # Try to import OCR context enhancer
    try:
        from ocr_context_enhancer import OCRContextEnhancer
        logger.info("Successfully imported OCR context enhancer")
        OCR_ENHANCEMENT_AVAILABLE = True
    except ImportError as e:
        logger.error(f"Error importing OCR context enhancer: {e}")
        OCR_ENHANCEMENT_AVAILABLE = False

    # Try to import slide description generator
    try:
        from slide_description_generator import SlideDescriptionGenerator
        logger.info("Successfully imported slide description generator")
        ADVANCED_FEATURES_AVAILABLE = True
    except ImportError as e:
        logger.error(f"Error importing slide description generator: {e}")
        ADVANCED_FEATURES_AVAILABLE = False
except ImportError as e:
    logger.error(f"Error importing enhanced modules: {e}")
    ENHANCED_FEATURES_AVAILABLE = False
    TRANSCRIPTION_AVAILABLE = False
    OCR_ENHANCEMENT_AVAILABLE = False
    ADVANCED_FEATURES_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)

# Configure database
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    # Fix for Heroku/Render postgres URL
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///slide_extractor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Celery
celery = make_celery(app)

# Configure CORS
try:
    from cors_config import configure_cors
    configure_cors(app)
    logger.info("CORS configured from cors_config.py")
except ImportError:
    # Default CORS configuration
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    logger.info("Using default CORS configuration")

# Define constants
SLIDES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slides")
os.makedirs(SLIDES_FOLDER, exist_ok=True)

# Global job tracking (legacy support - will be phased out)
extraction_jobs = {}
next_job_id = 1

# Initialize job storage service
job_storage.redis_client = job_storage.redis_client  # Ensure Redis is initialized

# Create a Flask route to serve the main page
@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "message": "Slide Extractor API is running",
        "version": "1.0.0"
    })

# Serve static files from the slides directory
@app.route('/slides/<path:filename>')
def serve_slide(filename):
    return send_file(os.path.join(SLIDES_FOLDER, filename), mimetype='image/png')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get server status and available features"""
    # Return actual feature availability
    return jsonify({
        'status': 'online',
        'enhanced_features': ENHANCED_FEATURES_AVAILABLE,
        'transcription': TRANSCRIPTION_AVAILABLE,
        'ocr_enhancement': OCR_ENHANCEMENT_AVAILABLE,
        'advanced_features': ADVANCED_FEATURES_AVAILABLE,
        'demo_videos': [
            {
                'title': 'Khan Academy - Introduction to Algebra',
                'url': 'https://www.youtube.com/watch?v=NybHckSEQBI',
                'description': 'Educational math content, good for testing'
            },
            {
                'title': 'MIT OpenCourseWare - Physics',
                'url': 'https://www.youtube.com/watch?v=ZM8ECpBuQYE',
                'description': 'University lecture with slides'
            },
            {
                'title': 'TED-Ed - Science Explanation',
                'url': 'https://www.youtube.com/watch?v=yWO-cvGETRQ',
                'description': 'Animated educational content'
            },
            {
                'title': 'Coursera - Machine Learning Basics',
                'url': 'https://www.youtube.com/watch?v=ukzFI9rgwfU',
                'description': 'Short educational video with clear slides'
            }
        ],
        'youtube_notice': 'Due to YouTube bot detection, some videos may fail to download. Try different videos if you encounter issues.',
        'tips': [
            'Try shorter videos (under 10 minutes) for better success rates',
            'Educational channels often have less restrictive content',
            'Popular videos may be more accessible than private/unlisted ones',
            'If one video fails, try a different one - the service is working correctly'
        ]
    })

@app.route('/api/test-video', methods=['POST'])
def test_video_accessibility():
    """Test if a video URL is accessible without full extraction"""
    try:
        data = request.json
        if not data or 'video_url' not in data:
            return jsonify({'error': 'No video URL provided'}), 400

        video_url = data['video_url']

        # Quick test using yt-dlp to check if video is accessible
        import subprocess

        test_command = [
            "yt-dlp",
            "--no-download",
            "--print", "title",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--no-check-certificates",
            "--ignore-errors",
            video_url
        ]

        result = subprocess.run(test_command, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            return jsonify({
                'accessible': True,
                'title': result.stdout.strip(),
                'message': 'Video appears to be accessible for extraction'
            })
        else:
            return jsonify({
                'accessible': False,
                'message': 'Video may not be accessible due to restrictions',
                'suggestion': 'Try a different video or check if the URL is correct'
            })

    except subprocess.TimeoutExpired:
        return jsonify({
            'accessible': False,
            'message': 'Video test timed out',
            'suggestion': 'Video may be restricted or unavailable'
        })
    except Exception as e:
        return jsonify({
            'accessible': False,
            'message': f'Error testing video: {str(e)}',
            'suggestion': 'Please check the video URL and try again'
        })

@app.route('/api/extract', methods=['POST'])
def extract_slides():
    """Start slide extraction process using Celery for async processing"""
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get video URL
        video_url = data.get('video_url')
        if not video_url:
            return jsonify({'error': 'No video URL provided'}), 400

        # Generate unique job ID (backward compatible)
        # Use simple integer for compatibility with existing frontend
        global next_job_id
        job_id = str(next_job_id)
        next_job_id += 1

        # Create output directory
        output_dir = os.path.join(SLIDES_FOLDER, job_id)
        os.makedirs(output_dir, exist_ok=True)

        # Extract parameters
        params = {
            'job_id': job_id,
            'video_url': video_url,
            'output_dir': output_dir,
            'adaptive_sampling': data.get('adaptive_sampling', True),
            'min_scene_length': data.get('min_scene_change', 30),
            'extract_content': data.get('extract_content', True),
            'organize_slides': data.get('organize_slides', True),
            'generate_pdf': data.get('generate_pdf', True),
            'enable_transcription': data.get('enable_transcription', False),
            'enable_ocr_enhancement': data.get('enable_ocr_enhancement', False),
            'enable_concept_extraction': data.get('enable_concept_extraction', False),
            'enable_slide_descriptions': data.get('enable_slide_descriptions', False),
            'gemini_api_key': data.get('gemini_api_key', os.environ.get('GEMINI_API_KEY', ''))
        }

        # Create job in storage
        job_storage.create_job(params)

        # Check if Celery is available
        use_celery = os.environ.get('USE_CELERY', 'true').lower() == 'true'

        if use_celery:
            try:
                # Start async task with Celery
                from tasks import extract_slides_task
                task = extract_slides_task.delay(job_id, params)

                logger.info(f"Started Celery task {task.id} for job {job_id}")

                return jsonify({
                    'job_id': job_id,
                    'status': 'pending',
                    'task_id': task.id,
                    'message': 'Job queued for processing'
                })

            except Exception as celery_error:
                logger.warning(f"Celery not available, falling back to threading: {celery_error}")
                use_celery = False

        if not use_celery:
            # Fallback to threading for backward compatibility
            # Store with both string and int keys for compatibility
            job_data = {
                'id': job_id,
                'status': 'initializing',
                'progress': 0,
                'params': params,
                'output_dir': output_dir,
                'slides': [],
                'error': None
            }
            extraction_jobs[job_id] = job_data
            try:
                # Also store with integer key if job_id is numeric
                int_job_id = int(job_id)
                extraction_jobs[int_job_id] = job_data
            except (ValueError, TypeError):
                pass

            # Start extraction in a background thread
            threading.Thread(target=run_extraction, args=(job_id, params)).start()

            return jsonify({
                'job_id': job_id,
                'status': 'initializing',
                'message': 'Job started with threading'
            })

    except Exception as e:
        logger.error(f"Error starting extraction: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_extraction(job_id, params):
    """Run slide extraction in background thread"""
    # Handle both string and integer job IDs
    job = None
    for check_id in [job_id, int(job_id) if str(job_id).isdigit() else None]:
        if check_id is not None and check_id in extraction_jobs:
            job = extraction_jobs[check_id]
            break

    if not job:
        logger.error(f"Job {job_id} not found in extraction_jobs")
        return

    try:
        job['status'] = 'downloading'
        update_job_progress(job_id, 10, 'Downloading video')

        # Create extractor
        extractor = EnhancedSlideExtractor(
            video_url=params['video_url'],
            output_dir=params['output_dir'],
            adaptive_sampling=params['adaptive_sampling'],
            extract_content=params['extract_content'],
            organize_slides=params['organize_slides'],
            callback=lambda msg: update_job_progress(job_id, None, msg)
        )

        # Extract slides
        update_job_progress(job_id, 20, 'Extracting slides')
        success = extractor.extract_slides()
        
        if not success:
            job['status'] = 'failed'
            job['error'] = 'Failed to extract slides'
            return

        # Get slides
        update_job_progress(job_id, 70, 'Processing slides')
        slides = extractor.get_slides()
        
        # Store slides in job
        job['slides'] = slides
        
        # Generate PDF if requested
        if params['generate_pdf']:
            update_job_progress(job_id, 80, 'Generating PDF')
            pdf_path = extractor.convert_slides_to_pdf()
            job['pdf_path'] = pdf_path

        # Process with enhanced features if available
        if ENHANCED_FEATURES_AVAILABLE and (
            params['enable_transcription'] or 
            params['enable_ocr_enhancement'] or 
            params['enable_concept_extraction'] or
            params['enable_slide_descriptions']
        ):
            update_job_progress(job_id, 85, 'Running enhanced analysis')
            
            # Initialize content analyzer
            content_analyzer = ContentAnalyzer(
                slides_dir=params['output_dir'],
                metadata=extractor.get_metadata()
            )
            
            # Run transcription if enabled
            if params['enable_transcription'] and TRANSCRIPTION_AVAILABLE:
                update_job_progress(job_id, 87, 'Transcribing audio')
                
                # Initialize transcription service
                transcription_service = GeminiTranscriptionService(
                    api_key=params['gemini_api_key']
                )
                
                # Get video path
                video_path = extractor.get_video_path()
                
                # Run transcription
                transcription = transcription_service.transcribe_video(video_path)
                
                # Store transcription in job
                job['transcription'] = transcription
                
                # Add transcription to content analyzer
                content_analyzer.add_transcription(transcription)
            
            # Run OCR enhancement if enabled
            if params['enable_ocr_enhancement'] and OCR_ENHANCEMENT_AVAILABLE:
                update_job_progress(job_id, 90, 'Enhancing OCR')
                
                # Initialize OCR enhancer
                ocr_enhancer = OCRContextEnhancer(
                    slides_dir=params['output_dir'],
                    metadata=extractor.get_metadata()
                )
                
                # Run enhancement
                enhanced_metadata = ocr_enhancer.enhance_ocr()
                
                # Update metadata in content analyzer
                content_analyzer.update_metadata(enhanced_metadata)
            
            # Run concept extraction if enabled
            if params['enable_concept_extraction']:
                update_job_progress(job_id, 92, 'Extracting concepts')
                
                # Extract concepts
                concepts = content_analyzer.extract_concepts()
                
                # Store concepts in job
                job['concepts'] = concepts
            
            # Generate slide descriptions if enabled
            if params['enable_slide_descriptions'] and ADVANCED_FEATURES_AVAILABLE:
                update_job_progress(job_id, 95, 'Generating slide descriptions')
                
                # Initialize description generator
                description_generator = SlideDescriptionGenerator(
                    api_key=params['gemini_api_key']
                )
                
                # Generate descriptions
                descriptions = description_generator.generate_descriptions(
                    slides=slides,
                    metadata=content_analyzer.get_metadata()
                )
                
                # Store descriptions in job
                job['descriptions'] = descriptions
            
            # Generate study guide
            update_job_progress(job_id, 97, 'Generating study guide')
            study_guide = content_analyzer.generate_study_guide()
            
            # Store study guide in job
            study_guide_path = os.path.join(params['output_dir'], 'study_guide.md')
            with open(study_guide_path, 'w', encoding='utf-8') as f:
                f.write(study_guide)
            
            job['study_guide_path'] = study_guide_path
        
        # Mark job as completed
        update_job_progress(job_id, 100, 'Completed')
        job['status'] = 'completed'
        
    except Exception as e:
        logger.error(f"Error in extraction job {job_id}: {str(e)}")
        job['status'] = 'failed'
        job['error'] = str(e)

def update_job_progress(job_id, progress, message):
    """Update job progress"""
    # Handle both string and integer job IDs
    job = None
    for check_id in [job_id, int(job_id) if str(job_id).isdigit() else None]:
        if check_id is not None and check_id in extraction_jobs:
            job = extraction_jobs[check_id]
            break

    if job:
        if progress is not None:
            job['progress'] = progress
        if message:
            job['message'] = message
        logger.info(f"Job {job_id}: {progress}% - {message}")
    else:
        logger.warning(f"Job {job_id} not found for progress update")

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status from storage service"""
    try:
        # Try to get from job storage first
        job_data = job_storage.get_job(job_id)

        if job_data:
            return jsonify(job_data)

        # Fallback to legacy in-memory storage (handle both string and int job IDs)
        legacy_job_id = None
        try:
            # Try as integer first
            legacy_job_id = int(job_id)
        except (ValueError, TypeError):
            # If job_id is already a string, try to find it directly
            pass

        # Check both the original job_id and the integer version
        for check_id in [job_id, legacy_job_id]:
            if check_id is not None and check_id in extraction_jobs:
                job = extraction_jobs[check_id]
                return jsonify({
                    'id': str(job['id']),  # Ensure ID is returned as string
                    'status': job['status'],
                    'progress': job['progress'],
                    'message': job.get('message', ''),
                    'error': job.get('error'),
                    'slides_count': len(job.get('slides', [])),
                    'has_pdf': 'pdf_path' in job,
                    'has_study_guide': 'study_guide_path' in job,
                    'has_transcription': 'transcription' in job,
                    'has_concepts': 'concepts' in job,
                    'has_descriptions': 'descriptions' in job
                })

        return jsonify({'error': 'Job not found'}), 404

    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/jobs/<job_id>/slides', methods=['GET'])
def get_job_slides(job_id):
    """Get slides for a job from database"""
    try:
        # Check if job exists and is completed
        job_data = job_storage.get_job(job_id)
        if job_data:
            if job_data['status'] != 'completed':
                return jsonify({'error': 'Job not completed yet'}), 400

            # Get slides from database
            slides = Slide.query.filter_by(job_id=job_id).order_by(Slide.slide_number).all()
            slides_data = [slide.to_dict() for slide in slides]

            if slides_data:
                return jsonify({
                    'slides': slides_data,
                    'count': len(slides_data)
                })

        # Fallback to legacy storage (handle both string and int job IDs)
        legacy_job_id = None
        try:
            legacy_job_id = int(job_id)
        except (ValueError, TypeError):
            pass

        # Check both the original job_id and the integer version
        for check_id in [job_id, legacy_job_id]:
            if check_id is not None and check_id in extraction_jobs:
                job = extraction_jobs[check_id]
                if job['status'] != 'completed':
                    return jsonify({'error': 'Job not completed yet'}), 400

                slides_data = job.get('slides', [])
                return jsonify({
                    'slides': slides_data,
                    'count': len(slides_data)
                })

        return jsonify({'error': 'Job not found'}), 404

    except Exception as e:
        logger.error(f"Error getting slides for job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/jobs/<job_id>/pdf', methods=['GET'])
def get_job_pdf(job_id):
    """Get PDF for a job"""
    try:
        # Try to get from job storage first
        job_data = job_storage.get_job(job_id)

        if job_data:
            if job_data['status'] != 'completed' or not job_data.get('has_pdf'):
                return jsonify({'error': 'PDF not available'}), 404

            # Get job from database to find PDF path
            job = Job.query.filter_by(job_id=job_id).first()
            if job and job.pdf_path and os.path.exists(job.pdf_path):
                return send_file(job.pdf_path, mimetype='application/pdf', as_attachment=True)

        # Fallback to legacy storage (convert job_id to int if needed)
        try:
            legacy_job_id = int(job_id) if job_id.isdigit() else None
            if legacy_job_id and legacy_job_id in extraction_jobs:
                job = extraction_jobs[legacy_job_id]
                if job['status'] == 'completed' and 'pdf_path' in job and os.path.exists(job['pdf_path']):
                    return send_file(job['pdf_path'], mimetype='application/pdf', as_attachment=True)
        except (ValueError, TypeError):
            pass

        return jsonify({'error': 'PDF not available'}), 404

    except Exception as e:
        logger.error(f"Error getting PDF for job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/jobs/<job_id>/study-guide', methods=['GET'])
def get_job_study_guide(job_id):
    """Get study guide for a job"""
    try:
        # Try to get from job storage first
        job_data = job_storage.get_job(job_id)

        if job_data:
            if job_data['status'] != 'completed' or not job_data.get('has_study_guide'):
                return jsonify({'error': 'Study guide not available'}), 404

            # Get job from database to find study guide path
            job = Job.query.filter_by(job_id=job_id).first()
            if job and job.study_guide_path and os.path.exists(job.study_guide_path):
                with open(job.study_guide_path, 'r', encoding='utf-8') as f:
                    study_guide_content = f.read()
                return jsonify({'content': study_guide_content})

        # Fallback to legacy storage (convert job_id to int if needed)
        try:
            legacy_job_id = int(job_id) if job_id.isdigit() else None
            if legacy_job_id and legacy_job_id in extraction_jobs:
                job = extraction_jobs[legacy_job_id]
                if job['status'] == 'completed':
                    study_guide_path = job.get('study_guide_path')
                    if study_guide_path and os.path.exists(study_guide_path):
                        with open(study_guide_path, 'r', encoding='utf-8') as f:
                            study_guide_content = f.read()
                        return jsonify({'content': study_guide_content})
        except (ValueError, TypeError):
            pass

        return jsonify({'error': 'Study guide not available'}), 404

    except Exception as e:
        logger.error(f"Error getting study guide for job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# New API endpoints for scalability features

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status')

        query = Job.query

        if status_filter:
            query = query.filter(Job.status == status_filter)

        jobs = query.order_by(Job.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'jobs': [job.to_dict() for job in jobs.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': jobs.total,
                'pages': jobs.pages,
                'has_next': jobs.has_next,
                'has_prev': jobs.has_prev
            }
        })

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/jobs/<job_id>/metrics', methods=['GET'])
def get_job_metrics(job_id):
    """Get detailed metrics for a job"""
    try:
        metrics = JobMetrics.query.filter_by(job_id=job_id).first()
        if not metrics:
            return jsonify({'error': 'Metrics not found'}), 404

        return jsonify(metrics.to_dict())

    except Exception as e:
        logger.error(f"Error getting metrics for job {job_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '2.0.0',
            'components': {}
        }

        # Check database
        try:
            db.session.execute(db.text('SELECT 1'))
            health_data['components']['database'] = 'healthy'
        except Exception as e:
            health_data['components']['database'] = f'unhealthy: {str(e)}'
            health_data['status'] = 'degraded'

        # Check Redis
        try:
            if job_storage.redis_client:
                job_storage.redis_client.ping()
                health_data['components']['redis'] = 'healthy'
            else:
                health_data['components']['redis'] = 'disabled'
        except Exception as e:
            health_data['components']['redis'] = f'unhealthy: {str(e)}'
            health_data['status'] = 'degraded'

        # Check Celery
        try:
            from celery_config import get_celery_health
            celery_health = get_celery_health()
            health_data['components']['celery'] = celery_health
            if celery_health['status'] != 'healthy':
                health_data['status'] = 'degraded'
        except Exception as e:
            health_data['components']['celery'] = f'error: {str(e)}'
            health_data['status'] = 'degraded'

        # Get system stats
        try:
            import psutil
            health_data['system'] = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except Exception:
            pass

        status_code = 200 if health_data['status'] == 'healthy' else 503
        return jsonify(health_data), status_code

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics and metrics"""
    try:
        # Job statistics
        total_jobs = Job.query.count()
        completed_jobs = Job.query.filter_by(status='completed').count()
        failed_jobs = Job.query.filter_by(status='failed').count()
        active_jobs = Job.query.filter(Job.status.in_(['pending', 'processing'])).count()

        # Recent activity (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_jobs = Job.query.filter(Job.created_at >= yesterday).count()

        # Average processing time
        avg_processing_time = db.session.query(
            db.func.avg(JobMetrics.total_processing_time)
        ).scalar() or 0

        return jsonify({
            'jobs': {
                'total': total_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'active': active_jobs,
                'recent_24h': recent_jobs,
                'success_rate': (completed_jobs / max(total_jobs, 1)) * 100
            },
            'performance': {
                'avg_processing_time': round(avg_processing_time, 2),
                'total_slides_extracted': db.session.query(db.func.sum(Job.slides_count)).scalar() or 0
            },
            'system': {
                'active_job_storage': len(job_storage.get_active_jobs()),
                'redis_enabled': job_storage.enable_redis,
                'celery_enabled': os.environ.get('USE_CELERY', 'true').lower() == 'true'
            }
        })

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Debug endpoint for troubleshooting
@app.route('/api/debug/jobs', methods=['GET'])
def debug_jobs():
    """Debug endpoint to see current jobs in memory"""
    try:
        return jsonify({
            'in_memory_jobs': {
                'keys': list(extraction_jobs.keys()),
                'count': len(extraction_jobs),
                'jobs': {str(k): {'id': v.get('id'), 'status': v.get('status')}
                        for k, v in extraction_jobs.items()}
            },
            'next_job_id': next_job_id,
            'storage_service_active_jobs': job_storage.get_active_jobs()
        })
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/init-db', methods=['POST'])
def init_database():
    """Manual database initialization endpoint"""
    try:
        create_tables()
        return jsonify({
            'status': 'success',
            'message': 'Database initialization attempted',
            'database_url': app.config['SQLALCHEMY_DATABASE_URI']
        })
    except Exception as e:
        logger.error(f"Manual database initialization error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Database initialization
def create_tables():
    """Create database tables"""
    try:
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables created successfully")

            # Test database connection
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text('SELECT 1'))
                logger.info("Database connection test successful")
            except Exception as conn_error:
                logger.warning(f"Database connection test failed: {conn_error}")

    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info("Application will continue without database features")

        # Try to create a simple SQLite database as fallback
        try:
            import sqlite3
            import os

            # Create a simple SQLite database in the current directory
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slide_extractor.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Create basic jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    video_url TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    message TEXT,
                    error TEXT,
                    created_at TEXT,
                    slides_count INTEGER DEFAULT 0,
                    pdf_path TEXT,
                    study_guide_path TEXT
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("Created fallback SQLite database")

        except Exception as sqlite_error:
            logger.error(f"Failed to create fallback database: {sqlite_error}")

# Initialize database tables on startup
create_tables()

if __name__ == '__main__':
    # Get port from environment variable for Render deployment
    port = int(os.environ.get('PORT', 5000))
    environment = os.environ.get('ENVIRONMENT', 'development').lower()
    debug = environment != 'production'

    # Log startup information
    logger.info(f"Starting Slide Extractor API v2.0")
    logger.info(f"Environment: {environment}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    logger.info(f"Redis enabled: {job_storage.enable_redis}")
    logger.info(f"Celery enabled: {os.environ.get('USE_CELERY', 'true')}")

    # Database tables are already created by create_tables() function above

    if environment == 'production':
        # Production mode - use gunicorn in production
        logger.info("Production mode: Use gunicorn for deployment")
        app.run(debug=False, host='0.0.0.0', port=port)
    else:
        # Development mode
        app.run(debug=debug, host='0.0.0.0', port=port)
