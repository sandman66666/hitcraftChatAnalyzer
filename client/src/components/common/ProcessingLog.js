import React, { useEffect, useRef, useState } from 'react';
import { Card } from 'react-bootstrap';
import { useAnalyzer } from '../../context/AnalyzerContext';
import './ProcessingLog.css';

const ProcessingLog = () => {
  const { state } = useAnalyzer();
  const { logs } = state;
  const logEndRef = useRef(null);
  
  // Auto-scroll to the bottom when new logs arrive
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);
  
  // Function to get log level class
  const getLogLevelClass = (level) => {
    switch (level) {
      case 'error':
        return 'text-danger';
      case 'warning':
        return 'text-warning';
      case 'success':
        return 'text-success';
      default:
        return 'text-info';
    }
  };
  
  return (
    <Card className="processing-log">
      <Card.Header>Processing Log</Card.Header>
      <Card.Body>
        <div className="log-container">
          {!logs || logs.length === 0 ? (
            <p className="text-muted text-center">No logs available yet.</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`log-entry ${getLogLevelClass(log.level)}`}>
                <span className="log-timestamp">{log.timestamp}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </Card.Body>
    </Card>
  );
};

export default ProcessingLog;
