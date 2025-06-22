#!/usr/bin/env python3
"""
Gradio Full-Stack Slide Extractor Application
Complete backend and frontend in one application - no separate API needed.
"""

import gradio as gr
import os
import sys
import json
import time
import tempfile
import threading
import logging
import uuid
import sqlite3
import shutil
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import slide extractor components
try:
    from slide_extractor import SlideExtractor
    BASIC_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Basic slide extractor not available: {e}")
    BASIC_EXTRACTOR_AVAILABLE = False

try:
    from enhanced_slide_extractor import EnhancedSlideExtractor
    ENHANCED_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced features not available: {e}")
    ENHANCED_AVAILABLE = False

# Import robust downloader
try:
    from robust_slide_extractor import RobustSlideExtractor, extract_slides_robust
    ROBUST_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Robust extractor not available: {e}")
    ROBUST_EXTRACTOR_AVAILABLE = False

# Import AI components if available
try:
    from content_analyzer import ContentAnalyzer
    CONTENT_ANALYZER_AVAILABLE = True
except ImportError:
    CONTENT_ANALYZER_AVAILABLE = False

try:
    from gemini_transcription import GeminiTranscriptionService
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TRANSCRIPTION_AVAILABLE = False

try:
    from ocr_context_enhancer import OCRContextEnhancer
    OCR_ENHANCEMENT_AVAILABLE = True
except ImportError:
    OCR_ENHANCEMENT_AVAILABLE = False

try:
    from slide_description_generator import SlideDescriptionGenerator
    SLIDE_DESCRIPTIONS_AVAILABLE = True
except ImportError:
    SLIDE_DESCRIPTIONS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gradio_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GradioSlideExtractor")

# Configuration
SLIDES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slides")
os.makedirs(SLIDES_FOLDER, exist_ok=True)

# Global job tracking
extraction_jobs = {}
next_job_id = 1
job_lock = threading.Lock()

# Database setup for job persistence
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gradio_jobs.db")

def init_database():
    """Initialize SQLite database for job tracking."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                video_url TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0.0,
                message TEXT,
                error TEXT,
                created_at TEXT,
                completed_at TEXT,
                slides_count INTEGER DEFAULT 0,
                output_dir TEXT,
                pdf_path TEXT,
                study_guide_path TEXT,
                options TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

def get_feature_status() -> str:
    """Get available features status."""
    features = []
    if ROBUST_EXTRACTOR_AVAILABLE:
        features.append("🚀 Robust Download System")
    if BASIC_EXTRACTOR_AVAILABLE:
        features.append("Basic Extraction")
    if ENHANCED_AVAILABLE:
        features.append("Enhanced Extraction")
    if CONTENT_ANALYZER_AVAILABLE:
        features.append("Content Analysis")
    if TRANSCRIPTION_AVAILABLE:
        features.append("Transcription")
    if OCR_ENHANCEMENT_AVAILABLE:
        features.append("OCR Enhancement")
    if SLIDE_DESCRIPTIONS_AVAILABLE:
        features.append("Slide Descriptions")

    if features:
        status = f"✅ Available Features: {', '.join(features)}"
        if ROBUST_EXTRACTOR_AVAILABLE:
            status += "\n🎯 Robust Download: Multiple fallback methods for maximum success rate!"
        return status
    else:
        return "⚠️ No slide extraction features available (missing dependencies)"

def create_job_id() -> str:
    """Create a unique job ID."""
    global next_job_id
    with job_lock:
        timestamp = int(time.time() * 1000)
        job_id = f"job_{timestamp}_{next_job_id}"
        next_job_id += 1
        return job_id

def save_job_to_db(job_data: Dict[str, Any]):
    """Save job to database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO jobs 
            (job_id, video_url, status, progress, message, error, created_at, 
             slides_count, output_dir, pdf_path, study_guide_path, options)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_data['job_id'],
            job_data['video_url'],
            job_data['status'],
            job_data['progress'],
            job_data.get('message', ''),
            job_data.get('error', ''),
            job_data['created_at'],
            job_data.get('slides_count', 0),
            job_data.get('output_dir', ''),
            job_data.get('pdf_path', ''),
            job_data.get('study_guide_path', ''),
            json.dumps(job_data.get('options', {}))
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save job to database: {e}")

def get_job_from_db(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            job_data = dict(zip(columns, row))
            if job_data.get('options'):
                job_data['options'] = json.loads(job_data['options'])
            return job_data
        return None
    except Exception as e:
        logger.error(f"Failed to get job from database: {e}")
        return None

def update_job_progress(job_id: str, progress: float, message: str, status: str = None):
    """Update job progress in memory and database."""
    with job_lock:
        if job_id in extraction_jobs:
            extraction_jobs[job_id]['progress'] = progress
            extraction_jobs[job_id]['message'] = message
            if status:
                extraction_jobs[job_id]['status'] = status
            
            # Update database
            save_job_to_db(extraction_jobs[job_id])
            
            logger.info(f"Job {job_id}: {progress}% - {message}")

# Initialize database on startup
init_database()

def extract_slides_background(job_id: str, video_url: str, options: Dict[str, Any]):
    """Run slide extraction in background thread."""
    try:
        # Update job status
        update_job_progress(job_id, 5, "Initializing extraction...", "processing")

        # Create output directory
        output_dir = os.path.join(SLIDES_FOLDER, job_id)
        os.makedirs(output_dir, exist_ok=True)

        extraction_jobs[job_id]['output_dir'] = output_dir

        # Choose extractor based on availability and options
        if ROBUST_EXTRACTOR_AVAILABLE:
            update_job_progress(job_id, 10, "Using robust extractor with multiple download methods...")

            # Use robust extractor for better download success rates
            extractor = RobustSlideExtractor(
                video_url=video_url,
                output_dir=output_dir,
                enable_proxy=options.get('enable_proxy', False),
                use_enhanced=ENHANCED_AVAILABLE and (
                    options.get('enable_transcription') or
                    options.get('enable_ocr_enhancement') or
                    options.get('enable_concept_extraction') or
                    options.get('enable_slide_descriptions')
                ),
                adaptive_sampling=options.get('adaptive_sampling', True),
                extract_content=options.get('extract_content', True),
                organize_slides=options.get('organize_slides', True),
                callback=lambda msg: update_job_progress(job_id, None, msg)
            )
        elif ENHANCED_AVAILABLE and (options.get('enable_transcription') or
                                  options.get('enable_ocr_enhancement') or
                                  options.get('enable_concept_extraction') or
                                  options.get('enable_slide_descriptions')):
            update_job_progress(job_id, 10, "Using enhanced extractor...")
            extractor = EnhancedSlideExtractor(
                video_url=video_url,
                output_dir=output_dir,
                adaptive_sampling=options.get('adaptive_sampling', True),
                extract_content=options.get('extract_content', True),
                organize_slides=options.get('organize_slides', True),
                callback=lambda msg: update_job_progress(job_id, None, msg)
            )
        elif BASIC_EXTRACTOR_AVAILABLE:
            update_job_progress(job_id, 10, "Using basic extractor...")
            extractor = SlideExtractor(
                video_url=video_url,
                output_dir=output_dir,
                adaptive_sampling=options.get('adaptive_sampling', True),
                extract_content=options.get('extract_content', True),
                organize_slides=options.get('organize_slides', True),
                callback=lambda msg: update_job_progress(job_id, None, msg)
            )
        else:
            raise Exception("No slide extractor available - missing dependencies")

        # Extract slides
        update_job_progress(job_id, 20, "Downloading and processing video...")
        success = extractor.extract_slides()

        if not success:
            raise Exception("Slide extraction failed")

        # Get slides
        update_job_progress(job_id, 70, "Processing extracted slides...")
        slides = extractor.get_slides()
        extraction_jobs[job_id]['slides'] = slides
        extraction_jobs[job_id]['slides_count'] = len(slides)

        # Generate PDF if requested
        if options.get('generate_pdf', True):
            update_job_progress(job_id, 80, "Generating PDF...")
            try:
                pdf_path = extractor.convert_slides_to_pdf()
                if pdf_path and os.path.exists(pdf_path):
                    extraction_jobs[job_id]['pdf_path'] = pdf_path
            except Exception as e:
                logger.warning(f"PDF generation failed: {e}")

        # Run enhanced features if available and requested
        if ENHANCED_AVAILABLE and isinstance(extractor, EnhancedSlideExtractor):
            update_job_progress(job_id, 85, "Running AI analysis...")

            # Initialize content analyzer if available
            if CONTENT_ANALYZER_AVAILABLE:
                content_analyzer = ContentAnalyzer(
                    slides_dir=output_dir,
                    metadata=extractor.get_metadata()
                )

                # Run transcription if enabled
                if options.get('enable_transcription') and TRANSCRIPTION_AVAILABLE:
                    update_job_progress(job_id, 87, "Transcribing audio...")
                    try:
                        transcription_service = GeminiTranscriptionService(
                            api_key=options.get('gemini_api_key', '')
                        )
                        video_path = extractor.get_video_path()
                        transcription = transcription_service.transcribe_video(video_path)
                        extraction_jobs[job_id]['transcription'] = transcription
                        content_analyzer.add_transcription(transcription)
                    except Exception as e:
                        logger.warning(f"Transcription failed: {e}")

                # Run OCR enhancement if enabled
                if options.get('enable_ocr_enhancement') and OCR_ENHANCEMENT_AVAILABLE:
                    update_job_progress(job_id, 90, "Enhancing OCR...")
                    try:
                        ocr_enhancer = OCRContextEnhancer(
                            slides_dir=output_dir,
                            metadata=extractor.get_metadata()
                        )
                        enhanced_metadata = ocr_enhancer.enhance_ocr()
                        content_analyzer.update_metadata(enhanced_metadata)
                    except Exception as e:
                        logger.warning(f"OCR enhancement failed: {e}")

                # Extract concepts if enabled
                if options.get('enable_concept_extraction'):
                    update_job_progress(job_id, 92, "Extracting concepts...")
                    try:
                        concepts = content_analyzer.extract_concepts()
                        extraction_jobs[job_id]['concepts'] = concepts
                    except Exception as e:
                        logger.warning(f"Concept extraction failed: {e}")

                # Generate slide descriptions if enabled
                if options.get('enable_slide_descriptions') and SLIDE_DESCRIPTIONS_AVAILABLE:
                    update_job_progress(job_id, 95, "Generating slide descriptions...")
                    try:
                        description_generator = SlideDescriptionGenerator(
                            api_key=options.get('gemini_api_key', '')
                        )
                        descriptions = description_generator.generate_descriptions(
                            slides=slides,
                            metadata=content_analyzer.get_metadata()
                        )
                        extraction_jobs[job_id]['descriptions'] = descriptions
                    except Exception as e:
                        logger.warning(f"Slide description generation failed: {e}")

                # Generate study guide
                update_job_progress(job_id, 97, "Generating study guide...")
                try:
                    study_guide = content_analyzer.generate_study_guide()
                    study_guide_path = os.path.join(output_dir, 'study_guide.md')
                    with open(study_guide_path, 'w', encoding='utf-8') as f:
                        f.write(study_guide)
                    extraction_jobs[job_id]['study_guide_path'] = study_guide_path
                except Exception as e:
                    logger.warning(f"Study guide generation failed: {e}")

        # Mark job as completed
        update_job_progress(job_id, 100, "Extraction completed successfully!", "completed")
        extraction_jobs[job_id]['completed_at'] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Error in extraction job {job_id}: {str(e)}")
        update_job_progress(job_id, 0, f"Error: {str(e)}", "failed")
        extraction_jobs[job_id]['error'] = str(e)

def start_extraction(video_url: str, adaptive_sampling: bool, extract_content: bool,
                    organize_slides: bool, generate_pdf: bool, enable_transcription: bool,
                    enable_ocr_enhancement: bool, enable_concept_extraction: bool,
                    enable_slide_descriptions: bool, enable_proxy: bool, gemini_api_key: str = "") -> Tuple[str, str, str]:
    """Start slide extraction process."""

    # Validate inputs
    if not video_url.strip():
        return "❌ Error: Please provide a video URL", "", ""

    if not BASIC_EXTRACTOR_AVAILABLE and not ENHANCED_AVAILABLE:
        return "❌ Error: No slide extractor available. Please install required dependencies.", "", ""

    # Create job
    job_id = create_job_id()

    # Prepare job data
    job_data = {
        'job_id': job_id,
        'video_url': video_url.strip(),
        'status': 'pending',
        'progress': 0,
        'message': 'Job created',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'slides_count': 0,
        'options': {
            'adaptive_sampling': adaptive_sampling,
            'extract_content': extract_content,
            'organize_slides': organize_slides,
            'generate_pdf': generate_pdf,
            'enable_transcription': enable_transcription,
            'enable_ocr_enhancement': enable_ocr_enhancement,
            'enable_concept_extraction': enable_concept_extraction,
            'enable_slide_descriptions': enable_slide_descriptions,
            'enable_proxy': enable_proxy,
            'gemini_api_key': gemini_api_key.strip()
        }
    }

    # Store job
    with job_lock:
        extraction_jobs[job_id] = job_data

    # Save to database
    save_job_to_db(job_data)

    # Start extraction in background thread
    thread = threading.Thread(
        target=extract_slides_background,
        args=(job_id, video_url.strip(), job_data['options']),
        daemon=True
    )
    thread.start()

    return (
        f"✅ Extraction started successfully! Job ID: {job_id}",
        job_id,
        "🔄 Processing..."
    )

def check_job_status(job_id: str) -> Tuple[str, str, str, str]:
    """Check the status of a job."""
    if not job_id.strip():
        return "❌ Please provide a Job ID", "", "", ""

    job_id = job_id.strip()

    # Check memory first, then database
    job_data = None
    with job_lock:
        if job_id in extraction_jobs:
            job_data = extraction_jobs[job_id]

    if not job_data:
        job_data = get_job_from_db(job_id)

    if not job_data:
        return "❌ Job not found", "", "", ""

    status = job_data.get('status', 'unknown')
    progress = job_data.get('progress', 0)
    message = job_data.get('message', '')
    error = job_data.get('error')

    # Format status message
    if status == 'completed':
        slides_count = job_data.get('slides_count', 0)
        has_pdf = bool(job_data.get('pdf_path'))
        has_study_guide = bool(job_data.get('study_guide_path'))

        status_msg = f"✅ Completed! Found {slides_count} slides"
        if has_pdf:
            status_msg += " | PDF available"
        if has_study_guide:
            status_msg += " | Study guide available"

        return status_msg, job_id, "✅ Completed", f"{progress}%"

    elif status == 'failed':
        return f"❌ Failed: {error or 'Unknown error'}", job_id, "❌ Failed", f"{progress}%"

    else:
        return f"🔄 {status.title()}: {message}", job_id, f"🔄 {status.title()}", f"{progress}%"

def get_job_results(job_id: str) -> Tuple[str, str, str]:
    """Get results from a completed job."""
    if not job_id.strip():
        return "❌ Please provide a Job ID", "", ""

    job_id = job_id.strip()

    # Get job data
    job_data = None
    with job_lock:
        if job_id in extraction_jobs:
            job_data = extraction_jobs[job_id]

    if not job_data:
        job_data = get_job_from_db(job_id)

    if not job_data:
        return "❌ Job not found", "", ""

    if job_data.get('status') != 'completed':
        return "❌ Job not completed yet", "", ""

    # Format results
    slides_count = job_data.get('slides_count', 0)
    results_info = f"📊 Extraction Results:\n"
    results_info += f"  • Found {slides_count} slides\n"

    if job_data.get('pdf_path'):
        results_info += f"  • PDF generated: {os.path.basename(job_data['pdf_path'])}\n"

    if job_data.get('study_guide_path'):
        results_info += f"  • Study guide generated\n"

    if job_data.get('transcription'):
        results_info += f"  • Audio transcription completed\n"

    if job_data.get('concepts'):
        concepts = job_data['concepts']
        results_info += f"  • Extracted {len(concepts)} key concepts\n"

    if job_data.get('descriptions'):
        descriptions = job_data['descriptions']
        results_info += f"  • Generated descriptions for {len(descriptions)} slides\n"

    # Get slides info
    slides_info = ""
    if job_data.get('slides'):
        slides = job_data['slides']
        slides_info = f"📋 Slide Details:\n"
        for i, slide in enumerate(slides[:5]):  # Show first 5 slides
            slides_info += f"  {i+1}. {slide.get('filename', 'Unknown')}\n"
        if len(slides) > 5:
            slides_info += f"  ... and {len(slides) - 5} more slides\n"

    # Get study guide preview
    study_guide_preview = ""
    if job_data.get('study_guide_path') and os.path.exists(job_data['study_guide_path']):
        try:
            with open(job_data['study_guide_path'], 'r', encoding='utf-8') as f:
                content = f.read()
                study_guide_preview = f"📚 Study Guide Preview:\n{content[:500]}..."
        except Exception as e:
            study_guide_preview = f"📚 Study Guide: Error reading file - {e}"

    return results_info, slides_info, study_guide_preview

def download_pdf(job_id: str) -> Optional[str]:
    """Get PDF file path for download."""
    if not job_id.strip():
        return None

    job_id = job_id.strip()

    # Get job data
    job_data = None
    with job_lock:
        if job_id in extraction_jobs:
            job_data = extraction_jobs[job_id]

    if not job_data:
        job_data = get_job_from_db(job_id)

    if not job_data:
        return None

    pdf_path = job_data.get('pdf_path')
    if pdf_path and os.path.exists(pdf_path):
        return pdf_path

    return None

def download_study_guide(job_id: str) -> Optional[str]:
    """Get study guide file path for download."""
    if not job_id.strip():
        return None

    job_id = job_id.strip()

    # Get job data
    job_data = None
    with job_lock:
        if job_id in extraction_jobs:
            job_data = extraction_jobs[job_id]

    if not job_data:
        job_data = get_job_from_db(job_id)

    if not job_data:
        return None

    study_guide_path = job_data.get('study_guide_path')
    if study_guide_path and os.path.exists(study_guide_path):
        return study_guide_path

    return None

def get_slides_gallery(job_id: str) -> List[str]:
    """Get list of slide image paths for gallery display."""
    if not job_id.strip():
        return []

    job_id = job_id.strip()

    # Get job data
    job_data = None
    with job_lock:
        if job_id in extraction_jobs:
            job_data = extraction_jobs[job_id]

    if not job_data:
        job_data = get_job_from_db(job_id)

    if not job_data or job_data.get('status') != 'completed':
        return []

    output_dir = job_data.get('output_dir')
    if not output_dir or not os.path.exists(output_dir):
        return []

    # Find slide images
    slide_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        slide_files.extend(Path(output_dir).glob(ext))

    # Sort by filename
    slide_files.sort(key=lambda x: x.name)

    return [str(f) for f in slide_files]

def test_video_url(video_url: str) -> str:
    """Test if a video URL is accessible."""
    if not video_url.strip():
        return "❌ Please provide a video URL"

    if not BASIC_EXTRACTOR_AVAILABLE and not ENHANCED_AVAILABLE:
        return "❌ No slide extractor available to test video"

    try:
        # Quick test using basic validation
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            return f"✅ YouTube URL detected: {video_url}\n\nNote: Actual accessibility will be tested during extraction."
        else:
            return f"⚠️ Non-YouTube URL detected: {video_url}\n\nSupport may be limited. YouTube URLs are recommended."
    except Exception as e:
        return f"❌ Error testing URL: {str(e)}"

def list_recent_jobs() -> str:
    """List recent jobs from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT job_id, video_url, status, progress, created_at, slides_count
            FROM jobs
            ORDER BY created_at DESC
            LIMIT 10
        ''')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No jobs found"

        result = "📋 Recent Jobs:\n\n"
        for row in rows:
            job_id, video_url, status, progress, created_at, slides_count = row
            # Truncate URL for display
            display_url = video_url[:50] + "..." if len(video_url) > 50 else video_url
            result += f"🔹 {job_id}\n"
            result += f"   URL: {display_url}\n"
            result += f"   Status: {status} ({progress}%)\n"
            result += f"   Slides: {slides_count}\n"
            result += f"   Created: {created_at}\n\n"

        return result

    except Exception as e:
        return f"❌ Error listing jobs: {str(e)}"

def create_gradio_interface():
    """Create and configure the main Gradio interface."""

    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .feature-status {
        background: linear-gradient(90deg, #4CAF50, #45a049);
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .job-status {
        background: #f0f8ff;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
    }
    """

    with gr.Blocks(
        title="🎬 Slide Extractor - Full Stack",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as interface:

        # Header
        gr.Markdown("""
        # 🎬 Slide Extractor - Full Stack Application

        Extract slides from educational videos with AI-powered analysis.
        **No separate API required** - everything runs in this application!
        """)

        # Feature Status
        with gr.Row():
            feature_status = gr.Textbox(
                label="🔧 Available Features",
                value=get_feature_status(),
                interactive=False,
                elem_classes=["feature-status"]
            )

        # Main tabs
        with gr.Tabs():

            # Tab 1: Extract Slides
            with gr.TabItem("🚀 Extract Slides"):
                with gr.Row():
                    with gr.Column(scale=2):
                        # Video URL input
                        video_url = gr.Textbox(
                            label="📹 Video URL",
                            placeholder="https://www.youtube.com/watch?v=...",
                            info="Enter a YouTube video URL (other platforms may work but are not guaranteed)"
                        )

                        # Test video button
                        with gr.Row():
                            test_video_btn = gr.Button("🔍 Test Video URL", variant="secondary", size="sm")
                            video_test_result = gr.Textbox(
                                label="Test Result",
                                interactive=False,
                                visible=False
                            )

                        # Basic options
                        gr.Markdown("### ⚙️ Basic Options")
                        with gr.Row():
                            adaptive_sampling = gr.Checkbox(label="Adaptive Sampling", value=True)
                            extract_content = gr.Checkbox(label="Extract Content", value=True)
                        with gr.Row():
                            organize_slides = gr.Checkbox(label="Organize Slides", value=True)
                            generate_pdf = gr.Checkbox(label="Generate PDF", value=True)

                        # AI Features (collapsible)
                        with gr.Accordion("🤖 AI Features (Optional)", open=False):
                            gemini_api_key = gr.Textbox(
                                label="🔑 Gemini API Key",
                                type="password",
                                placeholder="Enter your Google Gemini API key for AI features",
                                info="Required for transcription, OCR enhancement, and slide descriptions"
                            )

                            gr.Markdown("**AI Processing Options:**")
                            with gr.Row():
                                enable_transcription = gr.Checkbox(
                                    label="🎤 Audio Transcription",
                                    info="Extract and transcribe audio content"
                                )
                                enable_ocr_enhancement = gr.Checkbox(
                                    label="📝 OCR Enhancement",
                                    info="Improve text recognition accuracy"
                                )
                            with gr.Row():
                                enable_concept_extraction = gr.Checkbox(
                                    label="🧠 Concept Extraction",
                                    info="Identify key concepts and topics"
                                )
                                enable_slide_descriptions = gr.Checkbox(
                                    label="📋 Slide Descriptions",
                                    info="Generate AI descriptions for each slide"
                                )

                        # Robust Download Options
                        if ROBUST_EXTRACTOR_AVAILABLE:
                            gr.Markdown("**🚀 Robust Download Options:**")
                            enable_proxy = gr.Checkbox(
                                label="🌐 Enable Proxy Methods",
                                info="Use proxy services for better success rates (requires proxy configuration)"
                            )
                        else:
                            enable_proxy = gr.Checkbox(visible=False)  # Hidden if not available

                        # Start extraction button
                        extract_btn = gr.Button(
                            "🎬 Start Extraction",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column(scale=1):
                        # Status display
                        gr.Markdown("### 📊 Extraction Status")
                        extraction_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=3,
                            elem_classes=["job-status"]
                        )
                        job_id_display = gr.Textbox(
                            label="Job ID",
                            interactive=False
                        )
                        progress_display = gr.Textbox(
                            label="Progress",
                            interactive=False
                        )

                        # Manual refresh note
                        gr.Markdown("💡 **Tip:** Use the refresh button in the Monitor Jobs tab to check status updates.")

            # Tab 2: Monitor Jobs
            with gr.TabItem("📊 Monitor Jobs"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🔍 Job Lookup")
                        job_id_input = gr.Textbox(
                            label="Job ID",
                            placeholder="Enter Job ID to check status"
                        )

                        with gr.Row():
                            check_status_btn = gr.Button("📊 Check Status", variant="secondary")
                            refresh_status_btn = gr.Button("🔄 Refresh", variant="secondary")

                        gr.Markdown("### 📋 Recent Jobs")
                        list_jobs_btn = gr.Button("📋 List Recent Jobs", variant="secondary")
                        recent_jobs_display = gr.Textbox(
                            label="Recent Jobs",
                            interactive=False,
                            lines=10
                        )

                    with gr.Column():
                        gr.Markdown("### 📈 Job Status")
                        job_status_display = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=3
                        )
                        job_progress_display = gr.Textbox(
                            label="Progress",
                            interactive=False
                        )

                        gr.Markdown("### 📥 Results")
                        get_results_btn = gr.Button("📥 Get Results", variant="primary")
                        job_results_display = gr.Textbox(
                            label="Results Summary",
                            interactive=False,
                            lines=8
                        )

            # Tab 3: View Results
            with gr.TabItem("📁 View Results"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📥 Download Files")
                        download_job_id = gr.Textbox(
                            label="Job ID",
                            placeholder="Enter Job ID to download files"
                        )

                        with gr.Row():
                            download_pdf_btn = gr.Button("📄 Download PDF", variant="secondary")
                            download_study_guide_btn = gr.Button("📚 Download Study Guide", variant="secondary")

                        # File download outputs
                        pdf_download = gr.File(label="PDF Download", visible=False)
                        study_guide_download = gr.File(label="Study Guide Download", visible=False)

                        gr.Markdown("### 🖼️ Slide Gallery")
                        gallery_job_id = gr.Textbox(
                            label="Job ID for Gallery",
                            placeholder="Enter Job ID to view slides"
                        )
                        show_gallery_btn = gr.Button("🖼️ Show Slides", variant="primary")

                    with gr.Column():
                        # Slide gallery
                        slides_gallery = gr.Gallery(
                            label="Extracted Slides",
                            show_label=True,
                            elem_id="slides_gallery",
                            columns=3,
                            rows=2,
                            height="auto"
                        )

        # Event handlers
        def handle_test_video(url):
            result = test_video_url(url)
            return result, gr.update(visible=True)

        def handle_extract_slides(url, adaptive, content, organize, pdf, transcription,
                                ocr, concepts, descriptions, proxy, api_key):
            return start_extraction(url, adaptive, content, organize, pdf,
                                  transcription, ocr, concepts, descriptions, proxy, api_key)

        def handle_check_status(job_id):
            status, job_id_out, status_short, progress = check_job_status(job_id)
            return status, job_id_out, status_short, progress

        def handle_get_results(job_id):
            results, slides_info, study_guide = get_job_results(job_id)
            return results, slides_info, study_guide

        def handle_download_pdf(job_id):
            pdf_path = download_pdf(job_id)
            if pdf_path:
                return gr.update(value=pdf_path, visible=True)
            return gr.update(visible=False)

        def handle_download_study_guide(job_id):
            guide_path = download_study_guide(job_id)
            if guide_path:
                return gr.update(value=guide_path, visible=True)
            return gr.update(visible=False)

        def handle_show_gallery(job_id):
            slide_paths = get_slides_gallery(job_id)
            return slide_paths

        def handle_list_jobs():
            return list_recent_jobs()

        # Note: Auto-refresh removed for Gradio 3.x compatibility

        # Set up event handlers
        test_video_btn.click(
            fn=handle_test_video,
            inputs=[video_url],
            outputs=[video_test_result, video_test_result]
        )

        extract_btn.click(
            fn=handle_extract_slides,
            inputs=[
                video_url, adaptive_sampling, extract_content, organize_slides,
                generate_pdf, enable_transcription, enable_ocr_enhancement,
                enable_concept_extraction, enable_slide_descriptions, enable_proxy, gemini_api_key
            ],
            outputs=[extraction_status, job_id_display, progress_display]
        )

        check_status_btn.click(
            fn=handle_check_status,
            inputs=[job_id_input],
            outputs=[job_status_display, job_id_input, job_status_display, job_progress_display]
        )

        refresh_status_btn.click(
            fn=handle_check_status,
            inputs=[job_id_input],
            outputs=[job_status_display, job_id_input, job_status_display, job_progress_display]
        )

        get_results_btn.click(
            fn=handle_get_results,
            inputs=[job_id_input],
            outputs=[job_results_display, job_results_display, job_results_display]
        )

        download_pdf_btn.click(
            fn=handle_download_pdf,
            inputs=[download_job_id],
            outputs=[pdf_download]
        )

        download_study_guide_btn.click(
            fn=handle_download_study_guide,
            inputs=[download_job_id],
            outputs=[study_guide_download]
        )

        show_gallery_btn.click(
            fn=handle_show_gallery,
            inputs=[gallery_job_id],
            outputs=[slides_gallery]
        )

        list_jobs_btn.click(
            fn=handle_list_jobs,
            outputs=[recent_jobs_display]
        )

        # Note: Auto-refresh timer not available in Gradio 3.x
        # Users can manually refresh using the refresh button

    return interface

def get_demo_videos():
    """Get list of demo videos for testing."""
    return [
        {
            'title': 'Khan Academy - Introduction to Algebra',
            'url': 'https://www.youtube.com/watch?v=NybHckSEQBI',
            'description': 'Educational math content, good for testing'
        },
        {
            'title': 'MIT OpenCourseWare - Physics Lecture',
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
    ]

def print_startup_info():
    """Print startup information."""
    print("=" * 60)
    print("🎬 SLIDE EXTRACTOR - FULL STACK GRADIO APPLICATION")
    print("=" * 60)
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"📂 Slides Output: {SLIDES_FOLDER}")
    print(f"🗄️ Database: {DB_PATH}")
    print()
    print("🔧 Available Features:")
    print(f"  • Basic Extractor: {'✅' if BASIC_EXTRACTOR_AVAILABLE else '❌'}")
    print(f"  • Enhanced Extractor: {'✅' if ENHANCED_AVAILABLE else '❌'}")
    print(f"  • Content Analyzer: {'✅' if CONTENT_ANALYZER_AVAILABLE else '❌'}")
    print(f"  • Transcription: {'✅' if TRANSCRIPTION_AVAILABLE else '❌'}")
    print(f"  • OCR Enhancement: {'✅' if OCR_ENHANCEMENT_AVAILABLE else '❌'}")
    print(f"  • Slide Descriptions: {'✅' if SLIDE_DESCRIPTIONS_AVAILABLE else '❌'}")
    print()
    print("📺 Demo Videos Available:")
    for i, video in enumerate(get_demo_videos(), 1):
        print(f"  {i}. {video['title']}")
        print(f"     {video['url']}")
        print(f"     {video['description']}")
        print()
    print("🌐 Starting Gradio interface...")
    print("=" * 60)

if __name__ == "__main__":
    # Print startup information
    print_startup_info()

    # Create and launch the interface
    interface = create_gradio_interface()

    # Launch configuration
    launch_config = {
        "server_name": "0.0.0.0",
        "server_port": 7860,
        "share": True,  # Create public link
        "debug": True,
        "show_error": True,
        "quiet": False
    }

    print(f"🚀 Launching Gradio interface on port {launch_config['server_port']}...")
    print(f"🔗 Local URL: http://localhost:{launch_config['server_port']}")
    if launch_config['share']:
        print("🌍 Public URL will be generated...")
    print()
    print("💡 Tips:")
    print("  • Use the demo videos above for testing")
    print("  • Try shorter videos (under 10 minutes) for better success rates")
    print("  • Educational channels often have less restrictive content")
    print("  • If one video fails, try a different one")
    print()

    try:
        interface.launch(**launch_config)
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error launching application: {e}")
        print("💡 Try installing missing dependencies:")
        print("   pip install gradio opencv-python numpy pytesseract Pillow")
        print("   pip install scikit-image nltk yt-dlp reportlab matplotlib")
    finally:
        print("\n👋 Goodbye!")
