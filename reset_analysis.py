#!/usr/bin/env python3
"""
Reset script for HitCraft Chat Analyzer
Clears all analysis results and resets thread analysis state
"""
import os
import json
import shutil
from pathlib import Path

# Get the base directory
base_dir = Path(__file__).resolve().parent

# Clear analysis_results directory
analysis_results_dir = base_dir / "analysis_results"
if analysis_results_dir.exists():
    print(f"Clearing {analysis_results_dir}...")
    for file in analysis_results_dir.glob("*"):
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    print("Analysis results cleared.")
else:
    print(f"Analysis results directory not found at {analysis_results_dir}")

# Reset thread metadata
thread_metadata_file = base_dir / "organized_threads" / "thread_metadata.json"
if thread_metadata_file.exists():
    print(f"Creating backup of {thread_metadata_file}...")
    # Create backup
    shutil.copy(thread_metadata_file, thread_metadata_file.with_suffix(".backup.json"))
    
    # Reset analyzed state
    print("Resetting thread analysis state...")
    try:
        with open(thread_metadata_file, 'r') as f:
            data = json.load(f)
            
        modified = False
        for thread in data:
            if thread.get('analyzed', False):
                thread['analyzed'] = False
                modified = True
                
        if modified:
            with open(thread_metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Reset {sum(1 for thread in data if not thread.get('analyzed', False))} threads to unanalyzed state.")
        else:
            print("No analyzed threads found, nothing to reset.")
    except Exception as e:
        print(f"Error resetting thread metadata: {e}")
else:
    print(f"Thread metadata file not found at {thread_metadata_file}")
    
# Clear any temp files in session directories
temp_dir = base_dir / "temp_chunks"
if temp_dir.exists():
    print(f"Clearing temporary files in {temp_dir}...")
    for file in temp_dir.glob("*"):
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    print("Temporary files cleared.")

print("\nAnalysis history reset complete! Please restart the server for changes to take effect.")
