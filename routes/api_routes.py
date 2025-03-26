"""
API routes for HitCraft Chat Analyzer
"""
import os
import json
import glob
import datetime
from flask import Blueprint, request, jsonify, session, send_from_directory, g, has_request_context
import logging
from logging_manager import add_log
from thread_analyzer import filter_results_by_time
import config
import thread_storage
import threading
import random
import requests
import traceback
from dotenv import load_dotenv

# Create Blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/claude-key', methods=['GET'])
def get_claude_key():
    """Return the Claude API key"""
    from dotenv import load_dotenv
    load_dotenv()
    
    claude_key = os.environ.get('CLAUDE_API_KEY', '')
    return jsonify({'key': claude_key})

def get_claude_key_no_context():
    """
    Return the Claude API key without requiring Flask application context.
    This is safe to use in background threads.
    """
    load_dotenv()
    return os.environ.get('CLAUDE_API_KEY', '')

@api_bp.route('/dashboard_data', methods=['GET'])
def dashboard_data():
    """Return dashboard data with support for time-based filtering"""
    try:
        # Get time filter parameters
        start_date = request.args.get('start_date') 
        end_date = request.args.get('end_date')
        
        add_log(f"Getting dashboard data with filters - start: {start_date}, end: {end_date}")
        
        # Get the analysis results file
        results_dir = os.path.join(config.RESULTS_FOLDER)
        
        if not os.path.exists(results_dir):
            return jsonify({'error': 'No analysis results found'})
            
        # Find all result files
        result_files = glob.glob(os.path.join(results_dir, '*.json'))
        
        if not result_files:
            return jsonify({'error': 'No analysis results found'})
            
        # Sort by modification time (newest first)
        result_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        newest_file = result_files[0]
        
        with open(newest_file, 'r') as f:
            results = json.load(f)
        
        # Apply time filtering if necessary
        if start_date or end_date:
            filtered_results = filter_results_by_time(results, start_date, end_date)
            return jsonify(filtered_results)
        
        # Otherwise return all results
        return jsonify(results)
        
    except Exception as e:
        add_log(f"Error getting dashboard data: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/list_threads', methods=['GET'])
def get_thread_listing():
    """Return a list of available threads"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # First check if we have a session with threads
        session_id = session.get('session_id')
        if session_id:
            # Try session-specific threads first (newly uploaded)
            session_dir = os.path.join(config.TEMP_FOLDER, session_id)
            threads_dir = os.path.join(session_dir, 'threads')
            
            if os.path.exists(threads_dir):
                # Store newly uploaded threads permanently
                threads_added, total_count = thread_storage.store_threads_permanently(session_id, threads_dir)
                if threads_added > 0:
                    add_log(f"Added {threads_added} new threads to permanent storage")

        # Get all threads from persistent storage with pagination
        result = thread_storage.get_all_threads(page, per_page)
        return jsonify(result)
        
    except Exception as e:
        add_log(f"Error listing threads: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/get_threads', methods=['GET'])
def get_threads():
    """Direct implementation of thread listing for compatibility with React frontend"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # First check if we have a session with threads
        session_id = session.get('session_id')
        if session_id:
            # Check if we have newly uploaded threads
            session_dir = os.path.join(config.TEMP_FOLDER, session_id)
            threads_dir = os.path.join(session_dir, 'threads')
            
            if os.path.exists(threads_dir):
                # Store newly uploaded threads permanently
                threads_added, total_count = thread_storage.store_threads_permanently(session_id, threads_dir)
                if threads_added > 0:
                    add_log(f"Added {threads_added} new threads to permanent storage")
        
        # Get all threads from persistent storage with pagination
        result = thread_storage.get_all_threads(page, per_page)
        add_log(f"Returning {len(result['threads'])} threads (page {page}/{result['total_pages']})")
        return jsonify(result)
        
    except Exception as e:
        add_log(f"Error getting threads: {str(e)}", "error")
        return jsonify({
            'threads': [],
            'page': page,
            'per_page': per_page,
            'total': 0,
            'total_pages': 0
        })

@api_bp.route('/get_thread_content', methods=['GET'])
def get_thread_content():
    """Return the content of a specific thread"""
    try:
        thread_id = request.args.get('thread_id')
        
        if not thread_id:
            return jsonify({'error': 'No thread ID provided'}), 400
            
        # Get thread from persistent storage
        result = thread_storage.get_thread_content(thread_id)
        return jsonify(result)
        
    except Exception as e:
        add_log(f"Error getting thread content: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/thread_content', methods=['GET'])
def get_thread_content_legacy():
    """Legacy endpoint for thread content compatibility"""
    return get_thread_content()

@api_bp.route('/threads', methods=['GET'])
def get_threads_new():
    """New RESTful endpoint for thread listing"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # First check if we have a session with threads
        session_id = request.args.get('session_id') or session.get('session_id')
        if session_id:
            # Check if we have newly uploaded threads
            session_dir = os.path.join(config.TEMP_FOLDER, session_id)
            threads_dir = os.path.join(session_dir, 'threads')
            
            if os.path.exists(threads_dir):
                # Store newly uploaded threads permanently
                threads_added, total_count = thread_storage.store_threads_permanently(session_id, threads_dir)
                if threads_added > 0:
                    add_log(f"Added {threads_added} new threads to permanent storage")
        
        # Get all threads from persistent storage with pagination
        result = thread_storage.get_all_threads(page, per_page)
        add_log(f"Returning {len(result.get('threads', []))} threads (page {page}/{result.get('total_pages', 1)})")
        return jsonify(result)
        
    except Exception as e:
        add_log(f"Error getting threads: {str(e)}", "error")
        return jsonify({
            'threads': [],
            'page': page,
            'per_page': per_page,
            'total': 0,
            'total_pages': 0
        })

@api_bp.route('/thread/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    """Return the content of a specific thread"""
    try:
        session_id = request.args.get('session_id') or session.get('session_id')
        add_log(f"Loading thread content for thread_id: {thread_id}")
        
        # Get thread from storage
        thread_data = thread_storage.get_thread_content(thread_id)
        
        if not thread_data:
            return jsonify({
                'success': False,
                'error': f'Thread {thread_id} not found'
            })
        
        return jsonify({
            'success': True,
            'thread': thread_data
        })
        
    except Exception as e:
        add_log(f"Error getting thread content: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@api_bp.route('/get_results/<filename>', methods=['GET'])
def get_results(filename):
    """Return a specific results file"""
    try:
        return send_from_directory(config.RESULTS_FOLDER, filename)
    except Exception as e:
        add_log(f"Error retrieving results file: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/debug_threads', methods=['GET'])
def debug_threads():
    """Debug endpoint to check available threads"""
    try:
        # Get session ID from either session or query parameters
        session_id = session.get('session_id')
        if not session_id:
            session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                'error': 'No session ID provided',
                'session_cookie': session.items(),
                'args': dict(request.args)
            })
        
        # Check session directory structure
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        
        result = {
            'session_id': session_id,
            'session_dir_exists': os.path.exists(session_dir),
            'threads_dir_exists': os.path.exists(threads_dir),
            'temp_folder': config.TEMP_FOLDER
        }
        
        # Check for thread_list.json
        thread_list_path = os.path.join(threads_dir, 'thread_list.json')
        result['thread_list_exists'] = os.path.exists(thread_list_path)
        
        if result['thread_list_exists']:
            try:
                with open(thread_list_path, 'r') as f:
                    thread_list = json.load(f)
                    result['thread_count'] = len(thread_list)
            except Exception as e:
                result['thread_list_error'] = str(e)
        
        # Check contents of the threads directory
        if result['threads_dir_exists']:
            try:
                thread_files = glob.glob(os.path.join(threads_dir, '*.txt'))
                result['thread_files_count'] = len(thread_files)
                result['thread_files'] = [os.path.basename(f) for f in thread_files[:10]]  # Get first 10 file names
            except Exception as e:
                result['thread_files_error'] = str(e)
        
        return jsonify(result)
    
    except Exception as e:
        add_log(f"Error in debug_threads: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/get_analysis_stats', methods=['GET'])
def get_analysis_stats():
    """Return statistics about analyzed threads"""
    try:
        stats = thread_storage.get_analysis_stats()
        return jsonify(stats)
    except Exception as e:
        add_log(f"Error getting analysis stats: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/analysis_status', methods=['GET'])
def analysis_status():
    """Return the status of thread analysis"""
    try:
        session_id = request.args.get('session_id') or session.get('session_id')
        
        # Get analysis statistics from thread storage
        stats = thread_storage.get_analysis_stats()
        
        # Create response with stats
        return jsonify({
            'success': True,
            'total': stats['total'],
            'analyzed': stats['analyzed'],
            'remaining': stats['unanalyzed'],
            'percentage': stats['percentage']
        })
        
    except Exception as e:
        add_log(f"Error getting analysis status: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/thread_count', methods=['GET'])
def get_thread_count():
    """Return the total number of threads"""
    try:
        session_id = request.args.get('session_id') or session.get('session_id')
        
        # Get thread stats
        stats = thread_storage.get_analysis_stats()
        
        return jsonify({
            'success': True,
            'count': stats['total'],
            'analyzed': stats['analyzed'],
            'unanalyzed': stats['unanalyzed']
        })
        
    except Exception as e:
        add_log(f"Error getting thread count: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0
        }), 500

@api_bp.route('/analyze_threads', methods=['POST'])
def analyze_threads():
    """Analyze threads for insights"""
    try:
        # Get request data
        data = request.get_json() or {}
        session_id = data.get('session_id') or session.get('session_id')
        thread_count = int(data.get('count', 10))
        
        add_log(f"Starting analysis of up to {thread_count} threads")
        
        # Get threads to analyze
        threads = thread_storage.get_unanalyzed_threads(thread_count)
        
        if not threads:
            add_log("No unanalyzed threads found", "warning")
            return jsonify({
                'success': False,
                'message': 'No unanalyzed threads found',
                'analyzed_count': 0
            })
        
        add_log(f"Found {len(threads)} unanalyzed threads for analysis")
        
        # Make a local copy of the threads for background processing
        # to avoid Flask context issues
        thread_data = []
        for thread in threads:
            thread_data.append(thread.copy() if isinstance(thread, dict) else thread)
        
        add_log(f"Found {len(threads)} unanalyzed threads, starting analysis")
        
        # Start analysis in a background thread without relying on Flask's application context
        def run_analysis():
            try:
                # Direct call without Flask context
                analyze_thread_no_context(session_id, thread_data)
            except Exception as e:
                logging.error(f"Thread analysis failed: {str(e)}")
        
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'thread_count': len(threads),
            'message': f'Started analysis of {len(threads)} threads',
            'analyzed_count': len(threads)
        })
        
    except Exception as e:
        add_log(f"Error starting thread analysis: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/get_analysis_results', methods=['GET'])
def get_analysis_results():
    """Return the latest analysis results"""
    try:
        session_id = request.args.get('session_id') or session.get('session_id')
        
        # Get the latest analysis
        analysis_data = thread_storage.get_latest_analysis()
        
        if not analysis_data:
            # Return empty results structure when no analysis exists
            return jsonify({
                'success': True,
                'message': 'No analysis results found',
                'results': {
                    'threads': [],
                    'insights': [],
                    'stats': {
                        'total_threads': 0,
                        'analyzed_threads': 0
                    }
                },
                'metadata': {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'session_id': session_id
                }
            })
        
        # Return the analysis data
        return jsonify({
            'success': True,
            'results': analysis_data.get('results', {}),
            'metadata': analysis_data.get('metadata', {})
        })
        
    except Exception as e:
        add_log(f"Error getting analysis results: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """Return the application logs"""
    try:
        # Create a simple in-memory log storage if it doesn't exist
        if not hasattr(g, 'application_logs'):
            g.application_logs = []
        
        # Return the logs
        return jsonify({
            'success': True,
            'logs': g.application_logs
        })
        
    except Exception as e:
        add_log(f"Error getting logs: {str(e)}", "error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def add_log(message, level="info"):
    """Add a message to the application log"""
    if level == "error":
        logging.error(message)
    elif level == "warning":
        logging.warning(message)
    else:
        logging.info(message)
        
    # Only attempt to store in g if we're in a Flask request context
    try:
        from flask import g, has_request_context
        
        # Only proceed if we're in a request context
        if has_request_context():
            timestamp = datetime.datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'message': message,
                'level': level
            }
            
            # Create logs array if it doesn't exist
            if not hasattr(g, 'application_logs'):
                g.application_logs = []
                
            # Add to in-memory logs (limited to last 100 entries)
            g.application_logs.append(log_entry)
            if len(g.application_logs) > 100:
                g.application_logs = g.application_logs[-100:]
    except Exception as context_error:
        # Just log and continue, don't cause a failure
        logging.debug(f"Could not store log in request context: {str(context_error)}")

def analyze_thread_no_context(session_id, threads):
    """
    Analyze threads outside of Flask context
    This function is designed to run in a background thread
    without relying on Flask's request or app context
    """
    try:
        logging.info(f"Starting analysis batch for {len(threads)} threads")
        
        analyzed_thread_ids = []
        analysis_results = {
            'timestamp': datetime.datetime.now().isoformat(),
            'session_id': session_id,
            'threads_analyzed': len(threads),
            'threads': [],
            'insights': []
        }
        
        # Process each thread
        for i, thread in enumerate(threads):
            thread_id = thread.get('id')
            try:
                # Extract messages from thread
                messages = []
                
                # Handle different thread formats
                if 'messages' in thread:
                    messages = thread['messages']
                elif 'content' in thread:
                    if isinstance(thread['content'], list):
                        messages = thread['content']
                    elif isinstance(thread['content'], str):
                        # Try to parse as JSON
                        try:
                            parsed = json.loads(thread['content'])
                            if isinstance(parsed, list):
                                messages = parsed
                            else:
                                messages = [{'role': 'system', 'content': thread['content']}]
                        except:
                            messages = [{'role': 'system', 'content': thread['content']}]
                
                # Ensure messages is a list of objects with role and content
                parsed_messages = []
                for msg in messages:
                    if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                        parsed_messages.append(msg)
                    else:
                        # Try to determine role from content
                        content = str(msg)
                        role = 'system'
                        
                        if content.upper().startswith('USER:'):
                            role = 'user'
                            content = content[5:].strip()
                        elif content.upper().startswith('ASSISTANT:'):
                            role = 'assistant'
                            content = content[10:].strip()
                            
                        parsed_messages.append({'role': role, 'content': content})
                
                if not parsed_messages:
                    logging.warning(f"No valid messages found in thread {thread_id}")
                    continue
                
                # Perform thread analysis
                thread_analysis = analyze_single_thread(parsed_messages, thread_id)
                
                # Add thread to analyzed list
                analyzed_thread_ids.append(thread_id)
                
                # Add thread analysis to results
                thread_result = {
                    'thread_id': thread_id,
                    'message_count': len(parsed_messages),
                    'topic': thread_analysis.get('topic', 'Unknown topic'),
                    'sentiment': thread_analysis.get('sentiment', 'neutral'),
                    'key_points': thread_analysis.get('key_points', []),
                    'tags': thread_analysis.get('tags', [])
                }
                analysis_results['threads'].append(thread_result)
                
                # Add insights from this thread to overall insights
                if 'insights' in thread_analysis and thread_analysis['insights']:
                    for insight in thread_analysis['insights']:
                        # Check if this insight already exists
                        existing_insight = next((i for i in analysis_results['insights'] 
                                               if i['key'] == insight['key']), None)
                        
                        if existing_insight:
                            # Add this thread as evidence
                            if thread_id not in existing_insight['evidence_threads']:
                                existing_insight['evidence_threads'].append(thread_id)
                                existing_insight['evidence_count'] = len(existing_insight['evidence_threads'])
                        else:
                            # Add new insight
                            new_insight = {
                                'key': insight['key'],
                                'title': insight['title'],
                                'description': insight['description'],
                                'evidence_threads': [thread_id],
                                'evidence_count': 1,
                                'category': insight.get('category', 'general')
                            }
                            analysis_results['insights'].append(new_insight)
                
                logging.info(f"Completed analysis of thread {thread_id} ({i+1}/{len(threads)})")
                
            except Exception as e:
                logging.error(f"Error analyzing thread {thread_id}: {str(e)}")
        
        # Mark threads as analyzed in storage
        if analyzed_thread_ids:
            thread_storage.mark_threads_as_analyzed(analyzed_thread_ids)
            
            # Create evidence map for threads
            evidence_map = {}
            for insight in analysis_results['insights']:
                insight_key = insight['key']
                if insight_key not in evidence_map:
                    evidence_map[insight_key] = []
                evidence_map[insight_key].extend(insight['evidence_threads'])
            
            # Save the analysis results
            thread_storage.save_analysis_results(
                results=analysis_results,
                session_id=session_id,
                analyzed_thread_ids=analyzed_thread_ids
            )
        
        logging.info(f"Completed batch analysis of {len(threads)} threads. Marked {len(analyzed_thread_ids)} as analyzed.")
        
    except Exception as e:
        logging.error(f"Error in thread batch analysis: {str(e)}")

def analyze_single_thread(messages, thread_id):
    """
    Perform analysis on a single thread
    
    Args:
        messages (list): List of message objects with role and content
        thread_id (str): Thread ID
        
    Returns:
        dict: Analysis results for this thread
    """
    try:
        # Extract text content for analysis - handle both string and list content properly
        text_content_parts = []
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role', 'unknown')
            
            # Format with role for better context
            content_with_role = f"{role.upper()}: "
            
            if isinstance(content, list):
                # Handle content that is a list of content blocks
                text_blocks = []
                for block in content:
                    if isinstance(block, dict) and 'text' in block:
                        text_blocks.append(block['text'])
                    elif isinstance(block, str):
                        text_blocks.append(block)
                content_with_role += " ".join(text_blocks)
            elif isinstance(content, str):
                content_with_role += content
            
            text_content_parts.append(content_with_role)
        
        # Join all the text parts together
        text_content = "\n".join(text_content_parts)
        
        # Get the Claude API key using the non-context version
        api_key = get_claude_key_no_context()
        if not api_key:
            logging.error(f"Claude API key not found. Using simulated analysis for thread {thread_id}")
            # Fall back to simulated analysis if no API key
            return _simulated_analysis(text_content, thread_id)
        
        # Create the prompt for Claude
        prompt = f"""
You are analyzing a conversation thread from a chat platform. Your task is to extract useful insights from this conversation.

Here's the conversation:
---
{text_content}
---

Please analyze this conversation and return a JSON object with the following structure:
{{
  "thread_id": "{thread_id}",
  "topic_category": "Determine the primary topic category",
  "user_sentiment": "positive/negative/neutral/mixed",
  "key_points": ["List of 2-4 key points from the conversation"],
  "tags": ["List of 3-5 relevant tags"],
  "insights": [
    {{
      "title": "A clear, concise insight title",
      "description": "A more detailed description of the insight",
      "category": "user experience/product feedback/technical issue/feature request/etc.",
      "supporting_evidence": ["Specific quotes or evidence from the conversation"]
    }}
  ]
}}

Focus on extracting actionable insights about:
1. User satisfaction and pain points
2. Feature requests or product feedback
3. Common issues or confusions
4. Technical problems reported

Format your entire response as a valid JSON object with the structure described above.
"""
        
        # Make the API call to Claude
        logging.info(f"Calling Claude API for thread {thread_id}")
        
        # Claude API headers - using the latest API version for Claude-3 models
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Claude API payload with model and parameters
        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        
        # Make the API request
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60  # Add timeout to prevent hanging
            )
            
            if response.status_code != 200:
                logging.error(f"Claude API error: {response.status_code} - {response.text}")
                # Fall back to simulated analysis if API call fails
                return _simulated_analysis(text_content, thread_id)
        except Exception as e:
            logging.error(f"Claude API request failed: {str(e)}")
            return _simulated_analysis(text_content, thread_id)
        
        # Parse the response
        claude_response = response.json()
        logging.info(f"Claude API response received for thread {thread_id}")
        
        # Extract content from Claude's response
        content = claude_response.get("content", [])
        if not content or len(content) == 0:
            logging.error(f"Empty content in Claude response for thread {thread_id}")
            return _simulated_analysis(text_content, thread_id)
            
        # Extract the JSON from the text blocks
        json_text = ""
        for block in content:
            if block.get("type") == "text":
                json_text += block.get("text", "")
        
        # Parse the JSON response
        try:
            analysis_results = json.loads(json_text)
            logging.info(f"Successfully parsed Claude analysis for thread {thread_id}")
            return analysis_results
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse Claude JSON response: {str(e)}")
            logging.error(f"Raw response: {json_text[:500]}...")
            return _simulated_analysis(text_content, thread_id)
            
    except Exception as e:
        logging.error(f"Error in Claude thread analysis: {str(e)}")
        traceback.print_exc()
        return {
            "thread_id": thread_id,
            "topic": "Unknown",
            "sentiment": "neutral",
            "key_points": [],
            "tags": []
        }

def _simulated_analysis(text_content, thread_id):
    """
    Fallback simulation of analysis for when Claude API is not available
    """
    # Simple keyword-based analysis
    topics = {
        "technical": ["code", "bug", "error", "programming", "function", "api", "database"],
        "support": ["help", "issue", "problem", "ticket", "resolve", "assistance"],
        "feature": ["feature", "enhancement", "improvement", "add", "implement", "suggestion"],
        "general": ["question", "curious", "wondering", "thought", "idea"]
    }
    
    # Determine topic
    topic_scores = {t: 0 for t in topics}
    for topic, keywords in topics.items():
        for keyword in keywords:
            if keyword.lower() in text_content.lower():
                topic_scores[topic] += 1
    
    main_topic = max(topic_scores.items(), key=lambda x: x[1])[0] if any(topic_scores.values()) else "general"
    
    # Generate random tags from the content
    potential_tags = []
    for word in text_content.split():
        if len(word) > 5 and word.isalnum() and random.random() < 0.05:
            potential_tags.append(word.lower())
    
    tags = list(set(potential_tags))[:3]  # Up to 3 unique tags
    
    # Simple sentiment analysis
    positive_words = ["good", "great", "excellent", "helpful", "thanks", "appreciate", "solved"]
    negative_words = ["bad", "issue", "problem", "error", "bug", "wrong", "failed", "broken"]
    
    sentiment_score = 0
    for word in positive_words:
        if word.lower() in text_content.lower():
            sentiment_score += 1
    for word in negative_words:
        if word.lower() in text_content.lower():
            sentiment_score -= 1
            
    sentiment = "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral"
    
    # Extract a few key points (sentences)
    sentences = [s.strip() for s in text_content.replace("\n", ". ").split(".") if s.strip()]
    key_points = []
    for sentence in sentences:
        if len(sentence) > 15 and len(sentence) < 100 and random.random() < 0.2:
            key_points.append(sentence)
    
    # Keep only up to 3 key points
    key_points = key_points[:3]
    
    # Generate a unique insight with 50% probability
    insights = []
    if random.random() < 0.5:
        insight_categories = ["user experience", "product feedback", "technical issue", "feature request"]
        insight_templates = [
            "Users are experiencing issues with {feature}",
            "Multiple users have requested {feature}",
            "There's confusion around how to use {feature}",
            "Performance problems detected in {feature}"
        ]
        
        # Create a synthetic insight
        category = random.choice(insight_categories)
        feature = tags[0] if tags else "this feature"
        insight_key = f"{category.replace(' ', '_')}_{feature}"
        
        template = random.choice(insight_templates)
        title = template.format(feature=feature)
        
        insights.append({
            "key": insight_key,
            "title": title,
            "description": f"Based on analysis of thread {thread_id}, {title.lower()}.",
            "category": category
        })
    
    # Return the analysis results
    return {
        "thread_id": thread_id,
        "topic": main_topic,
        "sentiment": sentiment,
        "key_points": key_points,
        "tags": tags,
        "insights": insights
    }
