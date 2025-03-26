"""
HitCraft Chat Analyzer - Main Application

This is the entry point for the HitCraft Chat Analyzer application.
The application uses a modular structure with components organized in separate files.
"""
import logging
from flask import Flask
from flask_cors import CORS

# Import configuration
from config import SECRET_KEY, UPLOAD_FOLDER, TEMP_FOLDER, RESULTS_FOLDER, MAX_CONTENT_LENGTH
from config import CORS_ORIGINS, CORS_METHODS, CORS_HEADERS, create_app_directories
from config import HOST, PORT, DEBUG

# Import routes
from routes import index_bp, upload_bp, analysis_bp, api_bp

# Initialize logging
from logging_manager import logger, add_log

# Create Flask application
app = Flask(__name__)

# Configure application
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Configure CORS
CORS(app, 
     resources={r"/*": {"origins": CORS_ORIGINS, 
                        "supports_credentials": True,
                        "allow_headers": CORS_HEADERS,
                        "methods": CORS_METHODS}})

# Register blueprints
app.register_blueprint(index_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(api_bp)

# Create necessary directories
create_app_directories()

# Main entry point
if __name__ == '__main__':
    logging.info("Starting HitCraft Chat Analyzer server")
    add_log("Server starting...")
    app.run(host=HOST, port=PORT, debug=DEBUG)
