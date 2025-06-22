#!/usr/bin/env python3
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
    print("\nTest 2: Network Connectivity")
    try:
        result = subprocess.run(['ping', '-c', '1', 'youtube.com'], capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ Can reach YouTube")
        else:
            print("❌ Cannot reach YouTube")
    except:
        print("⚠️ Ping test failed (may be normal in some environments)")
    
    # Test 3: Simple download test
    print("\nTest 3: Simple Download Test")
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
    print("\n" + "=" * 50)
    if success:
        print("🎉 Deployment environment test PASSED")
        print("yt-dlp should work in this environment")
    else:
        print("❌ Deployment environment test FAILED")
        print("yt-dlp may have issues in this environment")
    
    sys.exit(0 if success else 1)
