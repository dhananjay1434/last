# 📁 File Storage Guide - Where Your Downloads Are Stored

## 🗂️ **Storage Structure Overview**

Your Slide Extractor application stores all downloaded and processed files in a well-organized directory structure:

```
📁 Project Root
├── 📁 slides/                    # Main storage directory
│   ├── 📁 1/                     # Job ID folder (e.g., job 1)
│   │   ├── 🎥 temp_video.mp4     # Downloaded video file
│   │   ├── 🖼️ slide_001.png      # Extracted slide images
│   │   ├── 🖼️ slide_002.png
│   │   ├── 📄 slides.pdf         # Generated PDF (if enabled)
│   │   ├── 📝 study_guide.md     # Study guide (if enabled)
│   │   ├── 📄 slide_index.html   # Web viewer
│   │   ├── 📁 temp/              # Temporary processing files
│   │   ├── 📁 metadata/          # Slide metadata and analysis
│   │   └── 📁 organized/         # Organized slides by type
│   ├── 📁 2/                     # Job ID folder (e.g., job 2)
│   └── 📁 3/                     # Job ID folder (e.g., job 3)
└── 📄 app.py                     # Application files
```

## 📍 **Exact File Locations**

### **1. Main Storage Directory**
```python
# Defined in app.py line 115
SLIDES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slides")
```

**Absolute Path Examples:**
- **Windows:** `C:\Users\bit\Downloads\day1\backend_deploy\slides\`
- **Linux/Mac:** `/path/to/backend_deploy/slides/`
- **Render.com:** `/opt/render/project/src/slides/`

### **2. Job-Specific Directories**
Each job gets its own folder named by job ID:
```python
# Defined in app.py line 252
output_dir = os.path.join(SLIDES_FOLDER, job_id)
```

**Examples:**
- Job 1: `slides/1/`
- Job 2: `slides/2/`
- Job 123: `slides/123/`

### **3. Downloaded Video Files**
```python
# Defined in slide_extractor.py line 151
self.video_path = os.path.join(self.output_dir, "temp_video.mp4")
```

**Full Path:** `slides/{job_id}/temp_video.mp4`

## 📋 **File Types & Locations**

### **🎥 Video Files**
| File | Location | Description |
|------|----------|-------------|
| `temp_video.mp4` | `slides/{job_id}/temp_video.mp4` | Original downloaded video |

### **🖼️ Image Files**
| File | Location | Description |
|------|----------|-------------|
| `slide_001.png` | `slides/{job_id}/slide_001.png` | First extracted slide |
| `slide_002.png` | `slides/{job_id}/slide_002.png` | Second extracted slide |
| `slide_XXX.png` | `slides/{job_id}/slide_XXX.png` | Additional slides |

### **📄 Document Files**
| File | Location | Description |
|------|----------|-------------|
| `slides.pdf` | `slides/{job_id}/slides.pdf` | Combined PDF of all slides |
| `study_guide.md` | `slides/{job_id}/study_guide.md` | Generated study guide |
| `slide_index.html` | `slides/{job_id}/slide_index.html` | Web viewer for slides |

### **📁 Subdirectories**
| Directory | Location | Purpose |
|-----------|----------|---------|
| `temp/` | `slides/{job_id}/temp/` | Temporary processing files |
| `metadata/` | `slides/{job_id}/metadata/` | Slide analysis and OCR data |
| `organized/` | `slides/{job_id}/organized/` | Slides organized by type |

## 🔍 **How to Find Your Files**

### **Method 1: Direct File System Access**

1. **Navigate to project directory:**
   ```bash
   cd /path/to/backend_deploy
   ```

2. **List all jobs:**
   ```bash
   ls -la slides/
   ```

3. **View specific job files:**
   ```bash
   ls -la slides/1/
   ```

### **Method 2: API Endpoints**

1. **Get job status (includes file info):**
   ```bash
   curl https://last-api-4ybg.onrender.com/api/jobs/1
   ```

2. **Download PDF directly:**
   ```bash
   curl https://last-api-4ybg.onrender.com/api/jobs/1/pdf -o slides.pdf
   ```

3. **Get study guide:**
   ```bash
   curl https://last-api-4ybg.onrender.com/api/jobs/1/study-guide
   ```

### **Method 3: Web Interface**

1. **View slides in browser:**
   ```
   https://last-api-4ybg.onrender.com/slides/1/slide_index.html
   ```

2. **Direct image access:**
   ```
   https://last-api-4ybg.onrender.com/slides/1/slide_001.png
   ```

## 💾 **Storage Configuration**

### **Environment Variables**
```bash
# Custom storage location (optional)
SLIDES_FOLDER=/custom/path/to/slides

# Maximum file size (100MB default)
MAX_CONTENT_LENGTH=104857600

# Upload timeout (10 minutes default)
UPLOAD_TIMEOUT=600
```

### **Docker Volume Mapping**
```yaml
# docker-compose.yml
volumes:
  - slides_data:/app/slides  # Persistent storage
  - ./local_slides:/app/slides  # Local mapping
```

### **Render.com Storage**
- **Ephemeral Storage:** Files stored in `/opt/render/project/src/slides/`
- **Persistent Storage:** Use external storage services for long-term retention
- **Download Limit:** Files available during deployment lifecycle

## 📊 **Storage Management**

### **File Sizes**
| File Type | Typical Size | Notes |
|-----------|--------------|-------|
| Video (MP4) | 10-100MB | Depends on video length/quality |
| Slide (PNG) | 100KB-2MB | High-quality screenshots |
| PDF | 1-20MB | Combined slides document |
| Study Guide | 1-50KB | Text-based markdown |

### **Cleanup & Maintenance**
```python
# Automatic cleanup (implemented in tasks.py)
@celery.task
def cleanup_old_jobs_task():
    # Removes files older than 24 hours
    job_storage.cleanup_completed_jobs(max_age_hours=24)
```

### **Manual Cleanup**
```bash
# Remove old job files
rm -rf slides/old_job_id/

# Clean up temporary files
find slides/ -name "temp_*" -delete

# Remove files older than 7 days
find slides/ -type f -mtime +7 -delete
```

## 🔒 **Security & Access**

### **File Permissions**
```bash
# Recommended permissions
chmod 755 slides/           # Directory: read/execute for all
chmod 644 slides/*/.*       # Files: read for all, write for owner
```

### **Access Control**
- **Public Access:** Static files served via `/slides/<path>` route
- **API Access:** Authenticated access via `/api/jobs/<id>/pdf` endpoints
- **Direct Access:** File system access for server administrators

### **Privacy Considerations**
- **Temporary Storage:** Files are temporary and cleaned up automatically
- **No Personal Data:** Only video content and extracted slides stored
- **Secure Deletion:** Files removed completely during cleanup

## 🚀 **Production Deployment**

### **Render.com Specifics**
```yaml
# render.yaml - persistent storage
services:
  - type: web
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: SLIDES_FOLDER
        value: /opt/render/project/src/slides
```

### **External Storage Integration**
```python
# For production, consider cloud storage
import boto3  # AWS S3
import azure.storage.blob  # Azure Blob
from google.cloud import storage  # Google Cloud Storage

# Example S3 integration
def upload_to_s3(file_path, bucket, key):
    s3 = boto3.client('s3')
    s3.upload_file(file_path, bucket, key)
```

## 📱 **Access from Frontend**

### **Download Links**
```javascript
// Frontend code to download files
const downloadPDF = async (jobId) => {
  const response = await fetch(`/api/jobs/${jobId}/pdf`);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `slides_${jobId}.pdf`;
  a.click();
};
```

### **File Previews**
```javascript
// Display slide images
const showSlides = async (jobId) => {
  const response = await fetch(`/api/jobs/${jobId}/slides`);
  const data = await response.json();
  
  data.slides.forEach(slide => {
    const img = document.createElement('img');
    img.src = `/slides/${jobId}/${slide.filename}`;
    document.body.appendChild(img);
  });
};
```

## 🎯 **Quick Reference**

### **Common File Paths**
```bash
# Video file
slides/{job_id}/temp_video.mp4

# First slide
slides/{job_id}/slide_001.png

# PDF output
slides/{job_id}/slides.pdf

# Study guide
slides/{job_id}/study_guide.md

# Web viewer
slides/{job_id}/slide_index.html
```

### **API Endpoints**
```bash
# Get job files info
GET /api/jobs/{job_id}

# Download PDF
GET /api/jobs/{job_id}/pdf

# Get study guide
GET /api/jobs/{job_id}/study-guide

# Get slides list
GET /api/jobs/{job_id}/slides

# Direct file access
GET /slides/{job_id}/{filename}
```

---

**📍 Summary:** All your downloaded videos, extracted slides, PDFs, and study guides are stored in the `slides/` directory, organized by job ID. Each job gets its own folder with all related files neatly organized and easily accessible via both file system and API endpoints.
