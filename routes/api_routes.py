"""
API routes for HitCraft Chat Analyzer
"""
import os
import json
import glob
import datetime
from flask import Blueprint, request, jsonify, session, send_from_directory
from logging_manager import add_log
from thread_analyzer import filter_results_by_time
import config

# Create Blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/claude-key', methods=['GET'])
def get_claude_key():
    """Return the Claude API key"""
    from dotenv import load_dotenv
    load_dotenv()
    
    claude_key = os.environ.get('CLAUDE_API_KEY', '')
    return jsonify({'key': claude_key})

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
        # Get session information
        session_id = session.get('session_id')
        add_log(f"get_thread_listing - Session ID from session: {session_id}", "info")
        
        if not session_id:
            session_id = request.args.get('session_id')
            add_log(f"get_thread_listing - Session ID from args: {session_id}", "info")
            if not session_id:
                add_log("get_thread_listing - No session ID found", "error")
                return jsonify({'error': 'No session ID provided'}), 400
        
        # Set up session-specific threads directory
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        add_log(f"get_thread_listing - Looking for threads in: {threads_dir}", "info")
        
        if not os.path.exists(threads_dir):
            add_log(f"get_thread_listing - Threads directory not found: {threads_dir}", "error")
            return jsonify({'error': 'No threads found'})
            
        # Check for thread list file first
        thread_list_path = os.path.join(threads_dir, 'thread_list.json')
        add_log(f"get_thread_listing - Thread list path: {thread_list_path}", "info")
        add_log(f"get_thread_listing - Thread list exists: {os.path.exists(thread_list_path)}", "info")
        
        if os.path.exists(thread_list_path):
            with open(thread_list_path, 'r') as f:
                thread_list = json.load(f)
                
            # Sort by timestamp if available
            thread_list.sort(key=lambda x: str(x.get('last_message_time', '')) if isinstance(x.get('last_message_time'), (dict, list)) else x.get('last_message_time', ''), reverse=True)
            return jsonify({'threads': thread_list})
        
        # Fallback: scan directory for thread files
        thread_files = glob.glob(os.path.join(threads_dir, '*.txt'))
        thread_list = []
        
        for thread_file in thread_files:
            thread_id = os.path.basename(thread_file).replace('.txt', '')
            thread_list.append({
                'id': thread_id,
                'message_count': 0,  # Unknown without parsing
                'title': f"Thread {thread_id}"
            })
            
        return jsonify({'threads': thread_list})
        
    except Exception as e:
        add_log(f"Error listing threads: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/get_threads', methods=['GET'])
def get_threads():
    """Direct implementation of thread listing for compatibility with React frontend"""
    try:
        # Get session ID from either session or query parameters
        session_id = session.get('session_id')
        if not session_id:
            session_id = request.args.get('session_id')
            add_log(f"get_threads - Using session_id from args: {session_id}", "info")
        
        add_log(f"get_threads - Session ID: {session_id}", "info")
        
        if not session_id:
            add_log("get_threads - No session ID found", "error")
            return jsonify({'threads': []})  # Return empty list instead of error for better UX
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Set up session directory paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        add_log(f"get_threads - Looking for threads in: {threads_dir}", "info")
        
        # Check if the threads directory exists
        if not os.path.exists(threads_dir):
            add_log(f"get_threads - Threads directory not found: {threads_dir}", "error")
            return jsonify({'threads': [], 'page': page, 'per_page': per_page, 'total': 0, 'total_pages': 0})
        
        # Look for thread list file
        thread_list_path = os.path.join(threads_dir, 'thread_list.json')
        
        if os.path.exists(thread_list_path):
            add_log(f"get_threads - Found thread_list.json", "info")
            with open(thread_list_path, 'r') as f:
                thread_list = json.load(f)
                
            # Safely handle thread sorting
            try:
                thread_list.sort(key=lambda x: str(x.get('last_message_time', '')) if isinstance(x.get('last_message_time'), (dict, list)) else x.get('last_message_time', ''), reverse=True)
            except Exception as e:
                add_log(f"get_threads - Error sorting threads: {str(e)}", "error")
            
            # Calculate pagination
            total = len(thread_list)
            total_pages = (total + per_page - 1) // per_page  # Ceiling division
            
            # Get the requested page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_threads = thread_list[start_idx:end_idx]
            
            add_log(f"get_threads - Returning {len(paginated_threads)} threads (page {page}/{total_pages})", "info")
            return jsonify({
                'threads': paginated_threads,
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            })
        
        # Fallback: Scan directory for thread files
        add_log(f"get_threads - No thread_list.json, scanning for thread files", "info")
        thread_files = glob.glob(os.path.join(threads_dir, '*.txt'))
        thread_list = []
        
        for thread_file in thread_files:
            thread_id = os.path.basename(thread_file).replace('.txt', '')
            thread_list.append({
                'id': thread_id,
                'message_count': 0,
                'title': f"Thread {thread_id}"
            })
        
        # Calculate pagination
        total = len(thread_list)
        total_pages = (total + per_page - 1) // per_page  # Ceiling division
        
        # Get the requested page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_threads = thread_list[start_idx:end_idx]
        
        add_log(f"get_threads - Found {total} thread files, returning page {page}/{total_pages}", "info")
        return jsonify({
            'threads': paginated_threads,
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages
        })
        
    except Exception as e:
        add_log(f"get_threads - Error listing threads: {str(e)}", "error")
        return jsonify({
            'error': str(e), 
            'threads': [],
            'page': 1,
            'per_page': 10,
            'total': 0,
            'total_pages': 0
        })

@api_bp.route('/thread/<thread_id>', methods=['GET'])
def get_thread_content(thread_id):
    """Return the content of a specific thread"""
    try:
        threads_dir = os.path.join(config.THREADS_FOLDER)
        thread_path = os.path.join(threads_dir, f"{thread_id}.json")
        
        # First try JSON format
        if os.path.exists(thread_path):
            with open(thread_path, 'r') as f:
                thread_data = json.load(f)
            return jsonify(thread_data)
            
        # Fall back to text format
        thread_path = os.path.join(threads_dir, f"{thread_id}.txt")
        if not os.path.exists(thread_path):
            return jsonify({'error': 'Thread not found'})
            
        with open(thread_path, 'r') as f:
            content = f.read()
            
        # Parse the text content into a structured format
        messages = []
        current_message = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('USER:'):
                if current_message:
                    messages.append(current_message)
                current_message = {'role': 'user', 'content': line[5:].strip()}
            elif line.startswith('ASSISTANT:'):
                if current_message:
                    messages.append(current_message)
                current_message = {'role': 'assistant', 'content': line[10:].strip()}
            else:
                if current_message:
                    current_message['content'] += ' ' + line
        
        if current_message:
            messages.append(current_message)
            
        return jsonify({'messages': messages})
        
    except Exception as e:
        add_log(f"Error getting thread content: {str(e)}", "error")
        return jsonify({'error': str(e)})

@api_bp.route('/get_thread_content', methods=['GET'])
def get_thread_content_legacy():
    """Legacy endpoint for thread content compatibility"""
    try:
        import json
        
        thread_id = request.args.get('thread_id')
        session_id = session.get('session_id')
        
        if not session_id:
            session_id = request.args.get('session_id')
            add_log(f"get_thread_content_legacy - Using session_id from args: {session_id}", "info")
            
        if not thread_id:
            add_log("get_thread_content_legacy - No thread ID provided", "error")
            return jsonify({'error': 'No thread ID provided'}), 400
        
        add_log(f"get_thread_content_legacy - Getting content for thread {thread_id}, session {session_id}", "info")
        
        # MongoDB ObjectId handling - extract the actual ID if in {"$oid": "XXX"} format
        try:
            if thread_id.startswith('{"$oid":'):
                # Extract the ID from the JSON structure
                oid_obj = json.loads(thread_id)
                cleaned_thread_id = oid_obj.get('$oid')
                add_log(f"get_thread_content_legacy - Extracted OID from JSON: {cleaned_thread_id}", "info")
            else:
                cleaned_thread_id = thread_id
        except Exception as e:
            add_log(f"get_thread_content_legacy - Error cleaning thread ID: {str(e)}", "error")
            cleaned_thread_id = thread_id.replace('{', '').replace('}', '').replace('"', '').replace('$oid:', '').strip()
            add_log(f"get_thread_content_legacy - Fallback cleaned ID: {cleaned_thread_id}", "info")
        
        # Set up session directory paths
        session_dir = os.path.join(config.TEMP_FOLDER, session_id)
        threads_dir = os.path.join(session_dir, 'threads')
        
        # Check for thread file - try both formats
        thread_file = os.path.join(threads_dir, f"{cleaned_thread_id}.txt")
        original_thread_file = os.path.join(threads_dir, f"{thread_id}.txt")
        
        # Try the cleaned ID first, then the original if that fails
        if os.path.exists(thread_file):
            add_log(f"get_thread_content_legacy - Found thread file with cleaned ID", "info")
            thread_path = thread_file
        elif os.path.exists(original_thread_file):
            add_log(f"get_thread_content_legacy - Found thread file with original ID", "info")
            thread_path = original_thread_file
        else:
            # If neither exists, try to find a file that contains the cleaned ID as part of the name
            matching_files = glob.glob(os.path.join(threads_dir, f"*{cleaned_thread_id}*.txt"))
            if matching_files:
                thread_path = matching_files[0]
                add_log(f"get_thread_content_legacy - Found matching thread file: {os.path.basename(thread_path)}", "info")
            else:
                # Try JSON files as well
                json_file = os.path.join(threads_dir, f"{cleaned_thread_id}.json")
                original_json_file = os.path.join(threads_dir, f"{thread_id}.json")
                
                if os.path.exists(json_file):
                    add_log(f"get_thread_content_legacy - Found .json file with cleaned ID", "info")
                    thread_path = json_file
                elif os.path.exists(original_json_file):
                    add_log(f"get_thread_content_legacy - Found .json file with original ID", "info")
                    thread_path = original_json_file
                else:
                    # Last resort: Check for MongoDB ObjectId-style JSON files
                    matching_json_files = glob.glob(os.path.join(threads_dir, f'*"$oid": "{cleaned_thread_id}"*.json'))
                    if matching_json_files:
                        thread_path = matching_json_files[0]
                        add_log(f"get_thread_content_legacy - Found MongoDB ObjectId JSON file: {os.path.basename(thread_path)}", "info")
                    else:
                        add_log(f"get_thread_content_legacy - Thread file not found for any ID variant", "error")
                        return jsonify({'error': 'Thread not found'}), 404
        
        # Read thread content
        try:
            with open(thread_path, 'r') as f:
                thread_content = f.read()
                add_log(f"get_thread_content_legacy - Read thread content, length: {len(thread_content)}", "info")
        except Exception as e:
            add_log(f"get_thread_content_legacy - Error reading thread file: {str(e)}", "error")
            return jsonify({'error': f'Error reading thread file: {str(e)}'}), 500
        
        # Parse messages
        messages = []
        # Try several approaches to parse the content
        try:
            # First attempt: Try to parse as standard JSON
            messages = json.loads(thread_content)
            add_log(f"get_thread_content_legacy - Successfully parsed thread content with {len(messages)} messages", "info")
        except json.JSONDecodeError as e:
            add_log(f"get_thread_content_legacy - Error parsing thread content as JSON: {str(e)}", "error")
            
            # Second attempt: Try with MongoDB ObjectId format
            try:
                # MongoDB ObjectIds can cause parsing issues, try replacing them
                cleaned_content = thread_content.replace('{"$oid":', '{"oid":')
                messages = json.loads(cleaned_content)
                add_log(f"get_thread_content_legacy - Successfully parsed thread content after ObjectId cleanup", "info")
            except json.JSONDecodeError:
                # Third attempt: Try with additional JSON cleanup
                try:
                    # Additional cleanup for common JSON issues
                    more_cleaned_content = thread_content.replace("'", '"').replace("True", "true").replace("False", "false").replace("None", "null")
                    messages = json.loads(more_cleaned_content)
                    add_log(f"get_thread_content_legacy - Successfully parsed thread content after additional cleanup", "info")
                except json.JSONDecodeError:
                    # Fourth attempt: Check if it's a JSON format with a surrounding structure
                    try:
                        # Some files might have the messages inside a container object
                        container = json.loads(f'{{"messages":{thread_content}}}')
                        if 'messages' in container and isinstance(container['messages'], list):
                            messages = container['messages']
                            add_log(f"get_thread_content_legacy - Successfully parsed thread content as array within container", "info")
                    except json.JSONDecodeError:
                        # Fallback: If it's not JSON, create a simple array of messages from the content
                        try:
                            # Split by chat patterns
                            if 'USER:' in thread_content and 'ASSISTANT:' in thread_content:
                                # Try to split by USER/ASSISTANT pattern
                                chunks = []
                                current_chunk = ""
                                current_role = None
                                
                                for line in thread_content.split('\n'):
                                    if line.startswith('USER:'):
                                        if current_role:
                                            chunks.append((current_role, current_chunk.strip()))
                                        current_role = 'user'
                                        current_chunk = line[5:].strip()
                                    elif line.startswith('ASSISTANT:'):
                                        if current_role:
                                            chunks.append((current_role, current_chunk.strip()))
                                        current_role = 'assistant'
                                        current_chunk = line[10:].strip()
                                    else:
                                        current_chunk += " " + line.strip()
                                
                                if current_role and current_chunk:
                                    chunks.append((current_role, current_chunk.strip()))
                                    
                                for role, content in chunks:
                                    messages.append({"role": role, "content": content})
                                    
                                add_log(f"get_thread_content_legacy - Created {len(messages)} messages from USER/ASSISTANT format", "info")
                            else:
                                # Default fallback: alternate lines as user/assistant messages
                                lines = thread_content.strip().split("\n")
                                messages = []
                                for i, line in enumerate(lines):
                                    if line.strip():
                                        role = "user" if i % 2 == 0 else "assistant"
                                        messages.append({"role": role, "content": line.strip()})
                                add_log(f"get_thread_content_legacy - Created {len(messages)} messages from alternating lines", "info")
                        except Exception as fallback_e:
                            add_log(f"get_thread_content_legacy - Fallback parsing also failed: {str(fallback_e)}", "error")
                            return jsonify({
                                'error': 'Error parsing thread content', 
                                'thread_id': thread_id,
                                'cleaned_id': cleaned_thread_id,
                                'file_path': thread_path,
                                'content_preview': thread_content[:200] if thread_content else "Empty content"
                            }), 500
        
        # Get thread metadata if available
        thread_metadata = None
        thread_list_path = os.path.join(threads_dir, 'thread_list.json')
        
        if os.path.exists(thread_list_path):
            try:
                with open(thread_list_path, 'r') as f:
                    thread_list = json.load(f)
                    for thread in thread_list:
                        if str(thread.get('id')) == str(cleaned_thread_id) or str(thread.get('id')) == str(thread_id):
                            thread_metadata = thread
                            break
            except Exception as e:
                add_log(f"get_thread_content_legacy - Error reading thread metadata: {str(e)}", "error")
        
        # Return response with messages formatted correctly for the frontend
        thread_response = {
            'id': cleaned_thread_id,
            'messages': messages
        }
        
        if thread_metadata:
            thread_response.update({
                'title': thread_metadata.get('title'),
                'message_count': thread_metadata.get('message_count'),
            })
        
        add_log(f"get_thread_content_legacy - Returning thread with {len(messages)} messages", "info")
        
        # For debugging
        try:
            # Print the first few messages to logs
            for i, msg in enumerate(messages[:3]):
                add_log(f"get_thread_content_legacy - Message {i}: role={msg.get('role', 'unknown')}, content={msg.get('content', '')[:50]}", "info")
        except Exception as e:
            add_log(f"get_thread_content_legacy - Error printing messages: {str(e)}", "error")
            
        return jsonify(thread_response)
    
    except Exception as e:
        add_log(f"get_thread_content_legacy - Error: {str(e)}", "error")
        return jsonify({'error': str(e)}), 500

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
