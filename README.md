# 🎬 Slide Extractor - AI-Powered Video Analysis

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/dhananjay1434/last)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/dhananjay1434/last)

## 🌐 Live Demo
- **Frontend**: [https://latenighter.netlify.app/](https://latenighter.netlify.app/)
- **Backend**: Deploy using the Render button above

> Extract slides from educational videos with AI-powered content analysis, transcription, and study guide generation.

## ✨ Features

- 🎥 **YouTube Video Processing** - Download and analyze educational videos
- 🖼️ **Smart Slide Extraction** - AI-powered scene detection and duplicate removal
- 🤖 **AI Content Analysis** - Concept extraction and content categorization
- 📝 **Auto Transcription** - Google Gemini API integration for audio transcription
- 👁️ **Enhanced OCR** - Multiple preprocessing techniques for better text extraction
- 📚 **Study Guide Generation** - Automatic creation of comprehensive study materials
- 📄 **PDF Export** - Professional slide compilation with metadata
- 🌐 **Modern Web Interface** - React frontend with real-time progress tracking
- 🔄 **Real-time Updates** - Live progress monitoring and status updates

## 🚀 Quick Start

### Option 1: Use Public Interface (Gradio)
Access the live demo: [Gradio Interface](https://f89c0e0489db068366.gradio.live) *(72-hour link)*

### Option 2: Deploy Your Own

#### Backend (Render.com)
1. Fork this repository
2. Connect to [Render.com](https://render.com)
3. Deploy as Web Service using `render.yaml`
4. Set environment variables (see below)

#### Frontend (Netlify)
1. Deploy `frontend/` folder to [Netlify](https://netlify.com)
2. Set build directory: `frontend/build`
3. Set API URL environment variable

## 🛠️ Local Development

### Prerequisites
- Python 3.9+
- Node.js 16+
- Tesseract OCR
- FFmpeg

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python app.py
```

### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Gradio Interface
```bash
# Run Gradio interface
python gradio_interface.py
```

## 🔧 Environment Variables

### Backend (.env)
```env
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://your-frontend-url.netlify.app
```

### Frontend (.env)
```env
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/status` | GET | Server status and features |
| `/api/extract` | POST | Start slide extraction |
| `/api/jobs/{id}` | GET | Job status |
| `/api/jobs/{id}/slides` | GET | Get extracted slides |
| `/api/jobs/{id}/pdf` | GET | Download PDF |
| `/api/jobs/{id}/study-guide` | GET | Get study guide |

## 🎯 Usage Example

```javascript
// Start extraction
const response = await fetch('/api/extract', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_url: 'https://www.youtube.com/watch?v=VIDEO_ID',
    adaptive_sampling: true,
    extract_content: true,
    generate_pdf: true,
    enable_transcription: true,
    gemini_api_key: 'your_api_key'
  })
});

const { job_id } = await response.json();

// Monitor progress
const status = await fetch(`/api/jobs/${job_id}`);
const jobData = await status.json();
```

## 🏗️ Architecture

```
Frontend (React)          Backend API (Flask)
     ↓                          ↓
Netlify/Render    ←→    Render.com
     ↓                          ↓
Static Files              Python + AI Services
                               ↓
                         YouTube + Gemini API
```

## 🧠 AI Features

- **Content Analysis**: NLP-based concept extraction
- **Transcription**: Google Gemini API for audio-to-text
- **OCR Enhancement**: Multiple preprocessing techniques
- **Study Guides**: Automatic generation of learning materials
- **Slide Descriptions**: AI-powered slide summaries

## 📊 Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Video Processing**: OpenCV, yt-dlp, MoviePy
- **AI/ML**: Google Gemini API, NLTK, scikit-image
- **OCR**: Tesseract
- **PDF Generation**: ReportLab

### Frontend
- **Framework**: React 18
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Icons**: Lucide React

## 🚀 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy to Render
1. Fork this repository
2. Connect to Render.com
3. Deploy using the included `render.yaml`
4. Set your `GEMINI_API_KEY` environment variable

## 📁 Project Structure

```
slide-extractor/
├── 🔧 Backend (Python/Flask)
├── 🎨 Frontend (React)
├── 📚 Documentation
└── 🚀 Deployment configs
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed structure.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Google Gemini API for AI capabilities
- OpenCV for computer vision
- Tesseract for OCR
- yt-dlp for video downloading
- React and Tailwind CSS for the frontend

## 📞 Support

- 📧 Email: [your-email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/dhananjay1434/last/issues)
- 📖 Documentation: [Deployment Guide](DEPLOYMENT.md)

---

**Made with ❤️ for education and learning**
