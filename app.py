import os
import uuid
import tempfile
import time
import sys
import logging
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from flask_cors import CORS  # Import CORS
import text_processor
import claude_analyzer
import json

# Create a global log buffer that will be sent to frontend
log_buffer = []

# Configure logging to avoid recursion issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

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
CORS(app)  # Enable CORS for all routes
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_FOLDER'] = 'temp_chunks'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'rtf'}
app.config['MAX_CHUNKS'] = int(os.environ.get('MAX_CHUNKS', 1))  # Default to analyzing just 1 chunk for testing

# Create necessary directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
os.makedirs('analysis_results', exist_ok=True)

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
        add_log(f"Starting to chunk file: {filename}")
        
        # Process without duplicate logs
        with FunctionLoggingDisabled():
            chunks = text_processor.chunk_file(filepath)
            
        add_log(f"File processed into {len(chunks)} chunks")
        
        # Generate a unique session ID for this analysis
        session_id = str(uuid.uuid4())
        add_log(f"Created session with ID: {session_id}")
        
        # Create a temp directory for this session's chunks
        session_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Save chunks to temporary files
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(session_dir, f"chunk_{i}.txt")
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            chunk_paths.append(chunk_path)
            add_log(f"Chunk {i+1} saved (size: {len(chunk)} characters)")
        
        # Store session info
        session['session_id'] = session_id
        session['filename'] = filename
        session['chunk_count'] = len(chunks)
        
        add_log(f"File processing complete, ready for analysis")
        return jsonify({
            'success': True,
            'filename': filename,
            'chunk_count': len(chunks),
            'logs': log_buffer
        })
    
    add_log(f"File type not allowed: {file.filename}", "error")
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/analyze', methods=['POST'])
def analyze():
    add_log("Starting analysis process")
    
    if 'session_id' not in session:
        add_log("No file has been uploaded", "error")
        return jsonify({'error': 'No file has been uploaded'}), 400
    
    session_id = session['session_id']
    filename = session.get('filename', 'Unknown file')
    chunk_count = session.get('chunk_count', 0)
    add_log(f"Analyzing file: {filename} with {chunk_count} chunks")
    
    # Get the session directory
    session_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
    if not os.path.exists(session_dir):
        add_log(f"Session data not found for session: {session_id}", "error")
        return jsonify({'error': 'Session data not found'}), 400
    
    # Load chunks from temporary files
    chunks = []
    add_log(f"Loading {chunk_count} chunks from temporary storage")
    for i in range(chunk_count):
        chunk_path = os.path.join(session_dir, f"chunk_{i}.txt")
        if os.path.exists(chunk_path):
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_content = f.read()
                chunks.append(chunk_content)
                add_log(f"Loaded chunk {i+1} (size: {len(chunk_content)} characters)")
    
    add_log(f"Successfully loaded {len(chunks)} chunks")
    
    # Get Claude API key from environment or request
    claude_api_key = os.environ.get('CLAUDE_API_KEY')
    if not claude_api_key and request.is_json and 'api_key' in request.json:
        claude_api_key = request.json['api_key']
        add_log("Using API key from request")
    elif claude_api_key:
        add_log("Using API key from environment")
    
    # Check if we should use mock data
    use_mock = False
    if not claude_api_key or claude_api_key.lower() == 'mock':
        use_mock = True
        add_log("Using MOCK DATA mode since no valid API key was provided", "warning")
    
    # Get max_chunks from config
    max_chunks = app.config['MAX_CHUNKS']
    if max_chunks > 0 and max_chunks < len(chunks):
        add_log(f"TESTING MODE: Limiting analysis to {max_chunks} of {len(chunks)} chunks", "warning")
    else:
        max_chunks = None  # Process all chunks
    
    # Analyze chunks with Claude
    try:
        add_log(f"Starting analysis of chunks with Claude AI")
        start_time = time.time()
        
        # We'll handle the Claude analyzer output ourselves to avoid duplicate logging
        with FunctionLoggingDisabled():
            results = claude_analyzer.analyze_chunks(chunks, claude_api_key, use_mock, max_chunks)
            
        analysis_time = time.time() - start_time
        add_log(f"Analysis completed in {analysis_time:.2f} seconds")
        
        # Combine results
        add_log("Combining analysis results from all chunks")
        
        # Handle combining without duplicate logs
        with FunctionLoggingDisabled():
            combined_analysis = claude_analyzer.combine_results(results)
            
        add_log("Results combined successfully")
        
        # Store the analysis results
        analysis_dir = 'analysis_results'
        os.makedirs(analysis_dir, exist_ok=True)
        
        result_filename = f"{filename.rsplit('.', 1)[0]}_analysis.json"
        result_path = os.path.join(analysis_dir, result_filename)
        
        with open(result_path, 'w') as f:
            json.dump(combined_analysis, f, indent=2)
        
        add_log(f"Analysis results saved to {result_path}")
        
        # Display some of the insights in the logs
        if 'key_insights' in combined_analysis and combined_analysis['key_insights']:
            add_log("Key insights from analysis:")
            for idx, insight in enumerate(combined_analysis['key_insights']):
                add_log(f"  {idx+1}. {insight}")
        
        return jsonify({
            'success': True,
            'analysis': combined_analysis,
            'logs': log_buffer
        })
    
    except Exception as e:
        add_log(f"Error during analysis: {str(e)}", "error")
        import traceback
        add_log(traceback.format_exc(), "error")
        return jsonify({'error': str(e), 'logs': log_buffer}), 500

@app.route('/results/<filename>')
def get_results(filename):
    add_log(f"Retrieving previous analysis for: {filename}")
    # Load and return previously generated analysis
    result_path = os.path.join('analysis_results', f"{filename.rsplit('.', 1)[0]}_analysis.json")
    
    if not os.path.exists(result_path):
        add_log(f"Analysis not found for {filename}", "error")
        return jsonify({'error': 'Analysis not found'}), 404
    
    with open(result_path, 'r') as f:
        analysis = json.load(f)
    
    add_log(f"Successfully retrieved analysis for {filename}")
    return jsonify(analysis)

if __name__ == '__main__':
    logging.info("Starting HitCraft Chat Analyzer server")
    app.run(host='0.0.0.0', port=8090, debug=True)