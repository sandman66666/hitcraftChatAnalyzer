/**
 * UI Manager - Handles UI state and transitions for the HitCraft Chat Analyzer
 * This manages the two-phase workflow for conversation thread analysis
 */

class UIManager {
    constructor() {
        this.state = {
            currentScreen: 'uploadScreen',
            currentFilename: null,
            processingActive: false,
            threadExtracted: false,
            threadCount: 0,
            threadsToAnalyze: 0,
            threadsAnalyzed: 0,
            analysisInProgress: false,
            analysisComplete: false
        };
        
        // DOM elements cache
        this.elements = {
            processingLog: document.getElementById('processing-log'),
            uploadStatus: document.getElementById('upload-status'),
            uploadArea: document.getElementById('upload-area'),
            fileInput: document.getElementById('file')
        };
        
        this.setupEventListeners();
        this.initializeFileUpload();
        
        console.log('UIManager initialized with elements:', this.elements);
    }
    
    setupEventListeners() {
        // Disable form submission for upload
        const uploadForm = document.getElementById('upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFileUpload();
            });
        }
    }
    
    /**
     * Initialize the file upload area
     */
    initializeFileUpload() {
        const { uploadArea, fileInput } = this.elements;
        
        if (!uploadArea || !fileInput) {
            console.error('Upload area or file input not found:', { 
                uploadArea: !!uploadArea, 
                fileInput: !!fileInput 
            });
            return;
        }
        
        console.log('Initializing file upload with elements:', {
            uploadArea: uploadArea,
            fileInput: fileInput
        });
        
        // Make the entire upload area clickable to open file dialog
        uploadArea.addEventListener('click', (e) => {
            // Don't trigger if we clicked on the input itself (to avoid double triggers)
            console.log('Upload area clicked', e.target);
            if (e.target !== fileInput) {
                e.preventDefault();
                console.log('Triggering file input click');
                fileInput.click();
            }
        });
        
        // Process file selection
        fileInput.addEventListener('change', () => {
            console.log('File input changed:', fileInput.files);
            if (fileInput.files && fileInput.files[0]) {
                const fileName = fileInput.files[0].name;
                const fileSize = (fileInput.files[0].size / 1024).toFixed(2) + ' KB';
                
                // Update the upload area UI
                const uploadIcon = uploadArea.querySelector('.upload-icon');
                const uploadTitle = uploadArea.querySelector('.upload-title');
                const uploadInfo = uploadArea.querySelector('.upload-info');
                
                if (uploadIcon) uploadIcon.innerHTML = this.getFileTypeIcon(fileName);
                if (uploadTitle) uploadTitle.textContent = fileName;
                if (uploadInfo) uploadInfo.textContent = fileSize;
                
                // Add selected state class
                uploadArea.classList.add('file-selected');
            }
        });
        
        // Handle drag & drop
        ['dragover', 'dragenter'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                console.log('Drag event:', eventName);
                uploadArea.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                console.log('Drag event:', eventName);
                uploadArea.classList.remove('drag-over');
            });
        });
        
        // Handle file drop
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            console.log('File dropped');
            
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                fileInput.files = e.dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
        
        console.log('File upload initialization complete!');
    }
    
    /**
     * Get appropriate icon based on file extension
     */
    getFileTypeIcon(fileName) {
        const extension = fileName.split('.').pop().toLowerCase();
        let icon = '<i class="bi bi-file-earmark-text"></i>';
        
        if (extension === 'json') {
            icon = '<i class="bi bi-filetype-json"></i>';
        } else if (extension === 'txt') {
            icon = '<i class="bi bi-filetype-txt"></i>';
        } else if (extension === 'csv') {
            icon = '<i class="bi bi-filetype-csv"></i>';
        }
        
        return icon;
    }
    
    /**
     * Switch to a different screen in the application
     * @param {string} screenId - The ID of the screen to display
     */
    showScreen(screenId) {
        // Update state
        this.state.currentScreen = screenId;
        
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        // Show the requested screen
        const targetScreen = document.getElementById(screenId);
        if (targetScreen) {
            targetScreen.classList.add('active');
        }
        
        // Update active nav link
        document.querySelectorAll('.sidebar-menu .nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Map screen IDs to nav buttons
        const screenToNav = {
            'uploadScreen': 'uploadNavBtn',
            'processingScreen': null,
            'resultsScreen': 'analysisNavBtn',
            'threadsScreen': 'threadsNavBtn'
        };
        
        // Activate the corresponding nav button
        const navBtnId = screenToNav[screenId];
        if (navBtnId) {
            document.getElementById(navBtnId).classList.add('active');
        }
    }
    
    /**
     * Show the thread selection UI after threads have been extracted
     * @param {number} threadCount - Total number of threads extracted
     */
    showThreadSelectionUI(threadCount) {
        // Create the thread selection UI
        const processingContainer = document.querySelector('.processing-container .container');
        if (!processingContainer) return;
        
        // Update state
        this.state.threadCount = threadCount;
        this.state.threadExtracted = true;
        
        // Create thread selection UI
        const threadSelectionHTML = `
            <div class="card mb-4">
                <div class="card-header bg-success text-white">
                    <h5 class="card-title mb-0">Conversation Threads Extracted</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <h4>Extracted ${threadCount} conversation threads</h4>
                        <p class="text-muted">Now you can select how many threads to analyze</p>
                    </div>
                    
                    <div class="mb-4">
                        <label for="thread-count-slider" class="form-label d-flex justify-content-between">
                            <span>Number of threads to analyze</span>
                            <span class="badge bg-primary" id="thread-count-value">${Math.min(threadCount, 10)}</span>
                        </label>
                        <div class="d-flex align-items-center gap-2">
                            <span class="option-range-min">1</span>
                            <input type="range" class="form-range flex-grow-1" id="thread-count-slider" 
                                min="1" max="${threadCount}" value="${Math.min(threadCount, 10)}">
                            <span class="option-range-max">${threadCount}</span>
                        </div>
                        <div class="d-flex justify-content-between mt-1">
                            <span class="form-text">Faster analysis</span>
                            <span class="form-text">More comprehensive results</span>
                        </div>
                    </div>
                    
                    <div class="d-grid">
                        <button id="start-analysis-btn" class="btn btn-primary btn-lg">
                            <i class="bi bi-lightning"></i> Start Analysis
                        </button>
                    </div>
                    
                    <div class="mt-3 text-center">
                        <small class="text-muted">
                            <i class="bi bi-info-circle"></i> 
                            You'll be able to view results in real-time as threads are analyzed
                        </small>
                    </div>
                </div>
            </div>
        `;
        
        // Update the UI
        processingContainer.innerHTML = threadSelectionHTML + processingContainer.innerHTML.split('<div class="card" id="logs-card">')[1];
        
        // Setup slider
        const slider = document.getElementById('thread-count-slider');
        const valueDisplay = document.getElementById('thread-count-value');
        
        if (slider && valueDisplay) {
            slider.addEventListener('input', () => {
                valueDisplay.textContent = slider.value;
            });
        }
        
        // Setup start analysis button
        const startButton = document.getElementById('start-analysis-btn');
        if (startButton) {
            startButton.addEventListener('click', () => {
                this.startThreadAnalysis(parseInt(slider.value, 10));
            });
        }
    }
    
    /**
     * Start the analysis of selected threads
     * @param {number} threadCount - Number of threads to analyze
     */
    startThreadAnalysis(threadCount) {
        // Update state
        this.state.threadsToAnalyze = threadCount;
        this.state.analysisInProgress = true;
        
        // Update the UI to show analysis progress
        const processingContainer = document.querySelector('.processing-container .container');
        if (!processingContainer) return;
        
        const analysisProgressHTML = `
            <div class="card mb-4">
                <div class="card-header bg-primary text-white">
                    <h5 class="card-title mb-0">Analyzing Conversation Threads</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-2">
                            <h5>Analyzing threads: <span id="threads-analyzed">0</span> of <span id="threads-total">${threadCount}</span></h5>
                            <h5><span id="analysis-percent">0%</span> complete</h5>
                        </div>
                        
                        <div class="progress mb-3" style="height: 20px;">
                            <div id="analysis-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                                role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" style="width: 0%">
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3 d-flex justify-content-between">
                        <button id="view-results-btn" class="btn btn-outline-primary">
                            <i class="bi bi-graph-up"></i> View Current Results
                        </button>
                        
                        <button id="cancel-analysis-btn" class="btn btn-outline-danger">
                            <i class="bi bi-x-circle"></i> Cancel Analysis
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Replace the thread selection UI with the analysis progress UI
        processingContainer.innerHTML = analysisProgressHTML + processingContainer.innerHTML.split('<div class="card" id="logs-card">')[1];
        
        // Setup event listeners
        document.getElementById('view-results-btn').addEventListener('click', () => {
            this.showScreen('resultsScreen');
        });
        
        document.getElementById('cancel-analysis-btn').addEventListener('click', () => {
            this.cancelAnalysis();
        });
        
        // Enable navigation to results screens
        this.enableResultsNavigation();
        
        // Trigger the analysis on the server
        this.triggerThreadAnalysis(threadCount);
    }
    
    /**
     * Enable navigation to results screens
     */
    enableResultsNavigation() {
        // Enable navigation links
        document.querySelectorAll('.sidebar-menu .nav-link.disabled').forEach(link => {
            link.classList.remove('disabled');
        });
    }
    
    /**
     * Update the analysis progress in the UI
     * @param {number} threadsAnalyzed - Number of threads analyzed so far
     * @param {number} totalThreads - Total number of threads to analyze
     */
    updateAnalysisProgress(threadsAnalyzed, totalThreads) {
        // Update state
        this.state.threadsAnalyzed = threadsAnalyzed;
        
        // Calculate percentage
        const percent = Math.round((threadsAnalyzed / totalThreads) * 100);
        
        // Update UI elements
        const threadsAnalyzedElement = document.getElementById('threads-analyzed');
        const analysisPercentElement = document.getElementById('analysis-percent');
        const progressBar = document.getElementById('analysis-progress-bar');
        
        if (threadsAnalyzedElement) {
            threadsAnalyzedElement.textContent = threadsAnalyzed;
        }
        
        if (analysisPercentElement) {
            analysisPercentElement.textContent = `${percent}%`;
        }
        
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.setAttribute('aria-valuenow', percent);
        }
        
        // Check if analysis is complete
        if (threadsAnalyzed >= totalThreads) {
            this.completeAnalysis();
        }
    }
    
    /**
     * Finalize the analysis process
     */
    completeAnalysis() {
        // Update state
        this.state.analysisInProgress = false;
        this.state.analysisComplete = true;
        
        // Update UI to show completion
        const progressBar = document.getElementById('analysis-progress-bar');
        if (progressBar) {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.remove('progress-bar-striped');
            progressBar.classList.add('bg-success');
            progressBar.setAttribute('aria-valuenow', 100);
            progressBar.style.width = '100%';
        }
        
        // Remove cancel button
        const cancelButton = document.getElementById('cancel-analysis-btn');
        if (cancelButton) {
            cancelButton.parentNode.removeChild(cancelButton);
        }
        
        // Update view results button
        const viewResultsButton = document.getElementById('view-results-btn');
        if (viewResultsButton) {
            viewResultsButton.textContent = 'View Complete Results';
            viewResultsButton.classList.remove('btn-outline-primary');
            viewResultsButton.classList.add('btn-success');
            viewResultsButton.classList.add('btn-lg');
            viewResultsButton.classList.add('w-100');
            
            // Make sure the button is clickable
            viewResultsButton.disabled = false;
        }
        
        // Enable the analysis tab
        this.enableAnalysisTab();
        
        // Add a log entry
        this.addProcessingLogEntry('Analysis complete! All selected threads have been analyzed.');
        
        // Automatically switch to results screen after a brief delay
        setTimeout(() => {
            this.showScreen('resultsScreen');
            
            // Load the analysis results
            this.loadAnalysisResults();
        }, 1500);
    }
    
    /**
     * Enable the analysis tab after analysis is complete
     */
    enableAnalysisTab() {
        // Enable the analysis tab
        const analysisTab = document.getElementById('analysis-tab');
        if (analysisTab) {
            analysisTab.classList.remove('disabled');
            analysisTab.setAttribute('aria-disabled', 'false');
            analysisTab.setAttribute('data-bs-toggle', 'tab');
        }
        
        // Make sure we have an active tab highlighted
        const navTabs = document.querySelectorAll('.nav-tabs .nav-link');
        let hasActiveTab = false;
        
        navTabs.forEach(tab => {
            if (tab.classList.contains('active')) {
                hasActiveTab = true;
            }
        });
        
        // If no active tab, activate the first one
        if (!hasActiveTab && navTabs.length > 0) {
            navTabs[0].classList.add('active');
        }
        
        console.log("Analysis tab enabled");
    }
    
    /**
     * Load and display analysis results
     */
    loadAnalysisResults() {
        this.addProcessingLogEntry('Loading analysis results...');
        
        fetch(`/api/get_analysis_results?filename=${this.state.currentFilename}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.results) {
                    this.displayAnalysisResults(data.results);
                    this.addProcessingLogEntry('Analysis results loaded successfully.');
                } else {
                    this.addProcessingLogEntry('Error loading analysis results: ' + (data.error || 'No results found'));
                }
            })
            .catch(error => {
                console.error('Error loading analysis results:', error);
                this.addProcessingLogEntry('Error loading analysis results: ' + error.message);
            });
    }
    
    /**
     * Cancel the ongoing analysis
     */
    cancelAnalysis() {
        if (!this.state.analysisInProgress) return;
        
        // Confirm cancellation
        if (!confirm('Are you sure you want to cancel the analysis? Current progress will be saved.')) {
            return;
        }
        
        // Update state
        this.state.analysisInProgress = false;
        
        // Make API call to cancel analysis
        fetch('/api/cancel_analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: this.state.currentFilename
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.addProcessingLogEntry('Analysis cancelled. You can view the results analyzed so far.');
                
                // Update UI
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
            } else {
                this.addProcessingLogEntry('Error cancelling analysis: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error cancelling analysis:', error);
            this.addProcessingLogEntry('Error cancelling analysis: ' + error.message);
        });
    }
    
    /**
     * Trigger the thread analysis on the server
     * @param {number} threadCount - Number of threads to analyze
     */
    triggerThreadAnalysis(threadCount) {
        this.addProcessingLogEntry(`Starting analysis of ${threadCount} conversation threads...`);
        
        // Make API call to start the analysis
        fetch('/api/analyze_threads', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: this.state.currentFilename,
                count: threadCount
            })
        })
        .then(response => {
            if (!response.ok) {
                console.error('Error starting analysis:', response.status, response.statusText);
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP error ${response.status}: ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'started' || data.success) {
                this.addProcessingLogEntry('Analysis started successfully.');
                
                // Start polling for progress updates
                this.startProgressPolling();
            } else {
                this.addProcessingLogEntry('Error starting analysis: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error starting analysis:', error);
            this.addProcessingLogEntry('Error starting analysis: ' + error.message);
            
            // Show retry button if analysis failed to start
            const analysisContainer = document.querySelector('.card-body');
            if (analysisContainer && !document.getElementById('retry-analysis-btn')) {
                const retryButton = document.createElement('button');
                retryButton.id = 'retry-analysis-btn';
                retryButton.className = 'btn btn-warning mt-3 w-100';
                retryButton.innerHTML = '<i class="bi bi-arrow-repeat"></i> Retry Analysis';
                retryButton.addEventListener('click', () => {
                    this.triggerThreadAnalysis(threadCount);
                    retryButton.remove();
                });
                analysisContainer.appendChild(retryButton);
            }
        });
    }
    
    /**
     * Start polling for progress updates during analysis
     */
    startProgressPolling() {
        // Clear any existing interval
        if (this._progressInterval) {
            clearInterval(this._progressInterval);
        }
        
        // Update state to show analysis is in progress
        this.state.analysisInProgress = true;
        
        // Set up polling interval
        this._progressInterval = setInterval(() => {
            // Only poll if analysis is in progress
            if (!this.state.analysisInProgress) {
                clearInterval(this._progressInterval);
                return;
            }
            
            // Poll for progress
            fetch(`/api/analysis_progress?filename=${this.state.currentFilename}`)
                .then(response => response.json())
                .then(data => {
                    console.log("Progress update:", data); // Debug logging
                    
                    if (data.success) {
                        // Update progress
                        this.updateAnalysisProgress(data.threads_analyzed, data.threads_total);
                        
                        // If there are new log entries, add them
                        if (data.log_entries && Array.isArray(data.log_entries)) {
                            data.log_entries.forEach(entry => {
                                this.addProcessingLogEntry(entry, false); // Don't add timestamp
                            });
                        }
                        
                        // If analysis is complete, stop polling and mark as complete
                        if (data.status === 'complete') {
                            clearInterval(this._progressInterval);
                            this.completeAnalysis();
                            
                            // Debug logging
                            console.log("Analysis completed, showing results");
                            this.addProcessingLogEntry("Analysis complete! Results are ready to view.");
                        }
                    } else if (data.error) {
                        this.addProcessingLogEntry(`Error checking progress: ${data.error}`);
                    }
                })
                .catch(error => {
                    console.error('Error polling for progress:', error);
                    this.addProcessingLogEntry(`Error checking progress: ${error.message}`);
                });
        }, 2000); // Poll every 2 seconds
    }
    
    /**
     * Handle the file upload and extraction of threads
     */
    handleFileUpload() {
        const fileInput = document.getElementById('file');
        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
            this.showMessage('upload-status', 'Please select a file to upload', 'danger');
            return;
        }
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        // Show processing screen
        this.showScreen('processingScreen');
        this.addProcessingLogEntry(`Uploading file: ${file.name}...`);
        
        // Upload the file
        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update state
                this.state.currentFilename = data.filename;
                
                this.addProcessingLogEntry(`File uploaded successfully. Extracting conversation threads...`);
                
                // Extract threads
                return fetch('/api/extract_threads', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        filename: data.filename
                    })
                });
            } else {
                throw new Error(data.error || 'Unknown error during file upload');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.addProcessingLogEntry(`Successfully extracted ${data.thread_count} conversation threads.`);
                
                // Show thread selection UI
                this.showThreadSelectionUI(data.thread_count);
            } else {
                throw new Error(data.error || 'Unknown error during thread extraction');
            }
        })
        .catch(error => {
            console.error('Error during upload/extraction:', error);
            this.addProcessingLogEntry(`Error: ${error.message}`);
            this.showMessage('upload-status', error.message, 'danger');
            
            // Go back to upload screen
            setTimeout(() => {
                this.showScreen('uploadScreen');
            }, 2000);
        });
    }
    
    /**
     * Add an entry to the processing log
     * @param {string} message - The message to log
     * @param {boolean} addTimestamp - Whether to add a timestamp
     */
    addProcessingLogEntry(message, addTimestamp = true) {
        if (!this.elements.processingLog) {
            this.elements.processingLog = document.getElementById('processing-log');
        }
        
        if (!this.elements.processingLog) return;
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        if (addTimestamp) {
            const timestamp = new Date().toLocaleTimeString();
            const timeElement = document.createElement('span');
            timeElement.className = 'log-time';
            timeElement.textContent = `[${timestamp}]`;
            entry.appendChild(timeElement);
        }
        
        const messageText = document.createTextNode(message);
        entry.appendChild(messageText);
        
        this.elements.processingLog.appendChild(entry);
        
        // Scroll to bottom
        this.elements.processingLog.scrollTop = this.elements.processingLog.scrollHeight;
    }
    
    /**
     * Show a message in the specified element
     * @param {string} elementId - The ID of the element to show the message in
     * @param {string} message - The message to display
     * @param {string} type - The type of message (info, success, warning, danger)
     */
    showMessage(elementId, message, type = 'info') {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.textContent = message;
        element.className = `alert alert-${type} mt-4`;
        element.classList.remove('d-none');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            element.classList.add('d-none');
        }, 5000);
    }

    /**
     * Display analysis results in the UI
     * @param {Object} results - The analysis results from the server
     */
    displayAnalysisResults(results) {
        console.log("Displaying analysis results:", results);
        
        // Get the results container
        const resultsContainer = document.getElementById('analysis-results-container');
        if (!resultsContainer) {
            console.error("Results container not found");
            return;
        }
        
        // Clear previous results
        resultsContainer.innerHTML = '';
        
        // Create header
        const header = document.createElement('div');
        header.className = 'analysis-header mb-4';
        header.innerHTML = `
            <h2>Analysis Results</h2>
            <p class="text-muted">Analyzed ${results.thread_count || 0} threads on ${new Date(results.date).toLocaleString()}</p>
        `;
        resultsContainer.appendChild(header);
        
        // Create categories section
        if (results.top_categories && results.top_categories.length > 0) {
            this.createResultSection(
                resultsContainer,
                'Top Categories',
                'Categories of conversations found in the analyzed threads',
                this.renderCategoriesList(results.top_categories)
            );
        }
        
        // Create discussions section
        if (results.top_discussions && results.top_discussions.length > 0) {
            this.createResultSection(
                resultsContainer,
                'Top Discussion Topics',
                'Most frequent topics discussed in the analyzed threads',
                this.renderDiscussionsList(results.top_discussions)
            );
        }
        
        // Create insights section
        if (results.key_insights && results.key_insights.length > 0) {
            this.createResultSection(
                resultsContainer,
                'Key Insights',
                'Important insights derived from the conversation analysis',
                this.renderInsightsList(results.key_insights)
            );
        }
        
        // Make the analysis tab visible and active
        const analysisTab = document.getElementById('analysis-tab');
        if (analysisTab) {
            analysisTab.classList.remove('disabled');
            analysisTab.click(); // Activate the tab
        }
    }
    
    /**
     * Create a section in the results container
     * @param {HTMLElement} container - The container to add the section to
     * @param {string} title - The section title
     * @param {string} description - The section description
     * @param {HTMLElement} content - The section content
     */
    createResultSection(container, title, description, content) {
        const section = document.createElement('div');
        section.className = 'analysis-section card mb-4';
        
        const header = document.createElement('div');
        header.className = 'card-header';
        header.innerHTML = `<h3>${title}</h3>`;
        
        const body = document.createElement('div');
        body.className = 'card-body';
        
        if (description) {
            const desc = document.createElement('p');
            desc.className = 'text-muted mb-3';
            desc.textContent = description;
            body.appendChild(desc);
        }
        
        body.appendChild(content);
        
        section.appendChild(header);
        section.appendChild(body);
        container.appendChild(section);
    }
    
    /**
     * Render categories list
     * @param {Array} categories - List of categories with counts
     * @returns {HTMLElement} - The rendered categories element
     */
    renderCategoriesList(categories) {
        const list = document.createElement('div');
        list.className = 'row';
        
        categories.forEach(cat => {
            const item = document.createElement('div');
            item.className = 'col-md-6 col-lg-4 mb-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            
            const body = document.createElement('div');
            body.className = 'card-body';
            
            const category = document.createElement('h5');
            category.className = 'card-title';
            category.textContent = cat.category;
            
            const count = document.createElement('p');
            count.className = 'card-text text-muted';
            count.textContent = `${cat.count} thread${cat.count !== 1 ? 's' : ''}`;
            
            body.appendChild(category);
            body.appendChild(count);
            card.appendChild(body);
            item.appendChild(card);
            list.appendChild(item);
        });
        
        return list;
    }
    
    /**
     * Render discussions list
     * @param {Array} discussions - List of discussion topics with counts
     * @returns {HTMLElement} - The rendered discussions element
     */
    renderDiscussionsList(discussions) {
        const list = document.createElement('ul');
        list.className = 'list-group';
        
        discussions.forEach(discussion => {
            const item = document.createElement('li');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            
            const topic = document.createElement('span');
            topic.textContent = discussion.topic;
            
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary rounded-pill';
            badge.textContent = discussion.count;
            
            item.appendChild(topic);
            item.appendChild(badge);
            list.appendChild(item);
        });
        
        return list;
    }
    
    /**
     * Render insights list
     * @param {Array} insights - List of key insights
     * @returns {HTMLElement} - The rendered insights element
     */
    renderInsightsList(insights) {
        const list = document.createElement('ul');
        list.className = 'list-group';
        
        insights.forEach(insight => {
            const item = document.createElement('li');
            item.className = 'list-group-item';
            item.textContent = insight;
            list.appendChild(item);
        });
        
        return list;
    }
}

// Initialize the UI manager when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.uiManager = new UIManager();
});
