#!/usr/bin/env python3
"""
Simple startup script for the Gradio Slide Extractor Application
"""

import os
import sys
import subprocess
import importlib.util

def check_dependency(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name
    
    spec = importlib.util.find_spec(import_name)
    return spec is not None

def install_basic_dependencies():
    """Install basic dependencies required for the application."""
    basic_deps = [
        "gradio>=4.0.0",
        "opencv-python>=4.5.0",
        "numpy>=1.19.0",
        "Pillow>=8.0.0",
        "requests>=2.31.0"
    ]
    
    print("📦 Installing basic dependencies...")
    for dep in basic_deps:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {dep}")

def check_and_install_dependencies():
    """Check for required dependencies and offer to install them."""
    required_deps = {
        "gradio": "gradio",
        "cv2": "opencv-python",
        "numpy": "numpy", 
        "PIL": "Pillow",
        "requests": "requests"
    }
    
    missing_deps = []
    for import_name, package_name in required_deps.items():
        if not check_dependency(package_name, import_name):
            missing_deps.append(package_name)
    
    if missing_deps:
        print("❌ Missing required dependencies:")
        for dep in missing_deps:
            print(f"  • {dep}")
        
        response = input("\n📦 Would you like to install missing dependencies? (y/n): ")
        if response.lower() in ['y', 'yes']:
            install_basic_dependencies()
        else:
            print("⚠️ Application may not work without required dependencies.")
            return False
    
    return True

def main():
    """Main startup function."""
    print("🎬 Slide Extractor - Gradio Full Stack Application")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check dependencies
    if not check_and_install_dependencies():
        print("❌ Dependency check failed")
        sys.exit(1)
    
    # Check if main application file exists
    app_file = "gradio_full_app.py"
    if not os.path.exists(app_file):
        print(f"❌ Application file '{app_file}' not found")
        print("Make sure you're running this script from the correct directory")
        sys.exit(1)
    
    print(f"✅ Found application file: {app_file}")
    
    # Optional dependencies check
    optional_deps = {
        "pytesseract": "OCR functionality",
        "nltk": "Natural Language Processing",
        "yt_dlp": "YouTube video downloading",
        "reportlab": "PDF generation",
        "matplotlib": "Plotting and visualization"
    }
    
    print("\n🔍 Checking optional dependencies:")
    for dep, description in optional_deps.items():
        if check_dependency(dep):
            print(f"✅ {dep} - {description}")
        else:
            print(f"⚠️ {dep} - {description} (not available)")
    
    print("\n🚀 Starting application...")
    print("=" * 50)
    
    # Run the main application
    try:
        import gradio_full_app
    except ImportError as e:
        print(f"❌ Failed to import application: {e}")
        print("Make sure all dependencies are installed")
        sys.exit(1)

if __name__ == "__main__":
    main()
