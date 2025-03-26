// thread-browser.js - Handles thread browsing functionality

let currentPage = 1;
let threadsPerPage = 50; // Increased from 10
let totalThreads = 0;
let threads = [];

// Load and display threads for the given page
function loadThreads(page = 1, perPage = 50) {
    currentPage = page;
    threadsPerPage = perPage;
    
    console.log(`Loading threads page ${page} with ${perPage} per page`);
    
    // Reset UI state
    document.getElementById('threadContent').innerHTML = '';
    document.getElementById('threadViewContainer').classList.add('d-none');
    
    // Fetch thread list
    fetch(`/get_threads?page=${page}&per_page=${perPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error loading threads:', data.error);
                document.getElementById('threadsListItems').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }
            
            threads = data.threads;
            totalThreads = data.total;
            
            console.log(`Received ${threads.length} threads out of ${totalThreads} total`);
            
            // Update UI
            renderThreadsList(threads);
            renderPagination();
            
            if (threads.length > 0) {
                // Auto select the first thread when loading a page
                viewThread(threads[0].id);
            }
        })
        .catch(error => {
            console.error('Error fetching threads:', error);
            document.getElementById('threadsListItems').innerHTML = `<div class="alert alert-danger">Failed to load threads: ${error.message}</div>`;
        });
}

// Render the threads list
function renderThreadsList(threads) {
    const listContainer = document.getElementById('threadsListItems');
    listContainer.innerHTML = '';
    
    if (threads.length === 0) {
        listContainer.innerHTML = '<div class="alert alert-info">No threads found</div>';
        return;
    }
    
    threads.forEach(thread => {
        const threadItem = document.createElement('div');
        threadItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        threadItem.setAttribute('data-thread-id', thread.id);
        threadItem.onclick = () => viewThread(thread.id);
        
        // Create thread title with truncated preview
        const previewLength = 100; // characters
        const preview = thread.preview.length > previewLength 
            ? thread.preview.substring(0, previewLength) + '...' 
            : thread.preview;
        
        // Format timestamp if available
        let timestampHtml = '';
        if (thread.timestamp) {
            const date = new Date(thread.timestamp);
            const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
            timestampHtml = `<small class="text-muted">${formattedDate}</small>`;
        }
        
        // Set thread item content
        threadItem.innerHTML = `
            <div>
                <div class="fw-bold">Thread #${thread.id}</div>
                <div class="small text-truncate" style="max-width: 500px;">${preview}</div>
                ${timestampHtml}
            </div>
            <span class="badge bg-primary rounded-pill">${thread.message_count} msgs</span>
        `;
        
        listContainer.appendChild(threadItem);
    });
}

// Render pagination controls
function renderPagination() {
    const paginationContainer = document.getElementById('threadsPagination');
    paginationContainer.innerHTML = '';
    
    if (totalThreads <= threadsPerPage) {
        return; // No pagination needed
    }
    
    const totalPages = Math.ceil(totalThreads / threadsPerPage);
    
    const pagination = document.createElement('nav');
    pagination.setAttribute('aria-label', 'Threads pagination');
    
    const pageList = document.createElement('ul');
    pageList.className = 'pagination justify-content-center';
    
    // Previous button
    const prevItem = document.createElement('li');
    prevItem.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevItem.innerHTML = `<a class="page-link" href="#" ${currentPage > 1 ? `onclick="loadThreads(${currentPage - 1}, ${threadsPerPage}); return false;"` : ''}>Previous</a>`;
    pageList.appendChild(prevItem);
    
    // Calculate page range to display (up to 5 pages)
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    // Adjust start if we're near the end
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        const pageItem = document.createElement('li');
        pageItem.className = `page-item ${i === currentPage ? 'active' : ''}`;
        pageItem.innerHTML = `<a class="page-link" href="#" onclick="loadThreads(${i}, ${threadsPerPage}); return false;">${i}</a>`;
        pageList.appendChild(pageItem);
    }
    
    // Next button
    const nextItem = document.createElement('li');
    nextItem.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextItem.innerHTML = `<a class="page-link" href="#" ${currentPage < totalPages ? `onclick="loadThreads(${currentPage + 1}, ${threadsPerPage}); return false;"` : ''}>Next</a>`;
    pageList.appendChild(nextItem);
    
    pagination.appendChild(pageList);
    paginationContainer.appendChild(pagination);
}

// View a specific thread by ID
function viewThread(threadId) {
    console.log(`Viewing thread ${threadId}`);
    
    // Highlight selected thread
    document.querySelectorAll('#threadsListItems .list-group-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-thread-id') === threadId.toString()) {
            item.classList.add('active');
        }
    });
    
    // Find the thread in our current data
    const thread = threads.find(t => t.id.toString() === threadId.toString());
    if (!thread) {
        console.error(`Thread ${threadId} not found in current data`);
        return;
    }
    
    // Fetch thread content
    fetch(`/get_thread_content?thread_id=${threadId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error fetching thread content:', data.error);
                document.getElementById('threadContent').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }
            
            // Display the thread content
            renderThreadContent(data);
            document.getElementById('threadViewContainer').classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error fetching thread content:', error);
            document.getElementById('threadContent').innerHTML = `<div class="alert alert-danger">Failed to load thread content: ${error.message}</div>`;
        });
}

// Render thread content
function renderThreadContent(threadData) {
    const contentContainer = document.getElementById('threadContent');
    contentContainer.innerHTML = '';
    
    if (!threadData.content || threadData.content.length === 0) {
        contentContainer.innerHTML = '<div class="alert alert-info">This thread has no messages</div>';
        return;
    }
    
    const threadHeader = document.createElement('div');
    threadHeader.className = 'mb-3 border-bottom pb-2';
    threadHeader.innerHTML = `
        <h5>Thread #${threadData.id}</h5>
        <div class="text-muted small">${threadData.message_count} messages</div>
    `;
    contentContainer.appendChild(threadHeader);
    
    // Parse and display messages
    const messagesContainer = document.createElement('div');
    messagesContainer.className = 'messages-container';
    
    // Format and add messages to the container
    threadData.content.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message mb-3';
        
        // Extract sender type (user/assistant) based on message format
        let senderType = 'user';
        if (msg.toLowerCase().includes('assistant:') || 
            msg.toLowerCase().includes('claude:') || 
            msg.toLowerCase().includes('chatgpt:') || 
            msg.toLowerCase().includes('ai:')) {
            senderType = 'assistant';
        }
        
        // Apply appropriate styling based on sender
        messageDiv.classList.add(senderType === 'assistant' ? 'message-assistant' : 'message-user');
        
        // Format the message with proper styling
        messageDiv.innerHTML = `
            <div class="message-bubble p-3 rounded ${senderType === 'assistant' ? 'bg-light' : 'bg-primary text-white'}">
                ${formatMessage(msg)}
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
    });
    
    contentContainer.appendChild(messagesContainer);
}

// Format message text with proper styling
function formatMessage(text) {
    // Replace newlines with <br> tags
    text = text.replace(/\n/g, '<br>');
    
    // Format code blocks (if any)
    text = text.replace(/```([\s\S]*?)```/g, '<pre class="code-block p-2 bg-dark text-light rounded"><code>$1</code></pre>');
    
    // Format inline code (if any)
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    return text;
}
