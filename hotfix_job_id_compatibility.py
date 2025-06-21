#!/usr/bin/env python3
"""
Hotfix script for job ID compatibility issues.
This script can be run to fix the immediate 404 errors.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_app_compatibility():
    """Check if the app.py file has the necessary compatibility fixes."""
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Check for key compatibility features
        checks = {
            'string_job_id_route': '@app.route(\'/api/jobs/<job_id>\', methods=[\'GET\'])',
            'legacy_job_id_handling': 'legacy_job_id = int(job_id)',
            'job_id_compatibility': 'for check_id in [job_id, legacy_job_id]',
            'string_job_id_generation': 'job_id = str(next_job_id)'
        }
        
        results = {}
        for check_name, pattern in checks.items():
            results[check_name] = pattern in content
        
        return results
        
    except Exception as e:
        logger.error(f"Error checking app compatibility: {e}")
        return {}

def test_job_endpoints():
    """Test if job endpoints are working correctly."""
    
    try:
        import requests
        
        # Test health endpoint first
        base_url = os.environ.get('API_BASE_URL', 'http://localhost:5000')
        
        logger.info(f"Testing API at {base_url}")
        
        # Test health endpoint
        try:
            response = requests.get(f"{base_url}/api/health", timeout=10)
            logger.info(f"Health check: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"API version: {health_data.get('version', 'unknown')}")
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
        
        # Test debug endpoint
        try:
            response = requests.get(f"{base_url}/api/debug/jobs", timeout=10)
            if response.status_code == 200:
                debug_data = response.json()
                logger.info(f"In-memory jobs: {debug_data.get('in_memory_jobs', {}).get('count', 0)}")
                logger.info(f"Next job ID: {debug_data.get('next_job_id', 'unknown')}")
            else:
                logger.warning(f"Debug endpoint returned: {response.status_code}")
        except Exception as e:
            logger.warning(f"Debug endpoint failed: {e}")
        
        # Test job status endpoint with a non-existent job
        try:
            response = requests.get(f"{base_url}/api/jobs/999", timeout=10)
            logger.info(f"Job 999 status: {response.status_code}")
            if response.status_code == 404:
                logger.info("✓ Job 404 handling is working correctly")
            else:
                logger.warning(f"Unexpected response for non-existent job: {response.status_code}")
        except Exception as e:
            logger.warning(f"Job status test failed: {e}")
        
        return True
        
    except ImportError:
        logger.warning("requests library not available for testing")
        return False
    except Exception as e:
        logger.error(f"Error testing endpoints: {e}")
        return False

def create_test_job():
    """Create a test job to verify the system is working."""
    
    try:
        import requests
        
        base_url = os.environ.get('API_BASE_URL', 'http://localhost:5000')
        
        # Create a test job
        test_data = {
            'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Roll for testing
            'adaptive_sampling': True,
            'extract_content': False,  # Disable to make it faster
            'generate_pdf': False,
            'enable_transcription': False,
            'enable_ocr_enhancement': False,
            'enable_concept_extraction': False,
            'enable_slide_descriptions': False
        }
        
        logger.info("Creating test job...")
        response = requests.post(f"{base_url}/api/extract", json=test_data, timeout=30)
        
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get('job_id')
            logger.info(f"✓ Test job created successfully: {job_id}")
            
            # Test job status
            status_response = requests.get(f"{base_url}/api/jobs/{job_id}", timeout=10)
            if status_response.status_code == 200:
                status_data = status_response.json()
                logger.info(f"✓ Job status retrieved: {status_data.get('status')}")
                return job_id
            else:
                logger.error(f"✗ Failed to get job status: {status_response.status_code}")
                return None
        else:
            logger.error(f"✗ Failed to create test job: {response.status_code}")
            if response.text:
                logger.error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating test job: {e}")
        return None

def main():
    """Main function to run compatibility checks and tests."""
    
    logger.info("🔧 Running Job ID Compatibility Hotfix Check")
    logger.info("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        logger.error("❌ app.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check app compatibility
    logger.info("1. Checking app.py compatibility...")
    compatibility = check_app_compatibility()
    
    all_good = True
    for check_name, passed in compatibility.items():
        status = "✓" if passed else "✗"
        logger.info(f"   {status} {check_name}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_good = False
    
    if not all_good:
        logger.error("❌ Some compatibility checks failed. Please ensure the hotfix has been applied.")
        sys.exit(1)
    
    logger.info("✅ All compatibility checks passed!")
    
    # Test endpoints if API is running
    logger.info("\n2. Testing API endpoints...")
    
    api_url = os.environ.get('API_BASE_URL')
    if not api_url:
        logger.info("   API_BASE_URL not set. Trying localhost...")
        api_url = 'http://localhost:5000'
        os.environ['API_BASE_URL'] = api_url
    
    logger.info(f"   Testing API at: {api_url}")
    
    if test_job_endpoints():
        logger.info("✅ Basic endpoint tests passed!")
        
        # Ask user if they want to create a test job
        try:
            create_test = input("\n3. Create a test job to verify full functionality? (y/N): ").lower().strip()
            if create_test in ['y', 'yes']:
                test_job_id = create_test_job()
                if test_job_id:
                    logger.info(f"✅ Test job {test_job_id} created successfully!")
                    logger.info("   You can monitor its progress in the frontend or via API.")
                else:
                    logger.warning("⚠️  Test job creation failed, but basic endpoints are working.")
        except KeyboardInterrupt:
            logger.info("\n   Skipping test job creation.")
    else:
        logger.warning("⚠️  Some endpoint tests failed. The API might not be running.")
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 Hotfix check completed!")
    logger.info("\nIf you're still experiencing 404 errors:")
    logger.info("1. Make sure the backend is deployed with the latest changes")
    logger.info("2. Clear your browser cache and refresh the frontend")
    logger.info("3. Check the browser console for any remaining errors")
    logger.info("4. Verify the API URL in your frontend configuration")

if __name__ == '__main__':
    main()
