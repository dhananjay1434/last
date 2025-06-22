#!/usr/bin/env python3
"""
Robust Slide Extractor with Enhanced YouTube Download Capabilities
Integrates the robust downloader with the existing slide extraction system
"""

import os
import sys
import logging
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from robust_youtube_downloader import RobustYouTubeDownloader, DownloadResult
    ROBUST_DOWNLOADER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Robust downloader not available: {e}")
    ROBUST_DOWNLOADER_AVAILABLE = False

try:
    from slide_extractor import SlideExtractor
    SLIDE_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Slide extractor not available: {e}")
    SLIDE_EXTRACTOR_AVAILABLE = False

try:
    from enhanced_slide_extractor import EnhancedSlideExtractor
    ENHANCED_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced slide extractor not available: {e}")
    ENHANCED_EXTRACTOR_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RobustSlideExtractor")

class RobustSlideExtractor:
    """
    Enhanced slide extractor with robust YouTube download capabilities
    """
    
    def __init__(self, video_url: str, output_dir: str = "slides", 
                 enable_proxy: bool = False, use_enhanced: bool = True, **kwargs):
        """
        Initialize the robust slide extractor
        
        Args:
            video_url: YouTube video URL
            output_dir: Directory to save slides
            enable_proxy: Enable proxy download methods
            use_enhanced: Use enhanced slide extractor if available
            **kwargs: Additional arguments for slide extractor
        """
        self.video_url = video_url
        self.output_dir = output_dir
        self.enable_proxy = enable_proxy
        self.use_enhanced = use_enhanced and ENHANCED_EXTRACTOR_AVAILABLE
        self.kwargs = kwargs
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.downloader = None
        self.extractor = None
        self.download_result = None
        self.video_path = None
        
        # Download statistics
        self.stats = {
            'download_method': None,
            'download_success': False,
            'extraction_success': False,
            'slides_count': 0,
            'errors': []
        }
        
        logger.info(f"RobustSlideExtractor initialized for: {video_url}")
    
    def _setup_downloader(self) -> bool:
        """Setup the robust YouTube downloader"""
        if not ROBUST_DOWNLOADER_AVAILABLE:
            self.stats['errors'].append("Robust downloader not available")
            return False
        
        try:
            # Create temporary directory for video download
            self.temp_dir = tempfile.mkdtemp(prefix="robust_video_")
            self.downloader = RobustYouTubeDownloader(
                output_dir=self.temp_dir,
                enable_proxy=self.enable_proxy
            )
            return True
        except Exception as e:
            error_msg = f"Failed to setup downloader: {e}"
            self.stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
    
    def _download_video(self) -> bool:
        """Download the video using robust methods"""
        if not self.downloader:
            return False
        
        try:
            logger.info("Starting robust video download...")
            self.download_result = self.downloader.download(self.video_url)
            
            if self.download_result.success:
                self.video_path = self.download_result.video_path
                self.stats['download_method'] = self.download_result.method
                self.stats['download_success'] = True
                logger.info(f"✅ Video downloaded successfully using: {self.download_result.method}")
                return True
            else:
                error_msg = f"Video download failed: {self.download_result.error}"
                self.stats['errors'].append(error_msg)
                logger.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Exception during video download: {e}"
            self.stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
    
    def _setup_slide_extractor(self) -> bool:
        """Setup the slide extractor with the downloaded video"""
        if not self.video_path or not os.path.exists(self.video_path):
            self.stats['errors'].append("No video file available for slide extraction")
            return False
        
        try:
            # Choose extractor type
            if self.use_enhanced and ENHANCED_EXTRACTOR_AVAILABLE:
                logger.info("Using Enhanced Slide Extractor")
                self.extractor = EnhancedSlideExtractor(
                    video_url=self.video_path,  # Use local file path
                    output_dir=self.output_dir,
                    **self.kwargs
                )
            elif SLIDE_EXTRACTOR_AVAILABLE:
                logger.info("Using Basic Slide Extractor")
                self.extractor = SlideExtractor(
                    video_url=self.video_path,  # Use local file path
                    output_dir=self.output_dir,
                    **self.kwargs
                )
            else:
                self.stats['errors'].append("No slide extractor available")
                return False
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to setup slide extractor: {e}"
            self.stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
    
    def _extract_slides(self) -> bool:
        """Extract slides from the downloaded video"""
        if not self.extractor:
            return False
        
        try:
            logger.info("Starting slide extraction...")
            success = self.extractor.extract_slides()
            
            if success:
                slides = self.extractor.get_slides()
                self.stats['slides_count'] = len(slides) if slides else 0
                self.stats['extraction_success'] = True
                logger.info(f"✅ Extracted {self.stats['slides_count']} slides")
                return True
            else:
                self.stats['errors'].append("Slide extraction failed")
                logger.error("❌ Slide extraction failed")
                return False
                
        except Exception as e:
            error_msg = f"Exception during slide extraction: {e}"
            self.stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
    
    def extract_slides(self) -> bool:
        """
        Main method to extract slides with robust download
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("🚀 Starting robust slide extraction process")
        
        # Step 1: Setup downloader
        if not self._setup_downloader():
            logger.error("❌ Failed to setup downloader")
            return False
        
        # Step 2: Download video
        if not self._download_video():
            logger.error("❌ Failed to download video")
            return False
        
        # Step 3: Setup slide extractor
        if not self._setup_slide_extractor():
            logger.error("❌ Failed to setup slide extractor")
            return False
        
        # Step 4: Extract slides
        if not self._extract_slides():
            logger.error("❌ Failed to extract slides")
            return False
        
        logger.info("🎉 Robust slide extraction completed successfully!")
        return True
    
    def get_slides(self) -> Optional[List[Dict[str, Any]]]:
        """Get the extracted slides"""
        if self.extractor and hasattr(self.extractor, 'get_slides'):
            return self.extractor.get_slides()
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get video and extraction metadata"""
        metadata = {
            'video_url': self.video_url,
            'output_dir': self.output_dir,
            'stats': self.stats.copy()
        }
        
        # Add download metadata
        if self.download_result and self.download_result.metadata:
            metadata['video_info'] = self.download_result.metadata
        
        # Add extractor metadata
        if self.extractor and hasattr(self.extractor, 'get_metadata'):
            metadata['extraction_info'] = self.extractor.get_metadata()
        
        return metadata
    
    def convert_slides_to_pdf(self) -> Optional[str]:
        """Convert slides to PDF"""
        if self.extractor and hasattr(self.extractor, 'convert_slides_to_pdf'):
            try:
                return self.extractor.convert_slides_to_pdf()
            except Exception as e:
                logger.error(f"PDF conversion failed: {e}")
                return None
        return None
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup: {e}")
    
    def get_success_rate_info(self) -> Dict[str, Any]:
        """Get information about download success rates"""
        return {
            'download_successful': self.stats['download_success'],
            'extraction_successful': self.stats['extraction_success'],
            'method_used': self.stats['download_method'],
            'slides_extracted': self.stats['slides_count'],
            'errors_encountered': len(self.stats['errors']),
            'error_details': self.stats['errors']
        }

# Convenience function for easy integration
def extract_slides_robust(video_url: str, output_dir: str = "slides", 
                         enable_proxy: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Extract slides from YouTube video with robust download methods
    
    Args:
        video_url: YouTube video URL
        output_dir: Directory to save slides
        enable_proxy: Enable proxy download methods
        **kwargs: Additional arguments for slide extractor
        
    Returns:
        Dict with results and metadata
    """
    extractor = RobustSlideExtractor(
        video_url=video_url,
        output_dir=output_dir,
        enable_proxy=enable_proxy,
        **kwargs
    )
    
    try:
        success = extractor.extract_slides()
        
        result = {
            'success': success,
            'slides': extractor.get_slides() if success else None,
            'metadata': extractor.get_metadata(),
            'pdf_path': extractor.convert_slides_to_pdf() if success else None,
            'stats': extractor.get_success_rate_info()
        }
        
        return result
        
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    # Test the robust slide extractor
    test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"  # Khan Academy
    
    print("🧪 Testing Robust Slide Extractor")
    print("=" * 40)
    
    result = extract_slides_robust(
        video_url=test_url,
        output_dir="test_slides",
        adaptive_sampling=True,
        extract_content=True
    )
    
    if result['success']:
        print("✅ Robust slide extraction successful!")
        print(f"📊 Slides extracted: {len(result['slides']) if result['slides'] else 0}")
        print(f"🔧 Download method: {result['stats']['method_used']}")
        print(f"📄 PDF generated: {'Yes' if result['pdf_path'] else 'No'}")
    else:
        print("❌ Robust slide extraction failed")
        print(f"🔍 Errors: {result['stats']['error_details']}")
    
    print(f"\n📈 Success Rate Info:")
    for key, value in result['stats'].items():
        print(f"  {key}: {value}")
