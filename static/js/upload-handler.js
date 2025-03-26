/**
 * upload-handler.js - Handles file upload and analysis process
 * Updated for tabbed workflow with Thread Creator, Thread Analyzer, and Dashboard tabs
 */

// Global state
let state = {
    filename: null,
    sessionId: null,
    threadCount: 0,
    threadsAnalyzed: 0,
    previouslyAnalyzed: 0,
    availableThreads: 0,
    threadsToAnalyze: 0,
    analysisInProgress: false,
    analysisComplete: false
};

// Polling interval for progress updates
let progressInterval = null;

/**
 * Fetch the Claude API key from the server
 */
function fetchClaudeApiKey() {
    const apiKeyInput = document.getElementById('claude-api-key');
    
    // Show loading state
    if (apiKeyInput) {
        apiKeyInput.placeholder = "Loading API key from server...";
    }
    
    fetch('/api/claude-key')
        .then(response => response.json())
        .then(data => {
            if (data.api_key) {
                // We have a valid API key
                if (apiKeyInput) {
                    apiKeyInput.value = "API key loaded from server";
                    // Store the API key in a variable for later use (not exposing in UI)
                    window.claudeApiKey = data.api_key;
                }
            } else if (data.error) {
                // Show error in the input
                if (apiKeyInput) {
                    apiKeyInput.value = "";
                    apiKeyInput.placeholder = "Error: API key not configured on server";
                    apiKeyInput.classList.add('is-invalid');
                }
                console.error('Failed to load API key:', data.error);
            }
        })
        .catch(error => {
            console.error('Error fetching API key:', error);
            if (apiKeyInput) {
                apiKeyInput.value = "";
                apiKeyInput.placeholder = "Error loading API key";
                apiKeyInput.classList.add('is-invalid');
            }
        });
}

/**
 * Initialize the thread counts for the Thread Creator tab
 */
function initializeThreadCounts() {
    // Get existing thread count
    fetch('/api/thread_count')
        .then(response => response.json())
        .then(data => {
            updateThreadCountUI(data.count);
            
            // Update the available thread count on the analyzer tab too
            document.getElementById('available-threads-count').textContent = data.count;
            state.availableThreads = data.count;
            
            // Update previously analyzed count if available
            if (data.previously_analyzed) {
                document.getElementById('previously-analyzed-count').textContent = data.previously_analyzed;
                state.previouslyAnalyzed = data.previously_analyzed;
            }
        })
        .catch(error => {
            console.error('Error fetching thread count:', error);
        });
}

/**
 * Update thread count UI elements
 */
function updateThreadCountUI(count) {
    const threadCountElement = document.getElementById('existing-threads-count');
    if (threadCountElement) {
        threadCountElement.textContent = count;
    }
    
    // Enable or disable the Thread Analyzer tab based on thread count
    const threadAnalyzerNavBtn = document.getElementById('threadAnalyzerNavBtn');
    if (threadAnalyzerNavBtn) {
        if (count > 0) {
            threadAnalyzerNavBtn.classList.remove('disabled');
        } else {
            threadAnalyzerNavBtn.classList.add('disabled');
        }
    }
}

/**
 * Handle file upload form submission
 * @param {Event} e - Form submit event
 */
function handleFileUpload(e) {
    e.preventDefault();
    console.log("Form submitted - handleFileUpload function called");
    
    // Get file input
    const fileInput = document.getElementById('file');
    const uploadStatus = document.getElementById('upload-status');
    
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        console.error("No file selected");
        if (uploadStatus) {
            uploadStatus.textContent = 'Please select a file to upload';
            uploadStatus.className = 'alert alert-danger mt-3';
            uploadStatus.classList.remove('d-none');
        }
        return;
    }
    
    console.log("File selected:", fileInput.files[0].name);
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // Show loading status
    if (uploadStatus) {
        uploadStatus.textContent = 'Uploading file...';
        uploadStatus.className = 'alert alert-info mt-3';
        uploadStatus.classList.remove('d-none');
    }
    
    // Upload the file
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log("Upload response:", data);
        if (data.success) {
            // Show success message
            if (uploadStatus) {
                uploadStatus.textContent = 'File uploaded successfully! Extracting threads...';
                uploadStatus.className = 'alert alert-success mt-3';
            }
            
            // Now extract threads
            fetch('/api/extract_threads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ filepath: data.filepath })
            })
            .then(response => response.json())
            .then(threadData => {
                console.log("Thread extraction response:", threadData);
                if (threadData.success) {
                    // Update UI with success
                    if (uploadStatus) {
                        uploadStatus.textContent = `Successfully extracted ${threadData.thread_count} threads!`;
                        uploadStatus.className = 'alert alert-success mt-3';
                    }
                    
                    // Enable the Thread Analyzer tab
                    const threadAnalyzerTab = document.getElementById('thread-analyzer-tab');
                    if (threadAnalyzerTab) {
                        threadAnalyzerTab.classList.remove('disabled');
                        // Switch to the Thread Analyzer tab
                        const tabEl = document.querySelector('button[data-bs-target="#threadAnalyzerTab"]');
                        if (tabEl) {
                            const tab = new bootstrap.Tab(tabEl);
                            tab.show();
                        }
                    }
                } else {
                    // Show error
                    if (uploadStatus) {
                        uploadStatus.textContent = threadData.message || 'Error extracting threads';
                        uploadStatus.className = 'alert alert-danger mt-3';
                    }
                }
            })
            .catch(error => {
                console.error("Thread extraction error:", error);
                if (uploadStatus) {
                    uploadStatus.textContent = 'Error extracting threads: ' + error.message;
                    uploadStatus.className = 'alert alert-danger mt-3';
                }
            });
        } else {
            // Show error
            if (uploadStatus) {
                uploadStatus.textContent = data.message || 'Error uploading file';
                uploadStatus.className = 'alert alert-danger mt-3';
            }
        }
    })
    .catch(error => {
        console.error("Upload error:", error);
        if (uploadStatus) {
            uploadStatus.textContent = 'Error uploading file: ' + error.message;
            uploadStatus.className = 'alert alert-danger mt-3';
        }
    });
}

/**
 * Initialize the thread analyzer tab
 */
function initializeThreadAnalyzer() {
    // Set up thread count slider
    const threadCountSlider = document.getElementById('thread-count-slider');
    const threadCountValue = document.getElementById('thread-count-value');
    const threadCountMax = document.getElementById('thread-count-max');
    
    // Get the maximum number of threads
    fetch('/api/thread_count')
        .then(response => response.json())
        .then(data => {
            const maxThreads = data.count;
            
            // Update UI elements
            if (threadCountMax) {
                threadCountMax.textContent = maxThreads;
            }
            
            if (threadCountSlider) {
                threadCountSlider.max = maxThreads;
                threadCountSlider.value = Math.min(maxThreads, 10);
                
                // Update the thread count value
                if (threadCountValue) {
                    threadCountValue.textContent = threadCountSlider.value;
                    state.threadsToAnalyze = parseInt(threadCountSlider.value);
                }
                
                // Add event listener for slider change
                threadCountSlider.addEventListener('input', function() {
                    threadCountValue.textContent = this.value;
                    state.threadsToAnalyze = parseInt(this.value);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching thread count:', error);
        });
        
    // Setup start analysis button
    const startAnalysisBtn = document.getElementById('start-analysis-btn');
    if (startAnalysisBtn) {
        startAnalysisBtn.addEventListener('click', function() {
            startThreadAnalysis(state.threadsToAnalyze);
        });
    }
    
    // Setup view dashboard button
    const viewDashboardBtn = document.getElementById('view-dashboard-btn');
    if (viewDashboardBtn) {
        viewDashboardBtn.addEventListener('click', function() {
            showScreen('dashboardScreen');
        });
    }
    
    // Setup cancel analysis button
    const cancelAnalysisBtn = document.getElementById('cancel-analysis-btn');
    if (cancelAnalysisBtn) {
        cancelAnalysisBtn.addEventListener('click', function() {
            cancelAnalysis();
        });
    }
}

/**
 * Start analysis of selected threads
 * @param {number} threadCount - Number of threads to analyze
 */
function startThreadAnalysis(threadCount) {
    if (!threadCount) {
        showMessage('analysis-status', 'Please select at least one thread to analyze', 'danger');
        return;
    }
    
    // Setup analyzer UI for progress tracking
    showAnalysisProgressUI(threadCount);
    
    addProcessingLog(`Starting analysis of ${threadCount} conversation threads...`, 'info');
    
    // Make API call to start analysis
    fetch('/api/analyze_threads', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            thread_count: threadCount
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to start analysis');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Analysis started:', data);
        
        // Update state
        state.analysisInProgress = true;
        state.threadsToAnalyze = threadCount;
        
        // Start polling for progress updates
        startProgressPolling();
        
        // Enable dashboard navigation
        enableDashboardNavigation();
    })
    .catch(error => {
        console.error('Error starting analysis:', error);
        addProcessingLog(`Error starting analysis: ${error.message}`, 'error');
        
        // Show error message
        const progressCard = document.getElementById('analysis-progress-card');
        if (progressCard) {
            progressCard.classList.add('d-none');
        }
        
        const selectionCard = document.getElementById('thread-selection-card');
        if (selectionCard) {
            selectionCard.classList.remove('d-none');
        }
    });
}

/**
 * Show the analysis progress UI
 * @param {number} threadCount - Total number of threads to analyze
 */
function showAnalysisProgressUI(threadCount) {
    // Hide thread selection card and show progress card
    const selectionCard = document.getElementById('thread-selection-card');
    const progressCard = document.getElementById('analysis-progress-card');
    
    if (selectionCard) {
        selectionCard.classList.add('d-none');
    }
    
    if (progressCard) {
        progressCard.classList.remove('d-none');
    }
    
    // Update the total thread count
    const threadsTotal = document.getElementById('threads-total');
    if (threadsTotal) {
        threadsTotal.textContent = threadCount;
    }
    
    // Reset progress indicators
    const threadsAnalyzed = document.getElementById('threads-analyzed');
    const analysisPercent = document.getElementById('analysis-percent');
    const progressBar = document.getElementById('analysis-progress-bar');
    
    if (threadsAnalyzed) {
        threadsAnalyzed.textContent = '0';
    }
    
    if (analysisPercent) {
        analysisPercent.textContent = '0%';
    }
    
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressBar.classList.add('progress-bar-animated');
        progressBar.classList.add('progress-bar-striped');
    }
    
    // Add initial log entry
    addProcessingLog(`Preparing to analyze ${threadCount} threads...`, 'info');
}

/**
 * Start polling for analysis progress updates
 */
function startProgressPolling() {
    // Clear any existing interval
    stopProgressPolling();
    
    // Start new polling interval
    progressInterval = setInterval(() => {
        fetch('/api/check_progress')
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to check progress');
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Progress update:', data);
                
                // Update progress UI
                updateAnalysisProgress(data);
                
                // Check if analysis is complete
                if (data.status === 'complete') {
                    completeAnalysis(data.threads_analyzed, state.threadsToAnalyze);
                }
            })
            .catch(error => {
                console.error('Error checking progress:', error);
                addProcessingLog(`Error checking progress: ${error.message}`, 'error');
            });
    }, 2000); // Poll every 2 seconds
}

/**
 * Stop polling for progress updates
 */
function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

/**
 * Update the analysis progress UI
 * @param {Object} progressData - Progress data from the server
 */
function updateAnalysisProgress(progressData) {
    // Update state
    state.threadsAnalyzed = progressData.threads_analyzed;
    
    // Update UI elements
    const threadsAnalyzedElement = document.getElementById('threads-analyzed');
    const analysisPercentElement = document.getElementById('analysis-percent');
    const progressBar = document.getElementById('analysis-progress-bar');
    
    if (threadsAnalyzedElement) {
        threadsAnalyzedElement.textContent = progressData.threads_analyzed;
    }
    
    if (analysisPercentElement) {
        analysisPercentElement.textContent = `${progressData.progress_percent}%`;
    }
    
    if (progressBar) {
        progressBar.style.width = `${progressData.progress_percent}%`;
        progressBar.setAttribute('aria-valuenow', progressData.progress_percent);
    }
    
    // Add any new log entries
    if (progressData.log_entries && Array.isArray(progressData.log_entries)) {
        progressData.log_entries.forEach(entry => {
            addProcessingLog(entry, 'info', false); // Don't add timestamp
        });
    }
}

/**
 * Cancel the ongoing analysis
 */
function cancelAnalysis() {
    if (!state.analysisInProgress) return;
    
    // Confirm cancellation
    if (!confirm('Are you sure you want to cancel the analysis? Current progress will be saved.')) {
        return;
    }
    
    // Make API call to cancel analysis
    fetch('/api/cancel_analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filename: state.filename
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to cancel analysis');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Analysis cancelled:', data);
        
        // Update state
        state.analysisInProgress = false;
        
        // Update UI
        addProcessingLog('Analysis cancelled. You can view the results analyzed so far.', 'warning');
        
        // Remove progress polling
        stopProgressPolling();
        
        // Update the UI to show cancellation
        const progressBar = document.getElementById('analysis-progress-bar');
        if (progressBar) {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.remove('progress-bar-striped');
        }
        
        // Replace cancel button with a message
        const cancelButton = document.getElementById('cancel-analysis-btn');
        if (cancelButton) {
            const parent = cancelButton.parentNode;
            parent.removeChild(cancelButton);
            
            const message = document.createElement('span');
            message.className = 'text-muted';
            message.innerHTML = '<i class="bi bi-info-circle"></i> Analysis cancelled';
            parent.appendChild(message);
        }
    })
    .catch(error => {
        console.error('Error cancelling analysis:', error);
        addProcessingLog(`Error cancelling analysis: ${error.message}`, 'error');
    });
}

/**
 * Complete the analysis process
 * @param {number} threadsAnalyzed - Number of threads analyzed
 * @param {number} totalThreads - Total number of threads
 */
function completeAnalysis(threadsAnalyzed, totalThreads) {
    // Update state
    state.analysisInProgress = false;
    state.analysisComplete = true;
    state.threadsAnalyzed = threadsAnalyzed;
    
    // Stop progress polling
    stopProgressPolling();
    
    // Update UI to show completion
    addProcessingLog('Analysis complete! All selected threads have been analyzed.', 'success');
    
    const progressBar = document.getElementById('analysis-progress-bar');
    if (progressBar) {
        progressBar.classList.remove('progress-bar-animated');
        progressBar.classList.remove('progress-bar-striped');
        progressBar.classList.add('bg-success');
    }
    
    // Remove cancel button
    const cancelButton = document.getElementById('cancel-analysis-btn');
    if (cancelButton) {
        cancelButton.parentNode.removeChild(cancelButton);
    }
    
    // Update view dashboard button
    const viewDashboardBtn = document.getElementById('view-dashboard-btn');
    if (viewDashboardBtn) {
        viewDashboardBtn.innerHTML = '<i class="bi bi-graph-up"></i> View Complete Results';
        viewDashboardBtn.classList.remove('btn-outline-primary');
        viewDashboardBtn.classList.add('btn-success');
    }
    
    // Load and display the final results
    loadAndDisplayResults(state.filename);
    
    // Automatically switch to dashboard screen after a brief delay
    setTimeout(() => {
        showScreen('dashboardScreen');
    }, 1500);
}

/**
 * Load and display analysis results
 * @param {string} filename - The filename to get results for
 */
function loadAndDisplayResults(filename) {
    if (!filename) return;
    
    console.log("Loading results for:", filename);
    
    fetch(`/get_results/${filename}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load results');
                });
            }
            return response.json();
        })
        .then(results => {
            console.log('Results loaded:', results);
            
            // Use the results-display.js to update the UI
            if (typeof updateDashboard === 'function') {
                updateDashboard(results);
            } else {
                console.error('updateDashboard function not found. Make sure results-display.js is loaded.');
            }
        })
        .catch(error => {
            console.error('Error loading results:', error);
            addProcessingLog(`Error loading results: ${error.message}`, 'error');
        });
}

/**
 * Add a log entry to the processing log
 * @param {string} message - The message to log
 * @param {string} level - Log level (info, success, warning, error)
 * @param {boolean} addTimestamp - Whether to add a timestamp
 */
function addProcessingLog(message, level = 'info', addTimestamp = true) {
    const logContainer = document.getElementById('processing-log');
    if (!logContainer) return;
    
    // Create log entry element
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${level}`;
    
    // Add timestamp if requested
    let logMessage = message;
    if (addTimestamp) {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        logMessage = `[${timeString}] ${message}`;
    }
    
    // Set icon based on level
    let icon = 'info-circle';
    switch (level) {
        case 'success':
            icon = 'check-circle';
            break;
        case 'warning':
            icon = 'exclamation-triangle';
            break;
        case 'error':
            icon = 'x-circle';
            break;
    }
    
    // Set the log entry content
    logEntry.innerHTML = `<i class="bi bi-${icon}"></i> ${logMessage}`;
    
    // Add to log container
    logContainer.appendChild(logEntry);
    
    // Scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Enable navigation to Thread Analyzer tab
 */
function enableThreadAnalyzerNavigation() {
    // Enable thread analyzer navigation
    document.getElementById('threadAnalyzerNavBtn').classList.remove('disabled');
}

/**
 * Enable navigation to Dashboard tab
 */
function enableDashboardNavigation() {
    // Enable dashboard navigation
    document.getElementById('dashboardNavBtn').classList.remove('disabled');
}

/**
 * Show a message in the specified element
 * @param {string} elementId - The ID of the element to show the message in
 * @param {string} message - The message to display
 * @param {string} type - The type of message (info, success, warning, danger)
 */
function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `alert alert-${type} mt-4`;
        element.classList.remove('d-none');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            element.classList.add('d-none');
        }, 5000);
    }
}

/**
 * Extract threads from the uploaded file
 * @param {string} filepath - The path to the uploaded file
 */
function extractThreadsFromUploadedFile(filepath) {
    // Make API call to extract threads
    fetch('/api/extract_threads', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filepath: filepath
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to extract threads');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Thread extraction success:', data);
        
        // Update state with thread count
        state.threadCount = data.thread_count;
        
        // Log thread extraction success
        addProcessingLog(`Successfully extracted ${data.thread_count} conversation threads!`, 'success');
        
        if (data.thread_count === 0) {
            addProcessingLog('No valid conversation threads found in the file.', 'warning');
            setTimeout(() => {
                showScreen('threadCreatorScreen');
                showMessage('upload-status', 'No valid conversation threads found in the file', 'warning');
            }, 2000);
            return;
        }
        
        // Update thread count UI
        initializeThreadCounts();
        
        // Return to the Thread Creator tab
        setTimeout(() => {
            showScreen('threadCreatorScreen');
            showMessage('upload-status', `Successfully extracted ${data.thread_count} threads from your file!`, 'success');
        }, 2000);
    })
    .catch(error => {
        console.error('Error extracting threads:', error);
        addProcessingLog(`Error extracting threads: ${error.message}`, 'error');
        
        // Return to Thread Creator screen after a delay
        setTimeout(() => {
            showScreen('threadCreatorScreen');
            showMessage('upload-status', `Error: ${error.message}`, 'danger');
        }, 2000);
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing upload handler');
    
    // Fetch the Claude API key from server
    fetchClaudeApiKey();
    
    // Initialize thread counts
    initializeThreadCounts();
    
    // Initialize the thread analyzer tab
    initializeThreadAnalyzer();
    
    // Set up file upload form
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        console.log('Found upload form, attaching submit event');
        uploadForm.addEventListener('submit', handleFileUpload);
    } else {
        console.error('Upload form not found on page');
    }
    
    // Set up view threads button
    const viewThreadsBtn = document.getElementById('view-threads-btn');
    if (viewThreadsBtn) {
        viewThreadsBtn.addEventListener('click', () => {
            // This action would typically show a threads modal or navigate to a threads view
            // For now, we will just show a message
            alert('Thread viewing functionality coming soon!');
        });
    }
});
