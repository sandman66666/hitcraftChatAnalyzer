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
import thread_storage
import copy
import glob

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
    'log_entries': [],  # Initialize log entries array
    'evidence_map': {}  # Map insights to their thread evidence
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

        # Get unanalyzed threads from persistent storage
        thread_data = thread_storage.get_unanalyzed_threads(thread_count)
        
        if not thread_data:
            return jsonify({'error': 'No unanalyzed threads found'}), 404
        
        # Get thread IDs for the analysis process
        thread_ids = [t['id'] for t in thread_data]
        
        # Clear previous analysis state
        analysis_state['is_analyzing'] = True
        analysis_state['current_thread'] = 0
        analysis_state['total_threads'] = len(thread_data)
        analysis_state['analyzed_threads'] = 0
        analysis_state['session_id'] = session_id
        analysis_state['filename'] = filename
        analysis_state['thread_files'] = thread_ids
        analysis_state['start_time'] = datetime.datetime.now()
        analysis_state['last_updated'] = datetime.datetime.now()
        analysis_state['thread_results'] = []
        analysis_state['combined_results'] = None
        analysis_state['thread_limit'] = len(thread_data)
        analysis_state['log_entries'] = []  # Reset log entries
        analysis_state['evidence_map'] = {}  # Reset evidence map
        
        add_analysis_log(f"Starting analysis of {len(thread_data)} threads", "info")
        
        # Start analysis in a background thread
        analysis_thread = threading.Thread(
            target=analyze_threads_in_background,
            args=(api_key, thread_data, analysis_state)
        )
        analysis_thread.daemon = True
        analysis_thread.start()
        
        analysis_state['analysis_thread'] = analysis_thread
        
        # Get analysis stats for response
        stats = thread_storage.get_analysis_stats()
        
        return jsonify({
            'status': 'started',
            'thread_count': len(thread_data),
            'total_threads': stats['total_threads'],
            'previously_analyzed': stats['analyzed_threads']
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
        # First check if we have results in the analysis state
        if analysis_state['combined_results']:
            add_log(f"Returning analysis results from state", "info")
            return jsonify({
                'success': True,
                'results': analysis_state['combined_results'],
                'analyzed_threads': analysis_state['analyzed_threads'],
                'total_threads': analysis_state['total_threads']
            })
        
        # If not in state, try to get from persistent storage
        result = thread_storage.get_latest_analysis()
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404
            
        # Get the stats for counts
        stats = thread_storage.get_analysis_stats()
            
        return jsonify({
            'success': True,
            'results': result['results'],
            'analyzed_threads': stats['analyzed_threads'],
            'total_threads': stats['total_threads'],
            'metadata': result['metadata']
        })
        
    except Exception as e:
        add_log(f"Error getting analysis results: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analysis_bp.route('/get_evidence', methods=['GET'])
def get_insight_evidence():
    """Get message evidence for a specific insight"""
    try:
        insight_key = request.args.get('key')
        
        if not insight_key:
            return jsonify({'error': 'No insight key provided'}), 400
            
        # Get evidence from thread storage
        evidence = thread_storage.get_evidence_for_insight(insight_key)
        
        if not evidence:
            return jsonify({
                'success': True,
                'evidence': [],
                'message': 'No evidence found for this insight'
            })
            
        return jsonify({
            'success': True,
            'evidence': evidence
        })
        
    except Exception as e:
        add_log(f"Error getting insight evidence: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Function to analyze threads in background
def analyze_threads_in_background(api_key, thread_data, state):
    """Analyze threads in the background and update state"""
    try:
        num_threads = len(thread_data)
        add_analysis_log(f"Starting analysis batch for {num_threads} threads")
        
        # List to store analysis results
        thread_results = []
        evidence_map = {}
        analyzed_thread_ids = []
        
        # For each thread
        for i, thread in enumerate(thread_data):
            thread_id = thread['id']
            add_analysis_log(f"Analyzing thread {thread_id} ({i+1}/{num_threads})")
            
            # Store metadata in state
            state['current_thread'] = thread_id
            state['completed_threads'] = i
            state['total_threads'] = num_threads
            state['last_updated'] = datetime.datetime.now()
            
            try:
                # Extract messages from thread
                messages = []
                
                # Try to get messages from thread content directly
                if 'content' in thread and 'messages' in thread['content']:
                    messages = thread['content']['messages']
                else:
                    # Try to load from JSON file if not in thread data
                    thread_dir = os.path.join(thread_storage.STORAGE_DIR, thread_id)
                    thread_json = os.path.join(thread_dir, f"{thread_id}.json")
                    
                    if os.path.exists(thread_json):
                        with open(thread_json, 'r', encoding='utf-8') as f:
                            thread_content = json.load(f)
                            messages = thread_content.get('messages', [])
                    else:
                        add_analysis_log(f"Error: No messages found for thread {thread_id}", "error")
                        continue
                
                # Call Claude to analyze this thread
                result = analyze_single_thread(api_key, messages)
                
                # Debug log the result structure
                if result:
                    add_analysis_log(f"Result for thread {thread_id} has keys: {list(result.keys())}", "debug")
                    if 'key_insights' in result:
                        if isinstance(result['key_insights'], list):
                            # Check the structure of the first few key_insights to help debugging
                            for idx, insight in enumerate(result['key_insights'][:3]):
                                add_analysis_log(f"key_insights[{idx}] type: {type(insight)}, structure: {insight}", "debug")
                        else:
                            add_analysis_log(f"key_insights is not a list: {type(result['key_insights'])}", "debug")
                
                if result and 'error' not in result:
                    try:
                        # Add thread ID to result
                        result['thread_id'] = thread_id
                        
                        # Deep copy the result before modifying to prevent unexpected side effects
                        thread_result = copy.deepcopy(result)
                        thread_results.append(thread_result)
                        
                        # No need to process evidence map if we're encountering errors
                        # Just track the thread as analyzed
                        analyzed_thread_ids.append(thread_id)
                        state['analyzed_threads'] += 1
                        add_analysis_log(f"Completed analysis of thread {thread_id} ({i+1}/{num_threads})", "info")
                    except KeyError as ke:
                        add_analysis_log(f"KeyError processing thread {thread_id}: {str(ke)}", "error")
                        add_analysis_log(f"Keys available in result: {list(result.keys())}", "debug")
                        # Try to continue despite the error, just add what we have
                        analyzed_thread_ids.append(thread_id)
                        state['analyzed_threads'] += 1
                    except Exception as thread_error:
                        add_analysis_log(f"Error processing thread {thread_id}: {str(thread_error)}", "error")
                        add_analysis_log(traceback.format_exc(), "error")
                else:
                    add_analysis_log(f"Error analyzing thread {thread_id}: {result.get('error', 'Unknown error')}", "error")
            
            except Exception as thread_error:
                add_analysis_log(f"Error processing thread {thread_id}: {str(thread_error)}", "error")
                add_analysis_log(traceback.format_exc(), "error")
                continue
        
        # Mark threads as analyzed in persistent storage
        thread_storage.mark_threads_as_analyzed(analyzed_thread_ids, evidence_map)
        
        # Save thread results to state
        state['thread_results'] = thread_results
        
        # If we have results, summarize them
        if thread_results:
            add_analysis_log(f"Analyzing completed for {len(thread_results)} threads. Generating overall summary...", "info")
            
            # Wrap the summarization in its own try-except to isolate errors
            try:
                combined_results = summarize_and_save_analysis_results(api_key, state['session_id'], state['filename'], thread_results)
                
                if combined_results:
                    state['combined_results'] = combined_results
                    
                    # Save to persistent storage
                    thread_storage.save_analysis_results(
                        combined_results, 
                        state['session_id'], 
                        state['filename'], 
                        analyzed_thread_ids
                    )
                    
                    add_analysis_log("Analysis completed successfully!", "info")
                else:
                    add_analysis_log("Error generating combined results", "error")
            except Exception as summary_error:
                add_analysis_log(f"Error in summarize_and_save_analysis_results: {str(summary_error)}", "error")
                add_analysis_log(traceback.format_exc(), "error")
        else:
            add_analysis_log("No threads were successfully analyzed", "error")
            
        # Update state
        state['is_analyzing'] = False
        state['last_updated'] = datetime.datetime.now()
        
    except Exception as e:
        add_analysis_log(f"Error in background thread analysis: {str(e)}", "error")
        add_analysis_log(traceback.format_exc(), "error")
        state['is_analyzing'] = False
        state['last_updated'] = datetime.datetime.now()

def analyze_single_thread(api_key, messages):
    """Analyze a single thread using Claude API"""
    try:
        # Read thread content
        thread_content = '\n'.join(messages)
            
        # Call Claude API directly since we have the thread content
        result = thread_analyzer.claude_analyzer.analyze_single_thread(thread_content, api_key)
        
        if result:
            # Normalize the result structure to prevent KeyErrors downstream
            try:
                # Normalize key_insights if present
                if 'key_insights' in result:
                    normalized_insights = []
                    for insight in result['key_insights']:
                        if isinstance(insight, str):
                            normalized_insights.append({"insight": insight})
                        elif isinstance(insight, dict):
                            new_insight = {}
                            # Handle different field names
                            if 'insight' in insight:
                                new_insight['insight'] = insight['insight']
                            elif 'key' in insight:
                                new_insight['insight'] = insight['key']
                            else:
                                # Create a fallback from the first field
                                keys = list(insight.keys())
                                if keys:
                                    new_insight['insight'] = f"{keys[0]}: {insight[keys[0]]}"
                                else:
                                    new_insight['insight'] = "Unknown insight"
                            
                            # Copy any other fields
                            for k, v in insight.items():
                                if k not in ['insight', 'key']:
                                    new_insight[k] = v
                            
                            normalized_insights.append(new_insight)
                        else:
                            normalized_insights.append({"insight": str(insight)})
                    
                    result['key_insights'] = normalized_insights
                
                # Normalize improvement_areas if present
                if 'improvement_areas' in result:
                    normalized_areas = []
                    for area in result['improvement_areas']:
                        if isinstance(area, str):
                            normalized_areas.append({"area": area})
                        elif isinstance(area, dict):
                            new_area = {}
                            # Handle different field names
                            if 'area' in area:
                                new_area['area'] = area['area']
                            elif 'key' in area:
                                new_area['area'] = area['key']
                            else:
                                # Create a fallback from the first field
                                keys = list(area.keys())
                                if keys:
                                    new_area['area'] = f"{keys[0]}: {area[keys[0]]}"
                                else:
                                    new_area['area'] = "Unknown area"
                            
                            # Copy any other fields
                            for k, v in area.items():
                                if k not in ['area', 'key']:
                                    new_area[k] = v
                            
                            normalized_areas.append(new_area)
                        else:
                            normalized_areas.append({"area": str(area)})
                    
                    result['improvement_areas'] = normalized_areas
                
                # Also normalize negative_chats.categories if present
                if 'negative_chats' in result and isinstance(result['negative_chats'], dict) and 'categories' in result['negative_chats']:
                    normalized_categories = []
                    for category in result['negative_chats']['categories']:
                        if isinstance(category, dict) and 'category' in category:
                            cat_name = category['category']
                            normalized_categories.append({"category": cat_name})
                        elif isinstance(category, str):
                            normalized_categories.append({"category": category})
                        else:
                            normalized_categories.append({"category": str(category)})
                    
                    result['negative_chats']['categories'] = normalized_categories
                
                add_analysis_log("Thread analysis and normalization completed successfully")
            except Exception as norm_error:
                add_analysis_log(f"Error normalizing thread analysis data: {str(norm_error)}", "error")
                # Continue with the original result rather than failing
            
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

def summarize_and_save_analysis_results(api_key, session_id, filename, threads):
    
    # For tracking metrics across all threads
    timestamp = datetime.datetime.now().isoformat()
    
    # Create a unique analysis ID based on timestamp
    analysis_id = f"analysis_{int(time.time())}"
    
    # Path for saving the combined results
    combined_path = os.path.join(config.TEMP_FOLDER, session_id, 'analysis', f"{analysis_id}.json")
    
    # Examine each thread to pull out insights, categories, etc.
    categories = {}
    discussions = {}
    response_scores = []
    improvement_areas = {}
    
    # User satisfaction metrics
    satisfaction_scores = []
    unmet_needs = []
    
    # Product effectiveness metrics
    product_strengths = {}
    product_weaknesses = {}
    
    # Key insights from all threads
    key_insights = {}
    
    # Problem categories for analysis
    problem_categories = {}
    
    # Good and bad examples
    good_examples = []
    poor_examples = []
    
    # Thread metadata
    thread_metadata = []
    thread_ids = []
    
    add_analysis_log(f"Generating analysis summary from {len(threads)} threads", "info")
    
    # Load existing analysis if available, to merge with new insights
    existing_combined_results = None
    
    # Track if we have any real analysis data from Claude
    has_real_analysis = False
    
    if os.path.exists(combined_path):
        # Load existing analysis
        try:
            with open(combined_path, 'r', encoding='utf-8') as f:
                existing_combined_results = json.load(f)
                add_analysis_log("Loaded existing analysis results to merge with", "info")
        except Exception as e:
            add_analysis_log(f"Error loading existing analysis: {str(e)}", "error")
    
    # Process each thread's analysis result
    for thread_data in threads:
        if not thread_data or 'error' in thread_data:
            continue
        
        thread_id = thread_data.get('thread_id', 'unknown')
        thread_ids.append(thread_id)
        
        # Debug log the thread_data structure to help with troubleshooting
        add_analysis_log(f"Processing thread {thread_id} with keys: {list(thread_data.keys())}", "debug")
        
        # Check if this is a real analysis (not mock data)
        mock_analysis = False
        if thread_data.get('categories') and thread_data.get('categories') == [
            "Music Production Assistance",
            "Songwriting Help",
            "Music Theory Questions",
            "Licensing & Copyright",
            "Music Business",
            "Genre Exploration"
        ]:
            add_analysis_log(f"Thread {thread_id} appears to use mock data", "warning")
            mock_analysis = True
        else:
            has_real_analysis = True
            add_analysis_log(f"Thread {thread_id} has real Claude analysis data", "info")
        
        # Only process non-mock data for key insights
        if not mock_analysis:
            # Track thread metadata
            meta = {
                'thread_id': thread_id,
                'message_count': thread_data.get('message_count', 0),
                'topic': thread_data.get('main_topic', 'Unknown topic'),
                'sentiment': thread_data.get('sentiment', 'neutral'),
                'key_points': thread_data.get('key_points', []),
                'tags': thread_data.get('tags', [])
            }
            thread_metadata.append(meta)
            
            # Extract categories
            try:
                if 'categories' in thread_data and thread_data['categories']:
                    for category in thread_data['categories']:
                        if isinstance(category, str):
                            cat_name = category
                        elif isinstance(category, dict) and 'name' in category:
                            cat_name = category['name']
                        else:
                            continue
                            
                        categories[cat_name] = categories.get(cat_name, 0) + 1
            except Exception as e:
                add_analysis_log(f"Error processing categories for thread {thread_id}: {str(e)}", "error")
            
            # Extract discussions/topics
            try:
                if 'top_discussions' in thread_data and thread_data['top_discussions']:
                    for discussion in thread_data['top_discussions']:
                        if isinstance(discussion, dict) and 'topic' in discussion:
                            topic = discussion['topic']
                            discussions[topic] = discussions.get(topic, 0) + 1
            except Exception as e:
                add_analysis_log(f"Error processing discussions for thread {thread_id}: {str(e)}", "error")
            
            # Extract response quality scores
            try:
                if 'response_quality' in thread_data and 'average_score' in thread_data['response_quality']:
                    score = thread_data['response_quality']['average_score']
                    if isinstance(score, (int, float)) and 0 <= score <= 10:
                        response_scores.append(score)
            except Exception as e:
                add_analysis_log(f"Error processing response scores for thread {thread_id}: {str(e)}", "error")
            
            # Extract good and poor examples
            try:
                if 'response_quality' in thread_data:
                    if 'good_examples' in thread_data['response_quality']:
                        for example in thread_data['response_quality']['good_examples']:
                            if isinstance(example, dict) and 'context' in example:
                                good_examples.append(example)
                    
                    if 'poor_examples' in thread_data['response_quality']:
                        for example in thread_data['response_quality']['poor_examples']:
                            if isinstance(example, dict) and 'context' in example:
                                poor_examples.append(example)
            except Exception as e:
                add_analysis_log(f"Error processing examples for thread {thread_id}: {str(e)}", "error")
            
            # Extract improvement areas
            try:
                if 'improvement_areas' in thread_data:
                    add_analysis_log(f"Processing improvement_areas: {thread_data['improvement_areas'][:100]}...", "debug")
                    for area in thread_data['improvement_areas']:
                        area_name = None
                        if isinstance(area, str):
                            area_name = area
                        elif isinstance(area, dict):
                            if 'area' in area:
                                area_name = area['area']
                            elif 'key' in area:
                                area_name = area['key']
                            elif len(area) > 0:
                                # Fallback to first key/value
                                key = list(area.keys())[0]
                                area_name = f"{key}: {area[key]}"
                        
                        if area_name:
                            improvement_areas[area_name] = improvement_areas.get(area_name, 0) + 1
            except Exception as e:
                add_analysis_log(f"Error processing improvement areas for thread {thread_id}: {str(e)}", "error")
            
            # Extract user satisfaction
            try:
                if 'user_satisfaction' in thread_data:
                    if 'score' in thread_data['user_satisfaction']:
                        score = thread_data['user_satisfaction']['score']
                        if isinstance(score, (int, float)) and 0 <= score <= 10:
                            satisfaction_scores.append(score)
                    
                    if 'unmet_needs' in thread_data['user_satisfaction']:
                        for need in thread_data['user_satisfaction']['unmet_needs']:
                            if isinstance(need, dict) and 'need' in need:
                                unmet_needs.append(need)
            except Exception as e:
                add_analysis_log(f"Error processing user satisfaction for thread {thread_id}: {str(e)}", "error")
            
            # Extract product effectiveness
            try:
                if 'product_effectiveness' in thread_data and isinstance(thread_data['product_effectiveness'], dict):
                    if 'strengths' in thread_data['product_effectiveness']:
                        for strength in thread_data['product_effectiveness']['strengths']:
                            if isinstance(strength, str):
                                product_strengths[strength] = product_strengths.get(strength, 0) + 1
                            elif isinstance(strength, dict) and 'strength' in strength:
                                product_strengths[strength['strength']] = product_strengths.get(strength['strength'], 0) + 1
                    
                    if 'weaknesses' in thread_data['product_effectiveness']:
                        for weakness in thread_data['product_effectiveness']['weaknesses']:
                            if isinstance(weakness, str):
                                product_weaknesses[weakness] = product_weaknesses.get(weakness, 0) + 1
                            elif isinstance(weakness, dict) and 'weakness' in weakness:
                                product_weaknesses[weakness['weakness']] = product_weaknesses.get(weakness['weakness'], 0) + 1
            except Exception as e:
                add_analysis_log(f"Error processing product effectiveness for thread {thread_id}: {str(e)}", "error")
            
            # Extract key insights
            try:
                if 'key_insights' in thread_data:
                    add_analysis_log(f"Processing key_insights type: {type(thread_data['key_insights'])}", "debug")
                    if isinstance(thread_data['key_insights'], list):
                        for insight in thread_data['key_insights']:
                            insight_text = None
                            if isinstance(insight, str):
                                insight_text = insight
                            elif isinstance(insight, dict):
                                # Try multiple possible field names
                                for field in ['insight', 'key', 'description', 'title', 'text']:
                                    if field in insight:
                                        insight_text = insight[field]
                                        break
                                
                                # If still no insight text, use the first available field
                                if not insight_text and len(insight) > 0:
                                    key = list(insight.keys())[0]
                                    insight_text = f"{key}: {insight[key]}"
                            
                            if insight_text:
                                key_insights[insight_text] = key_insights.get(insight_text, 0) + 1
                    else:
                        add_analysis_log(f"key_insights is not a list: {thread_data['key_insights']}", "warning")
            except Exception as e:
                add_analysis_log(f"Error processing key insights for thread {thread_id}: {str(e)}", "error")
                add_analysis_log(traceback.format_exc(), "error")
            
            # Extract problem categories
            try:
                if 'negative_chats' in thread_data and 'categories' in thread_data['negative_chats']:
                    for category in thread_data['negative_chats']['categories']:
                        if isinstance(category, dict) and 'category' in category:
                            cat_name = category['category']
                            problem_categories[cat_name] = problem_categories.get(cat_name, 0) + 1
            except Exception as e:
                add_analysis_log(f"Error processing negative chat categories for thread {thread_id}: {str(e)}", "error")
    
    # If we don't have any real analysis data, warn about it
    if not has_real_analysis:
        add_analysis_log("WARNING: No real Claude analysis data found. Only mock data was processed.", "warning")
    
    # Merge with existing insights if available
    if existing_combined_results and 'results' in existing_combined_results:
        existing_results = existing_combined_results['results']
        
        # Merge categories
        if 'categories' in existing_results:
            for cat, count in existing_results['categories'].items():
                categories[cat] = categories.get(cat, 0) + count
        
        # Merge discussions
        if 'discussions' in existing_results:
            for topic, count in existing_results['discussions'].items():
                discussions[topic] = discussions.get(topic, 0) + count
        
        # Merge improvement areas
        if 'improvement_areas' in existing_results:
            for area, count in existing_results['improvement_areas'].items():
                improvement_areas[area] = improvement_areas.get(area, 0) + count
        
        # Merge product strengths
        if 'product_strengths' in existing_results:
            for strength, count in existing_results['product_strengths'].items():
                product_strengths[strength] = product_strengths.get(strength, 0) + count
        
        # Merge product weaknesses
        if 'product_weaknesses' in existing_results:
            for weakness, count in existing_results['product_weaknesses'].items():
                product_weaknesses[weakness] = product_weaknesses.get(weakness, 0) + count
        
        # Merge key insights
        if 'key_insights' in existing_results:
            for insight, count in existing_results['key_insights'].items():
                key_insights[insight] = key_insights.get(insight, 0) + count
        
        # Merge problem categories
        if 'problem_categories' in existing_results:
            for cat, count in existing_results['problem_categories'].items():
                problem_categories[cat] = problem_categories.get(cat, 0) + count
                
        # Add previous examples
        if 'good_examples' in existing_results:
            good_examples.extend(existing_results['good_examples'])
            
        if 'poor_examples' in existing_results:
            poor_examples.extend(existing_results['poor_examples'])
            
        if 'unmet_needs' in existing_results:
            unmet_needs.extend(existing_results['unmet_needs'])
    
    # Calculate average scores
    avg_response_quality = sum(response_scores) / len(response_scores) if response_scores else 0
    avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
    
    # Convert dictionaries to sorted lists
    categories_list = [{"name": k, "count": v} for k, v in categories.items()]
    categories_list.sort(key=lambda x: x['count'], reverse=True)
    
    discussions_list = [{"topic": k, "count": v} for k, v in discussions.items()]
    discussions_list.sort(key=lambda x: x['count'], reverse=True)
    
    improvement_areas_list = [{"area": k, "count": v} for k, v in improvement_areas.items()]
    improvement_areas_list.sort(key=lambda x: x['count'], reverse=True)
    
    product_strengths_list = [{"strength": k, "count": v} for k, v in product_strengths.items()]
    product_strengths_list.sort(key=lambda x: x['count'], reverse=True)
    
    product_weaknesses_list = [{"weakness": k, "count": v} for k, v in product_weaknesses.items()]
    product_weaknesses_list.sort(key=lambda x: x['count'], reverse=True)
    
    key_insights_list = [{"insight": k, "count": v} for k, v in key_insights.items()]
    key_insights_list.sort(key=lambda x: x['count'], reverse=True)
    
    problem_categories_list = [{"category": k, "count": v} for k, v in problem_categories.items()]
    problem_categories_list.sort(key=lambda x: x['count'], reverse=True)
    
    # Assemble final result
    combined_results = {
        "metadata": {
            "id": analysis_id,
            "timestamp": int(time.time()),
            "date": timestamp,
            "session_id": session_id,
            "filename": filename,
            "thread_count": len(threads),
            "thread_ids": thread_ids
        },
        "results": {
            "timestamp": timestamp,
            "session_id": session_id,
            "threads_analyzed": len(threads),
            "threads": thread_metadata,
            "categories": categories_list,
            "discussions": discussions_list,
            "response_quality": {
                "average_score": avg_response_quality,
                "good_examples": good_examples[:5],  # Limit examples
                "poor_examples": poor_examples[:5]
            },
            "improvement_areas": improvement_areas_list,
            "user_satisfaction": {
                "average_score": avg_satisfaction,
                "unmet_needs": unmet_needs[:10]  # Limit needs
            },
            "product_strengths": product_strengths_list,
            "product_weaknesses": product_weaknesses_list,
            "key_insights": key_insights_list,
            "problem_categories": problem_categories_list,
            "response_scores": response_scores,
            "satisfaction_scores": satisfaction_scores,
            # Include any insights from evidence map
            "insights": []
        }
    }
    
    add_analysis_log(f"Analysis summary generated with {len(thread_metadata)} threads", "info")
    
    # Save combined results
    try:
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2)
        add_analysis_log(f"Saved combined analysis results to {combined_path}", "info")
    except Exception as e:
        add_analysis_log(f"Error saving combined results: {str(e)}", "error")
    
    return combined_results
