# Multi-stage Dockerfile for Slide Extractor with scalability support

# Base image with system dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    # FFmpeg for video processing
    ffmpeg \
    # Additional tools
    wget \
    curl \
    git \
    # Build tools (will be removed in production)
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
# Copy requirements (use requirements_production.txt for production)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

USER app

# Expose ports
EXPOSE 5000 5555

# Default command for development
CMD ["python", "app.py"]

# Production stage
FROM base as production

# Remove build dependencies to reduce image size
RUN apt-get update && apt-get remove -y \
    gcc \
    g++ \
    make \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/slides /app/logs /app/migrations && \
    chown -R app:app /app

USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Default command for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "app:app"]

# Worker stage for Celery workers
FROM production as worker

# Override default command for worker
CMD ["python", "celery_worker.py", "worker"]

# Beat stage for Celery beat scheduler
FROM production as beat

# Override default command for beat
CMD ["python", "celery_worker.py", "beat"]

# Flower stage for monitoring
FROM production as flower

# Install flower
RUN pip install --no-cache-dir flower

# Expose flower port
EXPOSE 5555

# Override default command for flower
CMD ["python", "celery_worker.py", "flower"]
