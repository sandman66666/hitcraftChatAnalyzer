"""
Time and date handling utilities for HitCraft Chat Analyzer
"""
import datetime

def parse_datetime(dt_str):
    """Parse various datetime formats into a datetime object"""
    if not dt_str:
        return None
        
    # Try different formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with milliseconds
        "%Y-%m-%dT%H:%M:%SZ",     # ISO format without milliseconds
        "%Y-%m-%dT%H:%M:%S",      # ISO format without Z
        "%Y-%m-%d %H:%M:%S",      # Simple format
        "%Y-%m-%d"                # Date only
    ]
    
    # Try parsing with datetime.fromisoformat
    try:
        return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except:
        pass
    
    # Try each format
    for fmt in formats:
        try:
            return datetime.datetime.strptime(dt_str, fmt)
        except:
            continue
    
    # If all fail, raise exception
    raise ValueError(f"Could not parse datetime: {dt_str}")

def generate_timestamp():
    """Generate a timestamp string in the format YYYYMMDD_HHMMSS"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def is_within_timeframe(time_obj, start_datetime=None, end_datetime=None):
    """Check if a datetime object is within a specified timeframe"""
    if not time_obj:
        return False
        
    if start_datetime and time_obj < start_datetime:
        return False
        
    if end_datetime and time_obj > end_datetime:
        return False
        
    return True
