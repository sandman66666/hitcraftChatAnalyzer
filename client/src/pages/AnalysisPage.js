import React, { useState, useEffect, useRef } from 'react';
import { useAnalyzer } from '../context/AnalyzerContext';
import LoadingIndicator from '../components/common/LoadingIndicator';
import './Pages.css';
import api from '../services/api';
import AnalysisResults from '../components/analysis/AnalysisResults';
import EvidenceModal from '../components/analysis/EvidenceModal';
import AnalysisProgressBar from '../components/analysis/AnalysisProgressBar';

const AnalysisPage = () => {
  const { state, actions } = useAnalyzer();
  const { sessionId, threadCount, threadsAnalyzed } = state;
  
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [error, setError] = useState(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  // Modal state for evidence
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [evidenceModalTitle, setEvidenceModalTitle] = useState("");
  const [evidenceModalData, setEvidenceModalData] = useState([]);
  
  // Analysis progress state
  const [analysisProgress, setAnalysisProgress] = useState({
    isAnalyzing: false,
    currentThread: 0,
    totalThreads: 0,
    analyzedThreads: 0,
    startTime: null,
    lastError: null
  });
  
  // Analysis controls
  const [analyzeCount, setAnalyzeCount] = useState(10);
  const [analysisStats, setAnalysisStats] = useState({
    total_threads: 0,
    analyzed_threads: 0,
    remaining_threads: 0
  });
  
  // Polling interval for progress updates
  const pollingIntervalRef = useRef(null);
  
  // Start polling for analysis progress
  const startProgressPolling = () => {
    // Clear any existing interval first
    stopProgressPolling();
    
    // Start a new polling interval - poll frequently during active analysis
    pollingIntervalRef.current = setInterval(() => {
      fetchAnalysisProgress();
    }, 2000); // Poll every 2 seconds during active analysis
  };
  
  // Slower polling when no analysis is in progress
  const startSlowPolling = () => {
    // Clear any existing interval first
    stopProgressPolling();
    
    // Start a new polling interval at a slower rate
    pollingIntervalRef.current = setInterval(() => {
      fetchAnalysisProgress();
    }, 30000); // Poll every 30 seconds when idle
  };
  
  // Stop polling
  const stopProgressPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };
  
  // Fetch current analysis progress
  const fetchAnalysisProgress = async () => {
    if (!sessionId) return;
    
    try {
      const response = await api.getAnalysisStatus(sessionId);
      if (response.data) {
        const isAnalyzing = response.data.is_analyzing || false;
        
        // Update component state with progress data
        setAnalysisProgress({
          isAnalyzing: isAnalyzing,
          currentThread: response.data.current_thread || 0,
          totalThreads: response.data.total_threads || 0,
          analyzedThreads: response.data.analyzed_threads || 0,
          startTime: response.data.start_time,
          lastError: response.data.last_error
        });
        
        // If analysis status changed from running to completed
        if (response.data.was_analyzing && !isAnalyzing) {
          // Analysis just finished, refresh results and switch to slow polling
          loadAnalysisData();
          startSlowPolling();
        } 
        // If analysis is running, ensure we're polling frequently 
        else if (isAnalyzing) {
          // Make sure we're on fast polling if analysis is running
          if (pollingIntervalRef.current && 
              (!analysisProgress.isAnalyzing || analysisProgress.isAnalyzing !== isAnalyzing)) {
            startProgressPolling();
          }
        }
        // If analysis is not running and we were previously in fast polling mode
        else if (!isAnalyzing && analysisProgress.isAnalyzing) {
          // Switch to slow polling
          startSlowPolling();
        }
      }
    } catch (err) {
      console.error("Error fetching analysis progress:", err);
    }
  };
  
  const fetchAnalysisStatus = async () => {
    try {
      const response = await api.getAnalysisStatus(sessionId);
      console.log("Analysis status response:", response.data);
      if (response.data) {
        // Update local component state
        setAnalysisStats({
          total_threads: response.data.total || 0,
          analyzed_threads: response.data.analyzed || 0,
          remaining_threads: response.data.remaining || 0
        });
        
        // Also update the global state
        actions.setThreadCount(response.data.total || 0);
        actions.updateAnalysisProgress(response.data.analyzed || 0);
      }
    } catch (err) {
      console.error("Error fetching analysis status:", err);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error fetching analysis status: ${err.message}`,
        level: 'error'
      });
    }
  };
  
  const loadAnalysisData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch analysis results with optional date filtering
      const response = await api.getAnalysisResults(sessionId, null, startDate, endDate);
      
      if (response.data && response.data.success) {
        setAnalysisData(response.data);
        
        // If we got results, update global state
        if (response.data.results) {
          actions.setResults(response.data.results);
        }
      } else if (response.data && response.data.error) {
        setError(response.data.error);
        setAnalysisData(null);
      } else {
        // If no analysis exists yet, just show empty data
        setAnalysisData(null);
      }
    } catch (err) {
      console.error("Error loading analysis data:", err);
      setError("Failed to load analysis data. Please try again.");
      setAnalysisData(null);
      
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error loading analysis: ${err.message}`,
        level: 'error'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleDateFilterChange = () => {
    loadAnalysisData();
  };
  
  const analyzeThreads = async () => {
    try {
      setLoading(true);
      
      // Log that we're starting analysis
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Starting analysis of ${analyzeCount} threads`,
        level: 'info'
      });
      
      // Update global state
      actions.startAnalysis(analyzeCount);
      
      // Call the API to analyze threads
      const response = await api.analyzeThreads(sessionId, analyzeCount);
      console.log("Analyze threads response:", response.data);
      
      // Start polling more frequently during analysis
      startProgressPolling();
      
      // Show success message
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Analysis started for ${analyzeCount} threads.`,
        level: 'success'
      });
    } catch (err) {
      console.error("Error analyzing threads:", err);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error analyzing threads: ${err.message}`,
        level: 'error'
      });
      
      setAnalysisProgress(prev => ({
        ...prev,
        lastError: err.message
      }));
    } finally {
      setLoading(false);
    }
  };
  
  // Handle insight click to show evidence
  const handleInsightClick = async (insight, category) => {
    console.log("Insight clicked:", insight, category);
    
    try {
      let title = '';
      let evidenceData = [];
      
      // Handle different insight formats
      if (typeof insight === 'string') {
        title = insight;
      } else if (insight.title) {
        title = insight.title;
      } else if (insight.insight) {
        title = insight.insight;
      } else {
        title = "Evidence";
      }
      
      // Try to gather evidence based on different data formats
      if (insight.evidence_threads && insight.evidence_threads.length > 0) {
        // This is our app's standard format
        const promises = insight.evidence_threads.map(async (threadId) => {
          try {
            const response = await api.getThread(sessionId, threadId);
            if (response.data) {
              return {
                thread_id: threadId,
                messages: response.data.messages || [],
                metadata: {
                  message_count: response.data.message_count || response.data.messages?.length || 0
                }
              };
            }
          } catch (err) {
            console.error(`Error loading thread ${threadId}:`, err);
            return null;
          }
        });
        
        const threadResults = await Promise.all(promises);
        evidenceData = threadResults.filter(t => t !== null);
      } 
      // Claude API format often has supporting_evidence as strings
      else if (insight.supporting_evidence && insight.supporting_evidence.length > 0) {
        evidenceData = insight.supporting_evidence;
      }
      // For instance-based evidence (used in discussions)
      else if (insight.instances && insight.instances.length > 0) {
        evidenceData = insight.instances.map(i => i.context);
      }
      
      // Show the modal with evidence
      setEvidenceModalTitle(title);
      setEvidenceModalData(evidenceData);
      setShowEvidenceModal(true);
      
    } catch (err) {
      console.error("Error preparing evidence:", err);
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error loading evidence: ${err.message}`,
        level: 'error'
      });
    }
  };

  // Update local stats when global state changes
  useEffect(() => {
    setAnalysisStats(prev => ({
      ...prev,
      total_threads: threadCount || 0,
      analyzed_threads: threadsAnalyzed || 0,
      remaining_threads: (threadCount || 0) - (threadsAnalyzed || 0)
    }));
  }, [threadCount, threadsAnalyzed]);
  
  // Load analysis data on component mount and when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadAnalysisData();
      fetchAnalysisStatus();
      // Start with slow polling on initial load
      startSlowPolling();
    }
    
    // Cleanup on unmount
    return () => {
      stopProgressPolling();
    };
  }, [sessionId]);
  
  // Render loading state
  if (loading) {
    return <LoadingIndicator message="Loading analysis data..." />;
  }
  
  // Calculate remaining threads
  const remainingThreads = analysisStats.total_threads - analysisStats.analyzed_threads;
  
  return (
    <div className="page-content">
      <h1>Analysis</h1>
      
      {!sessionId && analysisStats.total_threads === 0 ? (
        <div className="alert alert-info">
          Please upload a chat file first to see analysis.
        </div>
      ) : (
        <>
          {/* Analysis Progress Bar - Always show if we have progress data */}
          <AnalysisProgressBar 
            isAnalyzing={analysisProgress.isAnalyzing}
            currentThread={analysisProgress.currentThread}
            totalThreads={analysisProgress.totalThreads}
            analyzedThreads={analysisProgress.analyzedThreads}
            startTime={analysisProgress.startTime}
            lastError={analysisProgress.lastError}
          />
        
          {/* Thread Statistics Dashboard */}
          <div className="analysis-stats-section">
            <h3>Thread Statistics</h3>
            <div className="thread-stats-container">
              <div className="thread-stat-card">
                <h4>Total Threads</h4>
                <p className="thread-stat-value">{analysisStats.total_threads}</p>
              </div>
              <div className="thread-stat-card">
                <h4>Analyzed</h4>
                <p className="thread-stat-value">{analysisStats.analyzed_threads}</p>
              </div>
              <div className="thread-stat-card">
                <h4>Remaining</h4>
                <p className="thread-stat-value">{remainingThreads}</p>
              </div>
            </div>
            
            {remainingThreads > 0 && (
              <div className="analyze-controls">
                <div className="form-group">
                  <label htmlFor="analyzeCount">Number of threads to analyze:</label>
                  <input
                    type="number"
                    id="analyzeCount"
                    className="form-control"
                    value={analyzeCount}
                    onChange={(e) => setAnalyzeCount(parseInt(e.target.value) || 1)}
                    min="1"
                    max={remainingThreads}
                  />
                </div>
                <button className="btn btn-primary" onClick={analyzeThreads} disabled={loading}>
                  Analyze Threads
                </button>
              </div>
            )}
          </div>
          
          {/* Analysis Results Section */}
          {analysisData ? (
            <div className="analysis-results">
              <h2>Analysis Results</h2>
              
              <div className="date-filter-section">
                <h4>Filter by Date</h4>
                <div className="date-filter-controls">
                  <div className="form-group">
                    <label htmlFor="startDate">Start Date:</label>
                    <input
                      type="date"
                      id="startDate"
                      className="form-control"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="endDate">End Date:</label>
                    <input
                      type="date"
                      id="endDate"
                      className="form-control"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                    />
                  </div>
                  <button 
                    className="btn btn-outline-primary"
                    onClick={handleDateFilterChange}
                  >
                    Apply Filter
                  </button>
                </div>
              </div>
              
              {/* Analysis Data Visualization */}
              <div className="analysis-visualization">
                {analysisData.results ? (
                  <AnalysisResults 
                    results={analysisData.results} 
                    onInsightClick={handleInsightClick}
                  />
                ) : (
                  <div className="no-data-message">
                    <p>Thread Analysis Complete.</p>
                    <p>Results will be displayed as they become available.</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="no-data-message">
              {error ? (
                <div className="alert alert-danger">{error}</div>
              ) : (
                <p>No analysis data available yet. Use the controls above to analyze threads.</p>
              )}
            </div>
          )}
          
          {/* Evidence Modal */}
          <EvidenceModal 
            show={showEvidenceModal}
            onHide={() => setShowEvidenceModal(false)}
            title={evidenceModalTitle}
            evidence={evidenceModalData}
          />
        </>
      )}
    </div>
  );
};

export default AnalysisPage;
