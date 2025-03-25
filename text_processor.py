import re
import os
import chardet
from striprtf.striprtf import rtf_to_text
from typing import List

# Maximum chunk size in characters that Claude can handle
MAX_CHUNK_SIZE = 100000  # 100K characters - Claude 3 Opus can handle this

def detect_encoding(file_path):
    """Detect the encoding of a file"""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def read_file(file_path):
    """Read file content based on file type"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Handle RTF files
    if file_extension == '.rtf':
        try:
            # Read RTF file and convert to plain text
            with open(file_path, 'rb') as f:  # Use binary mode to avoid encoding issues
                rtf_content = f.read().decode('utf-8', errors='ignore')
            return rtf_to_text(rtf_content)
        except Exception as e:
            print(f"Error processing RTF file: {e}")
            # Try alternative approach for RTF handling
            try:
                with open(file_path, 'rb') as f:
                    rtf_content = f.read()
                # Try to detect encoding first
                detected_encoding = chardet.detect(rtf_content)['encoding'] or 'utf-8'
                rtf_content = rtf_content.decode(detected_encoding, errors='ignore')
                return rtf_to_text(rtf_content)
            except Exception as e2:
                print(f"Alternative RTF processing also failed: {e2}")
                # Let the exception propagate to be caught by the caller
                raise ValueError(f"Failed to process RTF file: {e}, then: {e2}")
    
    # For regular text files or as fallback
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        # Last resort - try with utf-8
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e2:
            raise ValueError(f"Failed to read file with any encoding method: {e}, then: {e2}")

def create_chunks(text: str, preserve_thread_boundaries: bool = True) -> List[str]:
    """
    Split a text into chunks of maximum size, respecting thread boundaries if specified.
    
    Args:
        text: Text to split into chunks
        preserve_thread_boundaries: If True, try to keep threads together
        
    Returns:
        List of text chunks
    """
    # If text is smaller than the max chunk size, return it as is
    if len(text) <= MAX_CHUNK_SIZE:
        return [text]
        
    chunks = []
    
    if preserve_thread_boundaries:
        # Try to preserve thread boundaries by splitting on thread patterns
        thread_pattern = r'(?:^|\n)Conversation #\d+:'
        thread_matches = list(re.finditer(thread_pattern, text))
        
        # Group threads into chunks that fit within MAX_CHUNK_SIZE
        if thread_matches:
            start_idx = 0
            current_chunk = ""
            
            for i, match in enumerate(thread_matches):
                thread_start = match.start()
                
                # Get the thread content (from this thread start to next thread start or end of text)
                if i < len(thread_matches) - 1:
                    thread_end = thread_matches[i + 1].start()
                    thread_content = text[thread_start:thread_end]
                else:
                    thread_content = text[thread_start:]
                
                # If adding this thread would exceed chunk size and we already have content
                if len(current_chunk) + len(thread_content) > MAX_CHUNK_SIZE and current_chunk:
                    # Save current chunk and start a new one
                    chunks.append(current_chunk)
                    current_chunk = thread_content
                else:
                    # Add this thread to the current chunk
                    current_chunk += thread_content
            
            # Add the last chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
                
            # If we successfully created chunks, return them
            if chunks:
                return chunks
    
    # Fallback to simple splitting if thread preservation didn't work well
    # or if preserve_thread_boundaries is False
    current_pos = 0
    while current_pos < len(text):
        chunk_end = min(current_pos + MAX_CHUNK_SIZE, len(text))
        
        # If we're not at the end of the text, try to find a good breaking point
        if chunk_end < len(text):
            # Try to find the last paragraph break
            last_break = text.rfind('\n\n', current_pos, chunk_end)
            
            if last_break > current_pos + MAX_CHUNK_SIZE * 0.8:
                chunk_end = last_break + 2  # Include the newlines
            else:
                # If no good paragraph break, try with a newline
                last_break = text.rfind('\n', current_pos, chunk_end)
                if last_break > current_pos + MAX_CHUNK_SIZE * 0.9:
                    chunk_end = last_break + 1  # Include the newline
        
        chunks.append(text[current_pos:chunk_end])
        current_pos = chunk_end
    
    return chunks

def clean_chunk(chunk):
    """Clean and prepare a chunk for analysis"""
    # Remove any control characters
    chunk = re.sub(r'[\x00-\x1F\x7F]', '', chunk)
    
    # Ensure the chunk has a clear beginning and end
    if not chunk.startswith("=========="):
        chunk = "========== CHUNK START ==========\n\n" + chunk
    
    if not chunk.endswith("=========="):
        chunk = chunk + "\n\n========== CHUNK END =========="
    
    return chunk

def process_file(file_path: str) -> List[str]:
    """
    Process a text file into chunks for analysis.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of chunks
    """
    # Read the file content
    text = read_file(file_path)
    
    # Simple validation
    if not text or len(text) < 10:
        return []
    
    # Format as chat log with markers
    formatted_text = f"===== CHAT LOG =====\n\n{text}\n\n===== END CHAT LOG =====\n"
    
    # Create chunks from the formatted text
    chunks = create_chunks(formatted_text)
    
    # Print stats about the chunks
    total_size = sum(len(chunk) for chunk in chunks)
    avg_size = total_size / len(chunks) if chunks else 0
    print(f"Created {len(chunks)} chunks, Total size: {total_size}, Average chunk size: {avg_size:.0f}")
    
    return chunks