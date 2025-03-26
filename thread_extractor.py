"""
Thread extraction functionality for HitCraft Chat Analyzer
"""
import os
import json
import hashlib
import datetime
import re
from logging_manager import add_log
import time_utils

def extract_threads_from_chat_file(filepath, threads_dir):
    """
    Extract conversation threads from a chat file by grouping messages with the same threadId.
    Handles tracking processed message IDs to avoid duplicates.
    """
    try:
        # Load the JSON data from file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create threads directory if it doesn't exist
        os.makedirs(threads_dir, exist_ok=True)
        
        # Check if data is already a list or has a messages key
        if isinstance(data, list):
            messages = data
        else:
            # Get the messages array from the JSON
            messages = data.get('messages', [])
            
        if not messages:
            add_log(f"No messages found in file: {filepath}", "warning")
            return 0, 0, []
            
        add_log(f"Found {len(messages)} messages in chat file")
        
        # Track processed message IDs to avoid duplicates
        processed_ids_file = os.path.join(os.path.dirname(threads_dir), 'processed_messages.json')
        processed_ids = set()
        
        # Check if we have previously processed message IDs
        if os.path.exists(processed_ids_file):
            try:
                with open(processed_ids_file, 'r') as f:
                    processed_ids = set(json.load(f))
                add_log(f"Loaded {len(processed_ids)} previously processed message IDs")
            except Exception as e:
                add_log(f"Error loading processed message IDs: {str(e)}", "warning")
        
        # Group messages by threadId
        threads = {}
        file_path_hash = hashlib.md5(filepath.encode()).hexdigest()
        
        # Track message IDs in this file to avoid future duplicates
        this_file_msg_ids = set()
        new_msg_count = 0
        
        # Process each message
        for message in messages:
            msg_id = message.get('id')
            
            # Skip if this message was already processed
            if msg_id and msg_id in processed_ids:
                continue
                
            # Get thread ID, skip if not present
            thread_id = message.get('threadId')
            if not thread_id:
                continue
                
            # Ensure thread_id is hashable (convert dict to string if needed)
            if isinstance(thread_id, dict):
                thread_id = json.dumps(thread_id, sort_keys=True)
            elif not isinstance(thread_id, (str, int)):
                thread_id = str(thread_id)
                
            # Add timestamp metadata to the message if not present
            if 'createdAt' not in message and 'timestamp' not in message:
                # Try to extract timestamp from content if in standard format
                content = message.get('content', '')
                timestamp_match = re.search(r'\[([\d\-: ]+)\]', content)
                if timestamp_match:
                    message['timestamp'] = timestamp_match.group(1)
                else:
                    # Use current time if no timestamp found
                    message['timestamp'] = datetime.datetime.now().isoformat()
            
            # Initialize thread if it doesn't exist
            if thread_id not in threads:
                threads[thread_id] = []
            
            # Add message to thread
            threads[thread_id].append(message)
            
            # Track that we've processed this message
            if msg_id:
                processed_ids.add(msg_id)
                this_file_msg_ids.add(msg_id)
                new_msg_count += 1
        
        add_log(f"Extracted {len(threads)} threads with {new_msg_count} new messages")
        
        # Sort messages in each thread by timestamp
        for thread_id, messages in threads.items():
            try:
                def get_sortable_timestamp(x):
                    # Try to get createdAt first
                    timestamp = x.get('createdAt')
                    if timestamp is None:
                        timestamp = x.get('timestamp', '')
                    
                    # If timestamp is a dict or non-comparable type, convert to string
                    if not isinstance(timestamp, (str, int, float)):
                        timestamp = str(timestamp)
                    
                    # Convert all timestamps to strings for consistent comparison
                    if isinstance(timestamp, (int, float)):
                        timestamp = str(timestamp)
                        
                    return timestamp
                    
                messages.sort(key=get_sortable_timestamp)
            except Exception as e:
                add_log(f"Error sorting messages for thread {thread_id}: {str(e)}", "warning")
                # Continue without sorting if there's an error
        
        # Save each thread to a file
        thread_list = []
        
        for thread_id, messages in threads.items():
            if not messages:
                continue
                
            # Calculate first and last message times for metadata
            first_msg_time = None
            last_msg_time = None
            
            # Get first message time
            first_msg = messages[0]
            if 'createdAt' in first_msg:
                first_msg_time = first_msg['createdAt']
            elif 'timestamp' in first_msg:
                first_msg_time = first_msg['timestamp']
                
            # Get last message time
            last_msg = messages[-1]  
            if 'createdAt' in last_msg:
                last_msg_time = last_msg['createdAt']
            elif 'timestamp' in last_msg:
                last_msg_time = last_msg['timestamp']
                
            # Format thread_id for filename (ensure it's valid)
            safe_thread_id = sanitize_thread_id(thread_id)
            
            # Save thread as JSON (preserves all message data)
            thread_json_path = os.path.join(threads_dir, f"{safe_thread_id}.json")
            thread_data = {
                'thread_id': thread_id,
                'messages': messages,
                'first_message_time': first_msg_time,
                'last_message_time': last_msg_time,
                'message_count': len(messages)
            }
            
            with open(thread_json_path, 'w', encoding='utf-8') as f:
                json.dump(thread_data, f, indent=2)
                
            # Save as text for easier human reading
            thread_text_path = os.path.join(threads_dir, f"{safe_thread_id}.txt")
            with open(thread_text_path, 'w', encoding='utf-8') as f:
                for msg in messages:
                    role = msg.get('role', 'UNKNOWN')
                    content = msg.get('content', '')
                    
                    # Handle content that might be a list
                    if isinstance(content, list):
                        # Join list items into a single string
                        content = ' '.join([str(item) for item in content])
                    
                    if role.lower() == 'user':
                        f.write(f"USER: {content}\n\n")
                    elif role.lower() == 'assistant':
                        f.write(f"ASSISTANT: {content}\n\n")
                    else:
                        f.write(f"{role.upper()}: {content}\n\n")
            
            # Get preview content for thread list
            preview_content = messages[0].get('content', '')
            if isinstance(preview_content, list):
                preview_content = ' '.join([str(item) for item in preview_content])
            preview = preview_content[:100] + '...' if preview_content else 'No content'
            
            # Add thread metadata to list
            thread_list.append({
                'id': safe_thread_id,
                'message_count': len(messages),
                'first_message_time': first_msg_time,
                'last_message_time': last_msg_time,
                'preview': preview
            })
        
        # Save thread list for UI browsing
        thread_list_path = os.path.join(os.path.dirname(threads_dir), 'thread_list.json')
        
        # If thread list already exists, merge with it
        if os.path.exists(thread_list_path):
            try:
                with open(thread_list_path, 'r') as f:
                    existing_thread_list = json.load(f)
                    
                # Create a set of existing thread IDs
                existing_thread_ids = {thread.get('id') for thread in existing_thread_list}
                
                # Only add threads that don't already exist
                for thread in thread_list:
                    if thread.get('id') not in existing_thread_ids:
                        existing_thread_list.append(thread)
                        
                thread_list = existing_thread_list
                
            except Exception as e:
                add_log(f"Error merging thread lists: {str(e)}", "warning")
                # Continue with just the new thread list if there's an error
        
        # Sort thread list by last message time
        thread_list.sort(key=lambda x: str(x.get('last_message_time', '')) if isinstance(x.get('last_message_time'), (dict, list)) else x.get('last_message_time', ''), reverse=True)
        
        with open(thread_list_path, 'w') as f:
            json.dump(thread_list, f, indent=2)
            
        # Save the updated processed message IDs
        with open(processed_ids_file, 'w') as f:
            json.dump(list(processed_ids), f)
            
        return len(threads), new_msg_count, thread_list
        
    except Exception as e:
        add_log(f"Error in extract_threads_from_chat_file: {str(e)}", "error")
        import traceback
        add_log(traceback.format_exc(), "error")
        raise

def sanitize_thread_id(thread_id):
    """
    Sanitizes a thread ID to make it safe for filenames.
    Handles MongoDB ObjectId format {"$oid": "xxx"} by extracting the ID.
    """
    if isinstance(thread_id, dict) and '$oid' in thread_id:
        return thread_id['$oid']
    
    if isinstance(thread_id, str):
        # Try to parse as JSON if it looks like a MongoDB ObjectId
        if thread_id.startswith('{"$oid":'):
            try:
                import json
                obj = json.loads(thread_id)
                if '$oid' in obj:
                    return obj['$oid']
            except:
                pass
        
        # Remove any characters that could cause issues in filenames
        return thread_id.replace('/', '_').replace('\\', '_').replace(':', '_')
    
    return str(thread_id)

def format_thread_messages_for_analysis(messages):
    """Format a list of messages as a thread for Claude analysis"""
    formatted_text = ""
    
    for msg in messages:
        role = msg.get('role', 'UNKNOWN')
        content = msg.get('content', '')
        
        # Handle content that might be a list
        if isinstance(content, list):
            # Join list items into a single string
            content = ' '.join([str(item) for item in content])
        
        if role.lower() == 'user':
            formatted_text += f"Human: {content}\n\n"
        elif role.lower() == 'assistant':
            formatted_text += f"Assistant: {content}\n\n"
        else:
            formatted_text += f"{role}: {content}\n\n"
            
    return formatted_text
