"""
Thread analysis functionality for HitCraft Chat Analyzer
"""
import os
import json
import datetime
import copy
import claude_analyzer
from logging_manager import add_log
import time_utils

def analyze_threads_in_background(api_key, session_id, filename, threads_dir, thread_files, analysis_state):
    """Analyze threads one by one in the background"""
    try:
        # STRICT ENFORCEMENT: Never process more threads than originally specified
        thread_limit = len(thread_files)
        add_log(f"ENFORCING STRICT THREAD LIMIT: Will analyze exactly {thread_limit} threads")
        
        # Store the thread limit for triple-checking later
        analysis_state['thread_limit'] = thread_limit
        
        # Create session-specific results directory
        session_dir = os.path.join('temp_chunks', session_id)
        results_dir = os.path.join(session_dir, 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # Also create global results directory
        os.makedirs('analysis_results', exist_ok=True)
        
        # Timestamp for this analysis run
        timestamp = time_utils.generate_timestamp()
        
        # Create results file paths - both in session folder and global folder
        session_result_path = os.path.join(results_dir, 'combined_results.json')
        global_result_path = os.path.join('analysis_results', f"analysis_{filename}_{timestamp}.json")
        
        # Initialize combined results
        combined_results = None
        
        # Check for existing results to accumulate analysis over time
        if os.path.exists(session_result_path):
            try:
                with open(session_result_path, 'r') as f:
                    combined_results = json.load(f)
                add_log("Found existing analysis results, will accumulate new insights")
                
                # Check if we have thread results field
                if 'thread_results' not in combined_results:
                    combined_results['thread_results'] = []
                    
                # Check previously analyzed thread IDs
                analyzed_thread_ids = [tr.get('thread_id') for tr in combined_results.get('thread_results', [])]
                add_log(f"Found {len(analyzed_thread_ids)} previously analyzed threads")
                
            except Exception as e:
                add_log(f"Error loading existing results, starting fresh: {str(e)}", "warning")
                combined_results = None
        
        # Initialize new combined results if needed
        if combined_results is None:
            combined_results = {
                'categories': [],
                'top_discussions': [],
                'response_quality': {
                    'average_score': 0,
                    'good_examples': [],
                    'poor_examples': []
                },
                'improvement_areas': [],
                'user_satisfaction': {
                    'overall_assessment': '',
                    'positive_indicators': [],
                    'negative_indicators': []
                },
                'unmet_needs': [],
                'product_effectiveness': {
                    'assessment': '',
                    'strengths': [],
                    'weaknesses': []
                },
                'key_insights': [],
                'thread_results': [],
                'analysis_metadata': {
                    'first_analyzed_at': timestamp,
                    'last_analyzed_at': timestamp,
                    'total_threads_analyzed': 0,
                    'total_messages_analyzed': 0
                }
            }
        else:
            # Update the last analyzed timestamp
            if 'analysis_metadata' not in combined_results:
                combined_results['analysis_metadata'] = {}
                
            combined_results['analysis_metadata']['last_analyzed_at'] = timestamp
        
        # Load thread list to get metadata
        thread_list_path = os.path.join(os.path.dirname(threads_dir), 'thread_list.json')
        thread_metadata = {}
        if os.path.exists(thread_list_path):
            try:
                with open(thread_list_path, 'r') as f:
                    thread_list = json.load(f)
                    # Create a map of thread ID to metadata
                    thread_metadata = {t['id']: t for t in thread_list}
            except Exception as e:
                add_log(f"Error loading thread metadata: {str(e)}", "warning")
        
        # Process each thread - STRICT ENFORCEMENT OF THREAD LIMIT
        new_thread_results = []
        skipped_threads = 0
        threads_analyzed = 0
        
        # Final thread list - strictly limited to the specified count
        limited_thread_files = thread_files[:thread_limit]
        
        add_log(f"THREAD LIMIT CHECK: Requested={thread_limit}, To Process={len(limited_thread_files)}")
        
        # Safety check - make absolutely sure we don't exceed the limit
        if len(limited_thread_files) > thread_limit:
            add_log(f"WARNING: Thread list still exceeds limit. Forcibly trimming to exactly {thread_limit} threads.")
            limited_thread_files = limited_thread_files[:thread_limit]
        
        # One last safety check - maximum number to process is exactly what was specified
        MAX_THREADS_TO_PROCESS = thread_limit
        
        for i, thread_file in enumerate(limited_thread_files):
            # CRITICAL: This is the most important check - if we've reached the limit, stop IMMEDIATELY
            if threads_analyzed >= MAX_THREADS_TO_PROCESS:
                add_log(f"HARD LIMIT ENFORCED: Thread limit of {thread_limit} reached. Stopping analysis immediately.")
                break
                
            # Update state
            analysis_state['current_thread'] = i + 1
            analysis_state['last_updated'] = datetime.datetime.now()
            
            # Extract thread ID from filename
            thread_id = thread_file.replace('.txt', '')
            thread_path = os.path.join(threads_dir, thread_file)
            
            add_log(f"Processing thread {i+1}/{thread_limit}: {thread_id}")
            
            # Check if we already have results for this thread
            thread_exists = False
            for result in combined_results.get('thread_results', []):
                if result.get('thread_id') == thread_id:
                    thread_exists = True
                    add_log(f"Thread {thread_id} already analyzed, skipping")
                    skipped_threads += 1
                    break
            
            if thread_exists:
                continue
            
            # Read thread content
            with open(thread_path, 'r', encoding='utf-8') as f:
                thread_content = f.read()
            
            # Analyze the thread with Claude
            try:
                thread_result = claude_analyzer.analyze_single_thread(thread_content, api_key)
                
                # Add thread ID and metadata to the result
                thread_result['thread_id'] = thread_id
                
                # Add timestamp metadata if available
                if thread_id in thread_metadata:
                    meta = thread_metadata[thread_id]
                    thread_result['first_message_time'] = meta.get('first_message_time')
                    thread_result['last_message_time'] = meta.get('last_message_time')
                    thread_result['message_count'] = meta.get('message_count')
                
                # Add to new thread results
                new_thread_results.append(thread_result)
                
                # Update thread counts
                analysis_state['analyzed_threads'] += 1
                threads_analyzed += 1
                
                add_log(f"Thread {thread_id} analysis completed ({threads_analyzed}/{thread_limit})")
                
                # Final safety check - stop if we've reached the thread limit
                if threads_analyzed >= thread_limit:
                    add_log(f"Thread limit of {thread_limit} reached. Stopping analysis.")
                    break
                
            except Exception as e:
                add_log(f"Error analyzing thread {thread_id}: {str(e)}", "error")
        
        # EMERGENCY STOP - if we somehow processed more threads than requested, log an error
        if threads_analyzed > thread_limit:
            add_log(f"ERROR: Processed {threads_analyzed} threads despite limit of {thread_limit}. This is a bug.", "error")
        
        # Update combined results with the new thread results
        combined_results['thread_results'].extend(new_thread_results)
        
        # Update metadata
        combined_results['analysis_metadata']['total_threads_analyzed'] = len(combined_results['thread_results'])
        
        # Count total messages
        message_count = sum(tr.get('message_count', 0) for tr in combined_results['thread_results'])
        combined_results['analysis_metadata']['total_messages_analyzed'] = message_count
        
        # Only recombine results if we have new threads
        if new_thread_results:
            # Combine all thread results to generate overall insights
            add_log(f"Generating combined insights from {len(combined_results['thread_results'])} threads")
            updated_combined = claude_analyzer.combine_results(combined_results['thread_results'])
            
            # Update the combined results fields while preserving the thread_results
            for key, value in updated_combined.items():
                if key != 'thread_results' and key != 'analysis_metadata':
                    combined_results[key] = value
            
            add_log("Combined insights updated with new thread data")
        else:
            add_log(f"No new threads analyzed, keeping existing insights ({skipped_threads} threads skipped)")
        
        # Save updated results to both session and global files
        with open(session_result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2)
        
        with open(global_result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2)
        
        # Update analysis state with combined results
        analysis_state['combined_results'] = combined_results
        
        # Final update after all threads are processed
        add_log(f"Analysis completed: {analysis_state['analyzed_threads']} new threads analyzed")
        add_log(f"Total threads in analysis: {len(combined_results['thread_results'])}")
        add_log(f"Results saved to session folder and global results folder")
        
        # Mark analysis as complete
        analysis_state['is_analyzing'] = False
        
    except Exception as e:
        error_message = str(e)
        add_log(f"Error in background thread analysis: {error_message}", "error")
        import traceback
        add_log(traceback.format_exc(), "error")
        analysis_state['is_analyzing'] = False

def filter_results_by_time(results, start_date=None, end_date=None):
    """Filter analysis results by time period"""
    try:
        # If no filtering needed, return original results
        if not start_date and not end_date:
            return results
            
        # Create a copy of results to modify
        filtered = copy.deepcopy(results)
        
        # Convert date strings to datetime objects
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.datetime.fromisoformat(start_date)
            except ValueError:
                # Try different format if ISO format fails
                start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        
        if end_date:
            try:
                end_datetime = datetime.datetime.fromisoformat(end_date)
            except ValueError:
                # Try different format if ISO format fails
                end_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
        
        # Filter thread results
        original_threads = results.get('thread_results', [])
        filtered_threads = []
        
        for thread in original_threads:
            # Check thread timestamps
            thread_time = None
            
            # First try last_message_time as the thread time
            if 'last_message_time' in thread:
                try:
                    thread_time = time_utils.parse_datetime(thread['last_message_time'])
                except:
                    pass
            
            # If that fails, try first_message_time
            if not thread_time and 'first_message_time' in thread:
                try:
                    thread_time = time_utils.parse_datetime(thread['first_message_time'])
                except:
                    pass
            
            # Skip this thread if we can't determine its time
            if not thread_time:
                continue
                
            # Apply time filters
            if start_datetime and thread_time < start_datetime:
                continue
            if end_datetime and thread_time > end_datetime:
                continue
                
            # Thread passed time filters
            filtered_threads.append(thread)
        
        # Update filtered results with filtered threads
        filtered['thread_results'] = filtered_threads
        filtered['thread_count'] = len(filtered_threads)
        
        # If there are no threads in the filtered results, return empty categories
        if not filtered_threads:
            add_log("No threads in specified time period")
            # Return empty structure with metadata
            filtered = {
                'categories': [],
                'top_discussions': [],
                'response_quality': {
                    'average_score': 0,
                    'good_examples': [],
                    'poor_examples': []
                },
                'improvement_areas': [],
                'user_satisfaction': {
                    'overall_assessment': 'No data for selected time period',
                    'positive_indicators': [],
                    'negative_indicators': []
                },
                'unmet_needs': [],
                'key_insights': [],
                'thread_results': [],
                'analysis_metadata': {
                    'filtered': True,
                    'original_thread_count': len(original_threads),
                    'filtered_thread_count': 0,
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            return filtered
            
        # Recombine results with only the filtered threads to generate time-specific insights
        add_log(f"Regenerating insights for {len(filtered_threads)} threads in time period")
        
        # Generate combined insights based on filtered threads
        updated_insights = claude_analyzer.combine_results(filtered_threads)
        
        # Update insight fields while keeping thread_results and metadata
        for key, value in updated_insights.items():
            if key != 'thread_results' and key != 'analysis_metadata':
                filtered[key] = value
        
        # Update metadata to indicate filtering
        if 'analysis_metadata' not in filtered:
            filtered['analysis_metadata'] = {}
            
        filtered['analysis_metadata']['filtered'] = True
        filtered['analysis_metadata']['original_thread_count'] = len(original_threads)
        filtered['analysis_metadata']['filtered_thread_count'] = len(filtered_threads)
        filtered['analysis_metadata']['start_date'] = start_date
        filtered['analysis_metadata']['end_date'] = end_date
        
        return filtered
        
    except Exception as e:
        add_log(f"Error filtering results by time: {str(e)}", "error")
        # Return original results if filtering fails
        return results
