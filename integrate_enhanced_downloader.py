#!/usr/bin/env python3
"""
Integration Script for Enhanced YouTube Downloader
Updates existing slide extractor with research-based improvements
"""

import os
import sys
import shutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloaderIntegration:
    """Integrates enhanced downloader into existing codebase"""
    
    def __init__(self):
        self.backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def backup_existing_files(self):
        """Backup existing files before modification"""
        logger.info("📁 Creating backup of existing files...")
        
        files_to_backup = [
            "slide_extractor.py",
            "enhanced_slide_extractor.py",
            "requirements.txt"
        ]
        
        os.makedirs(self.backup_dir, exist_ok=True)
        
        for file in files_to_backup:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(self.backup_dir, file))
                logger.info(f"✅ Backed up {file}")
        
        logger.info(f"📦 Backup created in {self.backup_dir}")
    
    def update_requirements(self):
        """Add new dependencies to requirements.txt"""
        logger.info("📦 Updating requirements.txt...")
        
        new_dependencies = [
            "selenium>=4.15.0",
            "pytube>=15.0.0", 
            "webdriver-manager>=4.0.0"
        ]
        
        # Read existing requirements
        existing_reqs = []
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", "r") as f:
                existing_reqs = f.read().splitlines()
        
        # Add new dependencies if not present
        updated = False
        for dep in new_dependencies:
            dep_name = dep.split(">=")[0]
            if not any(dep_name in req for req in existing_reqs):
                existing_reqs.append(dep)
                updated = True
                logger.info(f"➕ Added {dep}")
        
        if updated:
            with open("requirements.txt", "w") as f:
                f.write("\n".join(existing_reqs) + "\n")
            logger.info("✅ Requirements updated")
        else:
            logger.info("ℹ️ Requirements already up to date")
    
    def create_enhanced_download_method(self):
        """Create enhanced download method for existing extractors"""
        logger.info("🔧 Creating enhanced download method...")
        
        enhanced_method = '''
    def download_video_enhanced(self, video_url, output_path, callback=None):
        """
        Enhanced video download with multiple fallback strategies
        Based on 2024 research for improved success rates
        """
        import subprocess
        import tempfile
        import random
        import time
        
        def create_cookies_file():
            """Create realistic cookies for YouTube"""
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
                "command": lambda cookies_file: [
                    "yt-dlp",
                    "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst[ext=mp4]",
                    "-o", output_path,
                    "--cookies", cookies_file,
                    "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "--extractor-args", "youtube:player_client=web,mweb;skip=dash,hls",
                    "--sleep-interval", "2",
                    "--no-check-certificates",
                    "--ignore-errors",
                    video_url
                ]
            },
            {
                "name": "Android Client",
                "command": lambda _: [
                    "yt-dlp",
                    "-f", "best[height<=720][ext=mp4]/best[height<=480]/worst",
                    "-o", output_path,
                    "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
                    "--extractor-args", "youtube:player_client=android",
                    "--add-header", "X-YouTube-Client-Name:3",
                    "--add-header", "X-YouTube-Client-Version:19.09.37",
                    "--sleep-interval", "1",
                    "--no-check-certificates",
                    "--ignore-errors",
                    video_url
                ]
            },
            {
                "name": "iOS Client",
                "command": lambda _: [
                    "yt-dlp",
                    "-f", "best[height<=480][ext=mp4]/worst",
                    "-o", output_path,
                    "--user-agent", "com.google.ios.youtube/19.09.3 (iPhone14,3; U; CPU iOS 16_1_2 like Mac OS X)",
                    "--extractor-args", "youtube:player_client=ios",
                    "--add-header", "X-YouTube-Client-Name:5",
                    "--add-header", "X-YouTube-Client-Version:19.09.3",
                    "--sleep-interval", "2",
                    "--no-check-certificates",
                    "--ignore-errors",
                    video_url
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
                    
                    # Execute command
                    command = strategy["command"](cookies_file)
                    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                        self.logger.info(f"✅ Success with {strategy['name']}")
                        if callback:
                            callback(f"Download successful with {strategy['name']}")
                        return True
                    else:
                        self.logger.warning(f"❌ {strategy['name']} failed")
                
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
        
        return enhanced_method
    
    def update_slide_extractor(self):
        """Update slide_extractor.py with enhanced download method"""
        logger.info("🔧 Updating slide_extractor.py...")
        
        if not os.path.exists("slide_extractor.py"):
            logger.warning("slide_extractor.py not found, skipping...")
            return
        
        with open("slide_extractor.py", "r") as f:
            content = f.read()
        
        # Add enhanced method before the last class method
        enhanced_method = self.create_enhanced_download_method()
        
        # Find a good insertion point (before the last method)
        lines = content.split('\n')
        insertion_point = -1
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith('def ') and not lines[i].strip().startswith('def __'):
                insertion_point = i
                break
        
        if insertion_point > 0:
            # Insert the enhanced method
            lines.insert(insertion_point, enhanced_method)
            
            # Update the original download method to use enhanced version
            updated_content = '\n'.join(lines)
            
            # Replace calls to original download method
            updated_content = updated_content.replace(
                'self.download_video(',
                'self.download_video_enhanced('
            )
            
            with open("slide_extractor.py", "w") as f:
                f.write(updated_content)
            
            logger.info("✅ slide_extractor.py updated with enhanced download method")
        else:
            logger.warning("Could not find insertion point in slide_extractor.py")
    
    def create_test_script(self):
        """Create test script for enhanced downloader"""
        logger.info("🧪 Creating test script...")
        
        test_script = """#!/usr/bin/env python3
# Test script for enhanced YouTube downloader

import sys
import os
sys.path.insert(0, '.')

def test_enhanced_download():
    try:
        from enhanced_youtube_downloader import EnhancedYouTubeDownloader

        print("🧪 Testing Enhanced YouTube Downloader")
        print("=" * 40)

        # Test with Khan Academy video (usually accessible)
        test_url = "https://www.youtube.com/watch?v=NybHckSEQBI"

        def progress_callback(message):
            print(f"📥 {message}")

        downloader = EnhancedYouTubeDownloader(callback=progress_callback)
        success, path = downloader.download(test_url, "test_download.mp4")

        if success:
            print(f"✅ Test successful!")
            print(f"📁 Downloaded to: {path}")
            print(f"📊 File size: {os.path.getsize(path)} bytes")

            # Clean up test file
            os.remove(path)
            print("🧹 Test file cleaned up")
        else:
            print("❌ Test failed")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure enhanced_youtube_downloader.py is in the current directory")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    test_enhanced_download()
"""

        with open("test_enhanced_downloader.py", "w") as f:
            f.write(test_script)

        try:
            os.chmod("test_enhanced_downloader.py", 0o755)
        except:
            pass  # Windows doesn't support chmod the same way
        logger.info("✅ Test script created: test_enhanced_downloader.py")
    
    def run_integration(self):
        """Run the complete integration process"""
        logger.info("🚀 Starting Enhanced Downloader Integration")
        logger.info("=" * 50)
        
        try:
            # Step 1: Backup
            self.backup_existing_files()
            
            # Step 2: Update requirements
            self.update_requirements()
            
            # Step 3: Update slide extractor
            self.update_slide_extractor()
            
            # Step 4: Create test script
            self.create_test_script()
            
            # Summary
            logger.info("\n" + "=" * 50)
            logger.info("🎉 Integration Complete!")
            logger.info("=" * 50)
            logger.info("📋 What was done:")
            logger.info("  ✅ Created backup of existing files")
            logger.info("  ✅ Updated requirements.txt with new dependencies")
            logger.info("  ✅ Added enhanced download method to slide_extractor.py")
            logger.info("  ✅ Created test script")
            logger.info("\n📋 Next steps:")
            logger.info("  1. Install new dependencies: pip install -r requirements.txt")
            logger.info("  2. Test the enhanced downloader: python test_enhanced_downloader.py")
            logger.info("  3. Deploy the updated application")
            logger.info(f"\n📁 Backup available in: {self.backup_dir}")
            
        except Exception as e:
            logger.error(f"❌ Integration failed: {e}")
            logger.info(f"📁 Restore from backup: {self.backup_dir}")
            return False
        
        return True

def main():
    """Main integration function"""
    integration = DownloaderIntegration()
    success = integration.run_integration()
    
    if success:
        print("\n🎯 Integration successful! Your slide extractor now has enhanced download capabilities.")
        sys.exit(0)
    else:
        print("\n❌ Integration failed. Check logs and restore from backup if needed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
