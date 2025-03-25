import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import os
import text_processor  # Added missing import

# Get logger
logger = logging.getLogger('hitcraft_analyzer')

# Maximum chunk size in characters that Claude can handle
MAX_CHUNK_SIZE = 100000  # ~100K characters

def load_chat_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load chat data from a JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of chat message objects
    """
    logger.info(f"Loading chat data from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read the raw content first
            content = f.read()
            
            # Check if the content appears to be HTML instead of JSON
            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                logger.error("File appears to be HTML, not JSON")
                raise ValueError("The uploaded file appears to be HTML, not JSON. Please check the file and try again.")
            
            # Log the first 200 characters for debugging
            logger.info(f"First 200 chars of the file: {content[:200]}")
            
            # Parse JSON
            chat_data = json.loads(content)
            
            # If chat_data is a single JSON object instead of an array, 
            # wrap it in a list to ensure consistent processing
            if not isinstance(chat_data, list):
                logger.info("JSON is not a list, converting to list with single item")
                chat_data = [chat_data]
            
        logger.info(f"Successfully loaded {len(chat_data)} messages")
        return chat_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading chat data: {str(e)}")
        raise

def load_json_chat(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load JSON chat data from a file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary with thread IDs as keys and lists of messages as values
    """
    chat_data = load_chat_data(file_path)
    return organize_chats_by_thread(chat_data)

def organize_chats_by_thread(chat_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group chat messages by their thread ID
    
    Args:
        chat_data: List of chat message objects
        
    Returns:
        Dictionary with thread IDs as keys and lists of messages as values
    """
    logger.info("Organizing chats by thread ID")
    threads = {}
    
    for message in chat_data:
        # Extract the thread ID - using $oid value from the threadId field
        if "threadId" in message and "$oid" in message["threadId"]:
            thread_id = message["threadId"]["$oid"]
        else:
            logger.warning(f"Message missing threadId, using message ID instead: {message.get('_id', {}).get('$oid', 'unknown')}")
            # Fallback to message ID if thread ID is not available
            thread_id = message.get("_id", {}).get("$oid", "unknown")
        
        # Add message to the appropriate thread
        if thread_id not in threads:
            threads[thread_id] = []
        threads[thread_id].append(message)
    
    logger.info(f"Identified {len(threads)} unique threads")
    return threads

def sort_messages_by_date(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort messages by creation date
    
    Args:
        messages: List of chat message objects
        
    Returns:
        Sorted list of messages
    """
    def get_timestamp(message):
        # Extract the timestamp from createdAt field
        if "createdAt" in message and "$date" in message["createdAt"]:
            return message["createdAt"]["$date"]
        return "1970-01-01T00:00:00Z"  # Default date if not found
    
    return sorted(messages, key=get_timestamp)

def format_message_content(content: Any) -> str:
    """
    Format the content of a message
    
    Args:
        content: Content object (can be a list of objects or a string)
        
    Returns:
        Formatted content string
    """
    # If content is a string, return it directly
    if isinstance(content, str):
        return content
    
    # If content is None or empty, return empty string
    if not content:
        return ""
    
    # If content is not a list, try to convert it to string
    if not isinstance(content, list):
        return str(content)
    
    result = []
    
    for item in content:
        # If item is a string, append it directly
        if isinstance(item, str):
            result.append(item)
            continue
            
        # If item is a dict, process it based on type
        if isinstance(item, dict):
            if item.get("type") == "text" and "text" in item:
                result.append(item["text"])
            elif item.get("type") == "sketch_upload_request":
                result.append("[Sketch upload request]")
            elif item.get("type") == "reference_candidates":
                result.append("[Reference candidates]")
            elif item.get("type") == "reference_selection":
                result.append("[Reference selection]")
            elif item.get("type") == "song_rendering_start":
                result.append("[Song rendering started]")
            else:
                # For any other types, add a placeholder
                result.append(f"[{item.get('type', 'Unknown content')}]")
        else:
            # For non-dict items, convert to string
            result.append(str(item))
    
    return "\n".join(result)

def format_conversation(messages: List[Dict[str, Any]]) -> str:
    """
    Format a list of messages into a readable conversation
    
    Args:
        messages: List of chat message objects
        
    Returns:
        Formatted conversation string
    """
    conversation = []
    
    for message in messages:
        # Get timestamp
        timestamp = "Unknown time"
        if "createdAt" in message and "$date" in message["createdAt"]:
            try:
                dt = datetime.fromisoformat(message["createdAt"]["$date"].replace("Z", "+00:00"))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                # Fallback if date parsing fails
                timestamp = message["createdAt"]["$date"]
        
        # Get role
        role = message.get("role", "unknown")
        
        # Get user ID
        user_id = message.get("userId", {}).get("$oid", "unknown")
        
        # Get message content
        content = format_message_content(message.get("content", []))
        
        # Format the message
        formatted_message = f"[{timestamp}] {role.upper()} ({user_id}):\n{content}\n"
        conversation.append(formatted_message)
    
    # Join all formatted messages with a separator
    return "\n".join(conversation)

def format_threads_for_analysis(threads: Dict[str, List[Dict]]) -> str:
    """
    Format threads into a single text for analysis
    
    Args:
        threads: Dictionary of thread_id -> list of messages
        
    Returns:
        Formatted text with all threads
    """
    result = []
    
    for thread_id, messages in threads.items():
        # Sort messages by date
        sorted_messages = sort_messages_by_date(messages)
        
        # Format the conversation
        formatted_conversation = format_conversation(sorted_messages)
        
        # Add thread header and footer
        thread_text = f"Conversation #{thread_id}:\n\n{formatted_conversation}\n\n"
        result.append(thread_text)
    
    return "\n".join(result)

def process_chat_file(file_path: str, max_chunks: int = None) -> List[str]:
    """
    Process a chat file into chunks for analysis.
    
    Args:
        file_path: Path to the chat file
        max_chunks: Maximum number of chunks to return (default: None = all chunks)
        
    Returns:
        List of chunks
    """
    filename = os.path.basename(file_path)
    logger.info(f"Processing chat file: {filename}")
    
    # Read file based on extension
    _, ext = os.path.splitext(file_path)
    
    if ext.lower() == '.json':
        threads = load_json_chat(file_path)
        formatted_text = format_threads_for_analysis(threads)
        logger.info(f"Loaded JSON chat data with {len(threads)} threads")
    else:
        # Assume it's a text or RTF file
        text = ""
        formatted_text = f"===== CHAT LOG =====\n\n{text}\n\n===== END CHAT LOG =====\n"
        logger.info(f"Loaded text chat data with {len(text)} characters")
    
    # Create chunks from the formatted text
    all_chunks = text_processor.create_chunks(formatted_text)
    logger.info(f"Created {len(all_chunks)} chunks for analysis")
    
    # Print stats about the chunks
    total_size = sum(len(chunk) for chunk in all_chunks)
    avg_size = total_size / len(all_chunks) if all_chunks else 0
    logger.info(f"Total content size: {total_size} characters, Average chunk size: {avg_size:.0f} characters")
    
    # Only log individual chunk sizes if there are a reasonable number of them
    if len(all_chunks) <= 20:
        for i, chunk in enumerate(all_chunks):
            logger.info(f"Chunk {i+1} size: {len(chunk)} characters")
    else:
        logger.info(f"First chunk size: {len(all_chunks[0])} characters")
        logger.info(f"Last chunk size: {len(all_chunks[-1])} characters")
    
    # Limit the number of chunks if specified
    if max_chunks and max_chunks > 0 and max_chunks < len(all_chunks):
        logger.info(f"Limiting to {max_chunks} chunks as requested")
        return all_chunks[:max_chunks]
    
    return all_chunks

def save_chunks_to_files(chunks: List[str], output_dir: str) -> List[str]:
    """
    Save chunks to individual files
    
    Args:
        chunks: List of chunk strings
        output_dir: Directory to save files
        
    Returns:
        List of file paths
    """
    import os
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    file_paths = []
    for i, chunk in enumerate(chunks):
        file_path = os.path.join(output_dir, f"chunk_{i}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(chunk)
        file_paths.append(file_path)
        logger.info(f"Saved chunk {i+1} to {file_path} (size: {len(chunk)} characters)")
    
    return file_paths
