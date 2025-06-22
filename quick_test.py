#!/usr/bin/env python3
"""Quick test for enhanced YouTube downloader"""

import subprocess
import os
import tempfile

def quick_test():
    """Quick test of enhanced yt-dlp strategies"""
    print("Quick Test: Enhanced YouTube Download Strategies")
    print("=" * 50)
    
    test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"
    output_file = "quick_test_video.mp4"
    
    # Strategy 1: Android client (usually most reliable)
    print("Testing Android client strategy...")
    
    command = [
        "yt-dlp",
        "-f", "best[height<=480]/worst",
        "-o", output_file,
        "--user-agent", "com.google.android.youtube/19.09.37",
        "--extractor-args", "youtube:player_client=android",
        "--no-check-certificates",
        "--ignore-errors",
        test_url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"SUCCESS: Downloaded {file_size} bytes")
            
            # Clean up
            os.remove(output_file)
            print("Test file cleaned up")
            print("Enhanced download strategies are working!")
        else:
            print("FAILED: Download did not complete successfully")
            print("You may need to try different strategies or check your internet connection")
            
    except subprocess.TimeoutExpired:
        print("TIMEOUT: Download took too long")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    quick_test()
