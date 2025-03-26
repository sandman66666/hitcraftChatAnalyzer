"""
Index routes for HitCraft Chat Analyzer
"""
import os
from flask import Blueprint, render_template, jsonify, request
from logging_manager import add_log, get_logs

# Create Blueprint
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@index_bp.route('/logs')
def logs():
    """Return the log messages for display in the UI"""
    try:
        return jsonify({'logs': get_logs()})
    except Exception as e:
        return jsonify({'error': str(e)})
