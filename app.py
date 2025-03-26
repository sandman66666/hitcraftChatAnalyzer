"""
HitCraft Chat Analyzer - Modular Flask Application

This application analyzes Slack conversation threads to extract insights
using Claude-3 AI. The application is modularized for maintainability.
"""
import os
import json
import datetime
from flask import Flask, jsonify, session, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load configuration and utilities
import config
from logging_manager import add_log, set_analysis_state

# Import route blueprints
from routes.index_routes import index_bp
from routes.upload_routes import upload_bp
from routes.api_routes import api_bp
from routes.analysis_routes import analysis_bp

def create_app():
    """Create and configure the Flask application"""
    # Create Flask app
    app = Flask(__name__)
    
    # Setup CORS for the React frontend
    CORS(app, supports_credentials=True, resources={
        r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000", 
                           "http://localhost:3001", "http://127.0.0.1:3001",
                           "http://127.0.0.1:49371", "*"]}
    })
    
    # Load environment variables
    load_dotenv()
    
    # Configure app
    app.config.from_object(config)
    
    # Setup secret key for sessions
    app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
    
    # Create necessary directories
    os.makedirs(config.TEMP_FOLDER, exist_ok=True)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(index_bp)
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    
    # Register legacy routes for compatibility with frontend
    @app.route('/get_threads')
    def legacy_get_threads():
        """Legacy endpoint for thread listing - redirects to the API endpoint"""
        add_log(f"Legacy get_threads called with args: {request.args}", "info")
        from routes.api_routes import get_threads
        return get_threads()
        
    @app.route('/get_thread_content')
    def legacy_get_thread_content():
        """Legacy endpoint for thread content - redirects to the API endpoint"""
        add_log(f"Legacy get_thread_content called with args: {request.args}", "info")
        from routes.api_routes import get_thread_content_legacy
        return get_thread_content_legacy()
    
    # Setup path for uploaded files
    
    # Initialize analysis state from analysis_routes
    from routes.analysis_routes import analysis_state
    set_analysis_state(analysis_state)
    
    return app

if __name__ == '__main__':
    app = create_app()
    add_log("Starting HitCraft Chat Analyzer server")
    add_log("Server starting...")
    app.run(host="0.0.0.0", port=8096, debug=True)
