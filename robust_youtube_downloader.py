#!/usr/bin/env python3
"""
Robust YouTube Downloader with Multiple Fallback Methods
Designed for maximum success rate on cloud platforms like Render.com
"""

import os
import sys
import time
import random
import logging
import tempfile
import subprocess
import requests
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import hashlib
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RobustYouTubeDownloader")

class DownloadResult:
    """Container for download results"""
    def __init__(self, success: bool, video_path: str = None, audio_path: str = None, 
                 metadata: Dict = None, error: str = None, method: str = None):
        self.success = success
        self.video_path = video_path
        self.audio_path = audio_path
        self.metadata = metadata or {}
        self.error = error
        self.method = method

class RequestThrottler:
    """Intelligent request throttling to avoid rate limits"""
    
    def __init__(self):
        self.request_history = []
        self.min_interval = 2.0  # Minimum seconds between requests
        self.max_requests_per_minute = 10
        self.backoff_factor = 1.5
        self.current_delay = self.min_interval
    
    def wait_if_needed(self):
        """Wait if necessary to avoid rate limiting"""
        now = time.time()
        
        # Clean old requests (older than 1 minute)
        self.request_history = [t for t in self.request_history if now - t < 60]
        
        # Check if we're hitting rate limits
        if len(self.request_history) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_history[0]) + random.uniform(1, 3)
            logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
            self.current_delay = min(self.current_delay * self.backoff_factor, 10.0)
        
        # Ensure minimum interval
        if self.request_history:
            elapsed = now - self.request_history[-1]
            if elapsed < self.current_delay:
                sleep_time = self.current_delay - elapsed + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)
        
        self.request_history.append(time.time())
    
    def reset_delay(self):
        """Reset delay after successful request"""
        self.current_delay = max(self.current_delay * 0.9, self.min_interval)

class BrowserSimulator:
    """Advanced browser simulation for cloud environments"""
    
    @staticmethod
    def get_realistic_headers() -> Dict[str, str]:
        """Generate realistic browser headers"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    
    @staticmethod
    def get_ytdlp_config(output_dir: str) -> Dict[str, Any]:
        """Get optimized yt-dlp configuration for cloud environments"""
        headers = BrowserSimulator.get_realistic_headers()
        
        return {
            # Output settings
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'format': 'best[height<=720]/best',  # Prefer 720p or lower for speed
            
            # Browser simulation
            'user_agent': headers['User-Agent'],
            'referer': 'https://www.youtube.com/',
            'headers': headers,
            
            # Rate limiting and retries
            'sleep_interval': random.uniform(1.5, 3.0),
            'max_sleep_interval': 5,
            'sleep_interval_requests': random.uniform(0.5, 1.5),
            'sleep_interval_subtitles': random.uniform(0.5, 1.0),
            'retries': 5,
            'fragment_retries': 5,
            'file_access_retries': 3,
            
            # Error handling
            'ignoreerrors': False,
            'no_warnings': False,
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            
            # Performance optimizations
            'concurrent_fragment_downloads': 1,  # Conservative for cloud
            'http_chunk_size': 1048576,  # 1MB chunks
            
            # Metadata
            'writeinfojson': True,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            
            # Extraction settings
            'extract_flat': False,
            'force_json': False,
            'dump_single_json': False,
            
            # Network settings
            'socket_timeout': 30,
            'source_address': None,  # Let system choose
            
            # Cookies and session
            'cookiefile': None,  # We'll handle this separately if needed
            
            # Geo-bypass
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            
            # Additional anti-detection measures
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash'],  # Prefer direct downloads
                    'player_skip': ['configs'],
                }
            }
        }

class RobustYouTubeDownloader:
    """Main downloader class with multiple fallback methods"""
    
    def __init__(self, output_dir: str = None, enable_proxy: bool = False):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="youtube_downloads_")
        self.enable_proxy = enable_proxy
        self.throttler = RequestThrottler()
        self.browser_sim = BrowserSimulator()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Cache for successful configurations
        self.success_cache = {}
        
        logger.info(f"RobustYouTubeDownloader initialized with output_dir: {self.output_dir}")
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        import re
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_cache_key(self, url: str, method: str) -> str:
        """Generate cache key for successful configurations"""
        video_id = self._extract_video_id(url)
        return hashlib.md5(f"{video_id}_{method}".encode()).hexdigest()
    
    def _is_video_accessible(self, url: str) -> bool:
        """Quick check if video is accessible"""
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return False
            
            # Quick API check
            check_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            headers = self.browser_sim.get_realistic_headers()
            
            response = requests.get(check_url, headers=headers, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Accessibility check failed: {e}")
            return True  # Assume accessible if check fails

    def _method_1_enhanced_ytdlp(self, url: str) -> DownloadResult:
        """Method 1: Enhanced yt-dlp with advanced browser simulation"""
        try:
            import yt_dlp

            logger.info("Attempting Method 1: Enhanced yt-dlp")
            self.throttler.wait_if_needed()

            config = self.browser_sim.get_ytdlp_config(self.output_dir)

            # Add random delays to appear more human
            config['sleep_interval'] = random.uniform(2.0, 4.0)
            config['sleep_interval_requests'] = random.uniform(1.0, 2.0)

            with yt_dlp.YoutubeDL(config) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                if not info:
                    return DownloadResult(False, error="Could not extract video info", method="enhanced_ytdlp")

                # Download the video
                ydl.download([url])

                # Find downloaded files
                video_path = None
                info_path = None

                for file in os.listdir(self.output_dir):
                    if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                        video_path = os.path.join(self.output_dir, file)
                    elif file.endswith('.info.json'):
                        info_path = os.path.join(self.output_dir, file)

                if video_path and os.path.exists(video_path):
                    self.throttler.reset_delay()

                    # Load metadata if available
                    metadata = info
                    if info_path and os.path.exists(info_path):
                        try:
                            with open(info_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                        except:
                            pass

                    return DownloadResult(
                        success=True,
                        video_path=video_path,
                        metadata=metadata,
                        method="enhanced_ytdlp"
                    )
                else:
                    return DownloadResult(False, error="Video file not found after download", method="enhanced_ytdlp")

        except Exception as e:
            logger.warning(f"Method 1 (Enhanced yt-dlp) failed: {e}")
            return DownloadResult(False, error=str(e), method="enhanced_ytdlp")

    def _method_2_pytube(self, url: str) -> DownloadResult:
        """Method 2: pytube with custom configuration"""
        try:
            from pytube import YouTube

            logger.info("Attempting Method 2: pytube")
            self.throttler.wait_if_needed()

            # Custom headers for pytube
            headers = self.browser_sim.get_realistic_headers()

            # Create YouTube object with custom headers
            yt = YouTube(url)

            # Monkey patch the request headers
            if hasattr(yt, '_session'):
                yt._session.headers.update(headers)

            # Get video info
            title = yt.title
            video_id = yt.video_id

            # Select best available stream (prefer mp4, max 720p)
            stream = yt.streams.filter(
                progressive=True,
                file_extension='mp4'
            ).order_by('resolution').desc().first()

            if not stream:
                # Fallback to any available stream
                stream = yt.streams.filter(
                    adaptive=False
                ).order_by('resolution').desc().first()

            if not stream:
                return DownloadResult(False, error="No suitable stream found", method="pytube")

            # Download with safe filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_title}.{stream.subtype}"

            video_path = stream.download(
                output_path=self.output_dir,
                filename=filename
            )

            if video_path and os.path.exists(video_path):
                self.throttler.reset_delay()

                metadata = {
                    'title': title,
                    'video_id': video_id,
                    'duration': yt.length,
                    'views': yt.views,
                    'author': yt.author,
                    'description': yt.description[:500] if yt.description else "",
                    'resolution': stream.resolution,
                    'fps': stream.fps,
                    'filesize': stream.filesize
                }

                return DownloadResult(
                    success=True,
                    video_path=video_path,
                    metadata=metadata,
                    method="pytube"
                )
            else:
                return DownloadResult(False, error="Video file not found after download", method="pytube")

        except Exception as e:
            logger.warning(f"Method 2 (pytube) failed: {e}")
            return DownloadResult(False, error=str(e), method="pytube")

    def _method_3_youtube_dl(self, url: str) -> DownloadResult:
        """Method 3: Original youtube-dl as fallback"""
        try:
            logger.info("Attempting Method 3: youtube-dl")
            self.throttler.wait_if_needed()

            # Check if youtube-dl is available
            result = subprocess.run(['youtube-dl', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return DownloadResult(False, error="youtube-dl not available", method="youtube-dl")

            # Prepare command
            output_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
            headers = self.browser_sim.get_realistic_headers()

            cmd = [
                'youtube-dl',
                '--format', 'best[height<=720]/best',
                '--output', output_template,
                '--user-agent', headers['User-Agent'],
                '--referer', 'https://www.youtube.com/',
                '--sleep-interval', '2',
                '--max-sleep-interval', '5',
                '--retries', '3',
                '--write-info-json',
                url
            ]

            # Execute download
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Find downloaded files
                video_path = None
                info_path = None

                for file in os.listdir(self.output_dir):
                    if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                        video_path = os.path.join(self.output_dir, file)
                    elif file.endswith('.info.json'):
                        info_path = os.path.join(self.output_dir, file)

                if video_path and os.path.exists(video_path):
                    self.throttler.reset_delay()

                    # Load metadata
                    metadata = {}
                    if info_path and os.path.exists(info_path):
                        try:
                            with open(info_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                        except:
                            pass

                    return DownloadResult(
                        success=True,
                        video_path=video_path,
                        metadata=metadata,
                        method="youtube-dl"
                    )

            return DownloadResult(False, error=f"youtube-dl failed: {result.stderr}", method="youtube-dl")

        except Exception as e:
            logger.warning(f"Method 3 (youtube-dl) failed: {e}")
            return DownloadResult(False, error=str(e), method="youtube-dl")

    def _method_4_transcript_only(self, url: str) -> DownloadResult:
        """Method 4: Transcript-only fallback using youtube-transcript-api"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            logger.info("Attempting Method 4: Transcript-only")

            video_id = self._extract_video_id(url)
            if not video_id:
                return DownloadResult(False, error="Could not extract video ID", method="transcript_only")

            # Get transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get English transcript first
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except:
                # Get any available transcript
                for t in transcript_list:
                    transcript = t
                    break

            if not transcript:
                return DownloadResult(False, error="No transcript available", method="transcript_only")

            # Fetch transcript data
            transcript_data = transcript.fetch()

            # Create transcript file
            transcript_text = "\n".join([entry['text'] for entry in transcript_data])
            transcript_path = os.path.join(self.output_dir, f"transcript_{video_id}.txt")

            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_text)

            # Create metadata
            metadata = {
                'video_id': video_id,
                'transcript_language': transcript.language_code,
                'transcript_length': len(transcript_data),
                'method': 'transcript_only'
            }

            return DownloadResult(
                success=True,
                video_path=transcript_path,  # Use transcript as "video"
                metadata=metadata,
                method="transcript_only"
            )

        except Exception as e:
            logger.warning(f"Method 4 (transcript-only) failed: {e}")
            return DownloadResult(False, error=str(e), method="transcript_only")

    def _method_5_proxy_download(self, url: str) -> DownloadResult:
        """Method 5: Download through proxy service (if enabled)"""
        if not self.enable_proxy:
            return DownloadResult(False, error="Proxy not enabled", method="proxy")

        try:
            logger.info("Attempting Method 5: Proxy download")

            # This is a placeholder for proxy implementation
            # In production, you would integrate with services like:
            # - ProxyMesh
            # - Bright Data
            # - Oxylabs
            # - ScrapingBee

            # Example implementation (you need to configure with actual proxy service):
            proxy_config = {
                'http': os.getenv('HTTP_PROXY'),
                'https': os.getenv('HTTPS_PROXY')
            }

            if not any(proxy_config.values()):
                return DownloadResult(False, error="No proxy configuration found", method="proxy")

            # Use yt-dlp with proxy
            import yt_dlp

            config = self.browser_sim.get_ytdlp_config(self.output_dir)
            config['proxy'] = proxy_config.get('https') or proxy_config.get('http')

            with yt_dlp.YoutubeDL(config) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return DownloadResult(False, error="Could not extract video info via proxy", method="proxy")

                ydl.download([url])

                # Find downloaded file
                for file in os.listdir(self.output_dir):
                    if file.endswith(('.mp4', '.webm', '.mkv', '.avi')):
                        video_path = os.path.join(self.output_dir, file)
                        return DownloadResult(
                            success=True,
                            video_path=video_path,
                            metadata=info,
                            method="proxy"
                        )

                return DownloadResult(False, error="Video file not found after proxy download", method="proxy")

        except Exception as e:
            logger.warning(f"Method 5 (proxy) failed: {e}")
            return DownloadResult(False, error=str(e), method="proxy")

    def download(self, url: str, max_retries: int = 3) -> DownloadResult:
        """
        Main download method with intelligent fallback strategy

        Args:
            url: YouTube video URL
            max_retries: Maximum number of retry attempts per method

        Returns:
            DownloadResult object with success status and file paths
        """
        logger.info(f"Starting robust download for: {url}")

        # Quick accessibility check
        if not self._is_video_accessible(url):
            return DownloadResult(False, error="Video appears to be inaccessible", method="accessibility_check")

        # Define download methods in order of preference
        methods = [
            self._method_1_enhanced_ytdlp,
            self._method_2_pytube,
            self._method_3_youtube_dl,
            self._method_5_proxy_download,  # Try proxy before transcript-only
            self._method_4_transcript_only,  # Last resort
        ]

        # Track all errors for debugging
        all_errors = []

        for method_func in methods:
            method_name = method_func.__name__.replace('_method_', '').replace('_', ' ').title()

            for attempt in range(max_retries):
                try:
                    logger.info(f"Trying {method_name} (attempt {attempt + 1}/{max_retries})")

                    result = method_func(url)

                    if result.success:
                        logger.info(f"✅ Success with {method_name}!")
                        return result
                    else:
                        error_msg = f"{method_name} attempt {attempt + 1}: {result.error}"
                        all_errors.append(error_msg)
                        logger.warning(error_msg)

                        # Wait before retry (exponential backoff)
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                            logger.info(f"Waiting {wait_time:.1f}s before retry...")
                            time.sleep(wait_time)

                except Exception as e:
                    error_msg = f"{method_name} attempt {attempt + 1} exception: {str(e)}"
                    all_errors.append(error_msg)
                    logger.error(error_msg)

                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        time.sleep(wait_time)

        # All methods failed
        final_error = "All download methods failed:\n" + "\n".join(all_errors)
        logger.error(final_error)

        return DownloadResult(False, error=final_error, method="all_methods_failed")

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.output_dir) and self.output_dir.startswith(tempfile.gettempdir()):
                import shutil
                shutil.rmtree(self.output_dir)
                logger.info(f"Cleaned up temporary directory: {self.output_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directory: {e}")

# Convenience functions for easy integration
def download_youtube_video(url: str, output_dir: str = None, enable_proxy: bool = False) -> DownloadResult:
    """
    Simple function to download a YouTube video with robust fallback methods

    Args:
        url: YouTube video URL
        output_dir: Directory to save the video (optional)
        enable_proxy: Whether to enable proxy methods (optional)

    Returns:
        DownloadResult object
    """
    downloader = RobustYouTubeDownloader(output_dir=output_dir, enable_proxy=enable_proxy)
    try:
        return downloader.download(url)
    finally:
        if not output_dir:  # Only cleanup if using temp directory
            downloader.cleanup()

def test_download_methods(test_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    """Test all download methods with a sample video"""
    print("🧪 Testing Robust YouTube Downloader")
    print("=" * 50)

    downloader = RobustYouTubeDownloader()

    methods = [
        ("Enhanced yt-dlp", downloader._method_1_enhanced_ytdlp),
        ("pytube", downloader._method_2_pytube),
        ("youtube-dl", downloader._method_3_youtube_dl),
        ("Transcript-only", downloader._method_4_transcript_only),
    ]

    for name, method in methods:
        print(f"\n🔍 Testing {name}...")
        try:
            result = method(test_url)
            if result.success:
                print(f"✅ {name}: SUCCESS")
                print(f"   File: {result.video_path}")
                print(f"   Method: {result.method}")
            else:
                print(f"❌ {name}: FAILED")
                print(f"   Error: {result.error}")
        except Exception as e:
            print(f"💥 {name}: EXCEPTION - {e}")

    downloader.cleanup()

if __name__ == "__main__":
    # Example usage
    test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"  # Khan Academy video

    print("🎬 Robust YouTube Downloader Test")
    print("=" * 40)

    result = download_youtube_video(test_url)

    if result.success:
        print(f"✅ Download successful!")
        print(f"📁 File: {result.video_path}")
        print(f"🔧 Method: {result.method}")
        print(f"📊 Metadata: {result.metadata.get('title', 'N/A')}")
    else:
        print(f"❌ Download failed: {result.error}")
        print("\n🧪 Running method tests...")
        test_download_methods(test_url)
