#!/usr/bin/env python3
"""
Deployment Environment Fix for yt-dlp
Addresses differences between local Windows and deployed Linux environment
"""

import os
import sys
import subprocess
import platform
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeploymentEnvironmentFix:
    """Fix environment-specific issues for yt-dlp deployment"""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self.is_deployment = os.environ.get('ENVIRONMENT') == 'production'
        
    def diagnose_environment(self):
        """Diagnose the current environment and potential issues"""
        logger.info("🔍 Diagnosing deployment environment...")
        
        issues = []
        
        # Check 1: Operating System
        logger.info(f"Operating System: {platform.system()} {platform.release()}")
        if self.is_linux and not self.is_windows:
            logger.info("✅ Running on Linux (typical for deployment)")
        
        # Check 2: yt-dlp installation
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ yt-dlp version: {result.stdout.strip()}")
            else:
                issues.append("❌ yt-dlp not working properly")
                logger.error("❌ yt-dlp not working properly")
        except FileNotFoundError:
            issues.append("❌ yt-dlp not installed")
            logger.error("❌ yt-dlp not installed")
        except Exception as e:
            issues.append(f"❌ yt-dlp error: {e}")
            logger.error(f"❌ yt-dlp error: {e}")
        
        # Check 3: Network connectivity
        try:
            result = subprocess.run(['ping', '-c', '1', 'youtube.com'], capture_output=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ Network connectivity to YouTube")
            else:
                issues.append("❌ Network connectivity issues")
                logger.error("❌ Network connectivity issues")
        except:
            logger.warning("⚠️ Could not test network connectivity")
        
        # Check 4: SSL/TLS certificates
        try:
            import ssl
            import urllib.request
            urllib.request.urlopen('https://youtube.com', timeout=10)
            logger.info("✅ SSL/TLS certificates working")
        except Exception as e:
            issues.append(f"❌ SSL/TLS issues: {e}")
            logger.error(f"❌ SSL/TLS issues: {e}")
        
        # Check 5: User agent and headers
        if self.is_deployment:
            logger.info("🔧 Deployment environment detected - may need enhanced headers")
        
        return issues
    
    def create_deployment_optimized_download(self):
        """Create yt-dlp download method optimized for deployment environment"""
        logger.info("🔧 Creating deployment-optimized download method...")
        
        deployment_method = '''
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
            error_msg += "\\n\\nDeployment environment issues detected. This may be due to:"
            error_msg += "\\n1. Server firewall restrictions"
            error_msg += "\\n2. Different SSL/TLS configuration"
            error_msg += "\\n3. Network routing differences"
            error_msg += "\\n4. Missing system dependencies"
        
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
'''
        
        with open("deployment_optimized_download.py", "w", encoding='utf-8') as f:
            f.write(deployment_method)
        
        logger.info("✅ Deployment-optimized download method created")
    
    def create_environment_detection(self):
        """Create environment detection and auto-configuration"""
        logger.info("🔧 Creating environment detection...")
        
        detection_code = '''
def detect_and_configure_environment():
    """
    Detect deployment environment and configure yt-dlp accordingly
    """
    import os
    import platform
    import subprocess
    
    env_info = {
        "is_windows": platform.system() == "Windows",
        "is_linux": platform.system() == "Linux",
        "is_deployment": os.environ.get('ENVIRONMENT') == 'production',
        "is_render": 'RENDER' in os.environ,
        "is_heroku": 'DYNO' in os.environ,
        "python_version": platform.python_version(),
        "architecture": platform.machine()
    }
    
    # Configure based on environment
    if env_info["is_deployment"]:
        # Deployment-specific configurations
        os.environ.setdefault('PYTHONUNBUFFERED', '1')
        os.environ.setdefault('YTDL_NO_CHECK_CERTIFICATE', '1')
        
        # Set longer timeouts for deployment
        os.environ.setdefault('YTDL_SOCKET_TIMEOUT', '60')
        os.environ.setdefault('YTDL_READ_TIMEOUT', '120')
    
    return env_info

def get_optimal_yt_dlp_config(env_info=None):
    """
    Get optimal yt-dlp configuration based on environment
    """
    if env_info is None:
        env_info = detect_and_configure_environment()
    
    base_config = [
        "--no-check-certificates",
        "--ignore-errors",
        "--socket-timeout", "60",
        "--retries", "3"
    ]
    
    if env_info["is_deployment"]:
        # Deployment-specific optimizations
        base_config.extend([
            "--sleep-interval", "3",
            "--max-sleep-interval", "8",
            "--fragment-retries", "3",
            "--no-warnings"
        ])
        
        if env_info["is_linux"]:
            # Linux-specific optimizations
            base_config.extend([
                "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ])
    else:
        # Local development optimizations
        base_config.extend([
            "--sleep-interval", "1",
            "--max-sleep-interval", "3"
        ])
    
    return base_config
'''
        
        with open("environment_detection.py", "w", encoding='utf-8') as f:
            f.write(detection_code)
        
        logger.info("✅ Environment detection created")
    
    def create_deployment_test(self):
        """Create deployment-specific test"""
        logger.info("🧪 Creating deployment test...")
        
        test_code = '''#!/usr/bin/env python3
"""
Deployment Environment Test for yt-dlp
Tests yt-dlp functionality in deployment environment
"""

import os
import sys
import subprocess
import platform
import tempfile

def test_deployment_environment():
    """Test yt-dlp in deployment environment"""
    print("🧪 Testing Deployment Environment for yt-dlp")
    print("=" * 50)
    
    # Environment info
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print()
    
    # Test 1: yt-dlp installation
    print("Test 1: yt-dlp Installation")
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ yt-dlp version: {result.stdout.strip()}")
        else:
            print("❌ yt-dlp not working")
            return False
    except Exception as e:
        print(f"❌ yt-dlp error: {e}")
        return False
    
    # Test 2: Network connectivity
    print("\\nTest 2: Network Connectivity")
    try:
        result = subprocess.run(['ping', '-c', '1', 'youtube.com'], capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ Can reach YouTube")
        else:
            print("❌ Cannot reach YouTube")
    except:
        print("⚠️ Ping test failed (may be normal in some environments)")
    
    # Test 3: Simple download test
    print("\\nTest 3: Simple Download Test")
    test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"
    temp_file = os.path.join(tempfile.gettempdir(), "deployment_test.mp4")
    
    # Deployment-optimized command
    command = [
        "yt-dlp",
        "-f", "worst",  # Use worst quality for quick test
        "-o", temp_file,
        "--user-agent", "com.google.android.youtube/19.09.37",
        "--extractor-args", "youtube:player_client=android",
        "--socket-timeout", "60",
        "--retries", "2",
        "--no-check-certificates",
        "--ignore-errors",
        "--no-warnings",
        test_url
    ]
    
    try:
        print("Testing Android client method...")
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            file_size = os.path.getsize(temp_file)
            print(f"✅ Download successful: {file_size} bytes")
            
            # Clean up
            os.remove(temp_file)
            return True
        else:
            print(f"❌ Download failed: Return code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Download timed out")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

if __name__ == "__main__":
    success = test_deployment_environment()
    print("\\n" + "=" * 50)
    if success:
        print("🎉 Deployment environment test PASSED")
        print("yt-dlp should work in this environment")
    else:
        print("❌ Deployment environment test FAILED")
        print("yt-dlp may have issues in this environment")
    
    sys.exit(0 if success else 1)
'''
        
        with open("test_deployment_environment.py", "w", encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info("✅ Deployment test created")
    
    def run_diagnosis(self):
        """Run complete diagnosis and create fixes"""
        logger.info("🚀 Running Deployment Environment Diagnosis")
        logger.info("=" * 50)
        
        # Step 1: Diagnose current environment
        issues = self.diagnose_environment()
        
        # Step 2: Create deployment-optimized solutions
        self.create_deployment_optimized_download()
        self.create_environment_detection()
        self.create_deployment_test()
        
        # Step 3: Summary
        logger.info("\\n" + "=" * 50)
        logger.info("🎯 DIAGNOSIS COMPLETE")
        logger.info("=" * 50)
        
        if issues:
            logger.warning("Issues found:")
            for issue in issues:
                logger.warning(f"  {issue}")
        else:
            logger.info("✅ No major issues detected")
        
        logger.info("\\nFiles created:")
        logger.info("  📄 deployment_optimized_download.py")
        logger.info("  📄 environment_detection.py") 
        logger.info("  📄 test_deployment_environment.py")
        
        logger.info("\\nNext steps:")
        logger.info("  1. Run: python test_deployment_environment.py")
        logger.info("  2. If test passes, integrate deployment-optimized method")
        logger.info("  3. Deploy with environment-specific configurations")
        
        return len(issues) == 0

def main():
    """Main function"""
    fixer = DeploymentEnvironmentFix()
    success = fixer.run_diagnosis()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
