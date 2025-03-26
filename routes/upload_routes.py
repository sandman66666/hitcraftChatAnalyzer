"""
File upload routes for HitCraft Chat Analyzer
"""
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
import os
import uuid

from logging_manager import add_log
import config
from thread_extractor import extract_threads_from_chat_file

# Create a Blueprint
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and store the file"""
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        # Check if file has allowed extension
        if file and config.allowed_file(file.filename):
            # Get or create session ID
            session_id = session.get('session_id')
            if not session_id:
                session_id = os.urandom(16).hex()
                session['session_id'] = session_id
                
            # Create session directory
            session_dir = os.path.join(config.TEMP_FOLDER, session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Secure the filename and store it
            filename = secure_filename(file.filename)
            upload_path = os.path.join(config.UPLOAD_FOLDER, filename)
            file.save(upload_path)
            
            # Set current filename in session
            session['filename'] = filename
            
            add_log(f"File uploaded: {filename}")
            
            # Extract thread information from the file
            threads_dir = os.path.join(session_dir, 'threads')
            threads_extracted, messages_processed, thread_files = extract_threads_from_chat_file(upload_path, threads_dir)
            
            return jsonify({
                'status': 'success', 
                'filename': filename,
                'threads_count': threads_extracted,
                'messages_processed': messages_processed,
                'session_id': session_id
            })
        else:
            return jsonify({'error': 'File type not allowed'}), 400
            
    except Exception as e:
        error_message = str(e)
        add_log(f"Error uploading file: {error_message}", "error")
        import traceback
        add_log(traceback.format_exc(), "error")
        return jsonify({'error': error_message}), 500

@upload_bp.route('/extract_threads', methods=['POST'])
def extract_threads():
    """Extract conversation threads from a chat file by grouping messages with the same threadId"""
    try:
        data = request.get_json() or {}
        
        # Get session information
        session_id = session.get('session_id')
        if not session_id:
            session_id = data.get('session_id')
            if session_id:
                session['session_id'] = session_id
        
        filename = session.get('filename')
        if not filename:
            filename = data.get('filename')
            if filename:
                session['filename'] = filename
        
        if not session_id or not filename:
            add_log("No session or filename found", "error")
            return jsonify({'error': 'No uploaded file. Please upload a file first.'}), 400
        
        # Set up paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        threads_dir = os.path.join(session_dir, 'threads')
        
        # Make sure the file exists
        if not os.path.isfile(filepath):
            add_log(f"File not found: {filepath}", "error")
            return jsonify({'error': 'Uploaded file not found'}), 404
        
        # Extract threads from the file
        try:
            thread_count, new_messages, thread_list = extract_threads_from_chat_file(filepath, threads_dir)
            
            # Store thread count in session
            session['thread_count'] = thread_count
            
            # Return success with thread count
            return jsonify({
                'success': True,
                'thread_count': thread_count,
                'new_messages': new_messages,
                'session_id': session_id
            })
        except Exception as e:
            add_log(f"Error extracting threads: {str(e)}", "error")
            import traceback
            add_log(traceback.format_exc(), "error")
            return jsonify({'error': f'Error extracting threads: {str(e)}'}), 500
            
    except Exception as e:
        error_message = str(e)
        add_log(f"Error in extract_threads endpoint: {error_message}", "error")
        import traceback
        add_log(traceback.format_exc(), "error")
        return jsonify({'error': error_message}), 500
