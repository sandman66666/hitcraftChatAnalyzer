import re
import os
import chardet
from striprtf.striprtf import rtf_to_text

# Maximum chunk size in characters that Claude can handle
# This is an estimate and can be adjusted based on Claude's actual limits
MAX_CHUNK_SIZE = 100000  # ~100K characters

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
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            return rtf_to_text(rtf_content)
        except Exception as e:
            print(f"Error processing RTF file: {e}")
            # Fallback to regular text processing
            pass
    
    # For regular text files or as fallback
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        # Last resort - try with utf-8
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

def chunk_file(file_path):
    """Break a large file into chunks for Claude analysis"""
    text = read_file(file_path)
    print(f"Read file: {file_path}, size: {len(text)} characters")
    
    # Try multiple different thread boundary patterns
    thread_patterns = [
        # Original pattern
        r'==========\s+THREAD:.*?==========\s+END\s+THREAD\s+==========\s+',
        # Alternative patterns for different chat log formats
        r'Thread ID:\s*\w+.*?(?=Thread ID:|$)',
        r'ThreadId:.*?(?=ThreadId:|$)',
        r'Conversation: \d+.*?(?=Conversation: \d+|$)'
    ]
    
    threads = []
    for pattern in thread_patterns:
        print(f"Trying thread pattern: {pattern}")
        threads = re.split(pattern, text, flags=re.DOTALL)
        # Remove empty strings
        threads = [thread.strip() for thread in threads if thread.strip()]
        if len(threads) > 1:
            print(f"Found {len(threads)} threads using pattern: {pattern}")
            break
    
    # If we don't have clear thread boundaries, fall back to size-based chunking
    if len(threads) <= 1:
        print("No clear thread boundaries found, using size-based chunking")
        chunks = chunk_by_size(text, MAX_CHUNK_SIZE)
        print(f"Created {len(chunks)} chunks based on size")
        return chunks
    
    # Combine threads into chunks that respect MAX_CHUNK_SIZE
    chunks = []
    current_chunk = ""
    print(f"Processing {len(threads)} threads into chunks...")
    
    for i, thread in enumerate(threads):
        # Try to find the thread header if it was split off
        thread_header = ""
        header_match = re.search(r'==========\s+THREAD:.*?==========\s+', text, flags=re.DOTALL)
        if header_match:
            thread_header = header_match.group(0)
        
        thread_with_header = f"{thread_header}{thread}\n========== END THREAD ==========\n\n"
        
        # If adding this thread exceeds the chunk size, save current chunk and start new one
        if len(current_chunk) + len(thread_with_header) > MAX_CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk)
            
            # If a single thread is too large, break it into smaller chunks
            if len(thread_with_header) > MAX_CHUNK_SIZE:
                thread_chunks = chunk_by_size(thread_with_header, MAX_CHUNK_SIZE)
                chunks.extend(thread_chunks)
                current_chunk = ""
            else:
                current_chunk = thread_with_header
        else:
            current_chunk += thread_with_header
        
        # Log progress for large numbers of threads
        if (i+1) % 50 == 0:
            print(f"Processed {i+1} of {len(threads)} threads")
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    print(f"Final number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1} size: {len(chunk)} characters")
    
    return chunks

def chunk_by_size(text, max_size):
    """Split text into chunks of maximum size, trying to break at logical points"""
    print(f"Breaking text of size {len(text)} characters into chunks of max {max_size} characters")
    chunks = []
    
    while text:
        if len(text) <= max_size:
            chunks.append(text)
            print(f"Added final chunk of size {len(text)} characters")
            break
        
        # Try to find a good breaking point near the max_size
        # Prefer to break at end of a thread
        thread_end = text[:max_size].rfind("========== END THREAD ==========")
        if thread_end != -1 and thread_end > max_size * 0.5:  # Ensure we're not making tiny chunks
            split_point = thread_end + len("========== END THREAD ==========")
            chunks.append(text[:split_point])
            print(f"Split at thread end marker, chunk size: {split_point} characters")
            text = text[split_point:].strip()
            continue
        
        # Try to find message boundaries in different formats
        message_markers = [
            r"\n\s*User:\s*\n",
            r"\n\s*Assistant:\s*\n",
            r"\nFrom:\s+.*?\n",
            r"\nTo:\s+.*?\n",
            r"\n\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s*\n"  # Date/time markers
        ]
        
        for marker in message_markers:
            matches = list(re.finditer(marker, text[:max_size], re.DOTALL))
            if matches and len(matches) > 0:
                # Use the last match as a split point if it's not too close to the beginning
                last_match = matches[-1]
                if last_match.start() > max_size * 0.6:
                    chunks.append(text[:last_match.start()])
                    print(f"Split at message boundary, chunk size: {last_match.start()} characters")
                    text = text[last_match.start():].strip()
                    break
        else:  # This else belongs to the for loop, executes if no break occurred
            # Otherwise, try to break at a paragraph boundary
            paragraph = text[:max_size].rfind("\n\n")
            if paragraph != -1 and paragraph > max_size * 0.7:  # Ensure decent chunk size
                chunks.append(text[:paragraph])
                print(f"Split at paragraph, chunk size: {paragraph} characters")
                text = text[paragraph:].strip()
                continue
            
            # Last resort: break at a line boundary
            line = text[:max_size].rfind("\n")
            if line != -1 and line > max_size * 0.8:
                chunks.append(text[:line])
                print(f"Split at line break, chunk size: {line} characters")
                text = text[line:].strip()
            else:
                # If all else fails, just break at max_size
                chunks.append(text[:max_size])
                print(f"Split at max size, chunk size: {max_size} characters")
                text = text[max_size:].strip()
    
    print(f"Created {len(chunks)} chunks from text")
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