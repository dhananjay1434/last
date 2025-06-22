#!/usr/bin/env python3
"""
Test script for YouTube download functionality
Tests different download methods and provides recommendations
"""

import os
import sys
import logging
import tempfile
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test URLs (known working educational videos)
TEST_URLS = [
    "https://www.youtube.com/watch?v=kuIfHJEsPkY",  # User's URL
    "https://www.youtube.com/watch?v=NybHckSEQBI",  # Khan Academy
    "https://www.youtube.com/watch?v=ZM8ECpBuQYE",  # MIT OpenCourseWare
    "https://www.youtube.com/watch?v=yWO-cvGETRQ",  # TED-Ed
]

def test_yt_dlp_basic(url):
    """Test basic yt-dlp functionality"""
    try:
        logger.info(f"Testing yt-dlp with: {url}")
        
        # Test info extraction only (no download)
        cmd = [
            "yt-dlp",
            "--no-download",
            "--print", "title",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--no-check-certificates",
            "--ignore-errors",
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"✅ yt-dlp success: {result.stdout.strip()}")
            return True
        else:
            logger.warning(f"❌ yt-dlp failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning("❌ yt-dlp timeout")
        return False
    except Exception as e:
        logger.error(f"❌ yt-dlp error: {e}")
        return False

def test_robust_downloader(url):
    """Test robust downloader if available"""
    try:
        from robust_youtube_downloader import RobustYouTubeDownloader
        
        logger.info(f"Testing robust downloader with: {url}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = RobustYouTubeDownloader(output_dir=temp_dir)
            
            # Test accessibility check only
            if hasattr(downloader, '_is_video_accessible'):
                accessible = downloader._is_video_accessible(url)
                if accessible:
                    logger.info("✅ Robust downloader: Video appears accessible")
                    return True
                else:
                    logger.warning("❌ Robust downloader: Video not accessible")
                    return False
            else:
                logger.info("⚠️ Robust downloader: Accessibility check not available")
                return None
                
    except ImportError:
        logger.warning("❌ Robust downloader not available")
        return None
    except Exception as e:
        logger.error(f"❌ Robust downloader error: {e}")
        return False

def test_pytube(url):
    """Test pytube if available"""
    try:
        from pytube import YouTube
        
        logger.info(f"Testing pytube with: {url}")
        
        yt = YouTube(url)
        title = yt.title
        
        if title:
            logger.info(f"✅ pytube success: {title}")
            return True
        else:
            logger.warning("❌ pytube: No title found")
            return False
            
    except ImportError:
        logger.warning("❌ pytube not available")
        return None
    except Exception as e:
        logger.error(f"❌ pytube error: {e}")
        return False

def analyze_results(results):
    """Analyze test results and provide recommendations"""
    logger.info("\n📊 Test Results Analysis:")
    logger.info("=" * 50)
    
    working_methods = []
    failing_methods = []
    
    for url, methods in results.items():
        logger.info(f"\nURL: {url}")
        for method, success in methods.items():
            if success is True:
                working_methods.append(method)
                logger.info(f"  ✅ {method}: Working")
            elif success is False:
                failing_methods.append(method)
                logger.info(f"  ❌ {method}: Failed")
            else:
                logger.info(f"  ⚠️ {method}: Not available")
    
    # Recommendations
    logger.info("\n💡 Recommendations:")
    logger.info("=" * 30)
    
    if not working_methods:
        logger.info("❌ No download methods are working")
        logger.info("   This suggests network restrictions or YouTube blocking")
        logger.info("   Try:")
        logger.info("   1. Different network/VPN")
        logger.info("   2. Wait and try later")
        logger.info("   3. Use different video URLs")
    elif len(set(working_methods)) < 2:
        logger.info("⚠️ Limited download methods working")
        logger.info("   Consider implementing additional fallback methods")
    else:
        logger.info("✅ Multiple download methods working")
        logger.info("   Your setup should handle most videos reliably")
    
    # Specific advice for the deployment
    if 'yt-dlp' in failing_methods:
        logger.info("\n🔧 Deployment Fix Suggestions:")
        logger.info("1. Update yt-dlp to latest version")
        logger.info("2. Add more user agents and headers")
        logger.info("3. Implement request throttling")
        logger.info("4. Consider using proxy rotation")

def main():
    """Main test function"""
    logger.info("🧪 Testing YouTube Download Methods")
    logger.info("=" * 50)
    
    results = {}
    
    for url in TEST_URLS:
        logger.info(f"\n🎯 Testing URL: {url}")
        logger.info("-" * 40)
        
        url_results = {
            'yt-dlp': test_yt_dlp_basic(url),
            'robust_downloader': test_robust_downloader(url),
            'pytube': test_pytube(url)
        }
        
        results[url] = url_results
    
    # Analyze and provide recommendations
    analyze_results(results)
    
    logger.info("\n🎉 Testing completed!")

if __name__ == "__main__":
    main()
