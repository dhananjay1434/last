#!/usr/bin/env python3
"""
Deploy YouTube 2025 Fix
Updates the application to handle YouTube's new PO Token restrictions
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Deploy YouTube 2025 compatibility fixes"""
    logger.info("🚀 Deploying YouTube 2025 compatibility fixes...")
    
    # Check if we're in the right directory
    if not os.path.exists("requirements.txt"):
        logger.error("❌ requirements.txt not found. Run this script from the project root.")
        return False
    
    logger.info("📋 YouTube 2025 Update Summary:")
    logger.info("   ✅ Updated yt-dlp to latest version (2024.12.13+)")
    logger.info("   ✅ Enhanced download strategies for PO Token restrictions")
    logger.info("   ✅ Added rate limiting (5-10 seconds between downloads)")
    logger.info("   ✅ Switched to mweb client for better compatibility")
    logger.info("   ✅ Improved error handling for rate limits")
    logger.info("   ✅ Created YouTube2025Downloader class")
    
    logger.info("\n🔧 Key Changes:")
    logger.info("   - Rate limiting to avoid YouTube restrictions")
    logger.info("   - Enhanced retry mechanisms")
    logger.info("   - Better error detection and handling")
    logger.info("   - Mobile-first download strategies")
    
    logger.info("\n⚠️ Expected Impact:")
    logger.info("   - Slower download speeds (due to rate limiting)")
    logger.info("   - Higher success rates for public videos")
    logger.info("   - Better handling of YouTube restrictions")
    logger.info("   - Improved user experience with retries")
    
    logger.info("\n🎯 Next Steps:")
    logger.info("   1. Commit and push these changes")
    logger.info("   2. Monitor deployment logs")
    logger.info("   3. Test with sample videos")
    logger.info("   4. Monitor success rates")
    
    return True

def commit_and_deploy():
    """Commit and deploy the changes"""
    logger.info("📦 Committing YouTube 2025 fixes...")
    
    try:
        # Add all changes
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit with descriptive message
        commit_message = "Update for YouTube 2025 PO Token restrictions - Add rate limiting and enhanced download strategies"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        logger.info("✅ Changes committed successfully")
        
        # Push to deploy
        logger.info("🚀 Pushing to deploy...")
        subprocess.run(["git", "push"], check=True)
        
        logger.info("✅ Deployment initiated successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git operation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        return False

if __name__ == "__main__":
    print("🎬 YouTube 2025 Compatibility Update")
    print("=" * 50)
    
    success = main()
    
    if success:
        print("\n🤔 Ready to deploy? (y/n): ", end="")
        response = input().lower().strip()
        
        if response in ['y', 'yes']:
            deploy_success = commit_and_deploy()
            if deploy_success:
                print("\n🎉 YouTube 2025 fixes deployed successfully!")
                print("📊 Monitor your application for:")
                print("   - Improved download success rates")
                print("   - Reduced rate limit errors")
                print("   - Better handling of YouTube restrictions")
            else:
                print("\n❌ Deployment failed - check error messages above")
        else:
            print("\n📋 Changes ready but not deployed")
            print("💡 Run 'git add . && git commit -m \"YouTube 2025 fixes\" && git push' when ready")
    else:
        print("\n❌ Setup failed - check error messages above")
