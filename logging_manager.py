"""
Logging functionality for HitCraft Chat Analyzer
"""
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global buffer for logging messages to display on the frontend
log_buffer = []

# Our application logger
logger = logging.getLogger('hitcraft_analyzer')

# Analysis state - will be initialized by the app
analysis_state = None

# Context manager to temporarily disable logging for imported functions
class FunctionLoggingDisabled:
    """Context manager to temporarily disable logging for imported functions"""
    def __enter__(self):
        # Save the current state
        self.logger_level = logger.level
        # Temporarily disable the logger
        logger.setLevel(logging.CRITICAL)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the logger to its original state
        logger.setLevel(self.logger_level)

def add_log(message, level="info"):
    """Add a log message to the buffer for frontend display"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {"timestamp": timestamp, "message": message, "level": level}
    log_buffer.append(log_entry)
    
    # Also add to analysis state log entries for thread analysis progress
    if analysis_state:
        analysis_state['log_entries'].append(message)
        # Keep only last 100 entries
        if len(analysis_state['log_entries']) > 100:
            analysis_state['log_entries'].pop(0)
    
    # Log to the standard logger
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
    
    # Keep only the last 1000 messages to prevent memory issues
    if len(log_buffer) > 1000:
        log_buffer.pop(0)

def get_logs():
    """Return the log buffer"""
    return log_buffer

def set_analysis_state(state):
    """Set the analysis state reference"""
    global analysis_state
    analysis_state = state
