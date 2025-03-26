"""
Persistent thread storage for HitCraft Chat Analyzer

This module provides functionality to store threads persistently, 
track analyzed threads, and maintain analysis history.
"""
import os
import json
import time
import glob
import logging
import datetime
from collections import defaultdict
import config
import hashlib
import shutil
from logging_manager import add_log

# Define constants for storage paths
THREADS_FOLDER = config.THREADS_FOLDER
DATA_FOLDER = config.DATA_FOLDER
STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), THREADS_FOLDER)
ANALYSIS_HISTORY_PATH = os.path.join(DATA_FOLDER, "analysis_history.json")
THREAD_INDEX_PATH = os.path.join(DATA_FOLDER, "thread_index.json")

def initialize_storage():
    """
    Create necessary directories and index files for persistent storage
    """
    # Create storage directory if it doesn't exist
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(DATA_FOLDER, exist_ok=True)
    
    # Create thread index if it doesn't exist
    if not os.path.exists(THREAD_INDEX_PATH):
        with open(THREAD_INDEX_PATH, 'w', encoding='utf-8') as f:
            json.dump({
                "threads": [],
                "total_count": 0,
                "analyzed_count": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }, f, indent=2)
        add_log("Created new thread index file")
        
    # Create analysis history if it doesn't exist
    if not os.path.exists(ANALYSIS_HISTORY_PATH):
        with open(ANALYSIS_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump({
                "analyses": [],
                "latest": None,
                "last_updated": datetime.datetime.now().isoformat()
            }, f, indent=2)
        add_log("Created new analysis history file")

def store_threads_permanently(session_id, threads_dir):
    """
    Move threads from temporary session storage to permanent storage
    
    Args:
        session_id: Current session ID
        threads_dir: Directory containing threads from the current session
        
    Returns:
        tuple: (threads_added, total_threads)
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Load the thread index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
    except Exception as e:
        add_log(f"Error loading thread index, creating new one: {str(e)}", "error")
        thread_index = {
            "threads": [],
            "total_count": 0,
            "analyzed_count": 0,
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # Get current threads list and IDs for checking duplicates
    existing_thread_ids = {t['id'] for t in thread_index['threads']}
    
    # Check for thread files in the session directory
    if not os.path.exists(threads_dir):
        add_log(f"Threads directory not found: {threads_dir}", "error")
        return 0, thread_index['total_count']
    
    # Look for thread_list.json first which has metadata
    thread_list_path = os.path.join(threads_dir, 'thread_list.json')
    thread_files = []
    session_threads = []
    
    if os.path.exists(thread_list_path):
        try:
            with open(thread_list_path, 'r', encoding='utf-8') as f:
                session_threads = json.load(f)
        except Exception as e:
            add_log(f"Error loading thread list: {str(e)}", "error")
            session_threads = []
    
    # If we have thread metadata, use that to find thread files
    if session_threads:
        for thread_meta in session_threads:
            thread_id = thread_meta.get('id')
            if thread_id:
                thread_json = os.path.join(threads_dir, f"{thread_id}.json")
                thread_txt = os.path.join(threads_dir, f"{thread_id}.txt")
                
                if os.path.exists(thread_json) and os.path.exists(thread_txt):
                    thread_files.append((thread_id, thread_json, thread_txt, thread_meta))
    else:
        # Fallback to directory scan
        json_files = [f for f in os.listdir(threads_dir) if f.endswith('.json') and f != 'thread_list.json']
        
        for json_file in json_files:
            thread_id = os.path.splitext(json_file)[0]
            thread_json = os.path.join(threads_dir, json_file)
            thread_txt = os.path.join(threads_dir, f"{thread_id}.txt")
            
            if os.path.exists(thread_txt):
                # Create bare metadata
                thread_meta = {'id': thread_id}
                try:
                    with open(thread_json, 'r', encoding='utf-8') as f:
                        thread_data = json.load(f)
                        if 'message_count' in thread_data:
                            thread_meta['message_count'] = thread_data['message_count']
                        if 'first_message_time' in thread_data:
                            thread_meta['first_message_time'] = thread_data['first_message_time']
                        if 'last_message_time' in thread_data:
                            thread_meta['last_message_time'] = thread_data['last_message_time']
                except Exception as e:
                    add_log(f"Error reading thread data: {str(e)}", "error")
                
                thread_files.append((thread_id, thread_json, thread_txt, thread_meta))
    
    # Copy thread files to permanent storage
    threads_added = 0
    
    for thread_id, thread_json, thread_txt, thread_meta in thread_files:
        # Skip if this thread already exists
        if thread_id in existing_thread_ids:
            continue
            
        # Copy files to STORAGE_DIR
        try:
            shutil.copy2(thread_json, os.path.join(STORAGE_DIR, f"{thread_id}.json"))
            shutil.copy2(thread_txt, os.path.join(STORAGE_DIR, f"{thread_id}.txt"))
            
            # Add to index
            thread_meta['analyzed'] = False
            thread_meta['added_date'] = datetime.datetime.now().isoformat()
            
            thread_index['threads'].append(thread_meta)
            threads_added += 1
            
            add_log(f"Thread {thread_id} stored permanently")
        except Exception as e:
            add_log(f"Error copying thread {thread_id}: {str(e)}", "error")
    
    # Update index
    if threads_added > 0:
        thread_index['total_count'] = len(thread_index['threads'])
        thread_index['last_updated'] = datetime.datetime.now().isoformat()
        
        # Write updated index
        with open(THREAD_INDEX_PATH, 'w', encoding='utf-8') as f:
            json.dump(thread_index, f, indent=2)
    
    return threads_added, thread_index['total_count']

def get_all_threads(page=1, per_page=10):
    """
    Get all stored threads with pagination
    
    Args:
        page: Page number (1-based)
        per_page: Number of threads per page
        
    Returns:
        dict: Paginated threads and metadata
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Load the thread index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
    except Exception as e:
        add_log(f"Error loading thread index: {str(e)}", "error")
        thread_index = {
            "threads": [],
            "total_count": 0,
            "analyzed_count": 0
        }
    
    # Sort threads by last_message_time (newest first)
    try:
        thread_index['threads'].sort(
            key=lambda x: str(x.get('last_message_time', '')) if isinstance(x.get('last_message_time'), (dict, list)) 
            else x.get('last_message_time', ''), 
            reverse=True
        )
    except Exception as e:
        add_log(f"Error sorting threads: {str(e)}", "error")
    
    # Calculate pagination
    total = len(thread_index['threads'])
    total_pages = (total + per_page - 1) // per_page
    
    # Get the requested page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    if start_idx >= total:
        page_threads = []
    else:
        page_threads = thread_index['threads'][start_idx:end_idx]
    
    return {
        "threads": page_threads,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages
    }

def get_thread_content(thread_id):
    """
    Get content of a specific thread
    
    Args:
        thread_id: ID of the thread to retrieve
        
    Returns:
        dict: Thread content and metadata
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Check thread exists in index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
            
        thread_meta = None
        for t in thread_index['threads']:
            if t['id'] == thread_id:
                thread_meta = t
                break
                
        if not thread_meta:
            add_log(f"Thread {thread_id} not found in index", "error")
            return None
    except Exception as e:
        add_log(f"Error loading thread index: {str(e)}", "error")
        thread_meta = {'id': thread_id}
    
    # Try to load thread content
    thread_json_path = os.path.join(STORAGE_DIR, f"{thread_id}.json")
    thread_txt_path = os.path.join(STORAGE_DIR, f"{thread_id}.txt")
    
    if not os.path.exists(thread_txt_path):
        add_log(f"Thread {thread_id} not found at path {thread_txt_path}", "error")
        return None
    
    # Load thread content
    try:
        with open(thread_txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        thread_data = {"id": thread_id, "content": content}
        
        # Add metadata from JSON file if available
        if os.path.exists(thread_json_path):
            try:
                with open(thread_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    # Merge JSON data with thread_data
                    thread_data.update(json_data)
            except Exception as e:
                add_log(f"Error loading thread JSON: {str(e)}", "error")
        
        # Add metadata from index
        thread_data.update(thread_meta)
        
        return thread_data
    except Exception as e:
        add_log(f"Error loading thread content: {str(e)}", "error")
        return None

def get_unanalyzed_threads(count=10):
    """
    Get a specified number of unanalyzed threads
    
    Args:
        count: Number of threads to retrieve
        
    Returns:
        list: Thread data ready for analysis
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Load the thread index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
    except Exception as e:
        add_log(f"Error loading thread index: {str(e)}", "error")
        return []
    
    # Find unanalyzed threads
    unanalyzed = []
    for thread_meta in thread_index['threads']:
        if not thread_meta.get('analyzed', False):
            unanalyzed.append(thread_meta)
            if len(unanalyzed) >= count:
                break
    
    # Load full thread content for each unanalyzed thread
    threads_for_analysis = []
    for thread_meta in unanalyzed:
        thread_id = thread_meta['id']
        thread_content = get_thread_content(thread_id)
        if thread_content:
            threads_for_analysis.append(thread_content)
    
    add_log(f"Found {len(threads_for_analysis)} unanalyzed threads for analysis")
    return threads_for_analysis

def mark_threads_as_analyzed(thread_ids, evidence_map=None):
    """
    Mark threads as analyzed and update index
    
    Args:
        thread_ids: List of thread IDs that were analyzed
        evidence_map: Optional mapping of insights to thread evidence
        
    Returns:
        int: Number of threads marked
    """
    # Make sure storage is initialized
    initialize_storage()
    
    if not thread_ids:
        add_log("No thread IDs provided to mark as analyzed", "warning")
        return 0
    
    # Load the thread index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
    except Exception as e:
        add_log(f"Error loading thread index: {str(e)}", "error")
        return 0
    
    # Mark threads as analyzed
    count_marked = 0
    for i, thread_meta in enumerate(thread_index['threads']):
        if thread_meta['id'] in thread_ids:
            thread_index['threads'][i]['analyzed'] = True
            thread_index['threads'][i]['analyzed_date'] = datetime.datetime.now().isoformat()
            
            # Store evidence references
            if evidence_map:
                thread_index['threads'][i]['evidence_for'] = []
                for insight, thread_list in evidence_map.items():
                    if thread_meta['id'] in thread_list:
                        thread_index['threads'][i]['evidence_for'].append(insight)
            
            count_marked += 1
    
    # Update analyzed count
    thread_index['analyzed_count'] = sum(1 for t in thread_index['threads'] if t.get('analyzed', False))
    thread_index['last_updated'] = datetime.datetime.now().isoformat()
    
    # Write updated index
    with open(THREAD_INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(thread_index, f, indent=2)
    
    add_log(f"Marked {count_marked} threads as analyzed")
    return count_marked

def save_analysis_results(results, session_id=None, filename=None, analyzed_thread_ids=None):
    """
    Store analysis results permanently
    
    Args:
        results: Analysis results to store
        session_id: Optional session ID
        filename: Optional filename
        analyzed_thread_ids: Optional list of thread IDs that were part of this analysis
        
    Returns:
        dict: Saved analysis metadata
    """
    # Make sure storage is initialized
    initialize_storage()
    
    if not results:
        add_log("No results provided to save", "warning")
        return None
    
    # Generate a unique ID for this analysis
    timestamp = int(time.time())
    analysis_id = f"analysis_{timestamp}"
    
    # Create analysis metadata
    analysis_meta = {
        "id": analysis_id,
        "timestamp": timestamp,
        "date": datetime.datetime.now().isoformat(),
        "session_id": session_id,
        "filename": filename,
        "thread_count": len(analyzed_thread_ids) if analyzed_thread_ids else 0,
        "thread_ids": analyzed_thread_ids or [],
    }
    
    # Save the analysis results
    results_file = os.path.join(config.RESULTS_FOLDER, f"{analysis_id}.json")
    os.makedirs(config.RESULTS_FOLDER, exist_ok=True)
    
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": analysis_meta,
                "results": results
            }, f, indent=2)
        
        add_log(f"Saved analysis results to {results_file}")
    except Exception as e:
        add_log(f"Error saving analysis results: {str(e)}", "error")
        return None
    
    # Update analysis history
    try:
        with open(ANALYSIS_HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception as e:
        add_log(f"Error loading analysis history, creating new one: {str(e)}", "error")
        history = {
            "analyses": [],
            "latest": None,
            "last_updated": datetime.datetime.now().isoformat()
        }
    
    # Add this analysis to history
    history['analyses'].append(analysis_meta)
    history['latest'] = analysis_meta
    history['last_updated'] = datetime.datetime.now().isoformat()
    
    # Write updated history
    with open(ANALYSIS_HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)
    
    return analysis_meta

def get_latest_analysis():
    """
    Get the most recent analysis results
    
    Returns:
        dict: Analysis results and metadata
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Load analysis history
    try:
        with open(ANALYSIS_HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception as e:
        add_log(f"Error loading analysis history: {str(e)}", "error")
        return None
    
    # Get the latest analysis
    latest = history.get('latest')
    if not latest:
        add_log("No analysis found in history", "warning")
        return None
    
    # Load the analysis results
    results_file = os.path.join(config.RESULTS_FOLDER, f"{latest['id']}.json")
    if not os.path.exists(results_file):
        add_log(f"Analysis results file not found: {results_file}", "error")
        return None
    
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        return analysis_data
    except Exception as e:
        add_log(f"Error loading analysis results: {str(e)}", "error")
        return None

def get_analysis_stats():
    """
    Get statistics about thread analysis
    
    Returns:
        dict: Statistics about analyzed threads
    """
    # Make sure storage is initialized
    initialize_storage()
    
    try:
        # First try to load the thread index
        try:
            with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
                thread_index = json.load(f)
        except json.JSONDecodeError as e:
            # Handle corrupted JSON
            add_log(f"Error parsing thread index JSON: {str(e)}", "error")
            
            # Create a backup of the corrupted file
            backup_path = f"{THREAD_INDEX_PATH}.bak.{int(time.time())}"
            try:
                shutil.copy(THREAD_INDEX_PATH, backup_path)
                add_log(f"Created backup of corrupted thread index at {backup_path}", "info")
            except Exception as backup_err:
                add_log(f"Failed to backup corrupted thread index: {str(backup_err)}", "error")
            
            # Create a new thread index
            thread_index = {
                "threads": [],
                "total_count": 0,
                "analyzed_count": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            # Try to recover thread info from the storage directory
            try:
                thread_files = glob.glob(os.path.join(STORAGE_DIR, "*.txt"))
                for thread_file in thread_files:
                    thread_id = os.path.basename(thread_file).replace('.txt', '')
                    thread_index["threads"].append({
                        "id": thread_id,
                        "analyzed": False,
                        "created_date": datetime.datetime.now().isoformat()
                    })
                thread_index["total_count"] = len(thread_index["threads"])
                add_log(f"Recovered {len(thread_index['threads'])} threads from storage directory", "info")
            except Exception as recover_err:
                add_log(f"Failed to recover threads from storage: {str(recover_err)}", "error")
            
            # Save the new thread index
            try:
                with open(THREAD_INDEX_PATH, 'w', encoding='utf-8') as f:
                    json.dump(thread_index, f, indent=2)
                add_log("Created new thread index file after JSON error", "info")
            except Exception as save_err:
                add_log(f"Failed to save new thread index: {str(save_err)}", "error")
        
        # Count total and analyzed threads
        total = len(thread_index.get('threads', []))
        analyzed = sum(1 for t in thread_index.get('threads', []) if t.get('analyzed', False))
        unanalyzed = total - analyzed
        percentage = round((analyzed / total * 100) if total > 0 else 0, 1)
        
        return {
            'total': total,
            'analyzed': analyzed,
            'unanalyzed': unanalyzed,
            'percentage': percentage
        }
    except Exception as e:
        add_log(f"Error getting analysis stats: {str(e)}", "error")
        # Return default values on error
        return {
            'total': 0,
            'analyzed': 0,
            'unanalyzed': 0,
            'percentage': 0
        }

def get_evidence_for_insight(insight_key):
    """
    Find messages that are evidence for a specific insight
    
    Args:
        insight_key: Key of the insight to find evidence for
        
    Returns:
        list: Thread messages that support the insight
    """
    # Make sure storage is initialized
    initialize_storage()
    
    # Load the thread index
    try:
        with open(THREAD_INDEX_PATH, 'r', encoding='utf-8') as f:
            thread_index = json.load(f)
    except Exception as e:
        add_log(f"Error loading thread index: {str(e)}", "error")
        return []
    
    # Find threads that are evidence for this insight
    evidence_threads = []
    for thread_meta in thread_index['threads']:
        if thread_meta.get('evidence_for') and insight_key in thread_meta['evidence_for']:
            thread_id = thread_meta['id']
            thread_content = get_thread_content(thread_id)
            if thread_content:
                evidence_threads.append(thread_content)
    
    return evidence_threads

def get_total_thread_count():
    """
    Get the total number of threads stored in the database
    
    Returns:
        int: Total number of threads
    """
    stats = get_analysis_stats()
    return stats['total']

def get_analyzed_thread_count():
    """
    Get the number of threads that have been analyzed
    
    Returns:
        int: Number of analyzed threads
    """
    stats = get_analysis_stats()
    return stats['analyzed']
