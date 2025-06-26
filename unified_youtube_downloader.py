#!/usr/bin/env python3
"""
Unified YouTube Downloader
Combines strategies from various downloaders to provide a robust and resilient solution
for downloading YouTube videos, handling bot detection, and rate limiting.
"""

import os
import sys
import tempfile
import subprocess
import time
import random
import logging
import json
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import hashlib
from datetime import datetime, timedelta
import requests # Moved import to top level

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to stdout for Render
    ]
)
logger = logging.getLogger("UnifiedYouTubeDownloader")

@dataclass
class DownloadResult:
    """Result of a video download operation"""
    success: bool
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    method: Optional[str] = None
    rate_limited: bool = False
    retry_count: int = 0
    strategy_used: Optional[str] = None

class RequestThrottler:
    """Intelligent request throttling to avoid rate limits"""
    def __init__(self, min_interval: float = 2.0, max_requests_per_minute: int = 10):
        self.request_history: List[float] = []
        self.min_interval = min_interval
        self.max_requests_per_minute = max_requests_per_minute
        self.backoff_factor = 1.5
        self.current_delay = self.min_interval
        self.rate_limit_penalty_until: float = 0  # Timestamp until which a penalty is active

    def wait_if_needed(self):
        """Wait if necessary to avoid rate limiting"""
        now = time.time()

        if now < self.rate_limit_penalty_until:
            penalty_wait = self.rate_limit_penalty_until - now
            logger.warning(f"Rate limit penalty active. Waiting for {penalty_wait:.1f}s.")
            time.sleep(penalty_wait)
            # After penalty, reset delay to a moderate value
            self.current_delay = max(self.min_interval, 5.0)
            self.rate_limit_penalty_until = 0 # Reset penalty

        # Clean old requests (older than 1 minute)
        self.request_history = [t for t in self.request_history if now - t < 60]

        # Check if we're hitting rate limits
        if len(self.request_history) >= self.max_requests_per_minute:
            # Calculate remaining time in the current minute window for the oldest request
            time_to_wait_for_slot = 60 - (now - self.request_history[0]) + random.uniform(1, 3)
            logger.info(f"Approaching rate limit ({len(self.request_history)} requests in last minute), sleeping for {time_to_wait_for_slot:.1f} seconds")
            time.sleep(time_to_wait_for_slot)
            self.current_delay = min(self.current_delay * self.backoff_factor, 20.0) # Increase delay, cap at 20s
            # Re-clean history after waiting
            now = time.time()
            self.request_history = [t for t in self.request_history if now - t < 60]


        # Ensure minimum interval since last request
        if self.request_history:
            elapsed_since_last = now - self.request_history[-1]
            if elapsed_since_last < self.current_delay:
                required_wait = self.current_delay - elapsed_since_last + random.uniform(0.1, 0.5)
                time.sleep(required_wait)

        self.request_history.append(time.time())

    def notify_rate_limit_exceeded(self):
        """Call this if a rate limit error is explicitly detected from an API response."""
        logger.warning("External rate limit detected. Applying penalty.")
        self.current_delay = min(self.current_delay * 2, 30.0) # Double delay, cap at 30s
        self.rate_limit_penalty_until = time.time() + random.uniform(15, 45) # Penalty for 15-45s

    def reset_delay(self):
        """Reset delay after successful request or if conditions improve."""
        self.current_delay = max(self.current_delay * 0.9, self.min_interval)


class BrowserSimulator:
    """Advanced browser simulation for cloud environments"""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip"
    ]

    @staticmethod
    def get_realistic_headers() -> Dict[str, str]:
        """Generate realistic browser headers"""
        base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1', # Do Not Track
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none', # 'same-origin' or 'cross-site' depending on context
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0', # Varies, but good for initial request
        }
        user_agent = random.choice(BrowserSimulator.USER_AGENTS)
        base_headers['User-Agent'] = user_agent

        # Add sec-ch-ua headers if it's a Chrome-like UA
        if "Chrome" in user_agent or "Chromium" in user_agent:
            # Simplified example; real values are more complex
            major_version = "120" # Extract from UA if possible
            base_headers['sec-ch-ua'] = f'"Not_A Brand";v="8", "Chromium";v="{major_version}", "Google Chrome";v="{major_version}"'
            base_headers['sec-ch-ua-mobile'] = '?0' if "Windows" in user_agent or "Macintosh" in user_agent else '?1'
            base_headers['sec-ch-ua-platform'] = '"Windows"' if "Windows" in user_agent else '"macOS"' if "Macintosh" in user_agent else '"Android"' if "Android" in user_agent else '"iOS"'

        return base_headers

    @staticmethod
    def get_yt_dlp_config(output_dir: str) -> Dict[str, Any]:
        """Get optimized yt-dlp configuration"""
        headers = BrowserSimulator.get_realistic_headers()
        return {
            'outtmpl': os.path.join(output_dir, 'video_%(id)s.%(ext)s'),
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best', # Added /best as final fallback
            'user_agent': headers['User-Agent'],
            'referer': 'https://www.youtube.com/',
            'http_headers': headers, # Pass all generated headers
            'sleep_interval_requests': random.uniform(1.5, 3.5), # Increased
            'sleep_interval': random.uniform(2.5, 5.5), # Increased
            'max_sleep_interval': 12, # Slightly increased
            'retries': 5, # Number of retries for errors
            'fragment_retries': 5, # Retries for fragments
            'file_access_retries': 3,
            'ignoreerrors': False, # We want to catch errors to retry with different strategies
            'no_warnings': True, # Quieter logs
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'concurrent_fragment_downloads': 2, # Can speed up, but be careful with rate limits
            'socket_timeout': 60, # Longer timeout
            'geo_bypass': True,
            'geo_bypass_country': random.choice(['US', 'GB', 'DE', 'CA']), # Randomize common countries
            'no_check_certificate': True, # Sometimes helps in restricted environments
            'extractor_args': {
                'youtube': {
                    # 'player_client': random.choice(['web', 'mweb', 'android']), # Will be set by specific strategies
                    # 'skip': ['hls', 'dash'], # Removed to allow HLS/DASH attempts
                    'player_skip': ['configs', 'translations'], # Reduce unnecessary requests
                }
            },
            'writethumbnail': False, # Save disk space / time
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writeinfojson': True, # Useful for metadata
            'quiet': True, # Suppress yt-dlp console output, rely on our logger
            'progress': False, # Suppress progress bars
            'verbose': False,
        }

class UnifiedYouTubeDownloader:
    """Main downloader class with multiple fallback methods"""

    def __init__(self, output_dir: Optional[str] = None, enable_proxy: bool = False):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="unified_youtube_")
        self.enable_proxy = enable_proxy # Proxy support can be added later if needed
        self.throttler = RequestThrottler(min_interval=3.0, max_requests_per_minute=8) # Conservative throttling
        self.browser_sim = BrowserSimulator()

        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"UnifiedYouTubeDownloader initialized. Output directory: {self.output_dir}")

    def _extract_video_id(self, url: str) -> Optional[str]:
        import re
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        logger.warning(f"Could not extract video ID from URL: {url}")
        return None

    def _is_video_accessible(self, url: str) -> bool:
        """Quick check if video is accessible via oEmbed"""
        video_id = self._extract_video_id(url)
        if not video_id:
            return False # Cannot check if no ID

        # Use requests library for this check for more control
        try:
            import requests
            check_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            headers = self.browser_sim.get_realistic_headers()
            self.throttler.wait_if_needed() # Throttle this check as well
            response = requests.get(check_url, headers=headers, timeout=15)
            if response.status_code == 200:
                logger.info(f"Video {video_id} appears accessible via oEmbed.")
                self.throttler.reset_delay()
                return True
            elif response.status_code == 429: # Too Many Requests
                logger.warning(f"Rate limited during oEmbed check for {video_id}. Status: {response.status_code}")
                self.throttler.notify_rate_limit_exceeded()
                return False # Assume inaccessible if rate limited here
            else:
                logger.warning(f"Video {video_id} oEmbed check failed. Status: {response.status_code}, Content: {response.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.warning(f"Accessibility check via oEmbed failed for {video_id}: {e}")
            return True # Assume accessible if the check itself fails, to allow download attempts

    def _execute_yt_dlp_download(self, url: str, strategy_name: str, custom_config: Optional[Dict] = None) -> DownloadResult:
        try:
            import yt_dlp # Ensure yt-dlp is available

            self.throttler.wait_if_needed()
            logger.info(f"Attempting download strategy: {strategy_name} for URL: {url}")

            base_config = self.browser_sim.get_yt_dlp_config(self.output_dir)
            if custom_config:
                # Deep merge custom_config into base_config
                for key, value in custom_config.items():
                    if isinstance(value, dict) and key in base_config and isinstance(base_config[key], dict):
                        base_config[key].update(value)
                    else:
                        base_config[key] = value

            # Ensure output template is correctly set
            base_config['outtmpl'] = os.path.join(self.output_dir, 'video_%(id)s.%(ext)s')


            ydl_opts = base_config

            # Log the final effective yt-dlp options for debugging (selectively)
            # logger.debug(f"yt-dlp options for {strategy_name}: {json.dumps(ydl_opts, indent=2, default=str)}")


            downloaded_video_path = None
            downloaded_info_path = None
            download_error = "Unknown error during download"
            final_metadata = {}

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # First, try to extract info without downloading to get metadata early
                    # and to check if the video is available with current settings.
                    logger.info(f"[{strategy_name}] Extracting info for {url}...")
                    info_dict = ydl.extract_info(url, download=False)
                    if info_dict:
                        final_metadata.update(info_dict)
                        logger.info(f"[{strategy_name}] Successfully extracted info for: {info_dict.get('title', 'N/A')}")

                        # If only info extraction was intended by a strategy, return here
                        if ydl_opts.get('extract_flat', False) or ydl_opts.get('dump_single_json', False):
                            return DownloadResult(success=True, metadata=final_metadata, method=strategy_name, strategy_used=strategy_name)

                        logger.info(f"[{strategy_name}] Starting download for {url}...")
                        # Now, perform the actual download
                        # This call might raise DownloadError or other exceptions caught below
                        ydl.download([url])

                        # After download, find the files based on expected output
                        # yt-dlp might rename files, so we need to be robust
                        video_id = info_dict.get('id') if info_dict else self._extract_video_id(url)

                        found_video = False
                        if video_id: # Try to find by ID first
                            for ext in ['mp4', 'mkv', 'webm', 'avi', 'flv']: # Common video extensions
                                potential_path = os.path.join(self.output_dir, f"video_{video_id}.{ext}")
                                if os.path.exists(potential_path) and os.path.getsize(potential_path) > 1024: # Basic sanity check
                                    downloaded_video_path = potential_path
                                    found_video = True
                                    break

                        if not found_video: # Fallback: scan directory for any video file
                           for f_name in os.listdir(self.output_dir):
                               if f_name.startswith("video_") and any(f_name.endswith(ext) for ext in ['.mp4', '.mkv', '.webm', '.avi', '.flv']):
                                   potential_path = os.path.join(self.output_dir, f_name)
                                   if os.path.exists(potential_path) and os.path.getsize(potential_path) > 1024:
                                       downloaded_video_path = potential_path
                                       found_video = True
                                       break

                        if not found_video:
                            download_error = "Video file not found after download attempt."
                            logger.error(f"[{strategy_name}] {download_error}")
                            return DownloadResult(success=False, error=download_error, method=strategy_name, strategy_used=strategy_name)

                        logger.info(f"[{strategy_name}] Successfully downloaded video to: {downloaded_video_path}")

                        # Try to load the .info.json file for metadata
                        potential_info_json_path = None
                        if downloaded_video_path:
                             base_name, _ = os.path.splitext(downloaded_video_path)
                             potential_info_json_path = base_name + ".info.json" # yt-dlp default
                        elif video_id: # If video path not found but we have ID
                            potential_info_json_path = os.path.join(self.output_dir, f"video_{video_id}.info.json")

                        if potential_info_json_path and os.path.exists(potential_info_json_path):
                            try:
                                with open(potential_info_json_path, 'r', encoding='utf-8') as ij_file:
                                    downloaded_info_data = json.load(ij_file)
                                    final_metadata.update(downloaded_info_data)
                                downloaded_info_path = potential_info_json_path
                                logger.info(f"[{strategy_name}] Loaded metadata from: {downloaded_info_path}")
                            except Exception as e_json:
                                logger.warning(f"[{strategy_name}] Could not load .info.json: {e_json}")

                        self.throttler.reset_delay()
                        return DownloadResult(
                            success=True,
                            video_path=downloaded_video_path,
                            metadata=final_metadata,
                            method=strategy_name,
                            strategy_used=strategy_name
                        )

            except yt_dlp.utils.DownloadError as e:
                download_error = f"yt-dlp DownloadError: {str(e)}"
                logger.error(f"[{strategy_name}] {download_error}")
                rate_limited = "429" in str(e) or "too many requests" in str(e).lower()
                if rate_limited:
                    self.throttler.notify_rate_limit_exceeded()
                return DownloadResult(success=False, error=download_error, method=strategy_name, rate_limited=rate_limited, strategy_used=strategy_name)
            except yt_dlp.utils.ExtractorError as e:
                download_error = f"yt-dlp ExtractorError: {str(e)}"
                logger.error(f"[{strategy_name}] {download_error}")
                return DownloadResult(success=False, error=download_error, method=strategy_name, strategy_used=strategy_name)
            except Exception as e: # Catch any other exceptions
                download_error = f"Generic error during yt-dlp execution: {type(e).__name__} - {str(e)}"
                logger.error(f"[{strategy_name}] {download_error}")
                return DownloadResult(success=False, error=download_error, method=strategy_name, strategy_used=strategy_name)

        except ImportError:
            logger.critical("yt-dlp module not found. Please install it.")
            return DownloadResult(success=False, error="yt-dlp module not found.", method=strategy_name, strategy_used=strategy_name)
        except Exception as e: # Catch errors in setting up yt-dlp or initial config
            logger.critical(f"Failed to initialize or run yt-dlp for strategy {strategy_name}: {e}")
            return DownloadResult(success=False, error=f"Setup error for {strategy_name}: {e}", method=strategy_name, strategy_used=strategy_name)

    # --- Download Strategies ---
    def _strategy_yt_dlp_mweb(self, url: str) -> DownloadResult:
        """Strategy 1: yt-dlp with 'mweb' (mobile web) player client and specific mobile UA."""
        # Find an iPhone or generic mobile User-Agent
        mobile_ua = next((ua for ua in BrowserSimulator.USER_AGENTS if "iPhone" in ua), BrowserSimulator.USER_AGENTS[-2]) # Fallback to a known mobile UA
        config = {
            'extractor_args': {'youtube': {'player_client': 'mweb'}}, # Ensure player_client is a string
            'user_agent': mobile_ua,
            'http_headers': {'User-Agent': mobile_ua} # Also explicitly set in headers for yt-dlp
        }
        return self._execute_yt_dlp_download(url, "yt_dlp_mweb", custom_config=config)

    def _strategy_yt_dlp_web_simulated_browser(self, url: str) -> DownloadResult:
        """Strategy 2: yt-dlp with 'web' client and specific desktop browser UA."""
        # Find a Desktop User-Agent
        desktop_ua = next((ua for ua in BrowserSimulator.USER_AGENTS if "Windows NT" in ua or "Macintosh" in ua and "Mobile" not in ua), BrowserSimulator.USER_AGENTS[0])
        config = {
            'extractor_args': {'youtube': {'player_client': 'web'}}, # Ensure player_client is a string
            'user_agent': desktop_ua,
            'http_headers': {'User-Agent': desktop_ua}
        }
        return self._execute_yt_dlp_download(url, "yt_dlp_web_simulated_browser", custom_config=config)

    def _strategy_yt_dlp_android_client(self, url: str) -> DownloadResult:
        """Strategy 3: yt-dlp with 'android' player client and specific Android UA."""
        android_ua = next((ua for ua in BrowserSimulator.USER_AGENTS if "Android" in ua and "com.google.android.youtube" in ua), BrowserSimulator.USER_AGENTS[-1]) # Fallback to a known Android UA
        config = {
            'extractor_args': {'youtube': {'player_client': 'android'}}, # Ensure player_client is a string
            'user_agent': android_ua,
            'http_headers': {'User-Agent': android_ua}
        }
        return self._execute_yt_dlp_download(url, "yt_dlp_android_client", custom_config=config)

    def _strategy_yt_dlp_conservative(self, url: str) -> DownloadResult:
        """Strategy 4: yt-dlp with very conservative settings (lower quality, more tolerant), cycles player_client."""
        # This strategy can still cycle player_client as a last resort if others fail.
        conservative_player_client = random.choice(['web', 'mweb'])
        ua_for_conservative = ""
        if conservative_player_client == 'web':
            ua_for_conservative = next((ua for ua in BrowserSimulator.USER_AGENTS if "Windows NT" in ua or "Macintosh" in ua and "Mobile" not in ua), BrowserSimulator.USER_AGENTS[0])
        else: # mweb
            ua_for_conservative = next((ua for ua in BrowserSimulator.USER_AGENTS if "iPhone" in ua), BrowserSimulator.USER_AGENTS[-2])

        config = {
            'format': 'worstvideo[ext=mp4]+bestaudio[ext=m4a]/worst[ext=mp4]/worst', # Lower quality
            'retries': 8, # More retries
            'fragment_retries': 8,
            'socket_timeout': 120, # Longer timeout
            'extractor_args': {'youtube': {'player_client': conservative_player_client}},
            'user_agent': ua_for_conservative,
            'http_headers': {'User-Agent': ua_for_conservative}
        }
        return self._execute_yt_dlp_download(url, f"yt_dlp_conservative_{conservative_player_client}", custom_config=config)

    def _strategy_pytube_download(self, url: str, max_pytube_retries: int = 2) -> DownloadResult:
        """Strategy 5: Use pytube library as an alternative, with retries and custom User-Agent."""
        logger.info(f"Attempting download strategy: pytube for URL: {url}")

        try:
            from pytube import YouTube, request as pytube_request
            from pytube.exceptions import PytubeError, MaxRetriesExceeded, RegexMatchError, VideoUnavailable, MembersOnly, RecordingUnavailable, LiveStreamError

            # Set a custom User-Agent for pytube's requests
            # Choose a common desktop browser User-Agent
            desktop_ua = next((ua for ua in BrowserSimulator.USER_AGENTS if "Windows NT" in ua or "Macintosh" in ua and "Mobile" not in ua), BrowserSimulator.USER_AGENTS[0])
            original_headers = pytube_request.headers.copy()
            pytube_request.headers['User-Agent'] = desktop_ua
            logger.debug(f"[pytube] Set User-Agent to: {desktop_ua}")

            for attempt in range(max_pytube_retries):
                logger.info(f"[pytube] Attempt {attempt + 1}/{max_pytube_retries} for {url}")
                self.throttler.wait_if_needed() # Throttle before each attempt

                try:
                    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)

                    # Stream selection logic (prioritize progressive mp4)
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    if not stream: # Fallback to any progressive
                        logger.info("[pytube] No progressive MP4 found, trying any progressive stream.")
                        stream = yt.streams.filter(progressive=True).order_by('resolution').desc().first()
                    if not stream: # Fallback to highest resolution non-progressive if really needed (though we prefer single files)
                        logger.info("[pytube] No progressive stream found, trying highest resolution adaptive (video only).")
                        stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
                    # We could also try audio-only if that's ever useful: yt.streams.get_audio_only()

                    if not stream:
                        return DownloadResult(success=False, error="Pytube: No suitable stream found after fallbacks.", method="pytube", strategy_used="pytube_download")

                    logger.info(f"[pytube] Selected stream: Resolution: {stream.resolution}, MIME: {stream.mime_type}, Progressive: {stream.is_progressive}, Abr: {stream.abr if not stream.is_progressive else 'N/A'}")

                    # Download the video
                    filename_prefix = f"video_{yt.video_id}"
                    video_path = stream.download(output_path=self.output_dir, filename_prefix=filename_prefix)

                    if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 1024: # Basic sanity check
                        self.throttler.reset_delay()
                        metadata = {
                            'title': yt.title, 'author': yt.author, 'length': yt.length,
                            'publish_date': yt.publish_date.isoformat() if yt.publish_date else None,
                            'video_id': yt.video_id, 'resolution': stream.resolution,
                            'filesize': stream.filesize, 'source_library': 'pytube',
                            'stream_itag': stream.itag, 'stream_mime_type': stream.mime_type,
                            'stream_is_progressive': stream.is_progressive
                        }
                        info_json_path = os.path.splitext(video_path)[0] + ".info.json"
                        try:
                            with open(info_json_path, 'w', encoding='utf-8') as f_json:
                                json.dump(metadata, f_json, indent=4)
                        except Exception as e_json:
                            logger.warning(f"[pytube] Could not save .info.json: {e_json}")

                        # Restore original headers for pytube.request
                        pytube_request.headers = original_headers
                        return DownloadResult(success=True, video_path=video_path, metadata=metadata, method="pytube", strategy_used="pytube_download")
                    else:
                        # This attempt failed to produce a valid file
                        logger.warning(f"[pytube] Downloaded file not found or too small for attempt {attempt + 1}.")
                        # No immediate return, let the loop retry if attempts remain

                except (MaxRetriesExceeded, ConnectionResetError, TimeoutError) as e_transient: # Common transient network issues
                    logger.warning(f"[pytube] Transient error on attempt {attempt + 1}/{max_pytube_retries}: {type(e_transient).__name__} - {e_transient}")
                    if attempt < max_pytube_retries - 1:
                        time.sleep(random.uniform(3, 7) * (attempt + 1)) # Exponential backoff for retries
                        continue # Go to next attempt
                    else: # Max retries for this strategy reached
                        pytube_request.headers = original_headers # Restore before returning
                        return DownloadResult(success=False, error=f"Pytube: Max retries exceeded after transient errors. Last error: {e_transient}", method="pytube", strategy_used="pytube_download")
                except (RegexMatchError, VideoUnavailable, MembersOnly, RecordingUnavailable, LiveStreamError) as e_fatal: # Pytube specific fatal errors
                    logger.error(f"[pytube] Fatal Pytube error: {type(e_fatal).__name__} - {e_fatal}")
                    pytube_request.headers = original_headers # Restore before returning
                    return DownloadResult(success=False, error=f"Pytube: {type(e_fatal).__name__} - {e_fatal}", method="pytube", strategy_used="pytube_download")
                except PytubeError as e: # Other Pytube errors
                    error_msg = f"Pytube error: {type(e).__name__} - {str(e)}"
                    logger.error(f"[pytube] {error_msg}")
                    rate_limited = "429" in str(e) or "too many requests" in str(e).lower()
                    if rate_limited: self.throttler.notify_rate_limit_exceeded()
                    # For most other PytubeErrors, probably not worth retrying within this strategy immediately
                    pytube_request.headers = original_headers # Restore before returning
                    return DownloadResult(success=False, error=error_msg, method="pytube", rate_limited=rate_limited, strategy_used="pytube_download")
                except Exception as e_general: # Catch-all for unexpected issues during an attempt
                    logger.error(f"[pytube] Unexpected error on attempt {attempt + 1}: {type(e_general).__name__} - {str(e_general)}")
                    if attempt < max_pytube_retries - 1:
                        time.sleep(random.uniform(3, 7) * (attempt + 1))
                        continue
                    else:
                        pytube_request.headers = original_headers # Restore before returning
                        return DownloadResult(success=False, error=f"Pytube: Unexpected error after retries. Last error: {e_general}", method="pytube", strategy_used="pytube_download")

            # If loop finishes, all retries for this strategy failed
            pytube_request.headers = original_headers # Restore before returning
            return DownloadResult(success=False, error="Pytube: All download attempts within strategy failed.", method="pytube", strategy_used="pytube_download")

        except ImportError:
            logger.error("Pytube module not found. This strategy will be skipped.")
            return DownloadResult(success=False, error="Pytube module not found.", method="pytube", strategy_used="pytube_download")
        except Exception as e_setup: # Error in setting up pytube (e.g. header modification)
             logger.error(f"[pytube] Setup error: {type(e_setup).__name__} - {str(e_setup)}")
             return DownloadResult(success=False, error=f"Pytube setup error: {str(e_setup)}", method="pytube", strategy_used="pytube_download")


    def download_video(self, url: str, max_total_retries: int = 3) -> DownloadResult:
        """
        Main download method with intelligent fallback strategy.
        Retries the entire sequence of strategies if the first pass fails.
        """
        logger.info(f"Starting unified download for: {url}")

        if not self._is_video_accessible(url):
            # If even the oEmbed check suggests inaccessibility or hits a rate limit,
            # it might be better to fail fast or wait longer.
            # For now, we'll still proceed to actual download attempts as oEmbed isn't foolproof.
            logger.warning(f"Video accessibility check failed or indicated issues for {url}. Proceeding with download attempts cautiously.")


        # Define download strategies in order of preference / likelihood of success / robustness
        # yt-dlp strategies are generally more robust.
        strategies = [
            self._strategy_yt_dlp_mweb,
            self._strategy_yt_dlp_web_simulated_browser,
            self._strategy_yt_dlp_android_client,
            self._strategy_pytube_download, # Pytube as a distinct alternative
            self._strategy_yt_dlp_conservative, # yt-dlp conservative as a later fallback
        ]

        all_errors: List[str] = []
        overall_retry_count = 0

        while overall_retry_count < max_total_retries:
            logger.info(f"Overall download attempt {overall_retry_count + 1}/{max_total_retries} for {url}")

            for strategy_func in strategies:
                # Introduce a small random delay between trying different strategies
                # if it's not the first strategy in the first overall attempt.
                if not (overall_retry_count == 0 and strategy_func == strategies[0]):
                    time.sleep(random.uniform(1, 3))

                result = strategy_func(url)
                result.retry_count = overall_retry_count # Set the overall retry count

                if result.success:
                    logger.info(f"✅ Successfully downloaded {url} using strategy: {result.strategy_used} (Overall attempt {overall_retry_count + 1})")
                    return result
                else:
                    error_msg = f"Strategy {result.strategy_used or 'unknown'} failed (Attempt {overall_retry_count + 1}): {result.error}"
                    if result.rate_limited:
                        error_msg += " (Rate Limited)"
                    all_errors.append(error_msg)
                    logger.warning(error_msg)

                    if result.rate_limited:
                        # If a strategy reports rate limiting, apply a longer throttle before next strategy / retry
                        logger.warning("Rate limit detected by strategy. Applying longer throttle.")
                        self.throttler.notify_rate_limit_exceeded() # Penalize further
                        self.throttler.wait_if_needed() # Wait out the penalty

            overall_retry_count += 1
            if overall_retry_count < max_total_retries:
                wait_before_full_retry = (2 ** overall_retry_count) * 5 + random.uniform(5,10)
                logger.info(f"All strategies failed on attempt {overall_retry_count}. Retrying all strategies after {wait_before_full_retry:.1f}s...")
                time.sleep(wait_before_full_retry)
            else:
                logger.error(f"All strategies failed after {max_total_retries} overall attempts for {url}.")


        final_error_summary = "All download strategies failed after maximum retries.\nErrors:\n" + "\n".join(all_errors)
        return DownloadResult(
            success=False,
            error=final_error_summary,
            method="all_strategies_failed",
            retry_count=max_total_retries,
            strategy_used="none"
        )

    def cleanup(self, specific_job_id: Optional[str] = None):
        """
        Clean up temporary files. If specific_job_id is provided,
        it might be used to clean only files related to that job if the output_dir structure supports it.
        Currently, it cleans the entire self.output_dir if it's a temp directory.
        """
        try:
            # Check if the output_dir is a subdirectory of the system's temp directory
            # This is a safety measure to avoid deleting unintended directories.
            is_temp_dir_subpath = Path(self.output_dir).resolve().as_posix().startswith(Path(tempfile.gettempdir()).resolve().as_posix())

            if is_temp_dir_subpath and os.path.exists(self.output_dir):
                import shutil
                shutil.rmtree(self.output_dir)
                logger.info(f"Cleaned up temporary directory: {self.output_dir}")
            elif os.path.exists(self.output_dir) and not is_temp_dir_subpath:
                 logger.warning(f"Cleanup skipped for non-temporary directory: {self.output_dir}. Please manage cleanup manually if needed.")
            else:
                logger.info(f"Cleanup: Directory {self.output_dir} does not exist or was already cleaned.")

        except Exception as e:
            logger.warning(f"Failed to cleanup directory {self.output_dir}: {e}")


def test_downloader(test_urls=None, max_retries_override=None):
    """
    Test function for the UnifiedYouTubeDownloader.
    Can be called with a specific list of URLs for targeted testing.
    """
    if test_urls is None:
        # Default test URLs - reduced for quicker sandbox testing
        test_urls = [
            "https://www.youtube.com/watch?v=NybHckSEQBI",  # Khan Academy (educational, usually reliable)
            # "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
            # "https://www.youtube.com/shorts/m3_BRe35D-g",   # YouTube Short
        ]

    default_max_retries = 1 # Quicker for automated tests

    # Create a specific output directory for this test run
    test_output_dir = os.path.join(tempfile.gettempdir(), f"unified_downloader_test_{int(time.time())}")
    os.makedirs(test_output_dir, exist_ok=True)
    logger.info(f"Test output directory: {test_output_dir}")

    downloader = UnifiedYouTubeDownloader(output_dir=test_output_dir)

    for i, url in enumerate(test_urls):
        print("\n" + "="*50)
        logger.info(f"🧪 TESTING URL ({i+1}/{len(test_urls)}): {url}")
        print("="*50)

        current_max_retries = max_retries_override if max_retries_override is not None else default_max_retries
        logger.info(f"Using max_total_retries = {current_max_retries} for this test run.")

        result = downloader.download_video(url, max_total_retries=current_max_retries)

        if result.success:
            logger.info(f"✅ SUCCESS for {url}")
            logger.info(f"   Video Path: {result.video_path}")
            logger.info(f"   Strategy: {result.strategy_used}")
            logger.info(f"   Method: {result.method}")
            if result.metadata:
                logger.info(f"   Title: {result.metadata.get('title', 'N/A')}")
                # logger.info(f"   Metadata keys: {list(result.metadata.keys())}")
            if result.video_path and os.path.exists(result.video_path):
                logger.info(f"   File size: {os.path.getsize(result.video_path) / (1024*1024):.2f} MB")
                # Clean up individual video file immediately after successful test to save space during long tests
                # os.remove(result.video_path)
                # info_json = os.path.splitext(result.video_path)[0] + ".info.json"
                # if os.path.exists(info_json):
                #     os.remove(info_json)

        else:
            logger.error(f"❌ FAILED for {url}")
            logger.error(f"   Error: {result.error}")
            logger.error(f"   Strategy Attempted: {result.strategy_used}")
            logger.error(f"   Method: {result.method}")
            if result.rate_limited:
                logger.warning("   Download was likely rate-limited.")

        logger.info(f"Current throttler delay: {downloader.throttler.current_delay:.2f}s")


    # Final cleanup of the test-specific output directory
    logger.info(f"Attempting final cleanup of test directory: {test_output_dir}")
    downloader.cleanup() # This will clean test_output_dir as it was passed to constructor

if __name__ == "__main__":
    # Setup more verbose logging for command-line testing
    logging.getLogger().handlers.clear() # Clear existing handlers if any configured by imports
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # Set root logger level, and then specific logger level for our downloader
    logging.getLogger().setLevel(logging.INFO) # Root logger
    logger.setLevel(logging.DEBUG) # Our specific downloader logger

    # Add the handler to our specific logger
    logger.addHandler(console_handler)
    logger.propagate = False # Prevent messages from being passed to the root logger if it also has handlers

    # Also ensure yt-dlp's own logger is somewhat managed if it's too noisy
    # logging.getLogger("yt_dlp").setLevel(logging.WARNING)


    test_downloader()
    # Example of direct usage:
    # downloader = UnifiedYouTubeDownloader()
    # result = downloader.download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    # if result.success:
    # print(f"Downloaded: {result.video_path}")
    # else:
    # print(f"Failed: {result.error}")
    # downloader.cleanup()
