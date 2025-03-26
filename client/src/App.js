import React, { useEffect, useState, useCallback, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container } from 'react-bootstrap';
import { AnalyzerProvider, useAnalyzer } from './context/AnalyzerContext';
import api from './services/api';

// Import pages
import UploadPage from './pages/UploadPage';
import AnalysisPage from './pages/AnalysisPage';
import ThreadsPage from './pages/ThreadsPage';

// Import components
import Sidebar from './components/common/Sidebar';
import ProcessingLog from './components/common/ProcessingLog';

// Import styles
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

// AppContent component to handle state and data loading
function AppContent() {
  const { state, actions } = useAnalyzer();
  const [dataLoaded, setDataLoaded] = useState(false);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const loadingRef = useRef(false);
  const initRef = useRef(false);
  
  // Load data only once at startup
  useEffect(() => {
    // Skip if already initialized
    if (initRef.current) return;
    initRef.current = true;
    
    // Create a unique session ID if none exists
    if (!state.sessionId) {
      const tempSessionId = `session_${Date.now()}`;
      actions.setSession(tempSessionId, null);
      console.log('Created new session:', tempSessionId);
    }
    
    // Only run once
    const loadInitialData = async () => {
      if (loadingRef.current) return;
      loadingRef.current = true;
      
      try {
        console.log('Loading initial data...');
        setLoadingInitial(true);
        
        // Check thread count
        let threadCount = 0;
        try {
          const threadCountResponse = await api.getThreadCount(state.sessionId);
          console.log('Thread count response:', threadCountResponse);
          
          if (threadCountResponse.data && threadCountResponse.data.count > 0) {
            threadCount = threadCountResponse.data.count;
            console.log(`Found ${threadCount} existing threads`);
            actions.setThreadCount(threadCount);
            actions.setThreadExtracted(true);
            
            // Only load threads if we have any
            if (threadCount > 0) {
              const threadsResponse = await api.listThreads(state.sessionId);
              if (threadsResponse.data && threadsResponse.data.threads) {
                actions.setThreads(threadsResponse.data.threads);
              }
            }
          }
        } catch (err) {
          console.error('Error loading thread count:', err);
        }
        
        // Get analysis status (only if we have threads)
        if (threadCount > 0) {
          try {
            const statusResponse = await api.getAnalysisStatus(state.sessionId);
            if (statusResponse.data && statusResponse.data.analyzed) {
              actions.updateAnalysisProgress(statusResponse.data.analyzed);
            }
          } catch (err) {
            console.error('Error fetching analysis status:', err);
          }
        }
        
        // Load logs
        try {
          const logsResponse = await api.getLogs();
          if (logsResponse.data && logsResponse.data.logs) {
            actions.setLogs(logsResponse.data.logs);
          }
        } catch (err) {
          console.error('Error loading logs:', err);
        }
        
      } catch (error) {
        console.error('Error loading initial data:', error);
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: `Error loading data: ${error.message}`,
          level: 'error'
        });
      } finally {
        setLoadingInitial(false);
        setDataLoaded(true);
        loadingRef.current = false;
      }
    };
    
    // Load initial data - but only once
    loadInitialData();
    
  }, [actions, state.sessionId]);
  
  // Set up infrequent polling for stats - completely separate from the initial load
  useEffect(() => {
    // Skip if we're still loading initial data
    if (loadingInitial) return;
    
    // Skip if we don't have a session
    if (!state.sessionId) return;
    
    // Make polling less frequent - every minute
    const statsInterval = setInterval(async () => {
      console.log('Refreshing stats...');
      try {
        const statusResponse = await api.getAnalysisStatus(state.sessionId);
        if (statusResponse.data) {
          actions.setThreadCount(statusResponse.data.total || 0);
          actions.updateAnalysisProgress(statusResponse.data.analyzed || 0);
        }
      } catch (err) {
        console.error('Error refreshing stats:', err);
      }
    }, 60000); // Once per minute
    
    return () => {
      clearInterval(statsInterval);
    };
  }, [actions, state.sessionId, loadingInitial]);
  
  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="content-area">
          <Container fluid className="py-4">
            <Routes>
              <Route path="/" element={<UploadPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/threads" element={<ThreadsPage />} />
            </Routes>
            <ProcessingLog />
          </Container>
        </main>
      </div>
    </Router>
  );
}

function App() {
  return (
    <AnalyzerProvider>
      <AppContent />
    </AnalyzerProvider>
  );
}

export default App;
