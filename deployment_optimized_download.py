
def download_video_deployment_optimized(self, video_url, output_path, callback=None):
    """
    Deployment-optimized video download method
    Addresses differences between local Windows and deployed Linux environment
    """
    import subprocess
    import tempfile
    import random
    import time
    import os
    import platform
    
    def create_deployment_cookies():
        """Create cookies optimized for deployment environment"""
        cookies_content = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1735689600	CONSENT	YES+cb.20210328-17-p0.en+FX+667
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	Gtm5d3eFQONDhlQo
.youtube.com	TRUE	/	FALSE	1735689600	YSC	H3C4rqaEhGA
.youtube.com	TRUE	/	FALSE	1735689600	PREF	f4=4000000&hl=en&f5=30000
"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(cookies_content)
        temp_file.close()
        return temp_file.name
    
    # Deployment-specific configurations
    is_deployment = os.environ.get('ENVIRONMENT') == 'production'
    is_linux = platform.system() == "Linux"
    
    # Enhanced strategies for deployment environment
    strategies = [
        {
            "name": "Deployment-Optimized Android Client",
            "command": [
                "yt-dlp",
                "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst",
                "-o", output_path,
                "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
                "--extractor-args", "youtube:player_client=android",
                "--add-header", "X-YouTube-Client-Name:3",
                "--add-header", "X-YouTube-Client-Version:19.09.37",
                "--add-header", "Accept-Language:en-US,en;q=0.9",
                "--sleep-interval", "2",
                "--socket-timeout", "30",
                "--retries", "3",
                "--no-check-certificates",
                "--ignore-errors",
                "--no-warnings",
                video_url
            ]
        },
        {
            "name": "Linux-Optimized Web Client",
            "command": [
                "yt-dlp",
                "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst[ext=mp4]",
                "-o", output_path,
                "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "--extractor-args", "youtube:player_client=web;skip=dash,hls",
                "--add-header", "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "--add-header", "Accept-Language:en-US,en;q=0.9",
                "--add-header", "Accept-Encoding:gzip, deflate, br",
                "--add-header", "DNT:1",
                "--add-header", "Connection:keep-alive",
                "--add-header", "Upgrade-Insecure-Requests:1",
                "--sleep-interval", "3",
                "--socket-timeout", "30",
                "--retries", "2",
                "--no-check-certificates",
                "--ignore-errors",
                video_url
            ]
        },
        {
            "name": "Conservative Deployment Method",
            "command": [
                "yt-dlp",
                "-f", "18/worst[ext=mp4]/worst",  # Format 18 is 360p MP4
                "-o", output_path,
                "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "--extractor-args", "youtube:skip=dash,hls,live_chat",
                "--sleep-interval", "5",
                "--socket-timeout", "60",
                "--retries", "5",
                "--fragment-retries", "5",
                "--no-check-certificates",
                "--ignore-errors",
                "--no-warnings",
                video_url
            ]
        }
    ]
    
    # Add cookies to first strategy if in deployment
    if is_deployment:
        cookies_file = create_deployment_cookies()
        strategies[0]["command"].extend(["--cookies", cookies_file])
    else:
        cookies_file = None
    
    try:
        for i, strategy in enumerate(strategies, 1):
            try:
                if callback:
                    callback(f"Trying deployment method {i}/{len(strategies)}: {strategy['name']}")
                
                logger.info(f"Attempting download with {strategy['name']} (deployment environment)")
                
                # Clean up previous attempts
                if os.path.exists(output_path):
                    os.remove(output_path)
                
                # Execute command with extended timeout for deployment
                result = subprocess.run(
                    strategy["command"], 
                    capture_output=True, 
                    text=True, 
                    timeout=600,  # 10 minutes for deployment
                    env=dict(os.environ, PYTHONUNBUFFERED='1')  # Ensure output is not buffered
                )
                
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    file_size = os.path.getsize(output_path)
                    logger.info(f"SUCCESS: {strategy['name']} worked! (Size: {file_size/1024/1024:.1f}MB)")
                    if callback:
                        callback(f"Download successful with {strategy['name']}")
                    return True
                else:
                    logger.warning(f"FAILED: {strategy['name']} - Return code: {result.returncode}")
                    if result.stderr:
                        logger.warning(f"Error output: {result.stderr[:200]}")
            
            except subprocess.TimeoutExpired:
                logger.warning(f"TIMEOUT: {strategy['name']} took too long")
                continue
            except Exception as e:
                logger.warning(f"ERROR: {strategy['name']} - {str(e)[:100]}")
                continue
            
            # Progressive delay between attempts
            time.sleep(random.uniform(2, 5))
        
        # All strategies failed
        error_msg = "All deployment-optimized download methods failed."
        if is_deployment:
            error_msg += "\n\nDeployment environment issues detected. This may be due to:"
            error_msg += "\n1. Server firewall restrictions"
            error_msg += "\n2. Different SSL/TLS configuration"
            error_msg += "\n3. Network routing differences"
            error_msg += "\n4. Missing system dependencies"
        
        logger.error(error_msg)
        if callback:
            callback("Download failed: Deployment environment issues")
        return False
        
    finally:
        # Cleanup cookies file
        if cookies_file and os.path.exists(cookies_file):
            try:
                os.unlink(cookies_file)
            except:
                pass
