#!/bin/bash

# Scalable Slide Extractor Deployment Script
# Supports multiple deployment scenarios: local, docker, render

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_deps=()
    
    if ! command_exists python3; then
        missing_deps+=("python3")
    fi
    
    if ! command_exists pip; then
        missing_deps+=("pip")
    fi
    
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        if ! command_exists docker; then
            missing_deps+=("docker")
        fi
        if ! command_exists docker-compose; then
            missing_deps+=("docker-compose")
        fi
    fi
    
    if [[ "$DEPLOYMENT_TYPE" == "local" ]]; then
        if ! command_exists redis-server; then
            log_warning "Redis not found. Install Redis or use Docker deployment."
        fi
        if ! command_exists psql; then
            log_warning "PostgreSQL not found. Will use SQLite as fallback."
        fi
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_error "Please install the missing dependencies and try again."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup environment variables
setup_environment() {
    log_info "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_info "Creating .env file..."
        cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=sqlite:///slide_extractor.db
# For PostgreSQL: DATABASE_URL=postgresql://user:password@localhost:5432/slide_extractor

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
USE_CELERY=true

# API Keys (set these manually)
GEMINI_API_KEY=your_gemini_api_key_here

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# File Upload Configuration
MAX_CONTENT_LENGTH=104857600
UPLOAD_TIMEOUT=600

# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
EOF
        log_success "Created .env file. Please update with your actual values."
    else
        log_info ".env file already exists"
    fi
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    log_success "Dependencies installed successfully"
}

# Setup database
setup_database() {
    log_info "Setting up database..."
    
    # Initialize Flask-Migrate if not already done
    if [ ! -d "migrations" ]; then
        log_info "Initializing database migrations..."
        flask db init
    fi
    
    # Create migration
    log_info "Creating database migration..."
    flask db migrate -m "Initial migration with scalability features"
    
    # Apply migration
    log_info "Applying database migration..."
    flask db upgrade
    
    log_success "Database setup completed"
}

# Start local development
start_local() {
    log_info "Starting local development environment..."
    
    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        log_info "Starting Redis server..."
        redis-server --daemonize yes
    fi
    
    # Start Celery worker in background
    log_info "Starting Celery worker..."
    python celery_worker.py worker --worker-type general --concurrency 2 &
    CELERY_WORKER_PID=$!
    
    # Start Celery beat in background
    log_info "Starting Celery beat..."
    python celery_worker.py beat &
    CELERY_BEAT_PID=$!
    
    # Start Flask app
    log_info "Starting Flask application..."
    python app.py &
    FLASK_PID=$!
    
    # Save PIDs for cleanup
    echo $CELERY_WORKER_PID > .celery_worker.pid
    echo $CELERY_BEAT_PID > .celery_beat.pid
    echo $FLASK_PID > .flask.pid
    
    log_success "Local development environment started!"
    log_info "API: http://localhost:5000"
    log_info "Health check: http://localhost:5000/api/health"
    log_info "Stats: http://localhost:5000/api/stats"
    
    # Wait for user interrupt
    trap cleanup_local INT
    wait
}

# Cleanup local processes
cleanup_local() {
    log_info "Cleaning up local processes..."
    
    if [ -f .celery_worker.pid ]; then
        kill $(cat .celery_worker.pid) 2>/dev/null || true
        rm .celery_worker.pid
    fi
    
    if [ -f .celery_beat.pid ]; then
        kill $(cat .celery_beat.pid) 2>/dev/null || true
        rm .celery_beat.pid
    fi
    
    if [ -f .flask.pid ]; then
        kill $(cat .flask.pid) 2>/dev/null || true
        rm .flask.pid
    fi
    
    log_success "Cleanup completed"
    exit 0
}

# Start Docker deployment
start_docker() {
    log_info "Starting Docker deployment..."
    
    # Build and start services
    docker-compose up --build -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose exec api flask db upgrade
    
    log_success "Docker deployment started!"
    log_info "API: http://localhost:5000"
    log_info "Flower (monitoring): http://localhost:5555"
    log_info "View logs: docker-compose logs -f"
    log_info "Stop services: docker-compose down"
}

# Deploy to Render
deploy_render() {
    log_info "Preparing Render deployment..."
    
    # Check if render.yaml exists
    if [ ! -f render.yaml ]; then
        log_error "render.yaml not found. Cannot deploy to Render."
        exit 1
    fi
    
    log_info "Render deployment configuration found."
    log_info "Please follow these steps:"
    echo
    echo "1. Push your code to GitHub"
    echo "2. Connect your GitHub repository to Render"
    echo "3. Render will automatically deploy using render.yaml"
    echo "4. Set the following environment variables in Render dashboard:"
    echo "   - GEMINI_API_KEY"
    echo "   - CORS_ALLOWED_ORIGINS"
    echo
    log_info "For detailed instructions, see DEPLOYMENT.md"
}

# Show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  local     Start local development environment"
    echo "  docker    Start Docker deployment"
    echo "  render    Prepare for Render deployment"
    echo "  setup     Setup environment and dependencies"
    echo "  clean     Clean up local processes and files"
    echo
    echo "Options:"
    echo "  --help    Show this help message"
    echo
    echo "Examples:"
    echo "  $0 setup          # Setup environment and install dependencies"
    echo "  $0 local          # Start local development"
    echo "  $0 docker         # Start with Docker"
    echo "  $0 render         # Prepare for Render deployment"
}

# Clean up function
clean_up() {
    log_info "Cleaning up..."
    
    # Stop local processes
    cleanup_local
    
    # Clean Docker
    if command_exists docker-compose; then
        docker-compose down -v
    fi
    
    # Remove temporary files
    rm -f .celery_worker.pid .celery_beat.pid .flask.pid
    
    log_success "Cleanup completed"
}

# Main function
main() {
    local command="${1:-help}"
    
    case $command in
        setup)
            check_prerequisites
            setup_environment
            install_dependencies
            setup_database
            log_success "Setup completed! You can now run: $0 local"
            ;;
        local)
            DEPLOYMENT_TYPE="local"
            check_prerequisites
            start_local
            ;;
        docker)
            DEPLOYMENT_TYPE="docker"
            check_prerequisites
            start_docker
            ;;
        render)
            deploy_render
            ;;
        clean)
            clean_up
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
