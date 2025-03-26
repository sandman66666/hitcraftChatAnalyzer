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
        add_analysis_log(f"Starting background analysis of {len(thread_data)} threads", "info")
        
        # Process threads one by one
        thread_results = []
        evidence_map = {}
        analyzed_thread_ids = []
        
        for i, thread in enumerate(thread_data):
            thread_id = thread['id']
            
            try:
                # Update state
                state['current_thread'] = i + 1
                state['last_updated'] = datetime.datetime.now()
                
                add_analysis_log(f"Analyzing thread {i+1}/{len(thread_data)}: {thread_id}", "info")
                
                # Format thread messages for analysis
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
                
                if result and 'error' not in result:
                    # Add thread ID to result
                    result['thread_id'] = thread_id
                    thread_results.append(result)
                    
                    # Map insights to this thread for evidence tracking
                    # Update to use the correct field names from Claude response
                    if 'improvement_areas' in result:
                        for area in result['improvement_areas']:
                            if isinstance(area, dict) and 'area' in area:
                                key = f"improvement_areas:{area['area']}"
                            else:
                                key = f"improvement_areas:{area}"
                            if key not in evidence_map:
                                evidence_map[key] = []
                            evidence_map[key].append(thread_id)
                    
                    if 'key_insights' in result:
                        for insight in result['key_insights']:
                            if isinstance(insight, dict) and 'insight' in insight:
                                key = f"key_insights:{insight['insight']}"
                            else:
                                key = f"key_insights:{insight}"
                            if key not in evidence_map:
                                evidence_map[key] = []
                            evidence_map[key].append(thread_id)
                    
                    if 'product_effectiveness' in result and isinstance(result['product_effectiveness'], dict):
                        if 'strengths' in result['product_effectiveness']:
                            for strength in result['product_effectiveness']['strengths']:
                                key = f"strengths:{strength}"
                                if key not in evidence_map:
                                    evidence_map[key] = []
                                evidence_map[key].append(thread_id)
                        
                        if 'weaknesses' in result['product_effectiveness']:
                            for weakness in result['product_effectiveness']['weaknesses']:
                                key = f"weaknesses:{weakness}"
                                if key not in evidence_map:
                                    evidence_map[key] = []
                                evidence_map[key].append(thread_id)
                    
                    analyzed_thread_ids.append(thread_id)
                    state['analyzed_threads'] += 1
                    
                    # Update evidence map in state
                    state['evidence_map'] = evidence_map
                    
                    add_analysis_log(f"Thread {thread_id} analyzed successfully", "info")
                else:
                    add_analysis_log(f"Error analyzing thread {thread_id}: {result.get('error', 'Unknown error')}", "error")
            
            except Exception as thread_error:
                add_analysis_log(f"Error processing thread {thread_id}: {str(thread_error)}", "error")
                continue
        
        # Mark threads as analyzed in persistent storage
        thread_storage.mark_threads_as_analyzed(analyzed_thread_ids, evidence_map)
        
        # Save thread results to state
        state['thread_results'] = thread_results
        
        # If we have results, summarize them
        if thread_results:
            add_analysis_log(f"Analyzing completed for {len(thread_results)} threads. Generating overall summary...", "info")
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
        
        # Path to combined analysis file
        combined_path = os.path.join(analysis_dir, "combined_analysis.json")
        
        # Initialize with default structure
        combined_data = {
            "filename": filename,
            "thread_count": len(thread_results),
            "date": datetime.datetime.now().isoformat(),
            "thread_categories": {},
            "thread_discussions": {},
            "key_insights": [],
            "improvement_areas": [],
            "negative_chats": {"categories": []},
            "response_quality": {
                "average_score": 0,
                "good_examples": [],
                "poor_examples": []
            }
        }
        
        # If file exists, load previous analysis to merge with new results
        if os.path.exists(combined_path):
            try:
                with open(combined_path, 'r') as f:
                    existing_data = json.load(f)
                    
                # Update thread count
                if "thread_count" in existing_data:
                    combined_data["thread_count"] += existing_data.get("thread_count", 0)
                
                # Merge thread categories and discussions
                if "thread_categories" in existing_data:
                    for category, count in existing_data["thread_categories"].items():
                        combined_data["thread_categories"][category] = count
                elif "top_categories" in existing_data:
                    # Convert back from list to dict for easier merging
                    for cat_item in existing_data["top_categories"]:
                        if isinstance(cat_item, dict) and "category" in cat_item:
                            combined_data["thread_categories"][cat_item["category"]] = cat_item.get("count", 1)
                
                if "thread_discussions" in existing_data:
                    for topic, count in existing_data["thread_discussions"].items():
                        combined_data["thread_discussions"][topic] = count
                elif "top_discussions" in existing_data:
                    # Convert back from list to dict for easier merging
                    for disc_item in existing_data["top_discussions"]:
                        if isinstance(disc_item, dict) and "topic" in disc_item:
                            combined_data["thread_discussions"][disc_item["topic"]] = disc_item.get("count", 1)
                
                # Keep existing insights, improvement areas, negative chats
                if "key_insights" in existing_data and existing_data["key_insights"]:
                    combined_data["key_insights"] = existing_data["key_insights"]
                
                if "improvement_areas" in existing_data and existing_data["improvement_areas"]:
                    combined_data["improvement_areas"] = existing_data["improvement_areas"]
                
                if "negative_chats" in existing_data and existing_data["negative_chats"]:
                    combined_data["negative_chats"] = existing_data["negative_chats"]
                
                # Keep good quality examples
                if "response_quality" in existing_data and existing_data["response_quality"]:
                    if not isinstance(combined_data["response_quality"], dict):
                        combined_data["response_quality"] = {}
                    
                    if "good_examples" in existing_data["response_quality"]:
                        combined_data["response_quality"]["good_examples"] = existing_data["response_quality"]["good_examples"]
                    if "poor_examples" in existing_data["response_quality"]:
                        combined_data["response_quality"]["poor_examples"] = existing_data["response_quality"]["poor_examples"]
                    if "average_score" in existing_data["response_quality"]:
                        combined_data["response_quality"]["average_score"] = existing_data["response_quality"]["average_score"]
                
                add_analysis_log("Loaded existing analysis to merge with new results")
            except Exception as e:
                add_analysis_log(f"Error loading existing analysis: {str(e)}. Starting fresh.", "warning")
                
        # Process new thread results
        quality_scores = []
        for result in thread_results:
            # Add categories
            if 'categories' in result:
                for category in result['categories']:
                    if isinstance(category, str):
                        category_name = category
                    elif isinstance(category, dict) and 'category' in category:
                        category_name = category['category']
                    else:
                        continue
                        
                    if category_name in combined_data['thread_categories']:
                        combined_data['thread_categories'][category_name] += 1
                    else:
                        combined_data['thread_categories'][category_name] = 1
            
            # Add discussions
            if 'top_discussions' in result:
                for discussion in result['top_discussions']:
                    if isinstance(discussion, dict):
                        topic = discussion.get('topic', 'Unknown topic')
                        count = discussion.get('count', 1)
                    else:
                        topic = str(discussion)
                        count = 1
                    
                    if topic in combined_data['thread_discussions']:
                        combined_data['thread_discussions'][topic] += count
                    else:
                        combined_data['thread_discussions'][topic] = count
            
            # Add key insights
            if 'key_insights' in result and result['key_insights']:
                for insight in result['key_insights']:
                    # Skip if duplicate
                    if insight in combined_data['key_insights']:
                        continue
                    if isinstance(insight, dict) and insight.get('insight'):
                        is_duplicate = any(
                            isinstance(existing, dict) and 
                            existing.get('insight') == insight.get('insight') 
                            for existing in combined_data['key_insights']
                        )
                        if not is_duplicate:
                            combined_data['key_insights'].append(insight)
                    else:
                        combined_data['key_insights'].append(insight)
            
            # Add improvement areas
            if 'improvement_areas' in result and result['improvement_areas']:
                for area in result['improvement_areas']:
                    # Skip if duplicate
                    if area in combined_data['improvement_areas']:
                        continue
                    if isinstance(area, dict) and area.get('area'):
                        is_duplicate = any(
                            isinstance(existing, dict) and 
                            existing.get('area') == area.get('area') 
                            for existing in combined_data['improvement_areas']
                        )
                        if not is_duplicate:
                            combined_data['improvement_areas'].append(area)
                    else:
                        combined_data['improvement_areas'].append(area)
            
            # Add negative chat categories
            if 'negative_chats' in result and isinstance(result['negative_chats'], dict) and 'categories' in result['negative_chats']:
                for neg_cat in result['negative_chats']['categories']:
                    # Skip if duplicate
                    is_duplicate = False
                    for existing in combined_data['negative_chats']['categories']:
                        if isinstance(neg_cat, dict) and isinstance(existing, dict) and existing.get('category') == neg_cat.get('category'):
                            # Update count
                            existing['count'] = existing.get('count', 0) + neg_cat.get('count', 1)
                            # Add any new examples
                            if 'examples' in neg_cat:
                                if 'examples' not in existing:
                                    existing['examples'] = []
                                for example in neg_cat['examples']:
                                    if example not in existing['examples']:
                                        existing['examples'].append(example)
                            is_duplicate = True
                            break
                            
                    if not is_duplicate:
                        combined_data['negative_chats']['categories'].append(neg_cat)
            
            # Collect quality scores for averaging
            if 'response_quality' in result:
                if isinstance(result['response_quality'], dict) and 'average_score' in result['response_quality']:
                    quality_scores.append(result['response_quality']['average_score'])
                    
                    # Add good examples (without duplicating)
                    if 'good_examples' in result['response_quality']:
                        for example in result['response_quality']['good_examples']:
                            if example not in combined_data['response_quality']['good_examples']:
                                combined_data['response_quality']['good_examples'].append(example)
                    
                    # Add poor examples (without duplicating)
                    if 'poor_examples' in result['response_quality']:
                        for example in result['response_quality']['poor_examples']:
                            if example not in combined_data['response_quality']['poor_examples']:
                                combined_data['response_quality']['poor_examples'].append(example)
        
        # Update average quality score if we have new scores
        if quality_scores:
            # If we already have a score, average it with the new scores
            if combined_data['response_quality']['average_score'] > 0:
                existing_score = combined_data['response_quality']['average_score']
                new_average = (existing_score + sum(quality_scores) / len(quality_scores)) / 2
            else:
                new_average = sum(quality_scores) / len(quality_scores)
            
            combined_data['response_quality']['average_score'] = round(new_average, 1)
        
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
        
        # Limit arrays to reasonable sizes
        combined_data['key_insights'] = combined_data['key_insights'][:20]
        combined_data['improvement_areas'] = combined_data['improvement_areas'][:20]
        combined_data['negative_chats']['categories'] = combined_data['negative_chats']['categories'][:20]
        combined_data['response_quality']['good_examples'] = combined_data['response_quality']['good_examples'][:10]
        combined_data['response_quality']['poor_examples'] = combined_data['response_quality']['poor_examples'][:10]
        
        # Remove working dictionaries
        del combined_data['thread_categories']
        del combined_data['thread_discussions']
        
        # Save the combined analysis
        with open(combined_path, 'w') as f:
            json.dump(combined_data, f, indent=2)
        
        add_analysis_log("Saved combined analysis results with accumulated insights")
        return combined_data
    except Exception as e:
        add_analysis_log(f"Error saving combined analysis: {str(e)}", "error")
        add_analysis_log(traceback.format_exc(), "error")
        return False
