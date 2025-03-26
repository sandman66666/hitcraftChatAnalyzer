import axios from 'axios';

const BASE_URL = 'http://localhost:8096/api';
const ROOT_URL = 'http://localhost:8096';

const api = {
  // File upload
  uploadFile: (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return axios.post(`${BASE_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
      withCredentials: true // Enable cookies to persist session
    });
  },
  
  // Thread extraction
  extractThreads: (sessionId, filename) => {
    return axios.post(`${BASE_URL}/extract_threads`, { 
      session_id: sessionId, 
      filename 
    }, {
      withCredentials: true // Enable cookies to persist session
    });
  },

  // Get thread count
  getThreadCount: (sessionId) => {
    return axios.get(`${BASE_URL}/thread_count?session_id=${sessionId}`, {
      withCredentials: true
    });
  },
  
  // Start thread analysis
  analyzeThreads: (sessionId, threadCount = 10) => {
    return axios.post(`${BASE_URL}/analyze_threads`, { 
      session_id: sessionId,
      thread_count: threadCount
    }, {
      withCredentials: true
    });
  },
  
  // Check analysis progress
  checkProgress: (sessionId) => {
    return axios.get(`${BASE_URL}/check_progress?session_id=${sessionId}`, {
      withCredentials: true
    });
  },
  
  // Get analysis progress (new endpoint)
  getAnalysisProgress: (sessionId, filename) => {
    let url = `${BASE_URL}/analysis_progress`;
    if (sessionId) url += `?session_id=${sessionId}`;
    if (filename) url += `${sessionId ? '&' : '?'}filename=${filename}`;
    
    return axios.get(url, {
      withCredentials: true
    });
  },
  
  // Get analysis results (new endpoint)
  getAnalysisResults: (sessionId, filename) => {
    let url = `${BASE_URL}/get_analysis_results`;
    if (sessionId) url += `?session_id=${sessionId}`;
    if (filename) url += `${sessionId ? '&' : '?'}filename=${filename}`;
    
    return axios.get(url, {
      withCredentials: true
    });
  },
  
  // Cancel analysis
  cancelAnalysis: (sessionId) => {
    return axios.post(`${BASE_URL}/cancel_analysis`, { 
      session_id: sessionId 
    }, {
      withCredentials: true
    });
  },
  
  // Get dashboard data
  getDashboardData: (sessionId) => {
    return axios.get(`${BASE_URL}/dashboard_data?session_id=${sessionId}`, {
      withCredentials: true
    });
  },
  
  // List threads - Note: Different URL pattern!
  listThreads: (sessionId, page = 1, perPage = 10) => {
    return axios.get(`${ROOT_URL}/get_threads?session_id=${sessionId}&page=${page}&per_page=${perPage}`, {
      withCredentials: true
    });
  },
  
  // Get specific thread - Note: Different URL pattern!
  getThread: (sessionId, threadId) => {
    return axios.get(`${ROOT_URL}/get_thread_content?session_id=${sessionId}&thread_id=${threadId}`, {
      withCredentials: true
    });
  },
  
  // Get logs
  getLogs: () => {
    return axios.get(`${ROOT_URL}/logs`, {
      withCredentials: true
    });
  }
};

export default api;
