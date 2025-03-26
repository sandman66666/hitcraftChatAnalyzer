"""
Configuration settings for HitCraft Chat Analyzer
"""
import os

# Application configuration
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'temp_chunks'
RESULTS_FOLDER = 'analysis_results'
THREADS_FOLDER = 'organized_threads'
DATA_FOLDER = 'data'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
ALLOWED_EXTENSIONS = {'txt', 'rtf', 'json'}
MAX_CHUNKS = int(os.environ.get('MAX_CHUNKS', 1))
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# CORS configuration
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8095"]
CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_HEADERS = ["Content-Type", "Authorization", "X-Requested-With"]

# Server configuration
HOST = '0.0.0.0'
PORT = 8096  # Updated to match the actual running port
DEBUG = True

# Create necessary directories
def create_app_directories():
    """Create necessary directories for the application"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    os.makedirs(THREADS_FOLDER, exist_ok=True)
    os.makedirs(DATA_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if a file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
