import os
import uuid
import tempfile
import time
import sys
import json
import logging
import threading
import re
from flask import Flask, request, render_template, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

import chat_processor
import text_processor
import claude_analyzer
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global buffer for logging messages to display on the frontend
log_buffer = []

# Our application logger
logger = logging.getLogger('hitcraft_analyzer')

# Context manager to temporarily disable logging for imported functions
class FunctionLoggingDisabled:
    """Context manager to temporarily disable logging for imported functions"""
    def __enter__(self):
        # Save the current state
        self.logger_level = logger.level
        # Temporarily disable the logger
        logger.setLevel(logging.CRITICAL)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the logger to its original state
        logger.setLevel(self.logger_level)

def add_log(message, level="info"):
    """Add a log message to the buffer for frontend display"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "message": message, "level": level}
    log_buffer.append(log_entry)
    
    # Log to the standard logger (but don't call print to avoid recursion)
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
    
    # Keep only the last 1000 messages to prevent memory issues
    if len(log_buffer) > 1000:
        log_buffer.pop(0)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp_chunks'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'rtf', 'json'}  # Added JSON to allowed extensions
app.config['MAX_CHUNKS'] = int(os.environ.get('MAX_CHUNKS', 1))  # Default to analyzing just 1 chunk for testing
app.config['RESULTS_FOLDER'] = 'analysis_results'

# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs('organized_threads', exist_ok=True)  # Directory for organized thread files

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Clear log buffer when starting a new session
    global log_buffer
    log_buffer = []
    add_log("Starting new session")
    return render_template('index.html')

@app.route('/logs')
def get_logs():
    """Return the current logs to display in the UI"""
    return jsonify(log_buffer)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        add_log("Starting file upload process")
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            add_log("No file part in request", "error")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        # If user does not select file, browser submits empty file
        if file.filename == '':
            add_log("No selected file", "error")
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            add_log(f"File '{filename}' saved to {filepath}")
            
            # Process the file - chunk it and prepare for analysis
            add_log(f"Starting to process file: {filename}")
            
            # Process without duplicate logs
            with FunctionLoggingDisabled():
                try:
                    # Use chat_processor for JSON files, text_processor for other files
                    if filename.lower().endswith('.json'):
                        chunks = chat_processor.process_chat_file(filepath)
                    else:
                        chunks = text_processor.process_file(filepath)
                except Exception as e:
                    add_log(f"Error processing file: {str(e)}", "error")
                    return jsonify({'error': f'Failed to process file: {str(e)}'}), 500
            
            # Check if processing was successful
            if not chunks:
                add_log("Error processing file - no valid content found", "error")
                return jsonify({'error': 'No valid content found in the file'}), 400
            
            # Create a unique session ID for this upload
            session_id = str(uuid.uuid4())
            
            # Create a session directory to store chunks
            session_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            # Save chunks to temporary files
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(session_dir, f"chunk_{i}.txt")
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                add_log(f"Chunk {i+1} saved (size: {len(chunk)} characters)")
            
            # Save minimal session data
            session['session_id'] = session_id
            session['filename'] = filename
            session['chunk_count'] = len(chunks)
            
            # Setup thread viewing for browsing - create thread list and thread content files
            has_threads = False
            if filename.lower().endswith('.json'):
                try:
                    # Load chat data
                    with FunctionLoggingDisabled():
                        chat_data = chat_processor.load_chat_data(filepath)
                        threads = chat_processor.organize_chats_by_thread(chat_data)
                    
                    # Create threads directory
                    threads_dir = os.path.join(session_dir, 'threads')
                    os.makedirs(threads_dir, exist_ok=True)
                    
                    # Process each thread and save to file
                    thread_list = []
                    thread_count = 0
                    thread_list_path = os.path.join(threads_dir, "thread_list.json")
                    
                    for thread_id, messages in threads.items():
                        sorted_messages = chat_processor.sort_messages_by_date(messages)
                        formatted_conversation = chat_processor.format_conversation(sorted_messages)
                        
                        # Save thread to file
                        thread_path = os.path.join(threads_dir, f"thread_{thread_id}.txt")
                        with open(thread_path, 'w', encoding='utf-8') as f:
                            f.write(formatted_conversation)
                        
                        # Get preview (first 100 characters)
                        preview = formatted_conversation[:100] + '...' if len(formatted_conversation) > 100 else formatted_conversation
                        
                        # Add to thread list
                        thread_list.append({
                            'id': thread_id,
                            'message_count': len(messages),
                            'preview': preview
                        })
                        thread_count += 1
                    
                    # Save thread list to file instead of session
                    with open(thread_list_path, 'w', encoding='utf-8') as f:
                        json.dump(thread_list, f)
                    
                    # Save only thread metadata to session
                    session['threads_dir'] = threads_dir
                    session['thread_list_path'] = thread_list_path
                    session['thread_count'] = thread_count
                    session['has_threads'] = True
                    has_threads = True
                    add_log(f"Processed {thread_count} threads for browsing")
                except Exception as e:
                    add_log(f"Error setting up thread browsing: {str(e)}", "error")
                    # Continue anyway - this is not critical
                    has_threads = False
            
            add_log(f"File processed into {len(chunks)} chunks")
            add_log(f"Created session with ID: {session_id}")
            add_log("File processing complete, ready for analysis")
            
            # Return success with minimal data
            return jsonify({
                'success': True,
                'filename': filename,
                'chunk_count': len(chunks),
                'has_threads': has_threads,
                'logs': log_buffer
            })
        
        add_log("Invalid file type", "error")
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        # Catch all other exceptions and return a proper JSON response
        error_message = f"Unexpected error during file upload: {str(e)}"
        add_log(error_message, "error")
        return jsonify({'error': error_message, 'logs': log_buffer}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    add_log("Analyzing uploaded conversation data")
    
    # Get analysis parameters
    claude_api_key = request.form.get('api_key')
    
    # Get session information
    session_id = session.get('session_id')
    filename = session.get('filename')
    
    if not session_id or not filename:
        add_log("No session or filename found", "error")
        return jsonify({'error': 'No uploaded file to analyze. Please upload a file first.'}), 400
    
    # Check if API key is provided and is not just the mock mode key
    add_log(f"API key provided: {'Yes' if claude_api_key else 'No'}")
    
    # Get max_chunks to analyze (default to 15 if not provided)
    max_chunks = request.form.get('max_chunks', '10')
    try:
        max_chunks = int(max_chunks)
        add_log(f"Max chunks to analyze: {max_chunks}")
    except:
        add_log(f"Invalid max_chunks value, defaulting to 10", "warning")
        max_chunks = 10
    
    # Validate API key
    if not claude_api_key or claude_api_key.lower() == 'mock':
        add_log("No valid API key provided. Please enter a real Claude API key.", "error")
        return jsonify({'error': 'No valid API key provided. Please enter a real Claude API key.'}), 400
    
    # Set up session information
    add_log(f"Starting analysis on session {session_id}")
    session_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
    chunk_count = session.get('chunk_count', 0)
    
    # Load all chunks from session directory
    chunks = []
    for i in range(chunk_count):
        chunk_path = os.path.join(session_dir, f"chunk_{i}.txt")
        try:
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunks.append(f.read())
        except Exception as e:
            add_log(f"Error reading chunk {i}: {str(e)}", "error")
    
    # Check if we have any chunks to analyze
    if not chunks:
        add_log("No chunks found for analysis", "error")
        return jsonify({'error': 'No content chunks found for analysis'}), 400
    
    add_log(f"Using {len(chunks)} chunks for analysis")
    
    try:
        # Send chunks to Claude
        add_log(f"Sending {len(chunks)} chunks to Claude for analysis")
        results = claude_analyzer.analyze_chunks(chunks, claude_api_key, False, max_chunks)
        
        # Combine results
        combined_results = claude_analyzer.combine_results(results)
        
        # Save results to file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"analysis_{filename}_{timestamp}.json"
        result_path = os.path.join('analysis_results', result_filename)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2)
        
        add_log(f"Analysis results saved to {result_path}")
        add_log("Analysis completed successfully")
        
        # Return success with minimal data
        return jsonify({
            'success': True,
            'filename': filename,
            'result_path': result_path
        })
    
    except Exception as e:
        add_log(f"Error during analysis: {str(e)}", "error")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/analysis-status', methods=['GET'])
def analysis_status():
    """Return the current analysis status"""
    # If there's an active analysis, report its status
    if 'session_id' in session:
        # In a real-world application with long-running jobs, we would track progress
        # For this demo, we'll just return a simple status
        return jsonify({
            'status': 'in_progress',
            'progress': 50,  # Mock progress percentage
            'message': 'Analyzing conversations...'
        })
    
    # No active analysis
    return jsonify({
        'status': 'idle',
        'progress': 0,
        'message': 'No analysis in progress'
    })

@app.route('/get-chunks', methods=['POST'])
def get_chunks():
    """Return the conversation chunks for preview"""
    try:
        # Get the requested number of chunks
        data = request.get_json()
        max_chunks = int(data.get('max_chunks', 1)) if data else 1
        
        add_log(f"Loading chunks for preview, max chunks: {max_chunks}")
        
        # Ensure we have an active session
        if 'session_id' not in session:
            add_log("No active session found", "error")
            return jsonify({'error': 'No active session. Please upload a file first.'}), 400
        
        session_id = session['session_id']
        add_log(f"Getting chunks for session: {session_id}")
        
        # Get the session directory
        session_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
        if not os.path.exists(session_dir):
            add_log(f"Session directory not found: {session_dir}", "error")
            return jsonify({'error': 'Session data not found. Please upload a file again.'}), 404
        
        # Load all chunks from the session directory
        chunks = []
        chunk_files = sorted(
            [f for f in os.listdir(session_dir) if f.startswith('chunk_')],
            key=lambda x: int(x.split('_')[1].split('.')[0])
        )
        
        # Limit to the requested number of chunks
        chunk_files = chunk_files[:max_chunks]
        
        for chunk_file in chunk_files:
            chunk_path = os.path.join(session_dir, chunk_file)
            try:
                with open(chunk_path, 'r', encoding='utf-8') as f:
                    chunk_content = f.read()
                    chunks.append(chunk_content)
            except Exception as e:
                add_log(f"Error reading chunk file {chunk_file}: {str(e)}", "error")
        
        add_log(f"Successfully loaded {len(chunks)} chunks for preview")
        
        return jsonify({
            'chunks': chunks,
            'total_chunks': len(chunk_files)
        })
    
    except Exception as e:
        add_log(f"Error in get_chunks: {str(e)}", "error")
        add_log(traceback.format_exc(), "error")
        return jsonify({'error': str(e)}), 500

@app.route('/get_results/<filename>')
def get_results(filename):
    """Return the analysis results"""
    if 'session_id' not in session:
        return jsonify({'error': 'No active session found'}), 404
    
    # Look for the latest analysis results file for this filename
    results_dir = app.config['RESULTS_FOLDER']
    result_files = [f for f in os.listdir(results_dir) if f.startswith(f"analysis_{filename}_")]
    
    if not result_files:
        return jsonify({'error': 'No analysis results found for this file'}), 404
    
    # Get the most recent result file
    result_files.sort(reverse=True)
    latest_result = os.path.join(results_dir, result_files[0])
    
    try:
        with open(latest_result, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        add_log(f"Loaded analysis results: {latest_result}")
        return jsonify(results)
    except Exception as e:
        add_log(f"Error loading analysis results: {str(e)}", "error")
        return jsonify({'error': f'Error loading analysis results: {str(e)}'}), 500

@app.route('/get_threads')
def list_threads():
    """Return the list of threads available for browsing"""
    if 'thread_list_path' not in session or not session.get('has_threads', False):
        return jsonify({'error': 'No threads available. Please upload a JSON chat file first.'}), 404
    
    # Load thread list from file
    thread_list_path = session['thread_list_path']
    with open(thread_list_path, 'r', encoding='utf-8') as f:
        thread_list = json.load(f)
    
    # Return paginated results
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    total = len(thread_list)
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    
    current_page_threads = thread_list[start_idx:end_idx]
    
    return jsonify({
        'threads': current_page_threads,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/get_thread_content')
def get_thread():
    """Return the content of a specific thread"""
    if 'threads_dir' not in session or not session.get('has_threads', False):
        return jsonify({'error': 'No threads available. Please upload a JSON chat file first.'}), 404
    
    thread_id = request.args.get('thread_id')
    if not thread_id:
        return jsonify({'error': 'No thread ID provided'}), 400
    
    threads_dir = session['threads_dir']
    thread_path = os.path.join(threads_dir, f"thread_{thread_id}.txt")
    
    if not os.path.exists(thread_path):
        return jsonify({'error': f'Thread {thread_id} not found'}), 404
    
    try:
        with open(thread_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse content into messages array for better UI display
        messages = content.split('\n\n')
        # Filter out empty messages
        messages = [msg for msg in messages if msg.strip()]
        
        return jsonify({
            'id': thread_id, 
            'content': messages,
            'message_count': len(messages)
        })
    except Exception as e:
        add_log(f"Error retrieving thread content: {str(e)}", "error")
        return jsonify({'error': f'Error retrieving thread content: {str(e)}'}), 500

if __name__ == '__main__':
    logging.info("Starting HitCraft Chat Analyzer server")
    app.run(host='0.0.0.0', port=8090, debug=True)