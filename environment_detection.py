
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
