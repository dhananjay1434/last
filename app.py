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
        # First try to import from the current directory
        import slide_description_generator
        from slide_description_generator import SlideDescriptionGenerator
        logger.info("Successfully imported slide description generator")
        ADVANCED_FEATURES_AVAILABLE = True
    except ImportError as e:
        logger.error(f"Error importing slide description generator: {e}")
        ADVANCED_FEATURES_AVAILABLE = False
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False
    TRANSCRIPTION_AVAILABLE = False
    OCR_ENHANCEMENT_AVAILABLE = False
    ADVANCED_FEATURES_AVAILABLE = False

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

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables to track extraction jobs
extraction_jobs = {}
next_job_id = 1

# Create upload directory if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Create slides directory if it doesn't exist
SLIDES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slides')
os.makedirs(SLIDES_FOLDER, exist_ok=True)

# Configure upload settings
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size

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
        # Get parameters from request
        data = request.json
        video_url = data.get('video_url')

        if not video_url:
            return jsonify({'error': 'Missing video URL'}), 400

        # Create a unique job ID
        job_id = next_job_id
        next_job_id += 1

        # Create output directory
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'slides')
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

        # Initialize extractor
        if ENHANCED_FEATURES_AVAILABLE and (
            params.get('enable_transcription') or
            params.get('enable_ocr_enhancement') or
            params.get('enable_concept_extraction') or
            params.get('enable_slide_descriptions')
        ):
            # Use enhanced extractor
            # Create a dictionary of parameters for SlideExtractor
            slide_extractor_params = {
                'adaptive_sampling': params['adaptive_sampling'],
                'min_scene_length': params['min_scene_length'],
                'extract_content': params['extract_content'],
                'organize_slides': params['organize_slides']
            }

            # First create a basic extractor to download the video
            base_extractor = SlideExtractor(
                video_url=params['video_url'],
                output_dir=params['output_dir'],
                **slide_extractor_params
            )

            # Download the video
            if base_extractor.download_video():
                logger.info(f"Video downloaded to: {base_extractor.video_path}")
                # Store the video path in the job parameters
                params['video_path'] = base_extractor.video_path
            else:
                logger.error("Failed to download video")
                job['status'] = 'failed'
                job['error'] = 'Failed to download video'
                return

            # Create the EnhancedSlideExtractor
            extractor = EnhancedSlideExtractor(
                video_url=params['video_url'],
                output_dir=params['output_dir'],
                **slide_extractor_params
            )

            # Set the video path in the base extractor
            extractor.base_extractor.video_path = params['video_path']

            # Store additional parameters for later use
            extractor.enable_transcription = params['enable_transcription']
            extractor.enable_ocr_enhancement = params['enable_ocr_enhancement']
            extractor.enable_concept_extraction = params['enable_concept_extraction']
            extractor.enable_slide_descriptions = params['enable_slide_descriptions']
            extractor.gemini_api_key = params['gemini_api_key']

            # Log that we're using enhanced features
            logger.info(f"Using enhanced features with Gemini API key: {params['gemini_api_key'] != ''}")

            # Log which features are enabled
            if params['enable_transcription']:
                logger.info("Transcription is enabled")
                logger.info(f"Video path for transcription: {params['video_path']}")

            if params['enable_slide_descriptions']:
                logger.info("Slide descriptions are enabled")
        else:
            # Use basic extractor
            extractor = SlideExtractor(
                video_url=params['video_url'],
                output_dir=params['output_dir'],
                adaptive_sampling=params['adaptive_sampling'],
                min_scene_length=params['min_scene_length'],
                extract_content=params['extract_content'],
                organize_slides=params['organize_slides']
            )

        # Update job status
        job['status'] = 'extracting'

        # Extract slides
        success = extractor.extract_slides()

        if not success:
            job['status'] = 'failed'
            job['error'] = 'Slide extraction failed'
            return

        # Generate PDF if requested
        if params['generate_pdf']:
            job['status'] = 'generating_pdf'
            if isinstance(extractor, EnhancedSlideExtractor):
                extractor.base_extractor.convert_slides_to_pdf()
            else:
                extractor.convert_slides_to_pdf()

        # Get slide metadata
        if isinstance(extractor, EnhancedSlideExtractor):
            slides_metadata = extractor.base_extractor.slides_metadata
        else:
            slides_metadata = extractor.slides_metadata

        # Update job with results
        job['status'] = 'completed'
        job['progress'] = 100
        job['slides'] = slides_metadata

        # If enhanced extractor was used, include additional data
        if ENHANCED_FEATURES_AVAILABLE and isinstance(extractor, EnhancedSlideExtractor):
            job['enhanced_metadata'] = extractor.enhanced_metadata

            # Include study guide path if generated
            study_guide_path = os.path.join(params['output_dir'], 'analysis', 'study_guide.md')
            if os.path.exists(study_guide_path):
                job['study_guide_path'] = study_guide_path

            # Include language information if transcription was enabled
            if params['enable_transcription']:
                transcription_path = os.path.join(params['output_dir'], 'analysis', 'transcription.json')
                if os.path.exists(transcription_path):
                    try:
                        with open(transcription_path, 'r', encoding='utf-8') as f:
                            transcription_data = json.load(f)

                        # Add language information if available
                        if 'language' in transcription_data:
                            job['language'] = transcription_data['language']
                    except Exception as e:
                        logger.error(f"Error loading transcription data for language info: {e}")

    except Exception as e:
        logger.error(f"Error in extraction job {job_id}: {str(e)}")
        job['status'] = 'failed'
        job['error'] = str(e)

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of an extraction job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = extraction_jobs[job_id]

    # Return basic job info without full slide data to keep response size small
    return jsonify({
        'id': job['id'],
        'status': job['status'],
        'progress': job['progress'],
        'error': job['error'],
        'slide_count': len(job.get('slides', {}))
    })

@app.route('/api/jobs/<int:job_id>/slides', methods=['GET'])
def get_job_slides(job_id):
    """Get slides from an extraction job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = extraction_jobs[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400

    return jsonify({
        'slides': job.get('slides', {})
    })

@app.route('/api/jobs/<int:job_id>/study_guide', methods=['GET'])
def get_study_guide(job_id):
    """Get study guide for an extraction job"""
    if job_id not in extraction_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = extraction_jobs[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400

    study_guide_path = job.get('study_guide_path')
    if not study_guide_path or not os.path.exists(study_guide_path):
        return jsonify({'error': 'Study guide not available'}), 404

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
    app.run(debug=True, host='0.0.0.0', port=5000)
