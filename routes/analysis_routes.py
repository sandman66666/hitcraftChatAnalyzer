"""
Analysis routes for HitCraft Chat Analyzer
"""
from flask import Blueprint, request, jsonify, session
import os
import json
import time
import datetime
import threading
import traceback
import logging
import anthropic
import requests
from flask import Blueprint, request, jsonify, session
from logging_manager import add_log
import config
import thread_analyzer

# Create a Blueprint
analysis_bp = Blueprint('analysis', __name__)

# Analysis state tracking
analysis_state = {
    'is_analyzing': False,
    'current_thread': 0,
    'total_threads': 0,
    'analyzed_threads': 0,
    'session_id': None,
    'filename': None,
    'thread_files': [],
    'start_time': None,
    'last_updated': None,
    'thread_results': [],
    'combined_results': None,
    'thread_limit': 0,
    'log_entries': []  # Initialize log entries array
}

# Register analysis state with logging manager
from logging_manager import set_analysis_state
set_analysis_state(analysis_state)

# Function to add a log entry that also updates the analysis state
def add_analysis_log(message, level="info"):
    """Add a log entry and also update the analysis state log"""
    # Log using the normal logger
    add_log(message, level)
    
    # Also add to analysis state for frontend
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    
    # Make sure log_entries exists
    if 'log_entries' not in analysis_state:
        analysis_state['log_entries'] = []
        
    # Add the entry
    analysis_state['log_entries'].append(entry)
    
    # Keep only the last 100 entries
    if len(analysis_state['log_entries']) > 100:
        analysis_state['log_entries'] = analysis_state['log_entries'][-100:]

@analysis_bp.route('/analyze_threads', methods=['POST'])
def analyze_threads():
    """Start analysis of a specific number of threads"""
    try:
        # Log request details for debugging
        add_analysis_log(f"Request content type: {request.content_type}", "info")
        add_analysis_log(f"Request data: {request.data.decode('utf-8') if request.data else 'None'}", "info")
        
        # Get session information
        session_id = session.get('session_id')
        filename = session.get('filename')
        
        # Check if session_id is passed in the JSON body
        data = request.get_json(silent=True)
        add_analysis_log(f"Parsed JSON data: {data}", "info")
        
        if data and 'session_id' in data:
            session_id = data.get('session_id')
        
        if not session_id or not filename:
            return jsonify({'error': 'No active session or filename'}), 404
            
        # Get API key
        api_key = os.environ.get('CLAUDE_API_KEY')
        if not api_key:
            return jsonify({'error': 'Claude API key not set'}), 400
            
        # Check if analysis is already running
        if analysis_state['is_analyzing']:
            return jsonify({'error': 'Analysis already in progress'}), 409
            
        # More flexible handling of count parameter - check for both 'count' and 'thread_count'
        thread_count = None
        
        # Try to get count from JSON body - check both parameter names
        if data:
            if 'count' in data:
                thread_count = data.get('count', 0)
                add_analysis_log(f"Found 'count' in JSON body: {thread_count}", "info")
            elif 'thread_count' in data:
                thread_count = data.get('thread_count', 0)
                add_analysis_log(f"Found 'thread_count' in JSON body: {thread_count}", "info")
        
        # Fallback: try to get from query parameters
        if not thread_count and request.args.get('count'):
            try:
                thread_count = int(request.args.get('count', 0))
                add_analysis_log(f"Found count in query params: {thread_count}", "info")
            except ValueError:
                add_analysis_log(f"Invalid count in query params: {request.args.get('count')}", "error")
        elif not thread_count and request.args.get('thread_count'):
            try:
                thread_count = int(request.args.get('thread_count', 0))
                add_analysis_log(f"Found thread_count in query params: {thread_count}", "info")
            except ValueError:
                add_analysis_log(f"Invalid thread_count in query params: {request.args.get('thread_count')}", "error")
        
        # STRICT ENFORCEMENT: If no valid count is specified explicitly or count is <= 0, default to 1
        if not thread_count or thread_count <= 0:
            thread_count = 1
            add_analysis_log(f"No valid count specified, defaulting to analyzing 1 thread", "info")
        
        # Set up paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        
        # Get thread files
        try:
            thread_files = [f for f in os.listdir(threads_dir) if os.path.isfile(os.path.join(threads_dir, f))]
            # Sort thread files to ensure consistent order
            thread_files.sort()
        except FileNotFoundError:
            return jsonify({'error': 'No threads found for analysis'}), 404
            
        if not thread_files:
            return jsonify({'error': 'No threads found for analysis'}), 404
            
        # Calculate available thread count
        available_thread_count = len(thread_files)
        add_analysis_log(f"Found {available_thread_count} available threads", "info")
        
        # STRICT ENFORCEMENT: Limit to exactly the requested number or available threads, whichever is smaller
        thread_count = min(thread_count, available_thread_count)
        add_analysis_log(f"Will analyze exactly {thread_count} threads", "info")
        
        # Select only the threads we need
        thread_files = thread_files[:thread_count]
        
        # Double-check the thread count matches what we expect
        if len(thread_files) != thread_count:
            add_analysis_log(f"WARNING: Thread count mismatch. Requested: {thread_count}, Selected: {len(thread_files)}")
            thread_files = thread_files[:thread_count]
        
        # Clear previous analysis state
        analysis_state['is_analyzing'] = True
        analysis_state['current_thread'] = 0
        analysis_state['total_threads'] = thread_count
        analysis_state['analyzed_threads'] = 0
        analysis_state['session_id'] = session_id
        analysis_state['filename'] = filename
        analysis_state['thread_files'] = thread_files
        analysis_state['start_time'] = datetime.datetime.now()
        analysis_state['last_updated'] = datetime.datetime.now()
        analysis_state['thread_results'] = []
        analysis_state['combined_results'] = None
        analysis_state['thread_limit'] = thread_count
        analysis_state['log_entries'] = []  # Reset log entries
        
        add_analysis_log(f"Starting analysis of {thread_count} threads", "info")
        add_analysis_log(f"ENFORCING STRICT THREAD LIMIT: Will analyze exactly {thread_count} threads", "info")
        
        # Start analysis in a background thread
        analysis_thread = threading.Thread(
            target=thread_analyzer.analyze_threads_in_background,
            args=(api_key, session_id, filename, threads_dir, thread_files, analysis_state)
        )
        analysis_thread.daemon = True
        analysis_thread.start()
        
        analysis_state['analysis_thread'] = analysis_thread
        
        return jsonify({
            'status': 'started',
            'thread_count': len(thread_files),
            'available_count': available_thread_count
        })
        
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error starting analysis: {error_message}", "error")
        import traceback
        add_analysis_log(traceback.format_exc(), "error")
        # Reset analysis state in case of error
        analysis_state['is_analyzing'] = False
        return jsonify({'error': error_message}), 500

@analysis_bp.route('/thread_count', methods=['GET'])
def thread_count():
    """Return the current count of threads available and previously analyzed"""
    try:
        # Get session information
        session_id = session.get('session_id')
        filename = session.get('filename')
        
        if not session_id or not filename:
            return jsonify({'error': 'No active session or filename'}), 404
            
        # Set up paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        results_dir = os.path.join(session_dir, 'results')
        
        # Count thread files
        available_threads = 0
        try:
            thread_files = [f for f in os.listdir(threads_dir) if f.endswith('.txt')]
            available_threads = len(thread_files)
        except FileNotFoundError:
            pass
            
        # Count analyzed threads from session results
        analyzed_threads = 0
        combined_results_path = os.path.join(results_dir, 'combined_results.json')
        if os.path.isfile(combined_results_path):
            try:
                with open(combined_results_path, 'r') as f:
                    results = json.load(f)
                analyzed_threads = len(results.get('thread_results', []))
            except:
                pass
                
        return jsonify({
            'available_threads': available_threads,
            'analyzed_threads': analyzed_threads,
            'is_analyzing': analysis_state['is_analyzing']
        })
        
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error getting thread count: {error_message}", "error")
        return jsonify({'error': error_message}), 500

@analysis_bp.route('/check_progress', methods=['GET'])
def check_progress():
    """Return the current progress of thread analysis"""
    try:
        # Check if analysis is running
        if not analysis_state['is_analyzing'] and analysis_state['analyzed_threads'] == 0:
            return jsonify({'status': 'not_started'})
            
        # Calculate progress percentage
        total_threads = analysis_state['total_threads']
        if total_threads > 0:
            progress = (analysis_state['current_thread'] / total_threads) * 100
        else:
            progress = 0
            
        # Calculate time elapsed and estimated time remaining
        elapsed = None
        remaining = None
        if analysis_state['start_time']:
            elapsed_seconds = (datetime.datetime.now() - analysis_state['start_time']).total_seconds()
            elapsed = round(elapsed_seconds)
            
            if progress > 0:
                total_estimated = elapsed_seconds * (100 / progress)
                remaining = round(total_estimated - elapsed_seconds)
                
        return jsonify({
            'status': 'in_progress' if analysis_state['is_analyzing'] else 'completed',
            'current': analysis_state['current_thread'],
            'total': total_threads,
            'analyzed': analysis_state['analyzed_threads'],
            'progress': round(progress, 1),
            'elapsed_seconds': elapsed,
            'remaining_seconds': remaining,
            'log_entries': analysis_state['log_entries'][-20:],  # Send last 20 log entries
            'has_results': analysis_state['combined_results'] is not None
        })
        
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error checking progress: {error_message}", "error")
        return jsonify({'status': 'error', 'error': error_message})

@analysis_bp.route('/cancel_analysis', methods=['POST'])
def cancel_analysis():
    """Cancel the current thread analysis"""
    try:
        if not analysis_state['is_analyzing']:
            return jsonify({'status': 'not_analyzing'})
            
        # Mark analysis as canceled
        analysis_state['is_analyzing'] = False
        add_analysis_log("Analysis canceled by user", "warning")
        
        return jsonify({'status': 'canceled'})
        
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error canceling analysis: {error_message}", "error")
        return jsonify({'status': 'error', 'error': error_message})

@analysis_bp.route('/analysis/status', methods=['GET'])
def get_analysis_status():
    """Get current analysis status"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            session_id = request.args.get('session_id')
            
        # If we have a session ID, check for available threads
        if session_id:
            # Set up session directory paths
            session_dir = os.path.join(config.TEMP_FOLDER, session_id)
            threads_dir = os.path.join(session_dir, 'threads')
            
            # Count available threads
            if os.path.exists(threads_dir):
                thread_files = glob.glob(os.path.join(threads_dir, '*.txt'))
                thread_count = len(thread_files)
                
                # Update analysis state with thread count if we found threads
                if thread_count > 0 and analysis_state.get('threads_available', 0) == 0:
                    analysis_state['threads_available'] = thread_count
                    add_analysis_log(f"Updated analysis state with {thread_count} available threads", "info")
        
        # Return the current state
        return jsonify(analysis_state)
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error getting analysis status: {error_message}", "error")
        return jsonify({'status': 'error', 'error': error_message})

@analysis_bp.route('/debug_analysis_state', methods=['GET'])
def debug_analysis_state():
    """Debug endpoint to check the current analysis state"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            session_id = request.args.get('session_id')
        
        # Check if threads directory exists
        session_dir = os.path.join(config.TEMP_FOLDER, session_id) if session_id else None
        threads_dir = os.path.join(session_dir, 'threads') if session_dir else None
        
        result = {
            'session_id': session_id,
            'analysis_state': analysis_state,
            'session_dir_exists': os.path.exists(session_dir) if session_dir else False,
            'threads_dir_exists': os.path.exists(threads_dir) if threads_dir else False
        }
        
        # Count threads if directory exists
        if result['threads_dir_exists']:
            thread_files = glob.glob(os.path.join(threads_dir, '*.txt'))
            result['thread_count'] = len(thread_files)
            
            # Check thread_list.json
            thread_list_path = os.path.join(threads_dir, 'thread_list.json')
            if os.path.exists(thread_list_path):
                try:
                    with open(thread_list_path, 'r') as f:
                        thread_list = json.load(f)
                        result['thread_list_count'] = len(thread_list)
                except Exception as e:
                    result['thread_list_error'] = str(e)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@analysis_bp.route('/analysis_progress', methods=['GET'])
def analysis_progress():
    """Return the current progress of analysis for the frontend"""
    try:
        # Get filename from query params
        filename = request.args.get('filename')
        
        # Check if analysis is running
        is_analyzing = analysis_state.get('is_analyzing', False)
        total_threads = analysis_state.get('total_threads', 0)
        analyzed_threads = analysis_state.get('analyzed_threads', 0)
        
        # Check for completion
        status = 'in_progress' if is_analyzing else 'complete'
        
        # Check if any threads have been analyzed
        if not is_analyzing and analyzed_threads == 0:
            status = 'not_started'
        
        # Get session id
        session_id = analysis_state.get('session_id')
        
        # Check if results are available
        has_results = False
        if session_id:
            results_path = os.path.join(config.TEMP_FOLDER, session_id, 'analysis', 'combined_analysis.json')
            has_results = os.path.exists(results_path)
            
        # Build response
        response = {
            'success': True,
            'status': status,
            'threads_analyzed': analyzed_threads,
            'threads_total': total_threads,
            'progress': (analyzed_threads / total_threads * 100) if total_threads > 0 else 0,
            'has_results': has_results,
            'log_entries': analysis_state.get('log_entries', [])[-10:]  # Last 10 log entries
        }
        
        add_analysis_log(f"Progress check: {response['status']}, {response['threads_analyzed']}/{response['threads_total']}")
        
        return jsonify(response)
    
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error checking analysis progress: {error_message}", "error")
        return jsonify({'success': False, 'error': error_message})

@analysis_bp.route('/get_analysis_results', methods=['GET'])
def get_analysis_results():
    """Get the analysis results for display in the frontend"""
    try:
        # Get session id and filename from query params or session
        session_id = request.args.get('session_id') or session.get('session_id')
        filename = request.args.get('filename') or session.get('filename')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
            
        # Set up paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        analysis_dir = os.path.join(session_dir, 'analysis')
        combined_path = os.path.join(analysis_dir, 'combined_analysis.json')
        
        # Check if analysis results exist
        if not os.path.exists(combined_path):
            return jsonify({'success': False, 'error': 'No analysis results found for this session'}), 404
            
        # Read analysis results
        with open(combined_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
            
        add_analysis_log("Sending analysis results to frontend")
        
        # Return analysis results
        return jsonify({
            'success': True,
            'results': results,
            'session_id': session_id,
            'filename': filename
        })
        
    except Exception as e:
        error_message = str(e)
        add_analysis_log(f"Error getting analysis results: {error_message}", "error")
        return jsonify({'success': False, 'error': error_message}), 500

def analyze_single_thread(api_key, thread_path):
    """Analyze a single thread using Claude API"""
    try:
        # Read thread content
        with open(thread_path, 'r') as f:
            thread_content = f.read()
            
        # Call Claude API directly since we have the thread content
        result = thread_analyzer.claude_analyzer.analyze_single_thread(thread_content, api_key)
        
        if result:
            add_analysis_log("Thread analysis completed successfully")
            return result
        else:
            add_analysis_log("Failed to analyze thread", "error")
            return None
            
    except Exception as e:
        add_analysis_log(f"Error analyzing thread: {str(e)}", "error")
        return None

def save_thread_analysis(session_id, thread_id, result):
    """Save thread analysis to disk"""
    try:
        # Create analysis directory if it doesn't exist
        analysis_dir = os.path.join(config.TEMP_FOLDER, session_id, 'analysis')
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Save analysis result as JSON
        analysis_path = os.path.join(analysis_dir, f"{thread_id}.json")
        with open(analysis_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        return True
    except Exception as e:
        add_analysis_log(f"Error saving thread analysis: {str(e)}", "error")
        return False

def summarize_and_save_analysis_results(api_key, session_id, filename, thread_results):
    """Summarize all thread analyses and save combined result"""
    try:
        # Create analysis directory if it doesn't exist
        analysis_dir = os.path.join(config.TEMP_FOLDER, session_id, 'analysis')
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Save combined analysis as JSON
        combined_path = os.path.join(analysis_dir, "combined_analysis.json")
        with open(combined_path, 'w') as f:
            combined_data = {
                "filename": filename,
                "thread_count": len(thread_results),
                "date": datetime.datetime.now().isoformat(),
                "thread_categories": {},
                "thread_discussions": {}
            }
            
            # Aggregate categories and discussions
            for result in thread_results:
                # Add categories
                if 'categories' in result:
                    for category in result['categories']:
                        if category in combined_data['thread_categories']:
                            combined_data['thread_categories'][category] += 1
                        else:
                            combined_data['thread_categories'][category] = 1
                
                # Add discussions
                if 'top_discussions' in result:
                    for discussion in result['top_discussions']:
                        topic = discussion.get('topic', 'Unknown topic')
                        count = discussion.get('count', 0)
                        
                        if topic in combined_data['thread_discussions']:
                            combined_data['thread_discussions'][topic] += count
                        else:
                            combined_data['thread_discussions'][topic] = count
            
            # Convert dictionaries to sorted lists
            combined_data['top_categories'] = [
                {"category": cat, "count": count}
                for cat, count in sorted(
                    combined_data['thread_categories'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
            
            combined_data['top_discussions'] = [
                {"topic": topic, "count": count}
                for topic, count in sorted(
                    combined_data['thread_discussions'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
            
            # Remove original dictionaries
            del combined_data['thread_categories']
            del combined_data['thread_discussions']
            
            json.dump(combined_data, f, indent=2)
        
        add_analysis_log("Saved combined analysis results")
        return True
    except Exception as e:
        add_analysis_log(f"Error saving combined analysis: {str(e)}", "error")
        return False
