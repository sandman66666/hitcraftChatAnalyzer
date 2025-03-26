import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Button, ProgressBar, Alert } from 'react-bootstrap';
import { FaSync, FaCheck, FaTimesCircle } from 'react-icons/fa';
import AnalysisResults from '../components/analysis/AnalysisResults';
import ProcessingLog from '../components/common/ProcessingLog';
import { useAnalyzer } from '../context/AnalyzerContext';
import api from '../services/api';
import './Pages.css';

const AnalysisPage = () => {
  const { state, actions } = useAnalyzer();
  const { 
    sessionId, 
    filename,
    analysisInProgress, 
    analysisComplete, 
    results, 
    error, 
    logs 
  } = state;
  
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [intervalId, setIntervalId] = useState(null);
  
  // Calculate progress percentage
  const progressPercentage = state.threadsToAnalyze > 0 
    ? Math.round((state.threadsAnalyzed / state.threadsToAnalyze) * 100) 
    : 0;
  
  // Poll for analysis progress
  const pollForProgress = () => {
    if (!sessionId) return;
    
    console.log("Starting progress polling with sessionId:", sessionId, "filename:", filename);
    const intervalId = setInterval(async () => {
      try {
        // Try the new endpoint first
        let progressResponse;
        try {
          progressResponse = await api.getAnalysisProgress(sessionId, filename);
          console.log("Progress response from new endpoint:", progressResponse.data);
        } catch (error) {
          // Fall back to the old endpoint
          console.log("Falling back to old progress endpoint");
          progressResponse = await api.checkProgress(sessionId);
          console.log("Progress response from old endpoint:", progressResponse.data);
        }
        
        // Extract the relevant data, handling both new and old API responses
        let threadsAnalyzed = 0;
        let threadsTotal = 0;
        let isComplete = false;
        let hasResults = false;
        let logEntries = [];
        
        if (progressResponse.data.success) {
          // New API format
          threadsAnalyzed = progressResponse.data.threads_analyzed || 0;
          threadsTotal = progressResponse.data.threads_total || 0;
          isComplete = progressResponse.data.status === 'complete' || progressResponse.data.status === 'completed';
          hasResults = progressResponse.data.has_results || false;
          logEntries = progressResponse.data.log_entries || [];
        } else {
          // Old API format
          threadsAnalyzed = progressResponse.data.analyzed_threads || 0;
          threadsTotal = progressResponse.data.total_threads || 0;
          isComplete = !progressResponse.data.is_analyzing;
          hasResults = progressResponse.data.has_results || false;
        }
        
        // Update progress in the UI
        actions.updateAnalysisProgress(threadsAnalyzed);
        
        // Add any new log entries
        if (logEntries && Array.isArray(logEntries)) {
          logEntries.forEach(entry => {
            actions.addLog({
              timestamp: new Date().toISOString(),
              message: entry,
              level: 'info'
            });
          });
        }
        
        // Check if analysis is complete
        if (isComplete && threadsAnalyzed > 0) {
          console.log("Analysis marked as complete, has_results:", hasResults);
          
          // Add completion log
          actions.addLog({
            timestamp: new Date().toISOString(),
            message: 'Analysis completed successfully. Loading results...',
            level: 'success'
          });
          
          // Clear the polling interval
          clearInterval(intervalId);
          
          // Fetch the results
          await fetchResults();
          return true;
        }
        
        return false;
      } catch (error) {
        console.error('Error checking progress:', error);
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: `Error checking progress: ${error.message}`,
          level: 'error'
        });
        return false;
      }
    }, 2000);
    
    // Store interval ID for cleanup
    return intervalId;
  };

  // Start thread analysis
  const startAnalysis = async () => {
    if (!sessionId) return;
    
    try {
      setAnalysisStarted(true);
      
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: 'Starting thread analysis...',
        level: 'info'
      });
      
      const response = await api.analyzeThreads(sessionId, state.threadCount);
      
      actions.startAnalysis(response.data.thread_count);
      
      // Start polling for progress
      const intervalId = pollForProgress();
      
      // Clean up interval on component unmount
      return () => clearInterval(intervalId);
      
    } catch (error) {
      console.error('Error starting analysis:', error);
      actions.setError(error.response?.data?.error || 'Failed to start analysis');
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Analysis error: ${error.message}`,
        level: 'error'
      });
    }
  };
  
  // Cancel ongoing analysis
  const cancelAnalysis = async () => {
    if (!sessionId) return;
    
    try {
      const response = await api.cancelAnalysis(sessionId);
      
      if (response.data.success) {
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: 'Analysis cancelled',
          level: 'warning'
        });
      }
    } catch (error) {
      console.error('Error cancelling analysis:', error);
    }
  };
  
  // Fetch analysis results
  const fetchResults = async () => {
    if (!sessionId) return;
    
    try {
      console.log("Fetching analysis results with sessionId:", sessionId, "filename:", filename);
      
      // Try all possible endpoints until we get valid results
      let response = null;
      let validResults = false;
      
      // Try new endpoint first
      try {
        response = await api.getAnalysisResults(sessionId, filename);
        console.log("Results from new endpoint:", response.data);
        validResults = response.data.success && (response.data.results || response.data);
      } catch (newEndpointError) {
        console.log("New endpoint failed:", newEndpointError);
        
        // Fall back to the legacy endpoint
        try {
          console.log("Falling back to dashboard data endpoint");
          response = await api.getDashboardData(sessionId);
          console.log("Results from dashboard endpoint:", response.data);
          validResults = !!response.data;
        } catch (dashboardError) {
          console.error("All endpoints failed:", dashboardError);
          throw new Error("Failed to fetch results from any endpoint");
        }
      }
      
      // Process results if we have them
      if (validResults) {
        let resultsData = null;
        
        if (response.data.success && response.data.results) {
          resultsData = response.data.results;
        } else {
          resultsData = response.data;
        }
        
        console.log("Final results data:", resultsData);
        
        // Update state with results
        actions.completeAnalysis(resultsData);
        
        // Log success
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: 'Analysis results loaded successfully',
          level: 'success'
        });
        
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Error fetching results:', error);
      actions.setError(error.message || 'Failed to fetch results');
      actions.addLog({
        timestamp: new Date().toISOString(),
        message: `Error fetching results: ${error.message}`,
        level: 'error'
      });
      return false;
    }
  };
  
  // Check for existing analysis results on mount
  useEffect(() => {
    // If we already have results, just ensure the UI is properly updated
    if (sessionId && analysisComplete && results) {
      console.log("Found existing analysis results on mount, displaying them");
      setAnalysisStarted(true);
      
      // Add log entry for clarity
      if (logs.length === 0) {
        actions.addLog({
          timestamp: new Date().toISOString(),
          message: 'Loaded existing analysis results',
          level: 'info'
        });
      }
    } 
    // If we have a session but no results and analysis isn't in progress,
    // check if there are results on the server
    else if (sessionId && !analysisInProgress && !analysisComplete && !results) {
      console.log("Checking for existing analysis results on server");
      
      const checkForExistingResults = async () => {
        try {
          actions.addLog({
            timestamp: new Date().toISOString(),
            message: 'Checking for existing analysis results...',
            level: 'info'
          });
          
          const resultsFound = await fetchResults();
          
          if (resultsFound) {
            console.log("Found and loaded existing results from server");
            setAnalysisStarted(true);
          } else {
            console.log("No existing results found on server");
          }
        } catch (error) {
          console.error("Error checking for existing results:", error);
        }
      };
      
      checkForExistingResults();
    }
    // If analysis is already in progress, start polling
    else if (sessionId && analysisInProgress && !analysisComplete) {
      console.log("Analysis already in progress, starting polling");
      setAnalysisStarted(true);
      const id = pollForProgress();
      setIntervalId(id);
      
      // Clean up interval when unmounting
      return () => {
        if (id) clearInterval(id);
      };
    }
  }, [sessionId]);
  
  // Clean up polling when component unmounts
  useEffect(() => {
    return () => {
      if (intervalId) {
        console.log("Cleaning up polling interval");
        clearInterval(intervalId);
      }
    };
  }, [intervalId]);
  
  return (
    <div className="analysis-page">
      <h2 className="page-title">Chat Analysis</h2>
      
      {error && (
        <Alert variant="danger" className="mb-4">
          <FaTimesCircle className="me-2" />
          {error}
        </Alert>
      )}
      
      <Card className="mb-4">
        <Card.Body>
          {analysisComplete && results ? (
            <Card.Title>Analysis Results</Card.Title>
          ) : (
            <Card.Title>Start Thread Analysis</Card.Title>
          )}
          <Card.Text>
            {state.threadCount > 0 ? (
              <>Found {state.threadCount} conversation threads. Ready to analyze.</>
            ) : (
              <>No threads found. Please upload a chat file first.</>
            )}
          </Card.Text>
          {analysisComplete && results ? (
            <div className="analysis-status mb-4">
              <div className="status-badge complete">
                <FaCheck className="me-2" />
                Analysis Complete
              </div>
              <Button 
                variant="outline-primary" 
                size="sm"
                onClick={startAnalysis}
              >
                <FaSync className="me-2" />
                Re-run Analysis
              </Button>
            </div>
          ) : (
            <Button 
              variant="primary" 
              onClick={startAnalysis}
              disabled={!sessionId || state.threadCount === 0}
            >
              <FaSync className="me-2" />
              Start Analysis
            </Button>
          )}
          {analysisInProgress && (
            <div className="mt-3 mb-3">
              <ProgressBar 
                now={progressPercentage} 
                label={`${progressPercentage}%`}
                variant="info" 
                animated
              />
              <div className="text-center mt-2">
                <small className="text-muted">
                  Analyzed {state.threadsAnalyzed} of {state.threadsToAnalyze} threads
                </small>
              </div>
              <Button 
                variant="danger" 
                onClick={cancelAnalysis}
              >
                Cancel Analysis
              </Button>
            </div>
          )}
        </Card.Body>
      </Card>
      
      {analysisComplete && results && (
        <AnalysisResults results={results} />
      )}
      
      <Row className="mt-4">
        <Col>
          <div className="log-container">
            <ProcessingLog logs={logs} />
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default AnalysisPage;
