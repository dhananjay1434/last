import gradio as gr
import requests
import json
import time
import os
import threading
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

# Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', "http://127.0.0.1:5000")
POLL_INTERVAL = 2  # seconds
MAX_POLL_ATTEMPTS = 300  # 10 minutes max polling

def check_api_status() -> Tuple[bool, str]:
    """Check if the API server is running and get feature status."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            features = []
            if data.get('enhanced_features'):
                features.append("Enhanced Features")
            if data.get('transcription'):
                features.append("Transcription")
            if data.get('ocr_enhancement'):
                features.append("OCR Enhancement")
            if data.get('advanced_features'):
                features.append("Advanced Features")
            
            feature_text = f"Available features: {', '.join(features)}" if features else "Basic features only"
            return True, f"✅ API Server Online - {feature_text}"
        else:
            return False, f"❌ API Server Error: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"❌ API Server Offline: {str(e)}"

def extract_slides(
    video_url: str,
    adaptive_sampling: bool,
    extract_content: bool,
    organize_slides: bool,
    generate_pdf: bool,
    enable_transcription: bool,
    enable_ocr_enhancement: bool,
    enable_concept_extraction: bool,
    enable_slide_descriptions: bool,
    gemini_api_key: str = ""
) -> Tuple[str, str, str]:
    """Start slide extraction and return job status."""
    
    # Validate inputs
    if not video_url.strip():
        return "❌ Error: Please provide a video URL", "", ""
    
    # Check API status first
    api_online, status_msg = check_api_status()
    if not api_online:
        return f"❌ {status_msg}", "", ""
    
    # Prepare request data
    request_data = {
        "video_url": video_url.strip(),
        "adaptive_sampling": adaptive_sampling,
        "extract_content": extract_content,
        "organize_slides": organize_slides,
        "generate_pdf": generate_pdf,
        "enable_transcription": enable_transcription,
        "enable_ocr_enhancement": enable_ocr_enhancement,
        "enable_concept_extraction": enable_concept_extraction,
        "enable_slide_descriptions": enable_slide_descriptions
    }
    
    # Add API key if provided
    if gemini_api_key.strip():
        request_data["gemini_api_key"] = gemini_api_key.strip()
    
    try:
        # Start extraction
        response = requests.post(
            f"{API_BASE_URL}/api/extract",
            json=request_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            return (
                f"✅ Extraction started successfully! Job ID: {job_id}",
                f"Job ID: {job_id}",
                "🔄 Processing..."
            )
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('error', f'HTTP {response.status_code}')
            return f"❌ Error starting extraction: {error_msg}", "", ""
            
    except requests.exceptions.RequestException as e:
        return f"❌ Network error: {str(e)}", "", ""
    except json.JSONDecodeError:
        return "❌ Invalid response from server", "", ""

def check_job_status(job_id: str) -> Tuple[str, str, str]:
    """Check the status of a job."""
    if not job_id.strip():
        return "❌ Please provide a Job ID", "", ""
    
    try:
        # Extract numeric job ID
        job_id_num = job_id.strip().replace("Job ID: ", "")
        
        response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id_num}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)
            message = data.get('message', '')
            error = data.get('error')
            
            # Format status message
            if status == 'completed':
                slides_count = data.get('slides_count', 0)
                has_pdf = data.get('has_pdf', False)
                has_study_guide = data.get('has_study_guide', False)
                
                status_msg = f"✅ Completed! Found {slides_count} slides"
                if has_pdf:
                    status_msg += " | PDF available"
                if has_study_guide:
                    status_msg += " | Study guide available"
                    
                return status_msg, f"Job ID: {job_id_num}", "✅ Completed"
                
            elif status == 'failed':
                return f"❌ Failed: {error or 'Unknown error'}", f"Job ID: {job_id_num}", "❌ Failed"
                
            else:
                return f"🔄 {status.title()}: {message} ({progress}%)", f"Job ID: {job_id_num}", f"🔄 {progress}%"
                
        elif response.status_code == 404:
            return "❌ Job not found", "", ""
        else:
            return f"❌ Error checking status: HTTP {response.status_code}", "", ""
            
    except requests.exceptions.RequestException as e:
        return f"❌ Network error: {str(e)}", "", ""
    except Exception as e:
        return f"❌ Error: {str(e)}", "", ""

def get_job_results(job_id: str) -> Tuple[str, str]:
    """Get results from a completed job."""
    if not job_id.strip():
        return "❌ Please provide a Job ID", ""
    
    try:
        job_id_num = job_id.strip().replace("Job ID: ", "")
        
        # Get job status first
        status_response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id_num}", timeout=10)
        if status_response.status_code != 200:
            return "❌ Job not found", ""
            
        status_data = status_response.json()
        if status_data.get('status') != 'completed':
            return "❌ Job not completed yet", ""
        
        # Get slides
        slides_response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id_num}/slides", timeout=10)
        slides_info = ""
        if slides_response.status_code == 200:
            slides_data = slides_response.json()
            slides = slides_data.get('slides', [])
            slides_info = f"📊 Found {len(slides)} slides\n"
            
            # Show first few slide details
            for i, slide in enumerate(slides[:3]):
                slides_info += f"  • Slide {i+1}: {slide.get('filename', 'Unknown')}\n"
            if len(slides) > 3:
                slides_info += f"  • ... and {len(slides) - 3} more slides\n"
        
        # Get study guide if available
        study_guide_info = ""
        if status_data.get('has_study_guide'):
            study_response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id_num}/study-guide", timeout=10)
            if study_response.status_code == 200:
                study_data = study_response.json()
                content = study_data.get('content', '')
                study_guide_info = f"\n📚 Study Guide Preview:\n{content[:500]}..."
        
        # PDF info
        pdf_info = ""
        if status_data.get('has_pdf'):
            pdf_info = f"\n📄 PDF available for download at: {API_BASE_URL}/api/jobs/{job_id_num}/pdf"
        
        return f"✅ Job Results:\n{slides_info}{pdf_info}{study_guide_info}", slides_info
        
    except Exception as e:
        return f"❌ Error getting results: {str(e)}", ""

# Create Gradio interface
def create_interface():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(title="Slide Extractor API", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🎬 Slide Extractor API Interface
        
        Extract slides from educational videos with AI-powered analysis.
        """)
        
        # API Status
        with gr.Row():
            api_status = gr.Textbox(
                label="API Status",
                value="Checking...",
                interactive=False,
                container=True
            )
            refresh_btn = gr.Button("🔄 Refresh Status", size="sm")
        
        gr.Markdown("---")
        
        # Main extraction interface
        with gr.Tab("🚀 Extract Slides"):
            with gr.Row():
                with gr.Column(scale=2):
                    video_url = gr.Textbox(
                        label="Video URL",
                        placeholder="https://www.youtube.com/watch?v=...",
                        info="Enter a YouTube video URL"
                    )
                    
                    with gr.Row():
                        adaptive_sampling = gr.Checkbox(label="Adaptive Sampling", value=True)
                        extract_content = gr.Checkbox(label="Extract Content", value=True)
                        organize_slides = gr.Checkbox(label="Organize Slides", value=True)
                        generate_pdf = gr.Checkbox(label="Generate PDF", value=True)
                    
                    with gr.Accordion("🤖 AI Features", open=False):
                        gemini_api_key = gr.Textbox(
                            label="Gemini API Key (Optional)",
                            type="password",
                            placeholder="Enter your Gemini API key for AI features"
                        )
                        with gr.Row():
                            enable_transcription = gr.Checkbox(label="Transcription")
                            enable_ocr_enhancement = gr.Checkbox(label="OCR Enhancement")
                        with gr.Row():
                            enable_concept_extraction = gr.Checkbox(label="Concept Extraction")
                            enable_slide_descriptions = gr.Checkbox(label="Slide Descriptions")
                    
                    extract_btn = gr.Button("🎬 Start Extraction", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    extraction_status = gr.Textbox(
                        label="Extraction Status",
                        interactive=False,
                        lines=3
                    )
                    job_id_display = gr.Textbox(
                        label="Job ID",
                        interactive=False
                    )
                    progress_display = gr.Textbox(
                        label="Progress",
                        interactive=False
                    )
        
        # Job monitoring interface
        with gr.Tab("📊 Monitor Job"):
            with gr.Row():
                with gr.Column():
                    job_id_input = gr.Textbox(
                        label="Job ID",
                        placeholder="Enter Job ID to check status"
                    )
                    with gr.Row():
                        check_status_btn = gr.Button("📊 Check Status", variant="secondary")
                        get_results_btn = gr.Button("📥 Get Results", variant="primary")
                
                with gr.Column():
                    job_status_display = gr.Textbox(
                        label="Job Status",
                        interactive=False,
                        lines=3
                    )
                    job_results_display = gr.Textbox(
                        label="Job Results",
                        interactive=False,
                        lines=8
                    )
        
        # Event handlers
        def update_api_status():
            _, status = check_api_status()
            return status
        
        # Set up event handlers
        refresh_btn.click(
            fn=update_api_status,
            outputs=[api_status]
        )
        
        extract_btn.click(
            fn=extract_slides,
            inputs=[
                video_url, adaptive_sampling, extract_content, organize_slides,
                generate_pdf, enable_transcription, enable_ocr_enhancement,
                enable_concept_extraction, enable_slide_descriptions, gemini_api_key
            ],
            outputs=[extraction_status, job_id_display, progress_display]
        )
        
        check_status_btn.click(
            fn=check_job_status,
            inputs=[job_id_input],
            outputs=[job_status_display, job_id_input, progress_display]
        )
        
        get_results_btn.click(
            fn=get_job_results,
            inputs=[job_id_input],
            outputs=[job_results_display, job_status_display]
        )
        
        # Initialize API status
        interface.load(
            fn=update_api_status,
            outputs=[api_status]
        )
    
    return interface

if __name__ == "__main__":
    # Create and launch the interface
    interface = create_interface()
    
    print("🚀 Starting Gradio interface...")
    print(f"📡 API Server: {API_BASE_URL}")
    print("🌐 Gradio will be available at: http://127.0.0.1:7860")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        debug=True
    )
