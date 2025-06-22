#!/usr/bin/env python3
"""
Test the integrated enhanced download method
"""

import os
import sys
import tempfile
import shutil

def test_enhanced_slide_extractor():
    """Test the enhanced slide extractor with improved download"""
    print("Testing Enhanced Slide Extractor Integration")
    print("=" * 50)
    
    try:
        # Import the slide extractor
        from slide_extractor import SlideExtractor
        
        # Create a temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        print(f"Using temp directory: {temp_dir}")
        
        # Test URL (Khan Academy video - usually accessible)
        test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"
        
        def progress_callback(message):
            print(f"Progress: {message}")
        
        # Create slide extractor instance
        extractor = SlideExtractor(
            video_url=test_url,
            output_dir=temp_dir,
            callback=progress_callback,
            interval=30,  # Sample every 30 seconds for quick test
            similarity_threshold=0.8
        )
        
        print(f"Testing download for: {test_url}")
        
        # Test just the download method
        success = extractor.download_video()
        
        if success:
            print("SUCCESS: Enhanced download method is working!")
            
            # Check if video file exists
            if hasattr(extractor, 'video_path') and os.path.exists(extractor.video_path):
                file_size = os.path.getsize(extractor.video_path)
                print(f"Downloaded video: {file_size} bytes ({file_size/1024/1024:.1f}MB)")
            else:
                print("Video file not found at expected location")
        else:
            print("FAILED: Enhanced download method did not work")
        
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("Cleaned up test files")
        
        return success
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure slide_extractor.py is in the current directory")
        return False
    except Exception as e:
        print(f"Test error: {e}")
        return False

def test_quick_download():
    """Quick test of just the download functionality"""
    print("\nQuick Download Test")
    print("=" * 30)
    
    import subprocess
    import tempfile
    
    test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"
    temp_file = os.path.join(tempfile.gettempdir(), "quick_test.mp4")
    
    # Test Android client method (most reliable from our research)
    command = [
        "yt-dlp",
        "-f", "best[height<=480]/worst",
        "-o", temp_file,
        "--user-agent", "com.google.android.youtube/19.09.37",
        "--extractor-args", "youtube:player_client=android",
        "--no-check-certificates",
        "--ignore-errors",
        test_url
    ]
    
    try:
        print("Testing Android client method...")
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            file_size = os.path.getsize(temp_file)
            print(f"SUCCESS: Downloaded {file_size} bytes")
            
            # Clean up
            os.remove(temp_file)
            return True
        else:
            print("FAILED: Download did not complete")
            return False
            
    except subprocess.TimeoutExpired:
        print("TIMEOUT: Download took too long")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main test function"""
    print("Enhanced YouTube Downloader Integration Test")
    print("=" * 55)
    
    # Test 1: Quick download test
    quick_success = test_quick_download()
    
    # Test 2: Full integration test
    integration_success = test_enhanced_slide_extractor()
    
    # Summary
    print("\n" + "=" * 55)
    print("TEST SUMMARY")
    print("=" * 55)
    print(f"Quick Download Test: {'PASS' if quick_success else 'FAIL'}")
    print(f"Integration Test: {'PASS' if integration_success else 'FAIL'}")
    
    if quick_success and integration_success:
        print("\n🎉 All tests passed! Enhanced downloader is working correctly.")
        print("Your slide extractor now has improved download success rates!")
    elif quick_success:
        print("\n⚠️ Quick test passed but integration test failed.")
        print("The enhanced download method works, but there may be integration issues.")
    else:
        print("\n❌ Tests failed. Check your internet connection and try again.")
    
    return quick_success and integration_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
