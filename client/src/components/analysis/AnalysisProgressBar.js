import React from 'react';
import { ProgressBar, Card } from 'react-bootstrap';
import { FaSyncAlt, FaCheckCircle, FaExclamationCircle } from 'react-icons/fa';

const AnalysisProgressBar = ({ 
  isAnalyzing, 
  currentThread, 
  totalThreads, 
  analyzedThreads,
  startTime,
  lastError
}) => {
  if (!isAnalyzing && analyzedThreads === 0) {
    return null; // Don't show anything if no analysis has been started
  }
  
  // Calculate progress percentage
  const progressPercent = totalThreads > 0 
    ? Math.round((analyzedThreads / totalThreads) * 100) 
    : 0;
  
  // Calculate elapsed time in seconds if analysis is in progress
  const elapsedSeconds = startTime 
    ? Math.round((new Date() - new Date(startTime)) / 1000) 
    : 0;
    
  // Format elapsed time
  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
  };
  
  // Get progress bar variant based on status
  const getVariant = () => {
    if (lastError) return 'danger';
    if (!isAnalyzing && analyzedThreads === totalThreads) return 'success';
    return 'primary';
  };
  
  // Get status message
  const getStatusMessage = () => {
    if (lastError) {
      return `Error: ${lastError}`;
    }
    
    if (!isAnalyzing && analyzedThreads > 0) {
      return 'Analysis complete!';
    }
    
    if (isAnalyzing) {
      return `Analyzing thread ${currentThread} of ${totalThreads}...`;
    }
    
    return 'Ready to analyze';
  };
  
  // Get appropriate icon
  const getStatusIcon = () => {
    if (lastError) return <FaExclamationCircle className="text-danger" />;
    if (!isAnalyzing && analyzedThreads === totalThreads) return <FaCheckCircle className="text-success" />;
    if (isAnalyzing) return <FaSyncAlt className="text-primary fa-spin" />;
    return null;
  };
  
  return (
    <Card className="mb-4 analysis-progress-card">
      <Card.Header className="d-flex align-items-center">
        <span className="me-2">{getStatusIcon()}</span>
        <h5 className="mb-0">Analysis Progress</h5>
      </Card.Header>
      <Card.Body>
        <div className="progress-details mb-2">
          <div className="d-flex justify-content-between">
            <span>{getStatusMessage()}</span>
            <span className="progress-stats">
              {analyzedThreads} of {totalThreads} threads analyzed
              {isAnalyzing && elapsedSeconds > 0 && (
                <span className="ms-2 text-muted">
                  (Time elapsed: {formatTime(elapsedSeconds)})
                </span>
              )}
            </span>
          </div>
        </div>
        
        <ProgressBar 
          animated={isAnalyzing}
          now={progressPercent} 
          variant={getVariant()} 
          label={`${progressPercent}%`}
          style={{height: '25px'}}
        />
        
        {isAnalyzing && (
          <div className="thread-details mt-3">
            <small className="text-muted">
              Processing thread {currentThread} of {totalThreads}...
              {analyzedThreads > 0 && (
                <span> {analyzedThreads} thread(s) completed so far.</span>
              )}
            </small>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default AnalysisProgressBar;
