"""
YouTube Download Fix - Enhanced download strategies for better success rates
"""

import subprocess
import time
import random
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class YouTubeDownloadFix:
    """Enhanced YouTube download with improved success rates"""
    
    def __init__(self, video_url, output_path, callback=None):
        self.video_url = video_url
        self.output_path = output_path
        self.callback = callback
        
    def create_cookies_file(self):
        """Create a temporary cookies file for YouTube"""
        try:
            cookies_content = """# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	FALSE	1735689600	CONSENT	YES+cb.20210328-17-p0.en+FX+667
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	abcdefghijk123
.youtube.com	TRUE	/	FALSE	1735689600	YSC	random123456789
"""
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_file.write(cookies_content)
            temp_file.close()
            return temp_file.name
        except Exception:
            return None

    def get_enhanced_strategies(self):
        """Get enhanced download strategies with 2024 improvements"""
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]
        
        cookies_file = self.create_cookies_file()
        
        strategies = []
        
        # Strategy 1: Latest 2024 method with enhanced headers
        strategy1 = [
            "yt-dlp",
            "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst[ext=mp4]/worst",
            "-o", self.output_path,
            "--user-agent", random.choice(user_agents),
            "--add-header", "Accept-Language:en-US,en;q=0.9",
            "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "--add-header", "Sec-Ch-Ua:\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "--add-header", "Sec-Ch-Ua-Mobile:?0",
            "--add-header", "Sec-Ch-Ua-Platform:\"Windows\"",
            "--add-header", "Sec-Fetch-Dest:document",
            "--add-header", "Sec-Fetch-Mode:navigate",
            "--add-header", "Sec-Fetch-Site:none",
            "--add-header", "Sec-Fetch-User:?1",
            "--extractor-args", "youtube:player_client=web;skip=dash,hls",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5",
            "--no-check-certificates",
            "--ignore-errors",
            "--no-warnings",
            self.video_url
        ]
        
        if cookies_file:
            strategy1.extend(["--cookies", cookies_file])
        
        strategies.append(strategy1)
        
        # Strategy 2: Android client (often most reliable)
        strategies.append([
            "yt-dlp",
            "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst",
            "-o", self.output_path,
            "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
            "--extractor-args", "youtube:player_client=android",
            "--add-header", "X-YouTube-Client-Name:3",
            "--add-header", "X-YouTube-Client-Version:19.09.37",
            "--sleep-interval", "1",
            "--max-sleep-interval", "3",
            "--no-check-certificates",
            "--ignore-errors",
            "--no-warnings",
            self.video_url
        ])
        
        # Strategy 3: iOS client fallback
        strategies.append([
            "yt-dlp",
            "-f", "best[height<=480][ext=mp4]/worst",
            "-o", self.output_path,
            "--user-agent", "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 16_1_2 like Mac OS X)",
            "--extractor-args", "youtube:player_client=ios",
            "--add-header", "X-YouTube-Client-Name:5",
            "--add-header", "X-YouTube-Client-Version:19.09.3",
            "--sleep-interval", "2",
            "--no-check-certificates",
            "--ignore-errors",
            self.video_url
        ])
        
        # Strategy 4: Web client with minimal format requirements
        strategies.append([
            "yt-dlp",
            "-f", "18/worst[ext=mp4]/worst",  # Format 18 is 360p MP4
            "-o", self.output_path,
            "--user-agent", random.choice(user_agents),
            "--extractor-args", "youtube:player_client=web;skip=dash,hls,live_chat",
            "--sleep-interval", "3",
            "--max-sleep-interval", "6",
            "--retries", "2",
            "--fragment-retries", "2",
            "--no-check-certificates",
            "--ignore-errors",
            self.video_url
        ])
        
        # Strategy 5: Last resort - any available format
        strategies.append([
            "yt-dlp",
            "-f", "worst/best",
            "-o", self.output_path,
            "--user-agent", random.choice(user_agents),
            "--extractor-args", "youtube:player_client=web",
            "--sleep-interval", "4",
            "--retries", "1",
            "--no-check-certificates",
            "--ignore-errors",
            "--no-warnings",
            self.video_url
        ])
        
        return strategies, cookies_file

    def download_with_enhanced_strategies(self):
        """Download video using enhanced strategies"""
        strategies, cookies_file = self.get_enhanced_strategies()
        
        try:
            for i, command in enumerate(strategies, 1):
                try:
                    if self.callback:
                        self.callback(f"Trying enhanced download method {i}/{len(strategies)}...")
                    
                    logger.info(f"Attempting download with enhanced strategy {i}")
                    
                    # Progressive delay between attempts
                    if i > 1:
                        delay = random.uniform(1 + i, 3 + i)
                        time.sleep(delay)
                    
                    # Execute command with timeout
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minute timeout per attempt
                        cwd=os.path.dirname(self.output_path) if os.path.dirname(self.output_path) else None
                    )
                    
                    if result.returncode == 0 and os.path.exists(self.output_path):
                        # Verify file is not empty
                        if os.path.getsize(self.output_path) > 1024:  # At least 1KB
                            logger.info(f"✅ Enhanced method {i} succeeded!")
                            if self.callback:
                                self.callback(f"Download successful with method {i}")
                            return True
                        else:
                            logger.warning(f"Enhanced method {i} created empty file")
                            if os.path.exists(self.output_path):
                                os.remove(self.output_path)
                    else:
                        logger.warning(f"❌ Enhanced method {i} failed with return code {result.returncode}")
                        if result.stderr:
                            logger.debug(f"Error output: {result.stderr[:200]}")
                
                except subprocess.TimeoutExpired:
                    logger.warning(f"Enhanced method {i} timed out")
                    continue
                except Exception as e:
                    logger.warning(f"Enhanced method {i} exception: {str(e)[:100]}")
                    continue
            
            # All methods failed
            error_msg = "❌ All enhanced download methods failed.\n\n"
            error_msg += "This video may be restricted or unavailable. Try:\n"
            error_msg += "1. A different YouTube video\n"
            error_msg += "2. A shorter video (under 10 minutes)\n"
            error_msg += "3. An educational channel video\n"
            error_msg += "4. Waiting and trying again later"
            
            logger.error(error_msg)
            if self.callback:
                self.callback("Download failed: Video may be restricted")
            
            return False
            
        finally:
            # Clean up cookies file
            if cookies_file and os.path.exists(cookies_file):
                try:
                    os.unlink(cookies_file)
                except:
                    pass
        
        return False

def test_video_accessibility(video_url, timeout=30):
    """Test if a video is accessible without downloading"""
    try:
        command = [
            "yt-dlp",
            "--no-download",
            "--print", "title",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--no-check-certificates",
            "--ignore-errors",
            "--extractor-args", "youtube:player_client=web",
            video_url
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0 and result.stdout.strip():
            return True, result.stdout.strip()
        else:
            return False, "Video not accessible"
            
    except subprocess.TimeoutExpired:
        return False, "Test timed out"
    except Exception as e:
        return False, f"Test error: {str(e)}"
