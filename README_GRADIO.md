# 🎬 Slide Extractor - Gradio Full Stack Application

A complete, self-contained slide extraction application built with Gradio. **No separate API required** - everything runs in one application!

## ✨ Features

### 🎯 Core Functionality
- **Video Processing**: Extract slides from YouTube videos
- **Smart Detection**: Adaptive sampling with scene detection
- **OCR Integration**: Text recognition from slides
- **PDF Generation**: Compile slides into downloadable PDFs
- **Study Guides**: AI-generated study materials

### 🤖 AI-Powered Features (Optional)
- **Audio Transcription**: Extract and transcribe video audio
- **Content Analysis**: Identify key concepts and topics
- **Slide Descriptions**: AI-generated descriptions for each slide
- **OCR Enhancement**: Improved text recognition accuracy

### 🌐 User Interface
- **Modern Web UI**: Clean, responsive Gradio interface
- **Real-time Progress**: Live status updates during processing
- **File Downloads**: Direct download of PDFs and study guides
- **Slide Gallery**: Visual preview of extracted slides
- **Job Management**: Track and monitor multiple extraction jobs

## 🚀 Quick Start

### Option 1: Simple Startup (Recommended)
```bash
# Run the startup script (handles dependency installation)
python start_gradio_app.py
```

### Option 2: Manual Setup
```bash
# Install basic dependencies
pip install gradio opencv-python numpy Pillow requests

# Run the application
python gradio_full_app.py
```

### Option 3: Full Installation
```bash
# Install all dependencies for full functionality
pip install -r requirements_gradio.txt

# Run the application
python gradio_full_app.py
```

## 📋 Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space for video processing
- **Internet**: Required for video downloads

### Dependencies
The application works with different levels of functionality:

#### 🟢 Basic Level (Core Features)
```bash
pip install gradio opencv-python numpy Pillow requests
```

#### 🟡 Enhanced Level (More Features)
```bash
pip install pytesseract nltk yt-dlp reportlab matplotlib
```

#### 🟠 Full Level (All Features)
```bash
pip install google-generativeai selenium pytube webdriver-manager
```

## 🎮 How to Use

### 1. Start the Application
```bash
python start_gradio_app.py
```

### 2. Access the Web Interface
- **Local**: http://localhost:7860
- **Public**: Gradio will generate a public URL (if enabled)

### 3. Extract Slides
1. **Enter Video URL**: Paste a YouTube video URL
2. **Configure Options**: Choose extraction settings
3. **Start Extraction**: Click "Start Extraction"
4. **Monitor Progress**: Watch real-time status updates
5. **Download Results**: Get PDFs and study guides

### 4. AI Features (Optional)
1. **Get Gemini API Key**: From Google AI Studio
2. **Enable AI Features**: Check desired options
3. **Enter API Key**: In the AI Features section
4. **Enhanced Processing**: Get transcriptions and descriptions

## 📁 Application Structure

```
gradio_full_app.py          # Main application file
start_gradio_app.py         # Simple startup script
requirements_gradio.txt     # Dependency list
README_GRADIO.md           # This file

# Generated during use:
slides/                    # Extracted slides storage
gradio_jobs.db            # Job tracking database
gradio_app.log            # Application logs
```

## 🔧 Configuration

### Environment Variables (Optional)
```bash
# Set custom port
export GRADIO_PORT=7860

# Set custom slides directory
export SLIDES_FOLDER=/path/to/slides

# Enable debug mode
export GRADIO_DEBUG=true
```

### API Keys
- **Gemini API Key**: Required for AI features
  - Get from: https://makersuite.google.com/app/apikey
  - Used for: Transcription, OCR enhancement, slide descriptions

## 📊 Demo Videos

The application includes several demo videos for testing:

1. **Khan Academy - Introduction to Algebra**
   - URL: https://www.youtube.com/watch?v=NybHckSEQBI
   - Good for: Basic slide extraction testing

2. **MIT OpenCourseWare - Physics Lecture**
   - URL: https://www.youtube.com/watch?v=ZM8ECpBuQYE
   - Good for: University-level content

3. **TED-Ed - Science Explanation**
   - URL: https://www.youtube.com/watch?v=yWO-cvGETRQ
   - Good for: Animated content testing

4. **Coursera - Machine Learning Basics**
   - URL: https://www.youtube.com/watch?v=ukzFI9rgwfU
   - Good for: Technical content

## 🛠️ Troubleshooting

### Common Issues

#### "No slide extractor available"
```bash
# Install core dependencies
pip install opencv-python numpy Pillow
```

#### "YouTube download failed"
```bash
# Update yt-dlp
pip install --upgrade yt-dlp

# Try different video or check URL
```

#### "OCR not working"
```bash
# Install Tesseract OCR
# Windows: Download from GitHub
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr

pip install pytesseract
```

#### "AI features not available"
```bash
# Install AI dependencies
pip install google-generativeai

# Get API key from Google AI Studio
```

### Performance Tips

1. **Use shorter videos** (under 10 minutes) for faster processing
2. **Close other applications** to free up RAM
3. **Use SSD storage** for better I/O performance
4. **Enable GPU acceleration** if available (OpenCV)

## 🔒 Privacy & Security

- **Local Processing**: All video processing happens locally
- **No Data Collection**: Application doesn't collect user data
- **API Keys**: Stored temporarily in memory only
- **File Storage**: All files saved locally in slides/ directory

## 🤝 Contributing

This is a self-contained application built from the original slide extractor project. 

### Development Setup
```bash
git clone <repository>
cd backend_deploy
python gradio_full_app.py
```

## 📄 License

Same license as the original slide extractor project.

## 🆘 Support

### Getting Help
1. **Check Logs**: Look at `gradio_app.log` for errors
2. **Verify Dependencies**: Run `start_gradio_app.py` for dependency check
3. **Try Demo Videos**: Use provided demo URLs for testing
4. **Check Internet**: Ensure stable connection for video downloads

### Known Limitations
- **YouTube Restrictions**: Some videos may be blocked
- **Processing Time**: Large videos take longer to process
- **Memory Usage**: High-resolution videos require more RAM
- **AI Features**: Require internet connection and API keys

---

## 🎉 Enjoy Your Slide Extraction!

This Gradio application provides a complete, user-friendly interface for extracting slides from educational videos. No technical setup required - just run and use!
