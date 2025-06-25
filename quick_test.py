import logging
import sys
import os # Added for os.path and os.remove

# Ensure the main logger for the downloader is set up for testing
# This is similar to the __main__ block in unified_youtube_downloader.py
# to ensure its internal logger is active and properly configured.
logger_unified = logging.getLogger("UnifiedYouTubeDownloader")
if not logger_unified.handlers: # Avoid adding handlers multiple times if script is re-run in same session
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger_unified.addHandler(console_handler)
    logger_unified.setLevel(logging.DEBUG) # Set to DEBUG for detailed test output
    logger_unified.propagate = False

# Also configure the root logger to see messages from other libraries if needed,
# but less verbose than our specific downloader.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Configured root logger can conflict if not managed carefully with specific loggers.
# For this test, focusing on the UnifiedYouTubeDownloader's logger is primary.
if not logging.getLogger().handlers: # Basic config for root if no handlers exist
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


from unified_youtube_downloader import test_downloader, UnifiedYouTubeDownloader

if __name__ == "__main__":
    print("--- Running UnifiedYouTubeDownloader Test Suite ---")
    try:
        test_downloader()
        print("--- UnifiedYouTubeDownloader Test Suite Finished ---")
    except Exception as e:
        print(f"--- UnifiedYouTubeDownloader Test Suite FAILED: {e} ---")
        logger_unified.exception("Exception during test_downloader:")

    # Example of a single direct download test (optional, as test_downloader covers it)
    print("\n--- Single Direct Download Test (Example) ---")
    single_test_url = "https://www.youtube.com/watch?v=NybHckSEQBI" # Khan Academy
    
    # Create a specific output directory for this single test if needed, or let downloader use default temp
    # For this example, let UnifiedYouTubeDownloader create its own temp dir which it will manage.
    downloader_instance = UnifiedYouTubeDownloader()
    try:
        result = downloader_instance.download_video(single_test_url, max_total_retries=1)
        if result.success:
            print(f"Direct Download SUCCEEDED for {single_test_url}: {result.video_path} using {result.strategy_used}")
            # No need to manually remove result.video_path if it's inside downloader_instance.output_dir
            # as downloader_instance.cleanup() will handle it.
        else:
            print(f"Direct Download FAILED for {single_test_url}: {result.error}")
            if result.rate_limited:
                print("   (Rate limited during single test)")

        # The cleanup is crucial here as a new instance was created
        downloader_instance.cleanup()
        print(f"   Cleaned up temp directory: {downloader_instance.output_dir}")

    except Exception as e:
        print(f"Direct Download FAILED for {single_test_url} with exception: {e}")
        logger_unified.exception("Exception during single direct download test:")
        # Ensure cleanup even if an unexpected error occurs mid-process
        downloader_instance.cleanup()
        print(f"   Cleaned up temp directory due to exception: {downloader_instance.output_dir}")
    print("--- Single Direct Download Test (Example) Finished ---")

    # Note: Testing the full app.py run_extraction would require more setup (Flask app context, etc.)
    # and is closer to an integration test. This script focuses on the downloader module.
    print("\nTo test the integration with app.py, run the Flask application and use the API.")
