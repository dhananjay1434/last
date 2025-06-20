# 📁 Slide Extractor Project Structure

## 🏗️ Complete Architecture

```
slide-extractor/
├── 🔧 Backend (Python/Flask)
│   ├── app.py                          # Main Flask application
│   ├── slide_extractor.py              # Core slide extraction logic
│   ├── enhanced_slide_extractor.py     # Enhanced features wrapper
│   ├── content_analyzer.py             # AI content analysis
│   ├── gemini_transcription.py         # Gemini API integration
│   ├── ocr_context_enhancer.py         # OCR enhancement
│   ├── slide_description_generator.py  # AI slide descriptions
│   ├── syllabus_manager.py             # Syllabus management
│   ├── cors_config.py                  # CORS configuration
│   ├── requirements.txt                # Python dependencies
│   ├── render.yaml                     # Render deployment config
│   ├── Procfile                        # Process configuration
│   ├── runtime.txt                     # Python version
│   └── gradio_interface.py             # Gradio web interface
│
├── 🎨 Frontend (React)
│   ├── public/
│   │   └── index.html                  # HTML template
│   ├── src/
│   │   ├── App.js                      # Main React component
│   │   ├── index.js                    # React entry point
│   │   └── index.css                   # Tailwind CSS styles
│   ├── package.json                    # Node.js dependencies
│   ├── tailwind.config.js              # Tailwind configuration
│   ├── postcss.config.js               # PostCSS configuration
│   ├── netlify.toml                    # Netlify deployment config
│   └── render.yaml                     # Render static site config
│
├── 📚 Documentation
│   ├── README.md                       # Project overview
│   ├── DEPLOYMENT.md                   # Deployment guide
│   └── PROJECT_STRUCTURE.md            # This file
│
└── 🚀 Deployment
    ├── deploy.sh                       # Deployment helper script
    ├── .env.example                    # Backend environment variables
    └── frontend/.env.example           # Frontend environment variables
```

## 🔧 Backend Components

### Core Files
- **`app.py`**: Main Flask application with REST API endpoints
- **`slide_extractor.py`**: Core video processing and slide extraction
- **`enhanced_slide_extractor.py`**: Wrapper with advanced AI features

### AI & Analysis
- **`content_analyzer.py`**: NLP-based content analysis and concept extraction
- **`gemini_transcription.py`**: Google Gemini API for audio transcription
- **`ocr_context_enhancer.py`**: Enhanced OCR with multiple preprocessing techniques
- **`slide_description_generator.py`**: AI-powered slide description generation

### Configuration
- **`cors_config.py`**: Cross-origin resource sharing configuration
- **`requirements.txt`**: Python package dependencies
- **`render.yaml`**: Production deployment configuration for Render.com

## 🎨 Frontend Components

### React Application
- **`App.js`**: Main React component with full UI
- **`index.js`**: Application entry point
- **`index.css`**: Tailwind CSS styling

### Features
- Real-time API status monitoring
- Video URL input and validation
- Extraction progress tracking
- Results download (PDF, study guides)
- AI features configuration

## 🚀 Deployment Architecture

### Backend Deployment (Render.com)
```
GitHub Repository
       ↓
   Render.com
       ↓
Python Flask API
       ↓
- Video processing
- AI analysis
- File generation
```

### Frontend Deployment (Netlify/Render)
```
GitHub Repository
       ↓
  Netlify/Render
       ↓
React Static Site
       ↓
- User interface
- API communication
- File downloads
```

## 🔗 Integration Flow

1. **User Input**: Video URL entered in React frontend
2. **API Call**: Frontend sends extraction request to Flask backend
3. **Processing**: Backend downloads video, extracts slides, runs AI analysis
4. **Progress Updates**: Real-time status updates via polling
5. **Results**: Generated files available for download

## 📊 Data Flow

```
YouTube Video URL
       ↓
Video Download (yt-dlp)
       ↓
Frame Extraction (OpenCV)
       ↓
Slide Detection (Computer Vision)
       ↓
Content Analysis (OCR + NLP)
       ↓
AI Enhancement (Gemini API)
       ↓
Output Generation (PDF, Study Guide)
       ↓
Frontend Display & Download
```

## 🛠 Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Video Processing**: OpenCV, yt-dlp, MoviePy
- **AI/ML**: Google Gemini API, NLTK, scikit-image
- **OCR**: Tesseract
- **PDF Generation**: ReportLab
- **Server**: Gunicorn

### Frontend
- **Framework**: React 18
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **Build Tool**: Create React App

### Deployment
- **Backend Hosting**: Render.com
- **Frontend Hosting**: Netlify/Render
- **Version Control**: Git/GitHub
- **CI/CD**: Automatic deployment on push

## 🔧 Environment Variables

### Backend (.env)
```
GEMINI_API_KEY=your_gemini_api_key
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://your-frontend-url.netlify.app
```

### Frontend (.env)
```
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## 📈 Scalability Considerations

### Current Architecture
- Single-server deployment
- In-memory job storage
- Synchronous processing

### Future Enhancements
- **Database**: PostgreSQL for persistent storage
- **Queue System**: Redis/Celery for background jobs
- **Microservices**: Split into smaller services
- **CDN**: CloudFront for file delivery
- **Load Balancing**: Multiple server instances

## 🔒 Security Features

- CORS configuration for cross-origin requests
- Environment variable management
- Input validation and sanitization
- HTTPS enforcement in production
- API rate limiting (future enhancement)

## 📊 Monitoring & Logging

- Comprehensive logging throughout the application
- Error tracking and reporting
- Performance monitoring
- API health checks
- User analytics (frontend)

This architecture provides a robust, scalable foundation for the Slide Extractor application with clear separation between frontend and backend concerns.
