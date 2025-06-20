import os
import sys
import json
import logging
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import time

# Add the cracker-master directory to the Python path
cracker_master_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cracker-master')     
sys.path.append(cracker_master_dir)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import slide extractor components
from slide_extractor import SlideExtractor
from enhanced_slide_extractor import EnhancedSlideExtractor

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

# Global job tracking
extraction_jobs = {}
next_job_id = 1

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
        'advanced_features': ADVANCED_FEATURES_AVAILABLE
    })

@app.route('/api/extract', methods=['POST'])
def extract_slides():
    """Start slide extraction process"""
    global next_job_id
    
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get video URL
        video_url = data.get('video_url')
        if not video_url:
            return jsonify({'error': 'No video URL provided'}), 400

        # Create job ID and output directory
        job_id = next_job_id
        next_job_id += 1
        
        # Create output directory
        output_dir = os.path.join(SLIDES_FOLDER, f"job_{job_id}")
        os.makedirs(output_dir, exist_ok=True)

        # Extract parameters
        params = {
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

        # Store job information
        extraction_jobs[job_id] = {
            'id': job_id,
            'status': 'initializing',
            'progress': 0,
            'params': params,
            'output_dir': output_dir,
            'slides': [],
            'error': None
        }

        # Start extraction in a background thread
        threading.Thread(target=run_extraction, args=(job_id, params)).start()

        return jsonify({
            'job_id': job_id,
            'status': 'initializing'
        })

    except Exception as e:
        logger.error(f"Error starting extraction: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_extraction(job_id, params):
    """Run slide extraction in background thread"""
    job = extraction_jobs[job_id]

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
    if job_id in extraction_jobs:
        job = extraction_jobs[job_id]
        if progress is not None:
            job['progress'] = progress
        if message:
            job['message'] = message
        logger.info(f"Job {job_id}: {progress}% - {message}")

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = extraction_jobs[job_id]
    
    return jsonify({
        'id': job['id'],
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

@app.route('/api/jobs/<int:job_id>/slides', methods=['GET'])
def get_job_slides(job_id):
    """Get slides for a job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = extraction_jobs[job_id]
    
    # Check if job is completed
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    # Return slides
    return jsonify({
        'slides': job.get('slides', [])
    })

@app.route('/api/jobs/<int:job_id>/pdf', methods=['GET'])
def get_job_pdf(job_id):
    """Get PDF for a job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = extraction_jobs[job_id]
    
    # Check if job is completed
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    # Check if PDF is available
    if 'pdf_path' not in job or not os.path.exists(job['pdf_path']):
        return jsonify({'error': 'PDF not available'}), 404
    
    # Return PDF
    return send_file(job['pdf_path'], mimetype='application/pdf', as_attachment=True)

@app.route('/api/jobs/<int:job_id>/study-guide', methods=['GET'])
def get_job_study_guide(job_id):
    """Get study guide for a job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = extraction_jobs[job_id]
    
    # Check if job is completed
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    # Check if study guide is available
    study_guide_path = job.get('study_guide_path')
    if not study_guide_path or not os.path.exists(study_guide_path):
        return jsonify({'error': 'Study guide not available'}), 404
    
    # Return study guide
    try:
        with open(study_guide_path, 'r', encoding='utf-8') as f:
            study_guide_content = f.read()
        
        return jsonify({
            'content': study_guide_content
        })
    except Exception as e:
        logger.error(f"Error reading study guide: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable for Render deployment
    port = int(os.environ.get('PORT', 5000))
    environment = os.environ.get('ENVIRONMENT', 'development').lower()
    debug = environment != 'production'

    # Log startup information
    logger.info(f"Starting Slide Extractor API")
    logger.info(f"Environment: {environment}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug}")

    if environment == 'production':
        # Production mode - use gunicorn in production
        logger.info("Production mode: Use gunicorn for deployment")
        app.run(debug=False, host='0.0.0.0', port=port)
    else:
        # Development mode
        app.run(debug=debug, host='0.0.0.0', port=port)
