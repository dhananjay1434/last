#!/usr/bin/env python3
"""
YouTube 2025 Downloader
Updated downloader that addresses YouTube's new PO Token restrictions and rate limiting
"""

import os
import sys
import tempfile
import subprocess
import time
import random
import logging
import json
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class YouTube2025DownloadResult:
    """Result of a video download operation with 2025 restrictions"""
    success: bool
    video_path: Optional[str] = None
    error: Optional[str] = None
    method: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    rate_limited: bool = False
    retry_count: int = 0

class YouTube2025Downloader:
    """Enhanced YouTube downloader for 2025 restrictions"""
    
    def __init__(self, output_dir: str = None, enable_rate_limiting: bool = True):
        self.output_dir = output_dir or tempfile.mkdtemp()
        self.enable_rate_limiting = enable_rate_limiting
        self.last_download_time = 0
        self.min_delay = 5  # Minimum 5 seconds between downloads
        self.max_delay = 10  # Maximum 10 seconds between downloads
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"YouTube2025Downloader initialized with rate limiting: {enable_rate_limiting}")
    
    def _apply_rate_limiting(self):
        """Apply rate limiting between downloads"""
        if not self.enable_rate_limiting:
            return
            
        current_time = time.time()
        time_since_last = current_time - self.last_download_time
        
        if time_since_last < self.min_delay:
            delay = self.min_delay - time_since_last + random.uniform(1, 3)
            logger.info(f"Rate limiting: waiting {delay:.1f}s before download")
            time.sleep(delay)
        
        self.last_download_time = time.time()
    
    def _get_enhanced_config(self) -> Dict[str, Any]:
        """Get enhanced yt-dlp configuration for 2025 restrictions"""
        return {
            'format': 'best[height<=720]/best',
            'sleep_interval': self.min_delay,
            'max_sleep_interval': self.max_delay,
            'retries': 3,
            'fragment_retries': 3,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        }
    
    def download_video(self, url: str, max_retries: int = 3) -> YouTube2025DownloadResult:
        """
        Download YouTube video with 2025 restrictions handling
        
        Args:
            url: YouTube video URL
            max_retries: Maximum number of retry attempts
            
        Returns:
            YouTube2025DownloadResult object
        """
        
        # Apply rate limiting
        self._apply_rate_limiting()
        
        # Enhanced download strategies for 2025
        strategies = [
            self._strategy_mweb_client,
            self._strategy_web_client_with_delays,
            self._strategy_mobile_fallback,
            self._strategy_simple_fallback
        ]
        
        for strategy_idx, strategy in enumerate(strategies, 1):
            logger.info(f"Trying strategy {strategy_idx}/{len(strategies)}: {strategy.__name__}")
            
            for attempt in range(max_retries):
                try:
                    result = strategy(url, attempt + 1)
                    
                    if result.success:
                        logger.info(f"✅ Strategy {strategy_idx} succeeded on attempt {attempt + 1}")
                        result.method = f"{strategy.__name__} (attempt {attempt + 1})"
                        result.retry_count = attempt
                        return result
                    else:
                        logger.warning(f"❌ Strategy {strategy_idx} attempt {attempt + 1} failed: {result.error}")
                        
                        # Check for rate limiting
                        if "rate limit" in str(result.error).lower() or "try again later" in str(result.error).lower():
                            result.rate_limited = True
                            logger.warning("🚨 Rate limit detected, increasing delays")
                            self.min_delay = min(self.min_delay * 1.5, 30)  # Increase delay up to 30s
                        
                    # Wait between attempts with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(2, 5)
                        logger.info(f"Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"Strategy {strategy_idx} attempt {attempt + 1} exception: {e}")
        
        return YouTube2025DownloadResult(
            success=False,
            error="All download strategies failed with 2025 restrictions",
            retry_count=max_retries
        )
    
    def _strategy_mweb_client(self, url: str, attempt: int) -> YouTube2025DownloadResult:
        """Strategy 1: Use mweb client (recommended for 2025)"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "best[height<=720]/best",
            "--output", output_template,
            "--extractor-args", "youtube:player_client=mweb",
            "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "--sleep-interval", str(self.min_delay),
            "--max-sleep-interval", str(self.max_delay),
            "--retries", "3",
            "--fragment-retries", "3",
            "--no-check-certificates",
            "--ignore-errors",
            "--no-warnings",
            url
        ]
        
        return self._execute_command(cmd, "mweb_client_2025")
    
    def _strategy_web_client_with_delays(self, url: str, attempt: int) -> YouTube2025DownloadResult:
        """Strategy 2: Web client with enhanced delays"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "best[height<=480]/worst",
            "--output", output_template,
            "--extractor-args", "youtube:player_client=web",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--sleep-interval", str(self.min_delay + 2),
            "--max-sleep-interval", str(self.max_delay + 5),
            "--retries", "2",
            "--no-check-certificates",
            url
        ]
        
        return self._execute_command(cmd, "web_client_with_delays")
    
    def _strategy_mobile_fallback(self, url: str, attempt: int) -> YouTube2025DownloadResult:
        """Strategy 3: Mobile client fallback"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "worst[ext=mp4]/worst",
            "--output", output_template,
            "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "--extractor-args", "youtube:player_client=android",
            "--sleep-interval", str(self.min_delay + 3),
            "--retries", "2",
            url
        ]
        
        return self._execute_command(cmd, "mobile_fallback")
    
    def _strategy_simple_fallback(self, url: str, attempt: int) -> YouTube2025DownloadResult:
        """Strategy 4: Simple fallback with minimal options"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "worst",
            "--output", output_template,
            "--sleep-interval", str(self.min_delay + 5),
            "--ignore-errors",
            "--no-warnings",
            url
        ]
        
        return self._execute_command(cmd, "simple_fallback")
    
    def _execute_command(self, cmd: list, strategy_name: str) -> YouTube2025DownloadResult:
        """Execute yt-dlp command and return result"""
        try:
            logger.info(f"Executing {strategy_name} strategy with 2025 enhancements")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # Increased timeout
            
            if result.returncode == 0:
                # Find downloaded file
                for file in os.listdir(self.output_dir):
                    if file.startswith("video_") and not file.endswith(".txt"):
                        video_path = os.path.join(self.output_dir, file)
                        if os.path.getsize(video_path) > 1024:  # At least 1KB
                            return YouTube2025DownloadResult(
                                success=True,
                                video_path=video_path,
                                method=strategy_name
                            )
                
                return YouTube2025DownloadResult(
                    success=False,
                    error="No valid video file found"
                )
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                
                # Check for specific 2025 errors
                rate_limited = any(phrase in error_msg.lower() for phrase in [
                    "rate limit", "try again later", "too many requests", 
                    "temporarily unavailable", "quota exceeded"
                ])
                
                return YouTube2025DownloadResult(
                    success=False,
                    error=error_msg,
                    rate_limited=rate_limited
                )
                
        except subprocess.TimeoutExpired:
            return YouTube2025DownloadResult(
                success=False,
                error="Download timeout (increased for 2025 restrictions)"
            )
        except Exception as e:
            return YouTube2025DownloadResult(
                success=False,
                error=str(e)
            )
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            # Clean up any temporary files
            for file in os.listdir(self.output_dir):
                if file.endswith('.tmp') or file.endswith('.part'):
                    os.unlink(os.path.join(self.output_dir, file))
        except Exception as e:
            logger.warning(f"Failed to cleanup: {e}")
    
    def get_success_stats(self) -> Dict[str, Any]:
        """Get statistics about download success rates"""
        return {
            'rate_limiting_enabled': self.enable_rate_limiting,
            'current_min_delay': self.min_delay,
            'current_max_delay': self.max_delay,
            'last_download_time': self.last_download_time,
            'recommendations': [
                "Use rate limiting to avoid YouTube restrictions",
                "Expect longer download times due to 2025 changes",
                "Consider alternative video sources for critical content",
                "Monitor success rates and adjust delays as needed"
            ]
        }

def test_2025_downloader():
    """Test the 2025 YouTube downloader"""
    test_urls = [
        "https://www.youtube.com/watch?v=kuIfHJEsPkY",  # Your test video
        "https://www.youtube.com/watch?v=NybHckSEQBI"   # Khan Academy
    ]
    
    downloader = YouTube2025Downloader(enable_rate_limiting=True)
    
    for url in test_urls:
        print(f"\n🧪 Testing 2025 downloader: {url}")
        
        result = downloader.download_video(url)
        
        if result.success:
            print(f"✅ Success: {result.video_path}")
            print(f"🔧 Method: {result.method}")
            print(f"🔄 Retries: {result.retry_count}")
        else:
            print(f"❌ Failed: {result.error}")
            print(f"🚨 Rate limited: {result.rate_limited}")
        
        print(f"📊 Stats: {downloader.get_success_stats()}")
    
    downloader.cleanup()

if __name__ == "__main__":
    test_2025_downloader()
