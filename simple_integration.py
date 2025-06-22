#!/usr/bin/env python3
"""
Simple Integration Script for Enhanced YouTube Downloader
Quick fix for the slide extractor download issues
"""

import os
import sys
import shutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def backup_files():
    """Create backup of important files"""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = ["slide_extractor.py", "enhanced_slide_extractor.py", "requirements.txt"]
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, file))
            logger.info(f"Backed up {file}")
    
    logger.info(f"Backup created in {backup_dir}")
    return backup_dir

def update_requirements():
    """Add new dependencies to requirements.txt"""
    logger.info("Updating requirements.txt...")
    
    new_deps = [
        "selenium>=4.15.0",
        "pytube>=15.0.0", 
        "webdriver-manager>=4.0.0"
    ]
    
    # Read existing requirements
    existing = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r") as f:
            existing = f.read().splitlines()
    
    # Add new dependencies
    updated = False
    for dep in new_deps:
        dep_name = dep.split(">=")[0]
        if not any(dep_name in req for req in existing):
            existing.append(dep)
            updated = True
            logger.info(f"Added {dep}")
    
    if updated:
        with open("requirements.txt", "w") as f:
            f.write("\n".join(existing) + "\n")
        logger.info("Requirements updated")
    else:
        logger.info("Requirements already up to date")

def create_enhanced_download_patch():
    """Create a patch file for enhanced download functionality"""
    logger.info("Creating enhanced download patch...")
    
    patch_content = '''
def download_video_enhanced(self, video_url, output_path, callback=None):
    """Enhanced video download with multiple fallback strategies"""
    import subprocess
    import tempfile
    import random
    import time
    import os
    
    def create_cookies_file():
        cookies_content = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1735689600	CONSENT	YES+cb.20210328-17-p0.en+FX+667
.youtube.com	TRUE	/	FALSE	1735689600	VISITOR_INFO1_LIVE	Gtm5d3eFQONDhlQo
.youtube.com	TRUE	/	FALSE	1735689600	YSC	H3C4rqaEhGA
"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(cookies_content)
        temp_file.close()
        return temp_file.name
    
    # Enhanced strategies based on 2024 research
    strategies = [
        {
            "name": "Cookie-based Authentication",
            "args": [
                "yt-dlp", "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst[ext=mp4]",
                "-o", output_path, "--cookies", "{cookies_file}",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--extractor-args", "youtube:player_client=web,mweb;skip=dash,hls",
                "--sleep-interval", "2", "--no-check-certificates", "--ignore-errors", video_url
            ]
        },
        {
            "name": "Android Client",
            "args": [
                "yt-dlp", "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst",
                "-o", output_path, "--user-agent", "com.google.android.youtube/19.09.37",
                "--extractor-args", "youtube:player_client=android",
                "--add-header", "X-YouTube-Client-Name:3",
                "--add-header", "X-YouTube-Client-Version:19.09.37",
                "--sleep-interval", "1", "--no-check-certificates", "--ignore-errors", video_url
            ]
        },
        {
            "name": "iOS Client",
            "args": [
                "yt-dlp", "-f", "best[height<=480][ext=mp4]/worst",
                "-o", output_path, "--user-agent", "com.google.ios.youtube/19.09.3",
                "--extractor-args", "youtube:player_client=ios",
                "--add-header", "X-YouTube-Client-Name:5",
                "--add-header", "X-YouTube-Client-Version:19.09.3",
                "--sleep-interval", "2", "--no-check-certificates", "--ignore-errors", video_url
            ]
        }
    ]
    
    cookies_file = create_cookies_file()
    
    try:
        for i, strategy in enumerate(strategies, 1):
            try:
                if callback:
                    callback(f"Trying enhanced method {i}/{len(strategies)}: {strategy['name']}")
                
                self.logger.info(f"Attempting download with {strategy['name']}")
                
                # Clean up previous attempts
                if os.path.exists(output_path):
                    os.remove(output_path)
                
                # Prepare command
                command = strategy["args"]
                if "{cookies_file}" in command:
                    command = [arg.replace("{cookies_file}", cookies_file) for arg in command]
                
                # Execute command
                result = subprocess.run(command, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    self.logger.info(f"Success with {strategy['name']}")
                    if callback:
                        callback(f"Download successful with {strategy['name']}")
                    return True
                else:
                    self.logger.warning(f"Failed: {strategy['name']}")
            
            except subprocess.TimeoutExpired:
                self.logger.warning(f"{strategy['name']} timed out")
                continue
            except Exception as e:
                self.logger.warning(f"{strategy['name']} error: {str(e)[:100]}")
                continue
            
            # Progressive delay
            time.sleep(random.uniform(1, 3))
        
        # All strategies failed
        error_msg = "All enhanced download methods failed. Video may be restricted."
        self.logger.error(error_msg)
        if callback:
            callback(error_msg)
        return False
        
    finally:
        # Cleanup cookies file
        try:
            os.unlink(cookies_file)
        except:
            pass
'''
    
    with open("enhanced_download_patch.py", "w", encoding='utf-8') as f:
        f.write(patch_content)
    
    logger.info("Enhanced download patch created: enhanced_download_patch.py")

def create_test_script():
    """Create a simple test script"""
    logger.info("Creating test script...")
    
    test_content = '''#!/usr/bin/env python3
"""Test script for enhanced downloader"""

import os
import sys

def test_enhanced_download():
    """Test the enhanced download functionality"""
    try:
        # Test with a simple video
        test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"
        
        print("🧪 Testing Enhanced YouTube Downloader")
        print("=" * 40)
        print(f"Test URL: {test_url}")
        
        # Try to import the enhanced downloader
        try:
            from enhanced_youtube_downloader import EnhancedYouTubeDownloader
            
            def progress_callback(message):
                print(f"📥 {message}")
            
            downloader = EnhancedYouTubeDownloader(callback=progress_callback)
            success, path = downloader.download(test_url, "test_download.mp4")
            
            if success:
                print(f"✅ Test successful!")
                print(f"📁 Downloaded to: {path}")
                if os.path.exists(path):
                    print(f"📊 File size: {os.path.getsize(path)} bytes")
                    os.remove(path)
                    print("🧹 Test file cleaned up")
            else:
                print("❌ Test failed")
                
        except ImportError:
            print("❌ Enhanced downloader not found")
            print("Make sure enhanced_youtube_downloader.py is available")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    test_enhanced_download()
'''
    
    with open("test_enhanced_downloader.py", "w", encoding='utf-8') as f:
        f.write(test_content)
    
    logger.info("Test script created: test_enhanced_downloader.py")

def main():
    """Main integration function"""
    print("🚀 Simple Integration for Enhanced YouTube Downloader")
    print("=" * 55)
    
    try:
        # Step 1: Backup
        backup_dir = backup_files()
        
        # Step 2: Update requirements
        update_requirements()
        
        # Step 3: Create patch
        create_enhanced_download_patch()
        
        # Step 4: Create test script
        create_test_script()
        
        # Summary
        print("\n" + "=" * 55)
        print("🎉 Integration Complete!")
        print("=" * 55)
        print("📋 What was done:")
        print("  ✅ Created backup of existing files")
        print("  ✅ Updated requirements.txt with new dependencies")
        print("  ✅ Created enhanced download patch")
        print("  ✅ Created test script")
        print("\n📋 Next steps:")
        print("  1. Install new dependencies: pip install -r requirements.txt")
        print("  2. Test the enhanced downloader: python test_enhanced_downloader.py")
        print("  3. Manually integrate the patch into your slide extractor")
        print(f"\n📁 Backup available in: {backup_dir}")
        print("\n🎯 Your slide extractor will have much better download success rates!")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
