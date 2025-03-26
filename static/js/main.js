// main.js - Main application script for HitCraft Chat Analyzer

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI navigation
    initNavigation();
    
    // Set up file upload form
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
        
        // File drop area functionality
        setupFileDropArea();
    }
    
    // Slider for chunks
    const chunksSlider = document.getElementById('chunks');
    if (chunksSlider) {
        chunksSlider.addEventListener('input', function() {
            document.getElementById('chunks-value').textContent = this.value;
        });
    }
    
    // Initialize Bootstrap components
    initBootstrapComponents();
});

/**
 * Set up navigation between app screens
 */
function initNavigation() {
    // Upload screen navigation
    const uploadNavBtn = document.getElementById('uploadNavBtn');
    if (uploadNavBtn) {
        uploadNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showScreen('uploadScreen');
        });
    }
    
    // Analysis screen navigation (will be enabled after successful upload)
    const analysisNavBtn = document.getElementById('analysisNavBtn');
    if (analysisNavBtn) {
        analysisNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!this.classList.contains('disabled')) {
                showScreen('analysisScreen');
            }
        });
    }
    
    // Threads screen navigation (will be enabled after successful upload)
    const browsersNavBtn = document.getElementById('browsersNavBtn');
    if (browsersNavBtn) {
        browsersNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (!this.classList.contains('disabled')) {
                showScreen('threadsScreen');
            }
        });
    }
}

/**
 * Show specified screen and hide others
 * @param {string} screenId - ID of the screen to show
 */
function showScreen(screenId) {
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Show the requested screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
        
        // Update active state in navigation
        const navLinks = document.querySelectorAll('.sidebar-menu .nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // Map screen IDs to nav button IDs
        const screenToNavMap = {
            'uploadScreen': 'uploadNavBtn',
            'processingScreen': null,
            'analysisScreen': 'analysisNavBtn',
            'threadsScreen': 'threadsNavBtn'
        };
        
        // Activate corresponding nav item
        const navBtnId = screenToNavMap[screenId];
        if (navBtnId) {
            const navBtn = document.getElementById(navBtnId);
            if (navBtn) {
                navBtn.classList.add('active');
            }
        }
    }
}

/**
 * Initialize Bootstrap components
 */
function initBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Setup file drop area functionality
 */
function setupFileDropArea() {
    const dropArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file');
    
    console.log('Setting up file drop area:', dropArea);
    console.log('File input element:', fileInput);
    
    if (!dropArea || !fileInput) {
        console.error('Upload area or file input not found!');
        return;
    }
    
    // Highlight drop area when dragging file over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, function(e) {
            console.log('Drag event:', eventName);
            e.preventDefault();
            dropArea.classList.add('is-active');
        });
    });
    
    // Remove highlight when dragging leaves
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, function(e) {
            console.log('Drag event:', eventName);
            e.preventDefault();
            dropArea.classList.remove('is-active');
        });
    });
    
    // Handle file drop
    dropArea.addEventListener('drop', function(e) {
        console.log('File dropped');
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            // Trigger change event to update UI
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    });
    
    // Add click handler to open file dialog when clicking anywhere in the drop area
    dropArea.addEventListener('click', function(e) {
        console.log('Upload area clicked', e.target);
        // Prevent click from triggering if we clicked on the input itself
        if (e.target !== fileInput) {
            e.preventDefault();
            console.log('Triggering file input click');
            fileInput.click();
        }
    });
    
    // Update UI when file is selected
    fileInput.addEventListener('change', function() {
        console.log('File selection changed', this.files);
        if (this.files.length) {
            const fileName = this.files[0].name;
            const fileSize = (this.files[0].size / 1024).toFixed(2) + 'KB';
            const fileTypeIcon = getFileTypeIcon(fileName);
            
            dropArea.querySelector('.upload-icon').innerHTML = fileTypeIcon;
            dropArea.querySelector('.upload-title').textContent = fileName;
            dropArea.querySelector('.upload-info').textContent = fileSize;
        }
    });
    
    console.log('File drop area setup complete');
}

/**
 * Get appropriate icon based on file extension
 * @param {string} fileName - Name of the file
 * @returns {string} - HTML for the icon
 */
function getFileTypeIcon(fileName) {
    const extension = fileName.split('.').pop().toLowerCase();
    let icon = '<i class="bi bi-file-earmark-text"></i>';
    
    if (extension === 'json') {
        icon = '<i class="bi bi-filetype-json"></i>';
    } else if (extension === 'txt') {
        icon = '<i class="bi bi-filetype-txt"></i>';
    } else if (extension === 'rtf') {
        icon = '<i class="bi bi-file-richtext"></i>';
    }
    
    return icon;
}

/**
 * Show the processing screen
 * @param {string} message - Optional message to display
 */
function showProcessingScreen(message = 'Analyzing your conversations') {
    document.getElementById('processing-title').textContent = message;
    showScreen('processingScreen');
}

/**
 * Update progress bar on the processing screen
 * @param {number} percent - Progress percentage (0-100)
 */
function updateProgressBar(percent) {
    const progressBar = document.getElementById('analysis-progress-bar');
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
        document.getElementById('progress-percent').textContent = percent + '%';
    }
}

/**
 * Add a log entry to the processing log
 * @param {string} message - Log message
 * @param {string} type - Message type (info, success, warning, error)
 */
function addProcessingLog(message, type = 'info') {
    const logContent = document.getElementById('log-content');
    if (logContent) {
        const timestamp = new Date().toLocaleTimeString();
        const typeIcon = {
            'info': 'bi-info-circle',
            'success': 'bi-check-circle',
            'warning': 'bi-exclamation-triangle',
            'error': 'bi-x-circle'
        };
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry text-${type}`;
        logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <i class="bi ${typeIcon[type]}"></i> ${message}`;
        
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;
    }
}

/**
 * Enable navigation to results screens
 */
function enableResultsNavigation() {
    // Enable analysis and threads navigation
    const analysisNavBtn = document.getElementById('analysisNavBtn');
    const browsersNavBtn = document.getElementById('browsersNavBtn');
    
    if (analysisNavBtn) {
        analysisNavBtn.classList.remove('disabled');
    }
    
    if (browsersNavBtn) {
        browsersNavBtn.classList.remove('disabled');
    }
}

/**
 * Show alert message
 * @param {string} elementId - ID of the container to show the message in
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        element.classList.remove('d-none');
    }
}
