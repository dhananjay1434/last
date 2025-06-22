#!/usr/bin/env python3
"""
Advanced YouTube Downloader with Cookie Support and Bot Detection Bypass
Handles YouTube's enhanced bot detection and rate limiting
"""

import os
import subprocess
import tempfile
import logging
import time
import random
import json
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class AdvancedYouTubeDownloader:
    """Advanced YouTube downloader with cookie support and bot detection bypass"""
    
    def __init__(self, output_dir: str = None, enable_cookies: bool = True):
        self.output_dir = output_dir or tempfile.mkdtemp()
        self.enable_cookies = enable_cookies
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create cookies file for authentication
        self.cookies_file = self._create_cookies_file() if enable_cookies else None
        
        logger.info(f"AdvancedYouTubeDownloader initialized with output_dir: {self.output_dir}")
        if self.cookies_file:
            logger.info(f"Using cookies file: {self.cookies_file}")
    
    def _create_cookies_file(self) -> str:
        """Create a cookies file with realistic YouTube session data"""
        cookies_content = """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	FALSE	1735689600	CONSENT	YES+cb.20210328-17-p0.en+FX+667
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	Gtm5d3eFQONDhlQo
.youtube.com	TRUE	/	FALSE	1735689600	YSC	H3C4rqaEhGA
.youtube.com	TRUE	/	FALSE	1735689600	PREF	f1=50000000&f6=40000000&hl=en&gl=US
.youtube.com	TRUE	/	FALSE	1735689600	GPS	1
.youtube.com	TRUE	/	FALSE	1735689600	__Secure-3PSIDCC	APoG2W8xvKjomLn8
.youtube.com	TRUE	/	FALSE	1735689600	__Secure-3PAPISID	abc123def456
.youtube.com	TRUE	/	FALSE	1735689600	__Secure-3PSID	abc123def456
youtube.com	FALSE	/	FALSE	1735689600	wide	1
"""
        
        cookies_file = os.path.join(self.output_dir, "youtube_cookies.txt")
        with open(cookies_file, 'w', encoding='utf-8') as f:
            f.write(cookies_content)
        
        return cookies_file
    
    def _get_visitor_data(self) -> str:
        """Generate realistic visitor data for YouTube"""
        # This is a simplified visitor data - in production, you'd extract this from a real browser session
        return "CgtHdG01ZDNlRlFPTkRobFFvQUJJaUNndEhkRzAxWkRObFJsRlBUa1JvYkZGdlFVST0%3D"
    
    def download_video(self, url: str, max_retries: int = 3) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download YouTube video with advanced bot detection bypass
        
        Args:
            url: YouTube video URL
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success, video_path, error_message)
        """
        
        # Enhanced download strategies with bot detection bypass
        strategies = [
            self._strategy_cookies_with_visitor_data,
            self._strategy_browser_simulation,
            self._strategy_mobile_client,
            self._strategy_embedded_player,
            self._strategy_simple_fallback
        ]
        
        for strategy_idx, strategy in enumerate(strategies, 1):
            logger.info(f"Trying strategy {strategy_idx}/{len(strategies)}: {strategy.__name__}")
            
            for attempt in range(max_retries):
                try:
                    success, video_path, error = strategy(url, attempt + 1)
                    if success:
                        logger.info(f"✅ Strategy {strategy_idx} succeeded on attempt {attempt + 1}")
                        return True, video_path, None
                    else:
                        logger.warning(f"❌ Strategy {strategy_idx} attempt {attempt + 1} failed: {error}")
                        
                    # Wait between attempts with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(1, 3)
                        logger.info(f"Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"Strategy {strategy_idx} attempt {attempt + 1} exception: {e}")
        
        return False, None, "All download strategies failed"
    
    def _strategy_cookies_with_visitor_data(self, url: str, attempt: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """Strategy 1: Use cookies with visitor data"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        visitor_data = self._get_visitor_data()
        
        cmd = [
            "yt-dlp",
            "--format", "best[height<=720]/best",
            "--output", output_template,
            "--no-check-certificates",
            "--ignore-errors",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "--extractor-args", f"youtube:visitor_data={visitor_data}",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5"
        ]
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            cmd.extend(["--cookies", self.cookies_file])
        
        cmd.append(url)
        
        return self._execute_command(cmd, "cookies_with_visitor_data")
    
    def _strategy_browser_simulation(self, url: str, attempt: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """Strategy 2: Simulate real browser behavior"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "best[height<=480]/worst",
            "--output", output_template,
            "--no-check-certificates",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "--add-header", "Accept-Language:en-us,en;q=0.5",
            "--add-header", "Accept-Encoding:gzip,deflate",
            "--add-header", "Accept-Charset:ISO-8859-1,utf-8;q=0.7,*;q=0.7",
            "--add-header", "Connection:keep-alive",
            "--sleep-interval", "3",
            "--max-sleep-interval", "8",
            url
        ]
        
        return self._execute_command(cmd, "browser_simulation")
    
    def _strategy_mobile_client(self, url: str, attempt: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """Strategy 3: Use mobile client"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "worst[ext=mp4]/worst",
            "--output", output_template,
            "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "--extractor-args", "youtube:player_client=android",
            "--sleep-interval", "4",
            url
        ]
        
        return self._execute_command(cmd, "mobile_client")
    
    def _strategy_embedded_player(self, url: str, attempt: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """Strategy 4: Use embedded player"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "worst",
            "--output", output_template,
            "--extractor-args", "youtube:player_client=web_embedded",
            "--no-check-certificates",
            "--sleep-interval", "5",
            url
        ]
        
        return self._execute_command(cmd, "embedded_player")
    
    def _strategy_simple_fallback(self, url: str, attempt: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """Strategy 5: Simple fallback"""
        output_template = os.path.join(self.output_dir, "video_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "worst",
            "--output", output_template,
            "--ignore-errors",
            "--no-warnings",
            url
        ]
        
        return self._execute_command(cmd, "simple_fallback")
    
    def _execute_command(self, cmd: list, strategy_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute yt-dlp command and return result"""
        try:
            logger.info(f"Executing {strategy_name} strategy")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Find downloaded file
                for file in os.listdir(self.output_dir):
                    if file.startswith("video_") and not file.endswith(".txt"):
                        video_path = os.path.join(self.output_dir, file)
                        if os.path.getsize(video_path) > 1024:  # At least 1KB
                            return True, video_path, None
                
                return False, None, "No valid video file found"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, None, error_msg
                
        except subprocess.TimeoutExpired:
            return False, None, "Download timeout"
        except Exception as e:
            return False, None, str(e)
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.cookies_file and os.path.exists(self.cookies_file):
                os.unlink(self.cookies_file)
        except Exception as e:
            logger.warning(f"Failed to cleanup cookies file: {e}")

def test_advanced_downloader():
    """Test the advanced downloader"""
    test_urls = [
        "https://www.youtube.com/watch?v=kuIfHJEsPkY",
        "https://www.youtube.com/watch?v=NybHckSEQBI"
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing: {url}")
        downloader = AdvancedYouTubeDownloader()
        
        success, video_path, error = downloader.download_video(url)
        
        if success:
            print(f"✅ Success: {video_path}")
        else:
            print(f"❌ Failed: {error}")
        
        downloader.cleanup()

if __name__ == "__main__":
    test_advanced_downloader()
