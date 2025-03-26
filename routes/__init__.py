"""
Routes package for HitCraft Chat Analyzer
"""
from routes.index_routes import index_bp
from routes.upload_routes import upload_bp
from routes.analysis_routes import analysis_bp
from routes.api_routes import api_bp

# Export all blueprints
__all__ = ['index_bp', 'upload_bp', 'analysis_bp', 'api_bp']
